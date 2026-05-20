import json
import re
from pathlib import Path
from typing import AsyncGenerator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from routers.llm import get_async_client, get_model

router = APIRouter()


# ─────────────────────────────  THEMES  ─────────────────────────────
# Mirror of app/types/scene.ts THEMES — keep in sync.

THEMES: dict[str, dict] = {
    "cyber-orange": {
        "name": "Cyber Orange",
        "bg": "#08080f", "bg2": "#0f0f1a", "surface": "#141420",
        "accent": "#f97316", "accent2": "#fb923c", "accent3": "#fbbf24",
        "text1": "#f5f3ff", "text2": "#a09db8",
        "vibe": "premium dark news broadcast với accent cam ấm áp, gradient amber, scan-lines tinh tế, không khí editorial cao cấp, ánh sáng nóng",
        "fx": "particle burst cam, scanline thưa, corner brackets, animated grid lines",
    },
    "neo-cyan": {
        "name": "Neo Cyan",
        "bg": "#03070d", "bg2": "#061018", "surface": "#0a1722",
        "accent": "#22d3ee", "accent2": "#67e8f9", "accent3": "#a5f3fc",
        "text1": "#ecfeff", "text2": "#7dd3fc",
        "vibe": "Tron-inspired neo cyan sci-fi với glow lines, holographic grids, neon edges và data-stream",
        "fx": "data stream chạy ngang, holographic wireframe grid, hexagon pattern, glitch RGB split nhẹ",
    },
    "violet-pulse": {
        "name": "Violet Pulse",
        "bg": "#0a0518", "bg2": "#120a28", "surface": "#1c1242",
        "accent": "#a855f7", "accent2": "#d946ef", "accent3": "#f0abfc",
        "text1": "#fdf4ff", "text2": "#c4b5fd",
        "vibe": "synthwave/vaporwave với gradient tím-magenta, sun-grid retrowave, glow pulses, neon outline",
        "fx": "perspective grid floor, neon sun horizon, chromatic aberration, glow text outline",
    },
    "matrix-green": {
        "name": "Matrix Green",
        "bg": "#020a04", "bg2": "#04130a", "surface": "#062815",
        "accent": "#22c55e", "accent2": "#4ade80", "accent3": "#86efac",
        "text1": "#f0fdf4", "text2": "#86efac",
        "vibe": "matrix hacker terminal với character rain, monospace typography, scanlines, CRT glow xanh",
        "fx": "matrix character rain (canvas hoặc CSS), CRT scanlines dày, terminal cursor blink, ASCII art accents",
    },
    "crimson-broadcast": {
        "name": "Crimson Broadcast",
        "bg": "#0a0303", "bg2": "#170808", "surface": "#241010",
        "accent": "#ef4444", "accent2": "#f87171", "accent3": "#fbbf24",
        "text1": "#fef2f2", "text2": "#fecaca",
        "vibe": "BREAKING NEWS đỏ-vàng, alert glow, urgent ticker, cảm giác cảnh báo tin nóng",
        "fx": "blinking BREAKING badge, ticker scrolling, alert pulse, urgent corner stripes",
    },
    "aurora-mint": {
        "name": "Aurora Mint",
        "bg": "#031410", "bg2": "#062420", "surface": "#0a3530",
        "accent": "#10b981", "accent2": "#34d399", "accent3": "#a7f3d0",
        "text1": "#ecfdf5", "text2": "#6ee7b7",
        "vibe": "aurora borealis xanh mint hiện đại, glassmorphism, soft glow, calm cao cấp",
        "fx": "aurora wave gradient drift, soft particle glow, glass card blur, breathing pulse",
    },
    "y2k-magenta": {
        "name": "Y2K Magenta",
        "bg": "#0d0410", "bg2": "#1a0825", "surface": "#27123a",
        "accent": "#ec4899", "accent2": "#f472b6", "accent3": "#fde047",
        "text1": "#fdf4ff", "text2": "#f9a8d4",
        "vibe": "Y2K aesthetic với chrome highlights, bubble shapes, magenta-yellow contrast, playful nhưng vẫn premium",
        "fx": "chrome reflection, bubble shapes floating, sparkle stars, holographic border",
    },
    "gold-editorial": {
        "name": "Gold Editorial",
        "bg": "#0a0805", "bg2": "#15110a", "surface": "#221c10",
        "accent": "#eab308", "accent2": "#facc15", "accent3": "#fde68a",
        "text1": "#fefce8", "text2": "#d6d3d1",
        "vibe": "luxury magazine editorial vàng champagne trên đen sang trọng, serif accents, fine-line dividers",
        "fx": "serif drop-cap, gold leaf shimmer, fine-line dividers, refined fade",
    },
}

