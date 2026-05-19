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
from routers.llm import get_async_client

router = APIRouter()


def sse(data: dict) -> str:
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


# -------- TTS via gTTS (Google Translate, Vietnamese) --------

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


async def synthesize_tts(text: str, target: Path) -> None:
    lang = os.getenv("TTS_LANG", "vi")
    await asyncio.to_thread(_gtts_to_wav_sync, text, lang, target)


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
    yield sse({"type": "stage", "stage": "composition", "status": "start", "message": "Đang sinh composition HTML..."})

    comp_req = CompositionRequest(title=req.title, scenes=scenes_with_assets, totalDuration=req.totalDuration)
    html = ""
    char_count = 0
    async for ev in stream_composition_events(comp_req):
        if ev["type"] == "chunk":
            char_count += len(ev["text"])
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
        yield sse({"type": "stage", "stage": "tts", "status": "start", "message": f"Đang sinh giọng đọc cho {len(req.scenes)} scene..."})
        for s in req.scenes:
            wav_path = assets_dir / f"p{s.index + 1}.wav"
            yield sse({"type": "stage", "stage": "tts", "status": "progress", "scene": s.index + 1, "of": len(req.scenes)})
            try:
                await synthesize_tts(s.narration, wav_path)
            except Exception as e:
                yield sse({"type": "error", "stage": "tts", "message": f"TTS scene {s.index + 1}: {e}"})
                return
        yield sse({"type": "stage", "stage": "tts", "status": "done"})
    else:
        yield sse({"type": "stage", "stage": "tts", "status": "skipped"})

    # ---- Stage 4: Render ----
    yield sse({"type": "stage", "stage": "render", "status": "start", "message": "Đang render MP4 (1-3 phút)..."})

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
