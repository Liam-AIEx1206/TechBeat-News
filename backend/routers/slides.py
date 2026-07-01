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

_SVG_SYSTEM = """Bạn là chuyên gia thiết kế slide trình chiếu. Nhiệm vụ: tạo 1 slide SVG hoàn chỉnh theo yêu cầu.

QUY TẮC SVG BẮT BUỘC:
- Kích thước cố định: width="1280" height="720" (16:9)
- Tất cả phần tử dùng absolute coordinates (x, y, width, height — KHÔNG dùng %)
- Nền slide: rect x="0" y="0" width="1280" height="720" fill=BG_COLOR
- Font chỉ dùng: Arial, Helvetica, sans-serif (cross-platform)
- Text tiếng Việt phải render đúng — dùng thẻ <text> với dominant-baseline="hanging"
- Không dùng <foreignObject>, không dùng HTML bên trong SVG
- Không dùng <use href="...">, không dùng external images (chỉ inline hoặc bỏ qua ảnh)
- SVG phải self-contained, không cần font download

CẤU TRÚC SLIDE:
1. Background: gradient hoặc solid, dùng màu BG từ theme
2. Header bar: rect màu ACCENT, cao ~80px, chứa số slide + tiêu đề
3. Body: nội dung chính — bullet points từ narration, bố cục rõ ràng
4. Accent elements: đường kẻ, viền, badge màu ACCENT2/ACCENT3
5. Footer: tên bài/nguồn, nhỏ và mờ

OUTPUT: Chỉ trả về code SVG thuần túy, bắt đầu bằng <svg và kết thúc bằng </svg>.
KHÔNG thêm markdown, KHÔNG thêm giải thích, KHÔNG bọc trong ```svg.
"""

def _build_svg_prompt(scene: ScenePayload, theme_id: str | None, slide_num: int, total_slides: int) -> str:
    t = get_theme(theme_id)
    bullets = "\n".join(
        f"  - {line.strip()}"
        for line in scene.narration.split(".")
        if line.strip()
    )
    return f"""Tạo slide {slide_num}/{total_slides} cho bài trình chiếu.

THEME: {t['name']}
Màu nền (BG): {t['bg']}
Màu nền phụ (BG2): {t['bg2']}
Màu accent chính (ACCENT): {t['accent']}
Màu accent phụ (ACCENT2): {t['accent2']}
Màu accent 3 (ACCENT3): {t['accent3']}
Màu text chính (TEXT1): {t['text1']}
Màu text phụ (TEXT2): {t['text2']}
Phong cách: {t['vibe']}

TIÊU ĐỀ SLIDE: {scene.title}

NỘI DUNG (narration để tóm thành bullet points):
{scene.narration}

BULLET POINTS GỢI Ý:
{bullets}

Tạo SVG 1280x720 đẹp, professional, thể hiện đúng theme {t['name']} với màu sắc trên.
"""

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

    raw = resp.choices[0].message.content or ""
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

    # 2. Finalize SVG (expand <use>, flatten tspan)
    try:
        from finalize_svg import finalize_svg_file  # type: ignore[import]
        for svg_path in svg_paths:
            finalize_svg_file(svg_path, svg_path)
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
            str((svg_dir / f"slide_{i+1:02d}.svg").name): req.scenes[i].narration
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