DEFAULT_THEME = "cyber-orange"


def get_theme(theme_id: str | None) -> dict:
    return THEMES.get(theme_id or DEFAULT_THEME, THEMES[DEFAULT_THEME])


# ─────────────────────────────  PROMPT  ─────────────────────────────

def build_system_prompt(theme: dict) -> str:
    return f"""Bạn là chuyên gia tạo composition HyperFrames (HTML5 + GSAP) trình độ AWWWARDS — sáng tạo HTML cinematic, lung linh, gây WOW. Nhiệm vụ: từ scene plan đã cho, sinh ra một file `index.html` HOÀN CHỈNH với theme **{theme['name']}**.

⚠️ NGÔN NGỮ BẮT BUỘC: TIẾNG VIỆT
- TẤT CẢ text hiển thị trên video PHẢI tiếng Việt có dấu đầy đủ
- Giữ NGUYÊN VĂN narration/title/visualDescription từ scene plan
- Chỉ dùng tiếng Anh cho: tên class CSS, comment code, tên biến JS

═══════════════════════════════════════
QUY TẮC BẤT BIẾN (vi phạm = composition hỏng):
═══════════════════════════════════════

⚠️ SCENE COUNT BẮT BUỘC:
   PHẢI tạo ĐỦ chính xác N scene như scene plan (N được chỉ định trong user prompt).
   Mỗi scene PHẢI có id="sceneN" với N từ 1 đến tổng số scene.
   KHÔNG ĐƯỢC gộp 2 scene thành 1, KHÔNG ĐƯỢC bỏ scene cuối, KHÔNG ĐƯỢC tạo thiếu.
   Nếu user gửi 10 scene → output PHẢI có #scene1, #scene2, ..., #scene10 — đầy đủ 10 div riêng biệt.
   Mỗi scene phải có element con với id pattern: id="sN-title", id="sN-subtitle", id="sN-desc", id="sN-badge"
   (vd: scene 3 có #s3-title, #s3-subtitle, #s3-desc, #s3-badge)

1. ROOT STRUCTURE:
   <div id="root" data-composition-id="main" data-start="0" data-width="1920" data-height="1080" data-duration="{{TOTAL}}">

2. Mỗi scene: <div class="scene" id="sceneN"> — position:absolute, inset:0, opacity:0, visibility:hidden ban đầu.

3. KHÔNG dùng: setTimeout, setInterval, requestAnimationFrame, Date.now(), Math.random(), fetch. Tất cả animation qua GSAP timeline.

4. GSAP TIMELINE:
   - paused: true
   - Đăng ký: window.__timelines = window.__timelines || {{}}; window.__timelines["main"] = tl;
   - Mỗi scene: fade in tại `start`, fade out tại `start + duration - 1`, visibility hidden tại `start + duration`
   - KHÔNG dùng repeat: -1 (infinite). Nếu cần lặp idle anim, tính số lần dựa trên duration: `repeat: Math.floor(sceneDuration / cycleDuration) - 1`

5. AUDIO (bắt buộc, đặt cuối root trước </div>):
   <audio id="vN" src="assets/pN.wav" data-start="{{start}}" data-duration="{{duration}}" data-volume="1"></audio>

═══════════════════════════════════════
THEME: {theme['name'].upper()} — VIBE BẮT BUỘC
═══════════════════════════════════════

{theme['vibe']}

Ưu tiên đưa các yếu tố thị giác sau vào composition: {theme['fx']}.

6. FONTS — DUY NHẤT 2 family, KHÔNG dùng `inherit`, KHÔNG mix nhiều font display:
   - **Sans (UI/body/title)**: 'Inter' weights 300,400,500,600,700,800,900 — Google Fonts
   - **Mono (badge/code/data)**: 'JetBrains Mono' weights 400,600,800 — Google Fonts
   - Áp `font-family: 'Inter', system-ui, sans-serif` cho body. Áp `'JetBrains Mono', monospace` cho mono elements.
   - KHÔNG dùng Be Vietnam Pro, Orbitron, Audiowide, Space Grotesk, Georgia, Archivo Black, Bebas Neue, Helvetica, Futura, Playfair, Roboto, Montserrat, hay bất kỳ font nào khác. CHỈ Inter + JetBrains Mono.
   - KHÔNG hardcode `font-family: inherit` ở đâu — luôn ghi rõ Inter hoặc JetBrains Mono.
   - GSAP CDN: https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js

7. COLOR TOKENS — DÙNG CSS VARIABLES (hardcode vào :root):
   --bg: {theme['bg']}
   --bg2: {theme['bg2']}
   --surface: {theme['surface']}
   --accent: {theme['accent']}
   --accent2: {theme['accent2']}
   --accent3: {theme['accent3']}
   --text1: {theme['text1']}
   --text2: {theme['text2']}
   --glow: {theme['accent']}55
   Không hardcode hex khác — luôn dùng var(--xxx) trong styles.

═══════════════════════════════════════
DESIGN PRINCIPLES — LUNG LINH GRADE
═══════════════════════════════════════

8. BACKGROUND LAYER (áp dụng cho #root, multi-layer):
   - Layer 1 — Base: linear/radial gradient từ var(--bg) → var(--bg2)
   - Layer 2 — Glow orbs: 2-3 radial gradient blobs với var(--accent), opacity 0.06-0.12, kích thước 800-1400px, blur cao
   - Layer 3 — Pattern: dot grid HOẶC line grid HOẶC hexagon HOẶC noise SVG (chọn 1 phù hợp theme)
   - Layer 4 — Texture: SVG noise opacity 0.025 hoặc scanlines opacity 0.04
   - Layer 5 — Vignette: radial gradient từ trong suốt → rgba(0,0,0,0.6) ở rìa

9. SCENE LAYOUT — VARIETY (KHÔNG lặp lại layout giữa các scene):
   Chọn ngẫu nhiên 1 trong các pattern dưới cho mỗi scene:
   - SPLIT: Grid 2 cột 45/55, info trái + visual phải
   - CENTERED: 1 cột giữa, full-bleed visual phía sau
   - HERO-FULL: Title cực to chiếm 70% width, text nhỏ + visual ở góc
   - MAGAZINE: Grid 12 cột với asymmetric placement
   - QUOTE: Quotation mark khổng lồ + text italic + caption
   - DATA: Stats card lớn ở giữa, supporting text quanh
   - TIMELINE: Vertical với nodes + connecting lines
   - SCATTER: Cards floating ở các vị trí với rotation nhẹ

10. TYPOGRAPHY — DRAMATIC HIERARCHY:
    - Pretitle/Badge: 11-13px, mono, uppercase, letter-spacing 0.18em, accent2, padding 6px 14px, border-radius full, border 1px solid accent với background var(--surface)
    - Title chính: clamp(3.5rem, 6vw, 7rem), font-weight 900, line-height 1.0, letter-spacing -0.04em
    - Sub-title: 1.8-2.4rem, font-weight 700, accent2 hoặc text1
    - Body: 1.15-1.35rem, line-height 1.7, text2, max-width 560px
    - Caption: 0.85rem, mono, text2, uppercase letter-spacing 0.1em
    - Numbers (stats): clamp(5rem, 8vw, 9rem), font-weight 900, gradient text từ accent → accent3, font-feature-settings 'tnum'
    - Gradient text: background: linear-gradient(135deg, var(--accent), var(--accent2), var(--accent3)); -webkit-background-clip: text; -webkit-text-fill-color: transparent
    - Outline text (accent vibes): -webkit-text-stroke: 2px var(--accent); color: transparent;

11. VISUAL-COL CONTENT — RICHNESS BẮT BUỘC:

    A) NẾU có IllustrationImage (assets/sceneN.jpg):
       - .img-frame: position relative, border-radius 24px, overflow hidden, isolation isolate
       - <img>: width 100%, height auto (min 420px), object-fit cover
       - Multi-layer overlay:
         · Top fade: linear-gradient(to bottom, rgba(0,0,0,0.4) 0%, transparent 30%)
         · Bottom fade: linear-gradient(to top, rgba(0,0,0,0.85) 0%, transparent 60%)
         · Color tint: var(--accent) với mix-blend-mode multiply opacity 0.15
       - Glow border: box-shadow 0 0 0 1px var(--accent)55, 0 30px 80px -20px var(--accent), 0 0 100px -30px var(--accent)
       - Frame ornaments: 4 corner brackets (L-shaped), animated dash border, scan-line sweep
       - Caption pill: tiếng Việt, mono, ở góc dưới-trái, background blur, padding 8px 14px

    B) NẾU KHÔNG có ảnh — BẮT BUỘC tạo mock visual SÁNG TẠO RICHE — PHẢI ĐẦY ẶP NỘI DUNG, KHÔNG ĐƯỢC ĐỂ TRỐNG. Chọn 1-2 trong các pattern (kết hợp được):

       (B1) BIG STAT CARD — số liệu dramatic
            - Số hero: clamp(7rem,12vw,12rem), gradient text, font-weight 900
            - Suffix nhỏ ("triệu", "%", "x", "tỷ") font-weight 700, color text2
            - Caption mô tả 2-3 dòng bên dưới
            - Mini bars/progress bars để minh họa
            - Border glow + corner brackets

       (B2) CODE/TERMINAL BLOCK
            - Window chrome (3 dots đỏ-vàng-xanh)
            - 5-10 dòng code/log với syntax highlighting (string=accent2, keyword=accent3, comment=text2)
            - Cursor blink ở dòng cuối
            - Monospace font

       (B3) FEATURE GRID — 2x2 hoặc 3x2 cards
            - Mỗi card: icon emoji lớn + tiêu đề nhỏ + mô tả
            - Hover-style với border glow
            - Stagger animation khi enter

       (B4) COMPARISON / DUAL COLUMN
            - 2 cột "TRƯỚC vs SAU" hoặc "X vs Y"
            - Check ✓ / Cross ✗ icons với màu accent / red
            - Divider giữa với gradient line

       (B5) TIMELINE
            - Vertical line gradient với 4-6 dots
            - Mỗi dot có pulse ring animation
            - Year/label bên trái, mô tả bên phải

       (B6) QUOTE BLOCK
            - Quotation mark khổng lồ (font-size 12rem, opacity 0.15, accent)
            - Text italic, font-size 2rem, max-width 600px
            - Attribution với line accent

       (B7) DATA VIZ — animated bar chart hoặc sparkline
            - SVG path với stroke-dasharray để vẽ dần
            - Bars dùng GSAP để cao dần
            - Labels và values

       (B8) FACT CARDS GRID
            - 3-4 cards xếp tầng/scatter với rotation nhẹ (-2deg, +1deg)
            - Mỗi card chứa 1 fact ngắn

       (B9) HEADLINE BANNER (đặc biệt cho theme broadcast)
            - "BREAKING" badge
            - Headline lớn
            - Source/timestamp

       (B10) NEURAL NET / KNOWLEDGE GRAPH (cyber themes)
             - SVG nodes + edges
             - Animated pulse along edges
             - Tag labels

       Common cho mọi pattern:
       - Background: linear-gradient từ var(--surface) → semi-transparent
       - Border: 1px solid var(--accent)33
       - Border-radius: 20-32px
       - Backdrop-filter: blur(12px)
       - Inner glow: inset 0 0 60px rgba(255,255,255,0.02)
       - Outer glow: 0 30px 80px -20px var(--glow)
       - Corner brackets ở 4 góc
       - At least one animated element (pulse/shimmer/sweep)

12. ANIMATION SYSTEM — CINEMATIC GSAP TIMELINE:
    Mỗi scene có ít nhất 8-12 tween khác nhau (KHÔNG kể decorative):

    SCENE ENTER (0.0s → 1.5s sau start):
    - Scene container: opacity 0→1, duration 0.6s, ease "power3.out"
    - Background overlay reveal: clip-path inset(0 100% 0 0) → inset(0 0% 0 0), 1s, ease "power4.inOut"
    - Badge: y:-30→0, opacity 0→1, scale 0.8→1, 0.5s, "back.out(2)", delay +0.2s
    - Title: stagger từng từ HOẶC từng dòng (split với innerHTML manual), y:80→0, opacity 0→1, rotateX 30→0, stagger 0.06s, "power4.out", delay +0.3s
    - Subtitle: x:-40→0, opacity 0→1, 0.6s, "power3.out", delay +0.5s
    - Body: y:20→0, opacity 0→1, 0.5s, "power2.out", delay +0.7s
    - Visual frame: scale 0.9→1, opacity 0→1, 0.9s, "power3.out", delay +0.3s
    - Visual children stagger: y:30→0, opacity 0→1, stagger 0.08s, "back.out(1.4)", delay +0.6s
    - Numbers count-up (nếu có stat): từ 0 → giá trị, 1.5s, ease "power2.out"
    - Decorative lines draw: strokeDashoffset → 0, 1s, ease "power2.inOut"

    SCENE IDLE (lặp suốt scene):
    - Glow pulse: opacity 0.6 ↔ 1, yoyo, repeat -1, 2s, "sine.inOut"
    - Floating: y 0 ↔ -8, yoyo, repeat -1, 3s, "sine.inOut"
    - Shimmer sweep: backgroundPosition lặp, 3s linear infinite
    - Cursor blink (nếu code block): opacity 0 ↔ 1, 0.6s, repeat
    - Particle/blob drift (nếu có canvas): rotation/translate slow

    SCENE EXIT (1s trước end):
    - opacity 1→0, 0.6s, "power2.in"
    - Optional: scale 1→0.96, blur 0→8px

13. DECORATIVE ELEMENTS (mỗi scene):
    - 4 corner brackets (top-left, top-right, bottom-left, bottom-right) với border partial color var(--accent), 60×60px, opacity 0.4
    - Top accent line: full width, 2px, gradient transparent → accent → transparent với shimmer animation
    - Scene number indicator: góc dưới phải, font-size 10rem, font-weight 900, opacity 0.06, color var(--accent), font-family mono
    - Status pill: góc trên trái với "LIVE", "REC", "AI", v.v.
    - Progress dots: bottom-center showing scene N/total

14. SPECIAL EFFECTS (chọn 2-3 áp dụng global tùy theme):
    - SCAN LINES: pseudo-element với repeating-linear-gradient
    - CRT NOISE: SVG turbulence noise pattern overlay
    - GLITCH: clip-path animation tạo hiệu ứng RGB split khi enter title
    - PARTICLE: small SVG circles với GSAP loop xy
    - GRID FLOOR: CSS perspective với linear-gradient lines (synthwave)
    - DATA STREAM: <span> ngẫu nhiên ASCII chars trôi từ trên xuống (matrix)
    - HOLOGRAM LINES: horizontal lines với glow di chuyển ngang

15. TRANSITIONS GIỮA SCENES:
    - Overlap 0.5-0.8s: scene N fade out trong khi scene N+1 đã bắt đầu
    - Variation: clip-path wipe, scale zoom, blur fade — nên đa dạng giữa các scene
    - Audio crossfade tự động (đã có trong audio elements)

═══════════════════════════════════════
NHẮC NHỞ CUỐI:
═══════════════════════════════════════
- LUÔN dùng CSS variables (var(--xxx)) — không hardcode màu
- Mỗi scene PHẢI khác layout hoặc visual pattern
- Visual-col KHÔNG ĐƯỢC TRỐNG — luôn có stat/code/grid/quote/timeline/chart
- Animation phải LIÊN TỤC trong scene (idle anim) — không tĩnh
- Title quan trọng nên có gradient text + glow
- Code phải VALID HTML — KHÔNG markdown fence
- ⚠️ TUYỆT ĐỐI tạo ĐỦ N scene (N = số scene trong scene plan). Đếm lại trước khi output.
- ⚠️ CHỈ dùng 'Inter' và 'JetBrains Mono'. Không Be Vietnam Pro, không Orbitron, không Helvetica, không Georgia.
- ⚠️ KHÔNG dùng repeat:-1. Tính repeat finite cho mọi tween lặp.

OUTPUT: Trả về DUY NHẤT mã HTML hoàn chỉnh từ <!doctype html> đến </html>. KHÔNG giải thích, KHÔNG ```fence```."""


