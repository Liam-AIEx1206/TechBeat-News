# -*- coding: utf-8 -*-
"""
Slide export pipeline: ScenePlan → LLM gen SVG per slide → svg_to_pptx → .pptx

Endpoints:
  POST /gen-slide-one  — gen SVG cho 1 slide (dùng cho slidePreview + regen)
  POST /build-slides   — convert SVG list → PPTX file, trả SSE progress
"""
import json
import re
import shutil
import sys
import uuid
from pathlib import Path
from typing import AsyncGenerator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from routers.llm import chat_completions_with_fallback
from routers.compositions import ScenePayload, get_theme
from middleware.concurrency import limiter

import importlib.util as _ilu

def _load_lib(name: str):
    """Load a module from backend/lib/ by name, bypassing sys.path IDE issues."""
    spec = _ilu.spec_from_file_location(
        name,
        Path(__file__).resolve().parent.parent / "lib" / f"{name}.py",
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot find lib/{name}.py")
    mod = _ilu.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod

def _load_lib_pkg(name: str):
    """Load a package from backend/lib/<name>/__init__.py."""
    pkg_dir = Path(__file__).resolve().parent.parent / "lib" / name
    spec = _ilu.spec_from_file_location(
        name,
        pkg_dir / "__init__.py",
        submodule_search_locations=[str(pkg_dir)],
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot find lib/{name}/__init__.py")
    import sys as _sys
    mod = _ilu.module_from_spec(spec)
    _sys.modules[name] = mod  # register so intra-package imports work
    # also register all sub-modules so relative imports inside the package resolve
    _LIB_DIR2 = str(pkg_dir.parent)
    if _LIB_DIR2 not in _sys.path:
        _sys.path.insert(0, _LIB_DIR2)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod

router = APIRouter()

# ── project root helper (mirrors build.py) ────────────────────────────────────
def _get_project_root(session_id: str | None = None) -> Path:
    import os
    base = os.getenv("HYPERFRAMES_PROJECT") or str(
        Path(__file__).resolve().parent.parent.parent / "my-video"
    )
    root = Path(base)
    if session_id:
        return root / "sessions" / session_id
    return root

def sse(data: dict) -> str:
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"

# ── SVG slide prompt ──────────────────────────────────────────────────────────

_SVG_SYSTEM = """\
You are an expert presentation designer. Output ONE complete, publication-quality SVG slide.

═══════════ CANVAS ═══════════
width="1280" height="720" viewBox="0 0 1280 720"  ← EXACT, non-negotiable (Canva 16:9)

═══════════ TECHNICAL RULES (HARD) ═══════════
• All coordinates absolute (x, y, width, height) — NO percentages
• Colors: HEX only. Transparency = fill-opacity / stroke-opacity (NEVER rgba or fill="rgba(...)")
• Fonts: inline style only — NO <style>, NO class, NO @font-face
• Font stack MUST end with: Arial, Helvetica, sans-serif
• NO <foreignObject>, NO <use href="...">, NO <mask>, NO <script>, NO <animate>
• NO HTML entities (&nbsp; &mdash; etc.) — use raw Unicode or XML entities (&amp; &lt; &gt;)
• clip-path allowed ONLY on <image> elements
• Every linearGradient / radialGradient MUST be defined inside <defs>
• filter (shadow) MUST be defined inside <defs>
• One logical text line = ONE <text> + multiple <tspan> children (NEVER adjacent <text> for same line)
• Wrap related elements in <g id="..."> groups (3–8 top-level groups per slide)
• SVG must be completely self-contained and valid XML

═══════════ TYPOGRAPHY RAMP ═══════════
body = 28px  (base unit)
  footnote/label  : 16px   (0.57× body)
  annotation      : 20px   (0.71×)
  body text       : 28px   (1.00×)
  subtitle/lead   : 36px   (1.28×)
  section title   : 44px   (1.57×)
  slide title     : 56px   (2.00×)
  hero/cover      : 80–96px (2.8–3.4×)
line-height: 1.45 for dense blocks, 1.7 for large-type/breathing blocks
NEVER shrink below 20px. Widen/heighten card to fit — don't shrink the font.
Lift key numbers/contrasts with <tspan fill="ACCENT" font-weight="bold">

═══════════ SHADOW RECIPE ═══════════
Use ONLY when element genuinely floats above background. Max 2 tiers:
  resting  → stdDeviation="8" dy="4" flood-opacity="0.08"
  raised   → stdDeviation="14" dy="8" flood-opacity="0.16"
Flat peer-grid cards get NO shadow. Dark BG: skip shadow (invisible anyway).

Standard shadow <defs> block:
<defs>
  <filter id="sh" x="-15%" y="-15%" width="140%" height="140%">
    <feGaussianBlur in="SourceAlpha" stdDeviation="10"/>
    <feOffset dx="0" dy="5" result="ob"/>
    <feFlood flood-color="#000000" flood-opacity="0.12" result="sc"/>
    <feComposite in="sc" in2="ob" operator="in" result="s"/>
    <feMerge><feMergeNode in="s"/><feMergeNode in="SourceGraphic"/></feMerge>
  </filter>
</defs>

═══════════ SPACING & LAYOUT ═══════════
Safe margins: left/right 80px, top 60px, bottom 50px → content area 1120×610
Card padding: 32–48px inside; card radius: 16–24px
Column gutters: 24px for 2-col, 20px for 3-col, 16px for 4-col
Proximity: group related elements with tight spacing; separate unrelated groups

═══════════ OUTPUT ═══════════
Return ONLY the raw SVG code — start with <svg and end with </svg>.
NO markdown fences, NO explanation, NO comments outside the SVG.
"""

# 4 layout templates, rotated by slide index
_LAYOUT_TEMPLATES = [
    # 0 = HERO COVER / CHAPTER OPENER
    """LAYOUT: HERO / ANCHOR PAGE
- Full-bleed gradient background covering entire canvas
- Large centered title (80–96px, bold, white or TEXT1)
- Subtitle or lead line below (36px, TEXT2, lighter weight)
- Decorative accent bar or geometric shape (60–80px tall, full-width strip OR diagonal stripe) in ACCENT color
- Slide number badge bottom-right, small footnote label top-left
- NO bullet points — this is an impact page with breathing room
- Optional: large translucent ghost number or abstract shape in background""",

    # 1 = CONTENT WITH VISUAL WEIGHT
    """LAYOUT: CONTENT CARD GRID
- Dark header bar (60–72px tall) spanning full width with ACCENT left border (8px), contains slide title (44px bold)
- Body area split into 2 or 3 equal cards side by side
- Each card: rounded rect (rx=20), subtle fill (BG2 or slightly lighter than BG), raised shadow on hover card
- Inside each card: accent icon placeholder (48×48 circle or square in ACCENT color, top), bold number or short label (56px ACCENT), 2–3 lines body text (28px TEXT2)
- Accent horizontal rule (3px, ACCENT) separating header from body
- Footer: slide counter + deck title, 16px, TEXT2""",

    # 2 = DATA / STATS SPOTLIGHT
    """LAYOUT: STATS SPOTLIGHT
- Split layout: LEFT 55% = main narrative, RIGHT 45% = visual stat panel
- Left: section title (44px), body paragraphs (28px, 1.45 line-height), ACCENT accent bar left edge
- Right panel: dark card (BG2, rx=24, shadow), 1–3 large KPI numbers (80–96px, ACCENT bold), small labels below each (20px, TEXT2)
- Key numbers/percentages highlighted with <tspan fill="ACCENT" font-weight="bold"> inline
- Horizontal gradient divider between left and right
- Footer strip with slide meta""",

    # 3 = LIST / NARRATIVE
    """LAYOUT: STRUCTURED LIST
- Header zone (top 130px): title (56px bold, TEXT1) + subtitle (28px, TEXT2), left-aligned with 80px margin
- Accent bar: full-width rect (4px tall, ACCENT) below header zone
- Body: 3–5 items, each as a row with:
    • Colored circle or square bullet (24px, ACCENT, left margin 80px)
    • Item label (32px, bold, TEXT1) + short description (24px, TEXT2) on same row or below
    • Light separator line between items (1px, 8% opacity)
- Keep generous vertical spacing (min 28px between rows)
- Optional right-side decorative vertical bar (ACCENT2, 4px wide, 80% height)
- Slide number bottom-right""",
]


def _build_svg_prompt(scene: "ScenePayload", theme_id: str | None, slide_num: int, total_slides: int) -> str:
    t = get_theme(theme_id)

    # Choose layout: slide 1 (or last) gets HERO; others rotate 1→2→3→1→2→3
    if slide_num == 1 or slide_num == total_slides:
        layout = _LAYOUT_TEMPLATES[0]
    else:
        layout = _LAYOUT_TEMPLATES[1 + ((slide_num - 2) % 3)]

    # Parse narration into concise bullet points
    sentences = [s.strip() for s in re.split(r'[.。!?！？\n]', scene.narration) if len(s.strip()) > 10]
    bullets = "\n".join(f"  • {s}" for s in sentences[:5])

    return f"""=== SLIDE {slide_num} of {total_slides} ===

TITLE: {scene.title}

CONTENT BULLETS:
{bullets}

VISUAL DESCRIPTION: {scene.visualDescription}

=== COLOR PALETTE (USE ONLY THESE HEX VALUES) ===
BG (background):        {t['bg']}
BG2 (card/surface):     {t['bg2']}
ACCENT (primary):       {t['accent']}
ACCENT2 (secondary):    {t['accent2']}
ACCENT3 (tertiary):     {t['accent3']}
TEXT1 (heading):        {t['text1']}
TEXT2 (body/muted):     {t['text2']}
STYLE VIBE:             {t['vibe']}

=== REQUIRED LAYOUT FOR THIS SLIDE ===
{layout}

=== SLIDE CONTEXT ===
Deck title: {scene.title if slide_num == 1 else "(see title above)"}
Slide {slide_num} of {total_slides} — {"Opening slide" if slide_num == 1 else "Closing slide" if slide_num == total_slides else "Content slide"}

Now generate the complete SVG (1280×720). Return ONLY raw SVG, no explanation."""


# ── /gen-slide-one ────────────────────────────────────────────────────────────

class GenSlideOneRequest(BaseModel):
    title: str
    scenes: list[ScenePayload]
    totalDuration: float
    theme: str | None = None
    sceneIndex: int          # 0-based
    sessionId: str | None = None


@router.post("/gen-slide-one")
async def gen_slide_one(body: GenSlideOneRequest):
    """Gen SVG cho 1 slide. Trả JSON {svg, sceneIndex, provider, model}."""
    if body.sceneIndex < 0 or body.sceneIndex >= len(body.scenes):
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="sceneIndex out of range")

    scene = body.scenes[body.sceneIndex]
    total = len(body.scenes)
    prompt = _build_svg_prompt(scene, body.theme, body.sceneIndex + 1, total)

    async with limiter._llm_sem:
        def _kwargs(_provider: str) -> dict:
            return {
                "messages": [
                    {"role": "system", "content": _SVG_SYSTEM},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.6,
                "max_tokens": 4000,
                "stream": False,
            }
        resp, provider, model = await chat_completions_with_fallback(
            model_kind="composition", kwargs_factory=_kwargs
        )

    raw: str = (resp.choices[0].message.content or "")  # type: ignore[union-attr]
    svg = _extract_svg(raw)

    return {"svg": svg, "sceneIndex": body.sceneIndex, "provider": provider, "model": model}


def _extract_svg(raw: str) -> str:
    """Extract SVG từ response LLM (có thể bọc trong markdown)."""
    raw = re.sub(r"```(?:svg|xml)?\s*", "", raw).strip()
    raw = re.sub(r"```\s*$", "", raw).strip()
    m = re.search(r"(<svg[\s\S]*?</svg>)", raw, re.IGNORECASE)
    if m:
        return m.group(1).strip()
    if raw.lstrip().startswith("<svg"):
        return raw.strip()
    return raw.strip()


# ── /build-slides ─────────────────────────────────────────────────────────────

class BuildSlidesRequest(BaseModel):
    title: str
    scenes: list[ScenePayload]
    svgs: list[str]          # SVG string mỗi slide (index khớp với scenes)
    theme: str | None = None
    sessionId: str | None = None
    slideFormat: str = "pt169"  # canvas format cho pptx_builder


async def _build_slides_stream(req: BuildSlidesRequest) -> AsyncGenerator[str, None]:
    session_id = req.sessionId or uuid.uuid4().hex[:8]
    project_root = _get_project_root(session_id)
    slides_dir = project_root / "slides"
    svg_dir = slides_dir / "svg"
    svg_dir.mkdir(parents=True, exist_ok=True)

    total = len(req.svgs)
    yield sse({"type": "status", "message": f"Chuẩn bị {total} slide SVG..."})

    # 1. Ghi SVG files ra đĩa
    svg_paths: list[Path] = []
    for i, svg_str in enumerate(req.svgs):
        if not svg_str or not svg_str.strip():
            yield sse({"type": "slide_error", "index": i,
                       "message": f"Slide {i+1}: SVG rỗng — hãy regen slide này trước khi xuất."})
            return
        svg_path = svg_dir / f"slide_{i+1:02d}.svg"
        svg_path.write_text(svg_str, encoding="utf-8")
        svg_paths.append(svg_path)
    yield sse({"type": "status", "message": "Đang xử lý SVG (finalize)..."})

    # 2. Finalize SVG (flatten tspan, fix rounded rects)
    try:
        from finalize_svg import process_flatten_text, process_rounded_rect  # type: ignore[import]
        for svg_path in svg_paths:
            process_flatten_text(svg_path)
            process_rounded_rect(svg_path)
    except Exception as e:
        yield sse({"type": "warning", "message": f"finalize_svg bỏ qua: {e}"})

    yield sse({"type": "status", "message": "Đang convert SVG → PPTX native shapes..."})

    # 3. Convert sang PPTX
    safe_title = re.sub(r'[\\/:*?"<>|]', "_", req.title)[:60]
    pptx_name = f"{safe_title}_{session_id[:6]}.pptx"
    pptx_path = slides_dir / pptx_name

    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))
        from svg_to_pptx import create_pptx_with_native_svg  # type: ignore[import]

        slide_notes = {
            (svg_dir / f"slide_{i+1:02d}.svg").name: req.scenes[i].narration
            for i in range(min(len(svg_paths), len(req.scenes)))
        }

        ok = create_pptx_with_native_svg(
            svg_files=svg_paths,
            output_path=pptx_path,
            canvas_format=req.slideFormat,
            use_native_shapes=True,
            transition="fade",
            transition_duration=0.4,
            notes=slide_notes,
            verbose=False,
        )
        if not ok:
            yield sse({"type": "error", "message": "svg_to_pptx trả về False — xem logs server."})
            return
    except Exception as e:
        yield sse({"type": "error", "message": f"Lỗi convert PPTX: {e}"})
        return

    yield sse({"type": "status", "message": "Đang lưu file..."})

    # 4. Copy ra global slides dir (như build.py copy renders ra global)
    global_slides_dir = _get_project_root() / "slides"
    global_slides_dir.mkdir(parents=True, exist_ok=True)
    dest_path = global_slides_dir / pptx_name
    shutil.copy2(pptx_path, dest_path)

    pptx_url = f"/slides/{pptx_name}"
    file_size_mb = round(dest_path.stat().st_size / 1_048_576, 2)
    yield sse({
        "type": "done",
        "pptxUrl": pptx_url,
        "pptxPath": str(dest_path),
        "fileSize": file_size_mb,
        "totalSlides": total,
    })


@router.post("/build-slides")
async def build_slides(body: BuildSlidesRequest):
    return StreamingResponse(
        _build_slides_stream(body),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
