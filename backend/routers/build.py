import asyncio
import json
import os
import re
from pathlib import Path

import httpx
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from routers.compositions import (
    CompositionRequest,
    ScenePayload,
    get_project_root,
    stream_composition_events,
)

router = APIRouter()


def sse(data: dict) -> str:
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


# -------- TTS via ElevenLabs (primary) + gTTS (fallback) --------

ELEVENLABS_API = "https://api.elevenlabs.io/v1/text-to-speech"
# Default Vietnamese-capable voice — Adam (multilingual). User can override via env.
DEFAULT_ELEVEN_VOICE_ID = "pNInz6obpgDQGcFmaJgB"


async def _elevenlabs_to_wav(text: str, target: Path, voice_id: str | None = None) -> bool:
    """Try ElevenLabs TTS → wav. Returns True on success, False to fall back."""
    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        return False

    voice_id = voice_id or os.getenv("ELEVENLABS_VOICE_ID", DEFAULT_ELEVEN_VOICE_ID)
    model_id = os.getenv("ELEVENLABS_MODEL_ID", "eleven_multilingual_v2")

    url = f"{ELEVENLABS_API}/{voice_id}"
    payload = {
        "text": text,
        "model_id": model_id,
        "voice_settings": {
            "stability": 0.45,
            "similarity_boost": 0.75,
            "style": 0.30,
            "use_speaker_boost": True,
        },
    }
    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg",
    }

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(url, json=payload, headers=headers)
            if resp.status_code != 200:
                print(f"[tts] ElevenLabs HTTP {resp.status_code}: {resp.text[:200]}")
                return False
            mp3_bytes = resp.content
    except Exception as e:
        print(f"[tts] ElevenLabs request failed: {e}")
        return False

    # Convert mp3 → wav for HyperFrames
    try:
        from pydub import AudioSegment
        from io import BytesIO
        seg = AudioSegment.from_file(BytesIO(mp3_bytes), format="mp3")
        await asyncio.to_thread(seg.export, str(target), format="wav")
        return True
    except Exception as e:
        print(f"[tts] mp3→wav conversion failed, writing raw mp3: {e}")
        target.write_bytes(mp3_bytes)
        return True


def _gtts_to_wav_sync(text: str, lang: str, target: Path) -> None:
    """Run gTTS + mp3->wav conversion in a worker thread."""
    from gtts import gTTS
    from io import BytesIO

    mp3_buf = BytesIO()
    gTTS(text=text, lang=lang, slow=False).write_to_fp(mp3_buf)
    mp3_buf.seek(0)

    try:
        from pydub import AudioSegment
        seg = AudioSegment.from_file(mp3_buf, format="mp3")
        seg.export(str(target), format="wav")
    except Exception:
        # Fallback: keep mp3, just rename — HyperFrames audio tag accepts both
        target.write_bytes(mp3_buf.getvalue())


async def synthesize_tts(text: str, target: Path, voice_id: str | None = None) -> str:
    """
    Synthesize speech for `text` to `target`.
    Order: ElevenLabs (if ELEVENLABS_API_KEY set) → gTTS fallback.
    Returns the engine name actually used ('elevenlabs' or 'gtts').
    """
    if await _elevenlabs_to_wav(text, target, voice_id=voice_id):
        return "elevenlabs"

    lang = os.getenv("TTS_LANG", "vi")
    await asyncio.to_thread(_gtts_to_wav_sync, text, lang, target)
    return "gtts"


def get_audio_duration_s(path: Path) -> float:
    """Return duration in seconds of a wav/mp3 file. Falls back to 0 on error."""
    try:
        from pydub import AudioSegment
        seg = AudioSegment.from_file(str(path))
        return len(seg) / 1000.0
    except Exception:
        return 0.0


