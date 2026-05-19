import json
import re
from pathlib import Path
from typing import AsyncGenerator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from routers.llm import get_async_client, get_model

router = APIRouter()


COMPOSITION_PROMPT = """Bạn là chuyên gia tạo composition HyperFrames (HTML5 + GSAP). Nhiệm vụ: từ scene plan đã cho, sinh ra một file `index.html` HOÀN CHỈNH theo đúng tiêu chuẩn HyperFrames.

⚠️ NGÔN NGỮ BẮT BUỘC: TIẾNG VIỆT
- TẤT CẢ text hiển thị trên video (title, subtitle, badge, description, mock content) PHẢI tiếng Việt có dấu
- Giữ NGUYÊN VĂN narration/title/visualDescription từ scene plan, không dịch sang tiếng Anh
- Chỉ dùng tiếng Anh cho: tên class CSS, comment code, tên biến

QUY TẮC BẤT BIẾN (vi phạm = composition hỏng):

1. Cấu trúc root:
   <div id="root" data-composition-id="main" data-start="0" data-width="1920" data-height="1080" data-duration="{TOTAL}">

2. Mỗi scene là <div class="scene" id="sceneN"> với position:absolute, width 100%, height 100%, opacity 0, visibility hidden ban đầu.

3. KHÔNG dùng: setTimeout, setInterval, requestAnimationFrame, Date.now(), Math.random(), fetch ngoài. Tất cả animation phải qua GSAP timeline.

4. Timeline GSAP:
   - Phải `paused: true`
   - Phải đăng ký: `window.__timelines = window.__timelines || {}; window.__timelines["main"] = tl;`
   - Mỗi scene: tween vào (opacity 1 + visibility visible) ở thời điểm `start`, tween ra (opacity 0) ở `start + duration - 1`, set visibility hidden ở `start + duration`.

5. Audio narration cho mỗi scene (bắt buộc):
   <audio id="vN" src="assets/pN.wav" data-start="{start}" data-duration="{duration}" data-volume="1"></audio>
   Đặt sau cùng trong div root, ngay trước </div> đóng root.

6. Font: Be Vietnam Pro hoặc Inter (hỗ trợ dấu tiếng Việt) từ Google Fonts. GSAP qua CDN https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js

7. Style chủ đạo: NỀN CAM ẤM - background gradient từ #1a0f08 → #2d1810, accent màu #f97316 (cam đậm), #fb923c (cam sáng), #fdba74 (cam nhạt), #fff7ed (text). Glow effect màu cam (rgba(249, 115, 22, 0.15)).

8. Layout mỗi scene: grid 2 cột (info-col + visual-col), gap 80px, max-width 1600px, padding 60px.

9. Mỗi scene phải có: scene-badge ("Phần N" tiếng Việt), scene-title (h1 4.5rem tiếng Việt), scene-subtitle (h2 2.2rem màu cam tiếng Việt), scene-description (p 1.3rem tiếng Việt). Bên visual-col: NẾU scene có `IllustrationImage: assets/...` thì BẮT BUỘC dùng `<img src="assets/sceneN.jpg" class="scene-image" alt="">` làm phần tử chủ đạo (object-fit: cover, border-radius 24px, box-shadow cam, kích thước ~640x420), có thể bao quanh bằng badge/caption nhỏ tiếng Việt. NẾU không có image thì tạo mock visual đa dạng phù hợp nội dung scene.

10. Animation đa dạng: dùng các ease khác nhau (back.out, elastic.out, power3.out, power4.out), kết hợp scale/y/x/opacity, stagger các phần tử con.

OUTPUT: Trả về DUY NHẤT mã HTML hoàn chỉnh từ <!doctype html> đến </html>. KHÔNG markdown fence, KHÔNG giải thích, KHÔNG comment giới thiệu."""


class ScenePayload(BaseModel):
    id: str
    index: int
    title: str
    narration: str
    visualDescription: str
    duration: int
    imageQuery: str | None = None
    imageUrl: str | None = None
    imageAsset: str | None = None  # filled by build pipeline after download (e.g. "assets/scene1.jpg")