# ─────────────────────────────  MODELS  ─────────────────────────────

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
    theme: str | None = None  # ThemeId from frontend; falls back to DEFAULT_THEME


def sse(data: dict) -> str:
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


def build_user_prompt(req: CompositionRequest) -> str:
    theme = get_theme(req.theme)
    lines = [
        f"Tiêu đề video: {req.title}",
        f"Theme: {theme['name']} — {theme['vibe']}",
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
        else:
            lines.append("  ⚠️ KHÔNG CÓ ẢNH — bắt buộc tạo mock visual phong phú (stat card / code / feature grid / timeline / quote / data viz / fact cards) phù hợp với narration")
        cursor += s.duration
    lines.append(
        f"\nSinh composition HTML hoàn chỉnh dài đúng {cursor} giây với {len(req.scenes)} scene như trên. "
        f"Áp dụng theme {theme['name']} thật ấn tượng — palette accent={theme['accent']}, "
        f"vibe={theme['vibe']}. Mỗi scene phải có layout/visual khác nhau và animation cinematic."
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

    theme = get_theme(req.theme)
    full_text = ""
    try:
        prompt = build_user_prompt(req)
        stream = await client.chat.completions.create(
            model=get_model("composition"),
            messages=[
                {"role": "system", "content": build_system_prompt(theme)},
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
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

        # Validate scene count: every requested scene must have a matching #sceneN element
        expected = len(req.scenes)
        missing: list[int] = []
        for i in range(1, expected + 1):
            if not re.search(rf'id\s*=\s*["\']scene{i}["\']', html):
                missing.append(i)
        if missing:
            print(f"[composition] WARNING: LLM produced HTML missing scenes {missing} of {expected}. "
                  f"Build pipeline will inject placeholder cards so audio stays in sync.")

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