def patch_html_timing(
    html: str, 
    durations: list[float], 
    scene_titles: list[str] | None = None,
    scene_narrations: list[str] | None = None
) -> str:
    """
    Sync HTML timing to actual TTS audio lengths:
    - Strips the LLM-authored GSAP timeline so HyperFrames doesn't capture a
      reference to a timeline built on the (wrong) estimated durations.
    - Patches data-start / data-duration on each <audio id="vN"> tag
    - Embeds scene title as data-title on each <audio> for fallback rendering
    - Patches root data-duration
    - Injects a fresh <script> that builds the SOLE GSAP timeline using actual
      audio durations and registers it on window.__timelines.
    Each scene gets ceil(audio_duration) seconds + 1s tail for breathing room.
    """
    import math

    int_durs = [max(1, math.ceil(d) + 1) for d in durations]  # +1s buffer per scene
    starts: list[int] = []
    cursor = 0
    for d in int_durs:
        starts.append(cursor)
        cursor += d
    total = cursor

    # --- 1. Strip ALL <script> blocks that author a GSAP timeline ---
    # The LLM consistently builds a timeline based on its estimated scene
    # durations. HyperFrames captures the first registered timeline, so even
    # if we kill it client-side later, the render still uses the LLM's wrong
    # timing. Removing the original script entirely is the only reliable fix.
    def _is_timeline_script(body: str) -> bool:
        return ("gsap.timeline" in body or "GSAP" in body.upper() and "timeline" in body) \
               and ("__timelines" in body or "tl.to" in body or "tl.set" in body or "tl.from" in body)

    def _strip_timeline_scripts(s: str) -> str:
        out = []
        i = 0
        while True:
            m = re.search(r"<script\b[^>]*>", s[i:], flags=re.IGNORECASE)
            if not m:
                out.append(s[i:])
                break
            tag_start = i + m.start()
            tag_end = i + m.end()
            close = re.search(r"</script\s*>", s[tag_end:], flags=re.IGNORECASE)
            if not close:
                out.append(s[i:])
                break
            body_end = tag_end + close.start()
            block_end = tag_end + close.end()
            tag_open = s[tag_start:tag_end]
            body = s[tag_end:body_end]

            # ALWAYS preserve content between previous cursor and this script tag
            out.append(s[i:tag_start])

            # Keep external <script src="..."> (GSAP CDN) and any non-timeline script
            if re.search(r'\bsrc\s*=', tag_open, flags=re.IGNORECASE) or not _is_timeline_script(body):
                out.append(s[tag_start:block_end])
            # else: drop this <script>...</script> block (don't append it)

            i = block_end
        return "".join(out)

    html = _strip_timeline_scripts(html)

    # --- 2. Patch <audio> tags ---
    for i, (start, dur) in enumerate(zip(starts, int_durs)):
        n = i + 1
        html = re.sub(
            rf'(<audio\s[^>]*id=["\']v{n}["\'][^>]*?)data-start=["\'][^"\']*["\']([^>]*?)data-duration=["\'][^"\']*["\']',
            rf'\g<1>data-start="{start}"\2data-duration="{dur}"',
            html,
        )
        html = re.sub(
            rf'(<audio\s[^>]*id=["\']v{n}["\'][^>]*?)data-duration=["\'][^"\']*["\']([^>]*?)data-start=["\'][^"\']*["\']',
            rf'\g<1>data-duration="{dur}"\2data-start="{start}"',
            html,
        )

        # Add data-title for fallback placeholder rendering
        if scene_titles and i < len(scene_titles):
            safe_title = scene_titles[i].replace('"', '&quot;')
            # Only add if not already present
            if not re.search(rf'<audio\s[^>]*id=["\']v{n}["\'][^>]*data-title=', html):
                html = re.sub(
                    rf'(<audio\s[^>]*id=["\']v{n}["\'])',
                    rf'\1 data-title="{safe_title}"',
                    html,
                )

    # --- 3. Patch root data-duration ---
    html = re.sub(
        r'(id=["\']root["\'][^>]*?)data-duration=["\'][^"\']*["\']',
        rf'\1data-duration="{total}"',
        html,
    )
    html = re.sub(
        r'(data-composition-id=["\']main["\'][^>]*?)data-duration=["\'][^"\']*["\']',
        rf'\1data-duration="{total}"',
        html,
    )

    # --- 4. Inject SOLE timeline that uses actual TTS durations ---
    starts_js = ", ".join(str(s) for s in starts)
    durs_js = ", ".join(str(d) for d in int_durs)
    actual_durs_js = ", ".join(f"{d:.3f}" for d in durations)
    
    scene_narrations = scene_narrations or []
    safe_narrations = []
    for narration in scene_narrations:
        clean = narration.replace('\\', '\\\\').replace('"', '\\"').replace('\n', ' ')
        safe_narrations.append(clean)
    narrations_js = ", ".join(f'"{n}"' for n in safe_narrations)

    inject = f"""
<script>
// Sole timeline injected by TechBeat build pipeline.
// The LLM's original timeline script has been stripped server-side so this
// is the ONLY timeline registered on window.__timelines["main"].
(function() {{
  var starts = [{starts_js}];
  var durs   = [{durs_js}];
  var actualDurs = [{actual_durs_js}];
  var narrations = [{narrations_js}];
  var total  = {total};

  function ensureScenes() {{
    var root = document.getElementById("root");
    if (!root) return;
    for (var i = 0; i < starts.length; i++) {{
      var n = i + 1;
      if (document.getElementById("scene" + n)) continue;
      var ph = document.createElement("div");
      ph.id = "scene" + n;
      ph.className = "scene scene-fallback";
      ph.style.cssText = "position:absolute;inset:0;opacity:0;visibility:hidden;display:flex;align-items:center;justify-content:center;background:linear-gradient(135deg,var(--bg,#08080f),var(--bg2,#0f0f1a));";
      var audio = document.querySelector("audio#v" + n);
      var title = audio ? (audio.getAttribute("data-title") || "") : "";
      ph.innerHTML = '<div style="text-align:center;padding:80px;max-width:1400px;">' +
        '<div style="font-size:13px;font-weight:800;letter-spacing:.18em;text-transform:uppercase;color:var(--accent,#f97316);margin-bottom:24px;">Phân cảnh ' + n + '</div>' +
        '<div style="font-size:clamp(3rem,5vw,5rem);font-weight:900;line-height:1.1;letter-spacing:-.03em;color:var(--text1,#f5f3ff);">' + (title || ("Nội dung " + n)) + '</div>' +
      '</div>';
      root.appendChild(ph);
    }}
  }}

  function ensureSubtitles() {{
    var root = document.getElementById("root");
    if (!root) return;
    if (document.getElementById("techbeat-subtitles")) return;
    
    var subContainer = document.createElement("div");
    subContainer.id = "techbeat-subtitles";
    subContainer.className = "techbeat-subtitles";
    
    for (var i = 0; i < starts.length; i++) {{
      var n = i + 1;
      var text = narrations[i] || "";
      var subScene = document.createElement("div");
      subScene.id = "sub-scene" + n;
      subScene.className = "sub-scene";
      subScene.style.cssText = "display: none; opacity: 0;";
      
      var words = text.split(/\\s+/).filter(Boolean);
      for (var j = 0; j < words.length; j++) {{
        var wordSpan = document.createElement("span");
        wordSpan.className = "word sub-w-" + j;
        wordSpan.innerText = words[j];
        subScene.appendChild(wordSpan);
      }}
      subContainer.appendChild(subScene);
    }}
    root.appendChild(subContainer);
  }}

  function buildTimeline() {{
    if (!window.gsap) return;
    ensureScenes();
    ensureSubtitles();

    // Reset every scene's interior — LLM may have authored opacity:0 inline
    // styles to support its own (now-stripped) tl.from() tweens. Clearing
    // them ensures our fade-ins don't animate "0 -> 0" no-ops.
    gsap.set(".scene *", {{ clearProps: "all", opacity: 1 }});
    // Hide scenes 2..N via inline style. Scene1 keeps the CSS-level
    // opacity:1/visibility:visible fallback so the static initial frame
    // (captured before any timeline seek) renders correctly. The timeline
    // animates scene1 in at t=0 cleanly because tl.set() fires there too.
    gsap.utils.toArray(".scene").forEach(function(el, idx) {{
      if (idx === 0) return;
      gsap.set(el, {{ opacity: 0, visibility: "hidden", position: "absolute", inset: 0 }});
    }});
    gsap.set("#scene1", {{ position: "absolute", inset: 0 }});

    var tl = gsap.timeline({{ paused: true }});
    var lastIdx = starts.length - 1;

    function safeFrom(sel, vars, at) {{
      if (document.querySelector(sel)) tl.from(sel, vars, at);
    }}

    for (var i = 0; i < starts.length; i++) {{
      var n = i + 1;
      var s = starts[i];
      var d = durs[i];
      var sceneId = "#scene" + n;
      if (!document.querySelector(sceneId)) continue;
      var isLast = (i === lastIdx);

      // Scene 1 starts already visible (CSS fallback); only fade later scenes in.
      if (i === 0) {{
        tl.set(sceneId, {{ opacity: 1, visibility: "visible" }}, s);
      }} else {{
        tl.set(sceneId, {{ opacity: 0, visibility: "visible" }}, s);
        tl.to(sceneId,  {{ opacity: 1, duration: 0.6, ease: "power3.out" }}, s);
      }}

      // --- SUBTITLE TIMING ---
      var subSceneId = "#sub-scene" + n;
      if (document.getElementById("sub-scene" + n)) {{
        tl.set(subSceneId, {{ display: "flex", opacity: 1 }}, s);
        
        var words = document.querySelectorAll(subSceneId + " .word");
        var numWords = words.length;
        if (numWords > 0) {{
          var totalAudioTime = actualDurs[i] || d;
          var speechDur = totalAudioTime * 0.95; // use 95% of speech length to avoid trailing silence overlap
          var wordDur = speechDur / numWords;
          
          words.forEach(function(wordEl, wIdx) {{
            var wordStart = s + wIdx * wordDur;
            var wordEnd = wordStart + wordDur;
            
            // Highlight word
            tl.fromTo(wordEl,
              {{ color: "rgba(255, 255, 255, 0.75)", scale: 0.96, fontWeight: "300" }},
              {{ color: "#ff3b30", scale: 1.06, fontWeight: "600", duration: 0.12, immediateRender: false }},
              wordStart
            );
            // Revert word
            tl.to(wordEl,
              {{ color: "rgba(255, 255, 255, 0.75)", scale: 0.96, fontWeight: "300", duration: 0.12 }},
              wordEnd
            );
          }});
        }}
        
        // Hide subtitles at the end of the scene
        tl.to(subSceneId, {{ opacity: 0, duration: 0.3 }}, s + d - 0.3);
        tl.set(subSceneId, {{ display: "none" }}, s + d);
      }}

      safeFrom(sceneId + " [id$='-badge']",    {{ y: -20, opacity: 0, duration: 0.5, ease: "back.out(1.7)" }}, s + 0.3);
      safeFrom(sceneId + " [id$='-title']",    {{ y: 40,  opacity: 0, duration: 0.7, ease: "power4.out"   }}, s + 0.5);
      safeFrom(sceneId + " [id$='-subtitle']", {{ y: 30,  opacity: 0, duration: 0.6, ease: "power3.out"   }}, s + 0.7);
      safeFrom(sceneId + " [id$='-desc']",     {{ y: 20,  opacity: 0, duration: 0.5, ease: "power2.out"   }}, s + 0.9);
      if (document.querySelector(sceneId + " .visual-col > *")) {{
        tl.from(sceneId + " .visual-col > *", {{ scale: 0.9, opacity: 0, duration: 0.7, stagger: 0.15, ease: "back.out(1.5)" }}, s + 0.5);
      }}

      // Last scene stays visible until total — visuals never go black before audio ends.
      if (!isLast) {{
        tl.to(sceneId,  {{ opacity: 0, duration: 0.5, ease: "power2.in" }}, s + d - 0.6);
        tl.set(sceneId, {{ visibility: "hidden" }}, s + d);
      }}
    }}

    // Park timeline at t=0 so any pre-seek frame capture matches the
    // intended initial state instead of post-set hidden state.
    tl.progress(0).pause();

    // Register under every plausible key — HyperFrames doc says key matches
    // composition-id, but real-world runs vary. Cover "main" (our id) and
    // "root" (the doc default) to be safe.
    window.__timelines = window.__timelines || {{}};
    window.__timelines["main"] = tl;
    window.__timelines["root"] = tl;
  }}

  if (document.readyState === "loading") {{
    document.addEventListener("DOMContentLoaded", buildTimeline);
  }} else {{
    buildTimeline();
  }}
}})();
</script>
"""

    # Insert before </body>
    if "</body>" in html:
        html = html.replace("</body>", inject + "</body>")
    else:
        html += inject

    return html