class CompositionRequest(BaseModel):
    title: str
    scenes: list[ScenePayload]
    totalDuration: int


def sse(data: dict) -> str:
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


def build_user_prompt(req: CompositionRequest) -> str:
    lines = [
        f"Tiêu đề video: {req.title}",
        f"Tổng thời lượng: {req.totalDuration} giây",
        f"Số scene: {len(req.scenes)}",
        "",
        "Danh sách scene (đã có start time tích luỹ):",
    ]
    cursor = 0
    for s in req.scenes:
        lines.append(
            f"\n[Scene {s.index + 1}] start={cursor}s, duration={s.duration}s, end={cursor + s.duration}s"
        )
        lines.append(f"  Title: {s.title}")
        lines.append(f"  Narration: {s.narration}")
        lines.append(f"  Visual: {s.visualDescription}")
        if s.imageQuery:
            lines.append(f"  ImageQuery: {s.imageQuery}")
        if s.imageAsset:
            lines.append(f"  IllustrationImage: {s.imageAsset}  ← BẮT BUỘC dùng <img src=\"{s.imageAsset}\"> trong visual-col")
        cursor += s.duration
    lines.append(
        f"\nSinh composition HTML hoàn chỉnh dài đúng {cursor} giây với {len(req.scenes)} scene như trên."
    )
    return "\n".join(lines)


def strip_fences(html: str) -> str:
    html = html.strip()
    if html.startswith("```"):
        html = re.sub(r"^```(?:html)?\s*", "", html)
        html = re.sub(r"\s*```\s*$", "", html)
    return html


async def stream_composition_events(req: CompositionRequest) -> AsyncGenerator[dict, None]:
    """Yield raw event dicts: {type:'chunk',text} | {type:'done',html} | {type:'error',message}"""
    try:
        client = get_async_client()
    except ValueError as e:
        yield {"type": "error", "message": str(e)}
        return

    full_text = ""
    try:
        prompt = build_user_prompt(req)
        stream = await client.chat.completions.create(
            model=get_model("composition"),
            messages=[
                {"role": "system", "content": COMPOSITION_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.6,
            max_tokens=32000,
            stream=True,
        )
        async for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            text = getattr(delta, "content", None)
            if text:
                full_text += text
                yield {"type": "chunk", "text": text}

        html = strip_fences(full_text)
        if "<html" not in html.lower():
            yield {"type": "error", "message": "Không tìm thấy HTML hợp lệ trong response"}
            return

        # Sanity check — must close </html> AND register on window.__timelines
        lower = html.lower()
        if "</html>" not in lower:
            yield {"type": "error", "message": "HTML bị cắt giữa chừng (thiếu </html>). Tăng max_tokens hoặc rút gọn scene plan."}
            return
        if "window.__timelines" not in html:
            yield {"type": "error", "message": "HTML thiếu window.__timelines registration — render sẽ ra video trống."}
            return

        yield {"type": "done", "html": html}
    except Exception as e:
        yield {"type": "error", "message": str(e)}


async def stream_composition(req: CompositionRequest):
    async for ev in stream_composition_events(req):
        yield sse(ev)


@router.post("/generate-composition")
async def generate_composition(body: CompositionRequest):
    return StreamingResponse(
        stream_composition(body),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


class SaveRequest(BaseModel):
    html: str
    projectPath: str | None = None


def get_project_root(override: str | None = None) -> Path:
    import os
    if override:
        return Path(override)
    env_path = os.getenv("HYPERFRAMES_PROJECT")
    if env_path:
        return Path(env_path)
    return Path(__file__).resolve().parents[2] / "my-video"


@router.post("/save-composition")
async def save_composition(body: SaveRequest):
    project_root = get_project_root(body.projectPath)
    if not project_root.exists():
        raise HTTPException(status_code=404, detail=f"Project path không tồn tại: {project_root}")

    target = project_root / "index.html"
    try:
        target.write_text(body.html, encoding="utf-8")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Không ghi được file: {e}")

    return {
        "saved": True,
        "path": str(target),
        "projectPath": str(project_root),
        "next": f'cd "{project_root}" && npm run dev',
    }