# -------- Render via npx hyperframes render --------

async def run_render(project_root: Path, on_log) -> Path:
    """Spawn `npx hyperframes render` in a thread (avoids asyncio subprocess
    on Windows, which fails on uvicorn's selector loop)."""
    import subprocess
    import threading

    log_queue: asyncio.Queue[str | None] = asyncio.Queue()
    loop = asyncio.get_running_loop()

    def _runner() -> int:
        if os.name == "nt":
            cmd = ["npx.cmd", "--yes", "hyperframes@0.6.20", "render"]
            kwargs = {"shell": False}
        else:
            cmd = ["npx", "--yes", "hyperframes@0.6.20", "render"]
            kwargs = {}

        proc = subprocess.Popen(
            cmd,
            cwd=str(project_root),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=1,
            text=True,
            encoding="utf-8",
            errors="replace",
            **kwargs,
        )
        assert proc.stdout is not None
        for line in proc.stdout:
            line = line.rstrip()
            if line:
                asyncio.run_coroutine_threadsafe(log_queue.put(line), loop)
        rc = proc.wait()
        asyncio.run_coroutine_threadsafe(log_queue.put(None), loop)
        return rc

    runner_future = loop.run_in_executor(None, _runner)

    while True:
        item = await log_queue.get()
        if item is None:
            break
        await on_log(item)

    rc = await runner_future
    if rc != 0:
        raise RuntimeError(f"Render failed with exit code {rc}")

    renders_dir = project_root / "renders"
    if not renders_dir.exists():
        raise RuntimeError("Thư mục renders không tồn tại sau khi render")

    mp4s = sorted(renders_dir.glob("*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not mp4s:
        raise RuntimeError("Không tìm thấy file mp4 sau khi render")
    return mp4s[0]


# -------- Orchestrator --------

class BuildRequest(BaseModel):
    title: str
    scenes: list[ScenePayload]
    totalDuration: int
    projectPath: str | None = None
    skipTts: bool = False
    theme: str | None = None
    voiceId: str | None = None
    # Pre-built composition HTML from the html-preview stage. When present,
    # we skip the LLM composition stage entirely and go straight to save.
    compositionHtml: str | None = None


async def build_pipeline(req: BuildRequest):
    """Yield SSE events for the full pipeline."""

    project_root = get_project_root(req.projectPath)
    if not project_root.exists():
        yield sse({"type": "error", "message": f"Project path không tồn tại: {project_root}"})
        return

    assets_dir = project_root / "assets"
    assets_dir.mkdir(exist_ok=True)

    # ---- Stage 0: Download chosen illustration images ----
    scenes_with_assets: list[ScenePayload] = []
    async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as http:
        for s in req.scenes:
            asset_rel: str | None = None
            if s.imageUrl:
                ext = ".jpg"
                low = s.imageUrl.lower().split("?")[0]
                for cand in (".png", ".webp", ".jpeg", ".jpg", ".gif"):
                    if low.endswith(cand):
                        ext = ".jpg" if cand == ".jpeg" else cand
                        break
                local = assets_dir / f"scene{s.index + 1}{ext}"
                try:
                    resp = await http.get(
                        s.imageUrl,
                        headers={
                            "User-Agent": "Mozilla/5.0",
                            "Referer": "https://duckduckgo.com/",
                        },
                    )
                    if resp.status_code == 200 and resp.content:
                        local.write_bytes(resp.content)
                        asset_rel = f"assets/{local.name}"
                except Exception as e:
                    print(f"[build] Tải ảnh scene {s.index + 1} lỗi: {e}")
            scenes_with_assets.append(s.model_copy(update={"imageAsset": asset_rel}))

    # ---- Stage 1: Composition ----
    # If the html-preview stage already produced an HTML, skip the LLM call
    # entirely and reuse it. Saves the composition cost AND lets the user
    # see the exact same visual they previewed.
    if req.compositionHtml and "<html" in req.compositionHtml.lower():
        yield sse({"type": "stage", "stage": "composition", "status": "start", "message": "Sử dụng HTML từ bước xem trước..."})
        html = req.compositionHtml
        # Re-resolve image asset paths so that scenes whose images were
        # downloaded above get used. The HTML already has the correct
        # references because the preview stage rendered with the same
        # imageUrls — but we don't strictly need to splice anything here.
        yield sse({"type": "stage", "stage": "composition", "status": "done", "message": "Bỏ qua sinh HTML — dùng cache"})
    else:
        yield sse({"type": "stage", "stage": "composition", "status": "start", "message": "Đang sinh composition HTML..."})

        comp_req = CompositionRequest(
            title=req.title,
            scenes=scenes_with_assets,
            totalDuration=req.totalDuration,
            theme=req.theme,
        )
        html = ""
        char_count = 0
        async for ev in stream_composition_events(comp_req):
            if ev["type"] == "chunk":
                char_count += len(ev["text"])
                # Forward the actual text chunk so frontend can show LLM stream live
                yield sse({"type": "comp_chunk", "text": ev["text"]})
                if char_count % 500 < 50:
                    yield sse({"type": "stage", "stage": "composition", "status": "progress", "chars": char_count})
            elif ev["type"] == "done":
                html = ev["html"]
            elif ev["type"] == "error":
                yield sse({"type": "error", "stage": "composition", "message": ev["message"]})
                return

    if not html:
        yield sse({"type": "error", "stage": "composition", "message": "Không nhận được HTML"})
        return

    # ---- Stage 2: Save ----
    yield sse({"type": "stage", "stage": "save", "status": "start", "message": "Đang lưu index.html..."})
    target_html = project_root / "index.html"
    target_html.write_text(html, encoding="utf-8")
    yield sse({"type": "stage", "stage": "save", "status": "done", "path": str(target_html)})

    # ---- Stage 3: TTS ----
    if not req.skipTts:
        engines_used: dict[str, int] = {}
        yield sse({"type": "stage", "stage": "tts", "status": "start", "message": f"Đang sinh giọng đọc cho {len(req.scenes)} scene..."})
        wav_paths: list[Path] = []
        for s in req.scenes:
            wav_path = assets_dir / f"p{s.index + 1}.wav"
            wav_paths.append(wav_path)
            yield sse({"type": "stage", "stage": "tts", "status": "progress", "scene": s.index + 1, "of": len(req.scenes)})
            try:
                engine = await synthesize_tts(s.narration, wav_path, voice_id=req.voiceId)
                engines_used[engine] = engines_used.get(engine, 0) + 1
            except Exception as e:
                yield sse({"type": "error", "stage": "tts", "message": f"TTS scene {s.index + 1}: {e}"})
                return

        engine_summary = ", ".join(f"{k}×{v}" for k, v in engines_used.items())
        print(f"[tts] engines: {engine_summary}")

        # Measure actual audio durations and patch HTML timing
        durations = [get_audio_duration_s(p) for p in wav_paths]
        measured = [f"p{i+1}.wav={d:.1f}s" for i, d in enumerate(durations)]
        print(f"[tts] Measured durations: {', '.join(measured)}")
        scene_titles = [s.title for s in req.scenes]
        scene_narrations = [s.narration for s in req.scenes]
        html = patch_html_timing(html, durations, scene_titles, scene_narrations)
        target_html.write_text(html, encoding="utf-8")
        # Total composition duration after timing patch (ceil(d) + 1 buffer per scene)
        import math as _math
        actual_total = sum(max(1, _math.ceil(d) + 1) for d in durations)
        yield sse({
            "type": "stage", "stage": "tts", "status": "done",
            "engine": engine_summary,
            "actualDuration": actual_total,
            "audioDurations": [round(d, 1) for d in durations],
        })
    else:
        yield sse({"type": "stage", "stage": "tts", "status": "skipped"})

    # ---- Stage 4: Render ----
    yield sse({"type": "stage", "stage": "render", "status": "start", "message": "Đang render MP4..."})

    log_buffer: list[str] = []
    log_queue: asyncio.Queue[str] = asyncio.Queue()

    async def on_log(line: str):
        log_buffer.append(line)
        print(f"[render] {line}")
        await log_queue.put(line)

    render_task = asyncio.create_task(run_render(project_root, on_log))

    try:
        while not render_task.done() or not log_queue.empty():
            try:
                line = await asyncio.wait_for(log_queue.get(), timeout=1.5)
                yield sse({"type": "stage", "stage": "render", "status": "log", "line": line})
            except asyncio.TimeoutError:
                if render_task.done():
                    break
                continue
        mp4_path = await render_task
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        print(f"[render ERROR] {tb}")
        yield sse({
            "type": "error",
            "stage": "render",
            "message": f"{type(e).__name__}: {e}",
            "log": "\n".join(log_buffer[-30:]) + "\n--- traceback ---\n" + tb,
        })
        return

    rel_url = f"/renders/{mp4_path.name}"

    # Save to history automatically
    try:
        import datetime
        import shutil

        # 1. Ensure history directory structures
        history_dir = project_root / "history"
        htmls_dir = history_dir / "htmls"
        videos_dir = history_dir / "videos"
        history_dir.mkdir(exist_ok=True)
        htmls_dir.mkdir(exist_ok=True)
        videos_dir.mkdir(exist_ok=True)

        # 2. Generate timestamp
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        hist_html_name = f"html_{timestamp}.html"
        hist_video_name = f"video_{timestamp}.mp4"

        # 3. Write HTML file copy
        (htmls_dir / hist_html_name).write_text(html, encoding="utf-8")

        # 4. Copy MP4 video file
        shutil.copy2(mp4_path, videos_dir / hist_video_name)

        # 5. Append to db.json
        db_path = history_dir / "db.json"
        history_list = []
        if db_path.exists():
            try:
                history_list = json.loads(db_path.read_text(encoding="utf-8"))
            except Exception:
                history_list = []

        new_entry = {
            "id": timestamp,
            "title": req.title,
            "html_url": f"/static-history/htmls/{hist_html_name}",
            "video_url": f"/static-history/videos/{hist_video_name}",
            "duration": actual_total if ('actual_total' in locals() and actual_total) else req.totalDuration,
            "created_at": datetime.datetime.now().isoformat()
        }
        history_list.insert(0, new_entry) # newest first
        db_path.write_text(json.dumps(history_list, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"[history] Saved snapshot {timestamp} successfully!")
    except Exception as he:
        print(f"[history ERROR] Failed to save history snapshot: {he}")

    yield sse({
        "type": "done",
        "videoUrl": rel_url,
        "videoPath": str(mp4_path),
        "html": html,
    })


@router.post("/build-video")
async def build_video(body: BuildRequest):
    return StreamingResponse(
        build_pipeline(body),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
