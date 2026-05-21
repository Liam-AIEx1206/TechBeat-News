import json
import re
from pathlib import Path
from typing import AsyncGenerator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from routers.llm import chat_completions_with_fallback

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


# ─────────────────────────────  BASE CSS  ─────────────────────────────
# Static framework injected into every composition. Replaces ~600 lines of
# repeated per-scene CSS the LLM previously had to author from scratch.
# Uses CSS variables so themes still drive the look. The LLM only needs to
# write scene-specific HTML structure + tiny custom tweaks (max 60 lines).

BASE_CSS_TEMPLATE = """
:root {{
  --bg: {bg};
  --bg2: {bg2};
  --surface: {surface};
  --accent: {accent};
  --accent2: {accent2};
  --accent3: {accent3};
  --text1: {text1};
  --text2: {text2};
  --glow: {accent}55;
}}

*, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

body {{
  background: #000;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  font-family: 'Inter', system-ui, sans-serif;
  overflow: hidden;
}}

#root {{
  position: relative;
  width: 1920px;
  height: 1080px;
  overflow: hidden;
  background:
    radial-gradient(ellipse 1400px 900px at 20% 50%, {accent}14 0%, transparent 70%),
    radial-gradient(ellipse 1000px 700px at 80% 20%, {accent2}10 0%, transparent 60%),
    radial-gradient(ellipse 800px 600px at 60% 80%, {accent3}0a 0%, transparent 60%),
    linear-gradient(135deg, var(--bg) 0%, var(--bg2) 100%);
  transform-origin: top left;
}}

#root::before {{
  content: ''; position: absolute; inset: 0;
  background-image: radial-gradient(circle, {accent}24 1px, transparent 1px);
  background-size: 48px 48px; opacity: 0.32;
  pointer-events: none; z-index: 0;
}}

#root::after {{
  content: ''; position: absolute; inset: 0;
  background: radial-gradient(ellipse 140% 140% at 50% 50%, transparent 40%, rgba(0,0,0,0.65) 100%);
  pointer-events: none; z-index: 1;
}}

.scanlines {{
  position: absolute; inset: 0;
  background: repeating-linear-gradient(0deg, transparent, transparent 3px, rgba(0,0,0,0.04) 3px, rgba(0,0,0,0.04) 4px);
  pointer-events: none; z-index: 2;
}}

.scene {{
  position: absolute; inset: 0;
  opacity: 0; visibility: hidden; z-index: 10;
  font-family: 'Inter', system-ui, sans-serif;
}}

/* Frame-0 fallback — HyperFrames captures the static initial DOM before any
   GSAP timeline seek runs, so without this the very first frame would be
   black. The injected timeline overrides this once it seeks. */
#scene1 {{
  opacity: 1; visibility: visible;
}}

/* Standard layout patterns — pick one per scene via class on .scene */
.scene .layout {{
  display: grid; gap: 60px; height: 100%;
  padding: 80px; align-items: center;
  position: relative; z-index: 10;
}}
.scene.split .layout    {{ grid-template-columns: 1fr 1fr; }}
.scene.hero .layout     {{ grid-template-columns: 1fr; justify-items: start; }}
.scene.centered .layout {{ grid-template-columns: 1fr; justify-items: center; text-align: center; }}
.scene.magazine .layout {{ grid-template-columns: 7fr 5fr; gap: 80px; }}
.scene.data .layout     {{ grid-template-columns: 1fr 1.4fr; }}

.info-col   {{ display: flex; flex-direction: column; justify-content: center; gap: 18px; }}
.visual-col {{ display: flex; flex-direction: column; justify-content: center; gap: 16px; }}

/* Decorative chrome — present on every scene */
.corner-bracket {{ position: absolute; width: 60px; height: 60px; opacity: 0.4; z-index: 15; }}
.corner-bracket.tl {{ top: 32px; left: 32px;  border-top: 2px solid var(--accent); border-left: 2px solid var(--accent); }}
.corner-bracket.tr {{ top: 32px; right: 32px; border-top: 2px solid var(--accent); border-right: 2px solid var(--accent); }}
.corner-bracket.bl {{ bottom: 32px; left: 32px;  border-bottom: 2px solid var(--accent); border-left: 2px solid var(--accent); }}
.corner-bracket.br {{ bottom: 32px; right: 32px; border-bottom: 2px solid var(--accent); border-right: 2px solid var(--accent); }}

.top-line {{
  position: absolute; top: 0; left: 0; width: 100%; height: 2px;
  background: linear-gradient(90deg, transparent 0%, var(--accent) 40%, var(--accent3) 60%, transparent 100%);
  z-index: 20;
}}

.scene-num {{
  position: absolute; bottom: 20px; right: 40px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 9rem; font-weight: 800;
  color: var(--accent); opacity: 0.06; line-height: 1;
  pointer-events: none; z-index: 5;
}}

.status-pill {{
  position: absolute; top: 36px; left: 50%; transform: translateX(-50%);
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px; font-weight: 600;
  color: var(--accent3); background: {accent3}1a;
  border: 1px solid {accent3}4d;
  border-radius: 99px; padding: 5px 16px;
  letter-spacing: 0.18em; text-transform: uppercase; z-index: 20;
}}

/* Typography utilities */
.badge {{
  display: inline-flex; align-items: center; gap: 8px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px; font-weight: 600;
  color: var(--accent2); background: var(--surface);
  border: 1px solid var(--accent);
  border-radius: 99px; padding: 6px 16px;
  letter-spacing: 0.18em; text-transform: uppercase;
  width: fit-content;
}}

.title-xl {{
  font-size: clamp(3.5rem, 6vw, 6rem);
  font-weight: 900; line-height: 1.0; letter-spacing: -0.04em;
  color: var(--text1);
}}
.title-hero {{
  font-size: clamp(5rem, 8vw, 8rem);
  font-weight: 900; line-height: 0.95; letter-spacing: -0.05em;
  color: var(--text1);
}}
.subtitle {{
  font-size: 1.6rem; font-weight: 700;
  color: var(--accent2); line-height: 1.4;
}}
.body-text {{
  font-size: 1.2rem; line-height: 1.7;
  color: var(--text2); max-width: 560px;
}}
.caption {{
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.85rem; color: var(--text2);
  letter-spacing: 0.1em; text-transform: uppercase;
}}

.grad-text {{
  background: linear-gradient(135deg, var(--accent), var(--accent2), var(--accent3));
  -webkit-background-clip: text; background-clip: text;
  -webkit-text-fill-color: transparent; color: transparent;
}}
.outline-text {{
  -webkit-text-stroke: 2px var(--accent); color: transparent;
}}

/* Hero stat — for B1 BIG STAT pattern */
.stat-hero {{
  font-size: clamp(7rem, 12vw, 12rem);
  font-weight: 900; line-height: 1; letter-spacing: -0.05em;
  font-feature-settings: 'tnum';
  background: linear-gradient(135deg, var(--accent), var(--accent3));
  -webkit-background-clip: text; background-clip: text;
  -webkit-text-fill-color: transparent; color: transparent;
}}
.stat-suffix {{
  font-size: 2.4rem; font-weight: 700; color: var(--text2);
  margin-left: 0.4rem;
}}

/* Visual block — generic glass card wrapper */
.visual-block {{
  background: linear-gradient(135deg, var(--surface), {surface}b3);
  border: 1px solid {accent}33;
  border-radius: 24px;
  backdrop-filter: blur(12px);
  box-shadow: 0 30px 80px -20px var(--glow), inset 0 0 60px rgba(255,255,255,0.02);
  position: relative; overflow: hidden;
  padding: 32px;
}}
.visual-block::before {{
  content: ''; position: absolute; top: 0; left: 0; right: 0; height: 1px;
  background: linear-gradient(90deg, transparent, var(--accent2), transparent);
  opacity: 0.6;
}}

/* Image frame */
.img-frame {{
  position: relative; border-radius: 24px;
  overflow: hidden; isolation: isolate;
  box-shadow: 0 0 0 1px {accent}55, 0 30px 80px -20px var(--accent), 0 0 100px -30px var(--accent);
}}
.img-frame img {{ width: 100%; height: auto; min-height: 420px; object-fit: cover; display: block; }}
.img-frame::after {{
  content: ''; position: absolute; inset: 0;
  background:
    linear-gradient(to bottom, rgba(0,0,0,0.4) 0%, transparent 30%),
    linear-gradient(to top, rgba(0,0,0,0.85) 0%, transparent 60%);
  pointer-events: none;
}}
.img-caption {{
  position: absolute; bottom: 18px; left: 18px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.8rem; color: var(--text1);
  background: rgba(0,0,0,0.55); backdrop-filter: blur(8px);
  border: 1px solid {accent}55;
  padding: 8px 14px; border-radius: 99px; z-index: 2;
}}

/* Terminal block — for B2 CODE pattern */
.terminal {{
  font-family: 'JetBrains Mono', monospace;
  background: rgba(0,0,0,0.55); border: 1px solid {accent}33;
  border-radius: 16px; padding: 24px 28px;
  font-size: 0.95rem; line-height: 1.7; color: var(--text2);
}}
.terminal .dots {{ display: flex; gap: 8px; margin-bottom: 16px; }}
.terminal .dots i {{ width: 12px; height: 12px; border-radius: 50%; display: block; }}
.terminal .dots i:nth-child(1) {{ background: #ef4444; }}
.terminal .dots i:nth-child(2) {{ background: #fbbf24; }}
.terminal .dots i:nth-child(3) {{ background: #22c55e; }}
.terminal .k {{ color: var(--accent3); }}
.terminal .s {{ color: var(--accent2); }}
.terminal .c {{ color: var(--text2); opacity: 0.6; }}
.terminal .cursor {{ display: inline-block; width: 9px; height: 1.1em; background: var(--accent); vertical-align: -2px; }}

/* Feature grid — for B3 */
.feat-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }}
.feat-card {{
  padding: 20px 22px; border-radius: 18px;
  background: linear-gradient(135deg, var(--surface), {surface}80);
  border: 1px solid {accent}33;
}}
.feat-card .ic {{ font-size: 2rem; margin-bottom: 10px; }}
.feat-card .t  {{ font-weight: 700; color: var(--text1); margin-bottom: 4px; font-size: 1.05rem; }}
.feat-card .d  {{ font-size: 0.92rem; color: var(--text2); line-height: 1.5; }}

/* Comparison — for B4 */
.compare {{ display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }}
.compare .col {{ padding: 24px; border-radius: 20px; border: 1px solid {accent}33; background: var(--surface); }}
.compare .col h4 {{ font-family: 'JetBrains Mono', monospace; font-size: 0.8rem; letter-spacing: 0.18em; text-transform: uppercase; color: var(--accent2); margin-bottom: 14px; }}
.compare .col li {{ list-style: none; padding: 6px 0; color: var(--text2); font-size: 0.98rem; }}
.compare .col li::before {{ content: '✓ '; color: var(--accent3); font-weight: 700; }}
.compare .col.bad li::before {{ content: '✗ '; color: #ef4444; }}

/* Timeline — for B5 */
.tl-list {{ position: relative; padding-left: 32px; }}
.tl-list::before {{ content: ''; position: absolute; left: 8px; top: 0; bottom: 0; width: 2px; background: linear-gradient(to bottom, var(--accent), {accent}33); }}
.tl-item {{ position: relative; padding: 8px 0 18px; }}
.tl-item::before {{ content: ''; position: absolute; left: -29px; top: 14px; width: 14px; height: 14px; border-radius: 50%; background: var(--accent); box-shadow: 0 0 0 4px {accent}33; }}
.tl-item .y {{ font-family: 'JetBrains Mono', monospace; font-size: 0.85rem; color: var(--accent2); letter-spacing: 0.1em; }}
.tl-item .t {{ font-size: 1.1rem; font-weight: 700; color: var(--text1); margin: 4px 0; }}
.tl-item .d {{ color: var(--text2); font-size: 0.95rem; }}

/* Quote — for B6 */
.quote-block {{ position: relative; padding: 60px 40px; }}
.quote-block::before {{
  content: '"'; position: absolute; left: -10px; top: -40px;
  font-size: 14rem; line-height: 1; color: var(--accent);
  opacity: 0.18; font-family: Georgia, serif;
}}
.quote-text {{ font-size: 2rem; font-style: italic; line-height: 1.5; color: var(--text1); max-width: 600px; }}
.quote-attr {{ font-family: 'JetBrains Mono', monospace; font-size: 0.85rem; color: var(--accent2); margin-top: 24px; letter-spacing: 0.1em; }}
.quote-attr::before {{ content: '— '; }}

/* Glow orb */
.glow-orb {{ position: absolute; border-radius: 50%; filter: blur(80px); pointer-events: none; }}
"""


def render_base_css(theme: dict) -> str:
    return BASE_CSS_TEMPLATE.format(**{k: theme[k] for k in (
        "bg", "bg2", "surface", "accent", "accent2", "accent3", "text1", "text2"
    )})


# ─────────────────────────────  PROMPT  ─────────────────────────────

def build_system_prompt_compact(theme: dict) -> str:
    """Compact prompt — used for free-tier providers (Groq) with tight TPM
    caps. Trades some prompt richness for a smaller token footprint."""
    return f"""Bạn sinh `index.html` hoàn chỉnh cho HyperFrames, theme **{theme['name']}**.

NGÔN NGỮ: tiếng Việt có dấu. Giữ nguyên văn narration/title/visualDescription. Tiếng Anh chỉ cho class CSS, comment, tên biến.

═══════ BẠN CHỈ VIẾT ═══════
- HTML structure (root, scene, audio).
- <style> override TỐI ĐA 60 dòng (chỉ scene-specific tweaks).
- KHÔNG viết <script> chứa gsap.timeline (sẽ bị strip server-side).
- KHÔNG redeclare CSS class đã có sẵn.

CSS framework + GSAP timeline + Inter/JetBrains Mono font đã được inject server-side.

Class có sẵn (DÙNG, không tự viết): .scene/.split/.centered/.hero/.magazine/.data, .layout, .info-col, .visual-col, .badge, .title-xl, .title-hero, .subtitle, .body-text, .caption, .grad-text, .outline-text, .stat-hero, .stat-suffix, .visual-block, .img-frame, .img-caption, .terminal, .feat-grid, .feat-card, .compare, .tl-list, .tl-item, .quote-block, .quote-text, .corner-bracket (tl/tr/bl/br), .top-line, .scene-num, .scanlines.

═══════ HTML TEMPLATE ═══════

<!doctype html>
<html lang="vi"><head>
<meta charset="UTF-8">
<title>{{TITLE}}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=JetBrains+Mono:wght@400;600;800&display=swap" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
<style>/* override tối đa 60 dòng */</style>
</head><body>
<div id="root" data-composition-id="main" data-start="0" data-width="1920" data-height="1080" data-duration="{{TOTAL}}">
  <div class="scanlines"></div>
  {{N scene}}
  {{N audio}}
</div></body></html>

═══════ MỖI SCENE ═══════

<div class="scene split" id="sceneN">
  <div class="layout">
    <div class="info-col">
      <div id="sN-badge" class="badge">PHẦN N</div>
      <h1 id="sN-title" class="title-xl">{{tiêu đề}}</h1>
      <p id="sN-subtitle" class="subtitle">{{phụ đề}}</p>
      <p id="sN-desc" class="body-text">{{mô tả}}</p>
    </div>
    <div class="visual-col">{{VISUAL}}</div>
  </div>
  <div class="corner-bracket tl"></div><div class="corner-bracket tr"></div>
  <div class="corner-bracket bl"></div><div class="corner-bracket br"></div>
  <div class="top-line"></div>
  <span class="scene-num">0N</span>
</div>

BẮT BUỘC: 4 element id="sN-badge"/"sN-title"/"sN-subtitle"/"sN-desc" trong mỗi scene. Layout class chọn 1 trong: split, centered, hero, magazine, data — đa dạng giữa các scene.

═══════ AUDIO ═══════
<audio id="vN" src="assets/pN.wav" data-start="0" data-duration="10" data-volume="1"></audio>
(start/duration sẽ được patch lại — placeholder OK.)

═══════ VISUAL-COL — chọn 1 pattern, ĐA DẠNG, KHÔNG để trống ═══════

A) Có IllustrationImage:
<div class="img-frame"><img src="{{path}}" alt=""><span class="img-caption">{{caption}}</span></div>

B) Không ảnh — chọn 1:
- BIG STAT: <div class="visual-block" style="text-align:center"><span class="stat-hero">87</span><span class="stat-suffix">%</span><p class="caption">{{nhãn}}</p></div>
- TERMINAL: <div class="terminal"><div class="dots"><i></i><i></i><i></i></div><div><span class="c">// comment</span></div>...<div>$ <span class="cursor"></span></div></div>
- FEATURE GRID 2x2: <div class="feat-grid"><div class="feat-card"><div class="ic">⚡</div><div class="t">{{tên}}</div><div class="d">{{mô tả}}</div></div>×4</div>
- COMPARE: <div class="compare"><div class="col"><h4>X</h4><ul><li>...</li></ul></div><div class="col bad"><h4>Y</h4>...</div></div>
- TIMELINE: <div class="tl-list"><div class="tl-item"><div class="y">2024</div><div class="t">{{event}}</div><div class="d">{{detail}}</div></div>×4-6</div>
- QUOTE: <div class="quote-block"><p class="quote-text">{{trích}}</p><p class="quote-attr">{{tác giả}}</p></div>
- DATA VIZ: SVG bars/sparkline trong .visual-block
- HEADLINE BANNER (broadcast theme): badge BREAKING + headline lớn

═══════ NHẮC CUỐI ═══════
- TUYỆT ĐỐI tạo ĐỦ N scene id="scene1"…"sceneN". Đếm trước khi output.
- KHÔNG dùng Date.now / setTimeout / Math.random / fetch.
- OUTPUT: HTML thuần từ <!doctype html> đến </html>. KHÔNG markdown fence."""


def build_system_prompt_full(theme: dict) -> str:
    """Rich prompt — for paid providers (Pinkyne, Anthropic) where token cost
    is fine. Asks for more elaborate decoration, motion, and creative
    visuals while still leveraging the server-injected CSS framework."""
    return f"""Bạn là chuyên gia tạo composition HyperFrames trình độ AWWWARDS — sinh ra HTML cinematic, lung linh, gây WOW. Sinh `index.html` HOÀN CHỈNH cho theme **{theme['name']}**.

⚠️ NGÔN NGỮ: TIẾNG VIỆT có dấu đầy đủ. Giữ NGUYÊN VĂN narration/title/visualDescription. Tiếng Anh chỉ cho class CSS / comment / tên biến.

═══════════════════════════════════════
🎯 BẠN CHỈ VIẾT: HTML structure + <style> override (≤120 dòng cho scene-specific). KHÔNG VIẾT <script> GSAP timeline.
═══════════════════════════════════════

HỆ THỐNG ĐÃ LO SẴN — KHÔNG CẦN BẠN VIẾT LẠI:
✅ CSS framework đầy đủ (variables theme, layouts, typography, decorative chrome) đã được inject server-side trước HTML của bạn.
✅ GSAP timeline với fade in/out scene, audio sync, scene visibility lifecycle sẽ được inject server-side với duration thật từ TTS.
✅ Font Inter + JetBrains Mono đã link sẵn.

⚠️ TUYỆT ĐỐI KHÔNG VIẾT `<script>` chứa `gsap.timeline`. Build pipeline strip mọi script timeline rồi inject lại với duration thật. Viết script chỉ tốn token và bị xóa sạch.

═══════════════════════════════════════
THEME — {theme['name'].upper()}
═══════════════════════════════════════

VIBE: {theme['vibe']}

ƯU TIÊN visual effects: {theme['fx']}.

CSS variables đã có (DÙNG var(--xxx), KHÔNG hardcode hex):
--bg, --bg2, --surface, --accent, --accent2, --accent3, --text1, --text2, --glow

═══════════════════════════════════════
QUY TẮC HTML BẮT BUỘC
═══════════════════════════════════════

1. ROOT:
   <div id="root" data-composition-id="main" data-start="0" data-width="1920" data-height="1080" data-duration="{{TOTAL}}">

2. SCENE COUNT: PHẢI tạo ĐỦ N scene (N từ user prompt). Mỗi scene <div class="scene LAYOUT" id="sceneN"> với LAYOUT là 1 trong: split, centered, hero, magazine, data.

3. SCENE STRUCTURE — bắt buộc đầy đủ id pattern này:
   <div class="scene split" id="sceneN">
     <div class="layout">
       <div class="info-col">
         <div id="sN-badge" class="badge">PHẦN N</div>
         <h1 id="sN-title" class="title-xl grad-text">{{tiêu đề}}</h1>
         <p id="sN-subtitle" class="subtitle">{{phụ đề ngắn}}</p>
         <p id="sN-desc" class="body-text">{{mô tả 2-3 dòng}}</p>
       </div>
       <div class="visual-col">{{... pattern A hoặc B ...}}</div>
     </div>
     <div class="corner-bracket tl"></div><div class="corner-bracket tr"></div>
     <div class="corner-bracket bl"></div><div class="corner-bracket br"></div>
     <div class="top-line"></div>
     <span class="scene-num">{{N với padding 0, "01"–"99"}}</span>
   </div>

4. AUDIO (đặt cuối root, trước </div>):
   <audio id="vN" src="assets/pN.wav" data-start="0" data-duration="10" data-volume="1"></audio>
   data-start/duration sẽ được patch lại — placeholder OK.

5. LAYOUT VARIETY — KHÔNG lặp class giữa các scene:
   - .scene.split    → 2 cột info|visual — dùng cho stat/code/img
   - .scene.centered → 1 cột center text — dùng cho intro/quote
   - .scene.hero     → title cực to căn trái — dùng cho headline
   - .scene.magazine → 7:5 asymmetric — dùng cho mix text+visual
   - .scene.data     → info nhỏ + visual lớn — dùng cho data viz/chart

═══════════════════════════════════════
🎨 VISUAL-COL — RICHE BẮT BUỘC
═══════════════════════════════════════

A) NẾU có IllustrationImage (assets/sceneN.jpg):
   <div class="img-frame">
     <img src="{{asset path}}" alt="">
     <span class="img-caption">{{caption tiếng Việt mô tả ảnh}}</span>
   </div>

B) NẾU KHÔNG có ảnh — CHỌN 1 PATTERN, ĐA DẠNG GIỮA CÁC SCENE, KHÔNG ĐƯỢC ĐỂ TRỐNG:

   B1 — BIG STAT CARD (số liệu dramatic):
   <div class="visual-block" style="text-align:center;padding:60px;">
     <div><span class="stat-hero">{{số}}</span><span class="stat-suffix">{{đơn vị}}</span></div>
     <p class="caption" style="margin-top:24px;">{{nhãn}}</p>
     <p class="body-text" style="margin:16px auto 0;max-width:480px;">{{2-3 dòng giải thích}}</p>
   </div>

   B2 — TERMINAL/CODE (cyber themes):
   <div class="terminal">
     <div class="dots"><i></i><i></i><i></i></div>
     <div><span class="c">// {{comment liên quan content}}</span></div>
     <div><span class="k">const</span> data = <span class="s">"{{value}}"</span>;</div>
     <div><span class="k">function</span> analyze(input) {{</div>
     <div>  <span class="k">return</span> ai.process(input);</div>
     <div>}}</div>
     <div>$ <span class="cursor"></span></div>
   </div>

   B3 — FEATURE GRID 2×2 (so sánh 4 ý):
   <div class="feat-grid">
     <div class="feat-card">
       <div class="ic">{{emoji 1}}</div>
       <div class="t">{{tên ngắn}}</div>
       <div class="d">{{mô tả 1 dòng}}</div>
     </div>
     ... 4 cards với emoji + nội dung khác nhau ...
   </div>

   B4 — COMPARISON (X vs Y):
   <div class="compare">
     <div class="col">
       <h4>{{label tốt}}</h4>
       <ul><li>{{point 1}}</li><li>{{point 2}}</li><li>{{point 3}}</li></ul>
     </div>
     <div class="col bad">
       <h4>{{label xấu}}</h4>
       <ul><li>{{point 1}}</li><li>{{point 2}}</li><li>{{point 3}}</li></ul>
     </div>
   </div>

   B5 — TIMELINE (4-6 mốc):
   <div class="tl-list">
     <div class="tl-item">
       <div class="y">{{năm/giai đoạn}}</div>
       <div class="t">{{tiêu đề mốc}}</div>
       <div class="d">{{mô tả 1 dòng}}</div>
     </div>
     ... 4-6 items ...
   </div>

   B6 — QUOTE (trích dẫn nhân vật):
   <div class="quote-block">
     <p class="quote-text">"{{trích dẫn dài}}"</p>
     <p class="quote-attr">{{tác giả · vai trò}}</p>
   </div>

   B7 — DATA VIZ:
   <div class="visual-block" style="padding:48px;">
     <svg width="100%" height="320" viewBox="0 0 600 320">
       <!-- bars/sparkline với stroke, fill var(--accent), gradient -->
     </svg>
     <p class="caption">{{label}}</p>
   </div>

   B8 — FACT CARDS scatter:
   <div style="position:relative;height:480px;">
     <div class="feat-card" style="position:absolute;top:8%;left:5%;transform:rotate(-2deg);width:280px;">{{fact 1}}</div>
     <div class="feat-card" style="position:absolute;top:35%;right:8%;transform:rotate(1.5deg);width:260px;">{{fact 2}}</div>
     <div class="feat-card" style="position:absolute;bottom:8%;left:15%;transform:rotate(0.8deg);width:300px;">{{fact 3}}</div>
   </div>

   B9 — HEADLINE BANNER (broadcast themes):
   <div style="padding:60px;border-left:6px solid var(--accent);background:rgba(0,0,0,0.4);">
     <span class="badge" style="background:var(--accent);color:#000;">BREAKING</span>
     <h2 class="title-hero" style="margin:24px 0;">{{headline}}</h2>
     <p class="caption">{{source · timestamp}}</p>
   </div>

   B10 — NEURAL NET (cyber themes):
   <svg width="100%" height="420" viewBox="0 0 600 420">
     <!-- 6-12 nodes với <circle r=8> + edges <line> + pulse animation via class -->
   </svg>

   KHÔNG ĐƯỢC để visual-col trống. KHÔNG được gen visual-col chỉ chứa text trùng info-col.
   ⚠️ TUYỆT ĐỐI KHÔNG dùng <img> hay .img-frame trừ khi user prompt ghi rõ "IllustrationImage: assets/...". Nếu KHÔNG có IllustrationImage → BẮT BUỘC dùng mock visual (B1-B10).

═══════════════════════════════════════
TYPOGRAPHY (đã có sẵn class — DÙNG):
═══════════════════════════════════════
- .badge (mono uppercase pill)
- .title-xl (clamp 3.5-6rem) cho hầu hết title
- .title-hero (clamp 5-8rem) cho hero scene
- .subtitle, .body-text, .caption
- .grad-text (gradient accent), .outline-text (chỉ outline)
- .stat-hero (số khổng lồ gradient)

═══════════════════════════════════════
HEAD BOILERPLATE (copy nguyên xi):
═══════════════════════════════════════

<!doctype html>
<html lang="vi">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{{title video}}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=JetBrains+Mono:wght@400;600;800&display=swap" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
<style>
/* CHỈ override scene-specific. KHÔNG redeclare class đã sẵn.
   Ví dụ: tinh chỉnh font-size title cho 1 scene, custom keyframes
   shimmer riêng, gradient accent đặc biệt cho stat-hero.
   Thoải mái thêm idle animation (pulse, drift, scan-line sweep). */
</style>
</head>
<body>
<div id="root" data-composition-id="main" data-start="0" data-width="1920" data-height="1080" data-duration="{{TOTAL}}">
  <div class="scanlines"></div>

  {{... N scene ở đây — đa dạng layout class ...}}

  {{... N audio elements ở đây ...}}
</div>
</body>
</html>

═══════════════════════════════════════
NHẮC CUỐI:
═══════════════════════════════════════
- LUÔN dùng var(--xxx) — không hardcode hex.
- Mỗi scene khác nhau về layout HOẶC visual pattern.
- Visual-col KHÔNG ĐƯỢC TRỐNG.
- Title quan trọng có .grad-text hoặc .outline-text.
- KHÔNG dùng Date.now / setTimeout / Math.random / fetch / repeat:-1.
- TUYỆT ĐỐI tạo ĐỦ N scene "scene1"…"sceneN". Đếm trước khi output.
- OUTPUT: chỉ HTML thuần từ <!doctype html> đến </html>. KHÔNG markdown fence, KHÔNG giải thích, KHÔNG comment trên đầu."""


# Backwards-compat default — anyone calling build_system_prompt() unchanged
# gets the rich version. Per-provider routing happens in the wrapper kwargs_factory.
def build_system_prompt(theme: dict) -> str:
    return build_system_prompt_full(theme)


def build_system_prompt_groq_premium(theme: dict, scene_count: int) -> str:
    """Quality-focused prompt for Groq.

    Strategy: ask for FEWER scenes but each one cinematic-grade. The system
    prompt aggressively pushes for: 1) full visual block, never empty col;
    2) rich decorative elements (corner brackets, scan-lines, gradients);
    3) inline keyframes / animation overrides on top of the framework's
    GSAP timeline. Llama 3.3 70B is creative when narrowly focused — this
    prompt narrows it."""
    return f"""Bạn sinh `index.html` cinematic cho HyperFrames, theme **{theme['name']}**.

⚠️ NGÔN NGỮ: TIẾNG VIỆT có dấu. Giữ nguyên văn narration/title.

═══════ MISSION ═══════
Sinh CHỈ {scene_count} scene nhưng MỖI SCENE phải đẹp như Awwwards entry:
- Visual-col KHÔNG ĐƯỢC TRỐNG, KHÔNG ĐƯỢC chỉ chứa text. PHẢI có 1 visual pattern dramatic.
- ⚠️ TUYỆT ĐỐI KHÔNG dùng <img> hay .img-frame trừ khi user prompt ghi rõ "IllustrationImage: assets/...". Nếu KHÔNG có IllustrationImage → BẮT BUỘC dùng mock visual (B1-B8).
- Mỗi scene khác layout (split / hero / data / centered / magazine).
- Mỗi scene phải có decorative chrome đầy đủ: 4 corner-bracket, top-line, scene-num.
- Title quan trọng dùng .grad-text hoặc gradient inline.

CSS framework + GSAP timeline + font Inter/JetBrains Mono đã được inject server-side. KHÔNG viết <script> gsap.timeline (sẽ bị xóa).

═══════ CLASS CÓ SẴN — DÙNG ═══════
.scene/.split/.centered/.hero/.magazine/.data, .layout, .info-col, .visual-col, .badge, .title-xl, .title-hero, .subtitle, .body-text, .caption, .grad-text, .outline-text, .stat-hero, .stat-suffix, .visual-block, .img-frame, .img-caption, .terminal, .feat-grid, .feat-card, .compare, .tl-list, .tl-item, .quote-block, .quote-text, .corner-bracket (tl/tr/bl/br), .top-line, .scene-num, .scanlines.

═══════ HTML TEMPLATE ═══════
<!doctype html>
<html lang="vi"><head>
<meta charset="UTF-8">
<title>{{TITLE}}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=JetBrains+Mono:wght@400;600;800&display=swap" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
<style>
/* Override scene-specific (≤80 dòng): keyframes shimmer/pulse cho visual,
   gradient riêng cho stat-hero, custom decorative element nếu cần. */
@keyframes shimmer {{ 0%,100% {{ opacity:.6 }} 50% {{ opacity:1 }} }}
@keyframes drift {{ 0%,100% {{ transform: translateY(0) }} 50% {{ transform: translateY(-8px) }} }}
.shimmer {{ animation: shimmer 2s ease-in-out infinite; }}
.drift {{ animation: drift 4s ease-in-out infinite; }}
</style>
</head><body>
<div id="root" data-composition-id="main" data-start="0" data-width="1920" data-height="1080" data-duration="{{TOTAL}}">
  <div class="scanlines"></div>
  {{SCENES}}
  {{AUDIO}}
</div></body></html>

═══════ MỖI SCENE — bắt buộc đầy đủ ═══════
<div class="scene LAYOUT" id="sceneN">
  <div class="layout">
    <div class="info-col">
      <div id="sN-badge" class="badge">PHẦN N</div>
      <h1 id="sN-title" class="title-xl grad-text">{{tiêu đề}}</h1>
      <p id="sN-subtitle" class="subtitle">{{phụ đề ngắn 1 câu}}</p>
      <p id="sN-desc" class="body-text">{{mô tả 2-3 dòng}}</p>
    </div>
    <div class="visual-col">{{VISUAL — pattern A hoặc B}}</div>
  </div>
  <div class="corner-bracket tl"></div><div class="corner-bracket tr"></div>
  <div class="corner-bracket bl"></div><div class="corner-bracket br"></div>
  <div class="top-line shimmer"></div>
  <span class="scene-num">0N</span>
</div>

LAYOUT: split (mặc định) / centered / hero / magazine / data — đa dạng.

═══════ VISUAL-COL — BẮT BUỘC RICH ═══════
A) Có IllustrationImage:
<div class="img-frame drift">
  <img src="{{path}}" alt="">
  <span class="img-caption">{{caption tiếng Việt}}</span>
</div>

B) Không ảnh — chọn 1 (ĐỪNG để trống, ĐỪNG repeat):

B1 BIG STAT:
<div class="visual-block drift" style="text-align:center;padding:60px;">
  <div><span class="stat-hero">{{số}}</span><span class="stat-suffix">{{đơn vị}}</span></div>
  <p class="caption" style="margin-top:24px;">{{nhãn}}</p>
  <p class="body-text" style="margin:16px auto 0;max-width:480px;">{{2-3 dòng}}</p>
</div>

B2 TERMINAL (cyber/matrix):
<div class="terminal">
  <div class="dots"><i></i><i></i><i></i></div>
  <div><span class="c">// {{comment}}</span></div>
  <div><span class="k">const</span> ai = <span class="s">"{{value}}"</span>;</div>
  <div><span class="k">function</span> run() {{</div>
  <div>  <span class="k">return</span> ai.process();</div>
  <div>}}</div>
  <div>$ <span class="cursor"></span></div>
</div>

B3 FEATURE GRID 2×2 (4 ý):
<div class="feat-grid">
  <div class="feat-card"><div class="ic">⚡</div><div class="t">{{tên}}</div><div class="d">{{mô tả}}</div></div>
  ... 4 card khác nhau ...
</div>

B4 COMPARE:
<div class="compare">
  <div class="col"><h4>{{tốt}}</h4><ul><li>...</li><li>...</li></ul></div>
  <div class="col bad"><h4>{{xấu}}</h4><ul><li>...</li></ul></div>
</div>

B5 TIMELINE (4-5 mốc):
<div class="tl-list">
  <div class="tl-item"><div class="y">2024</div><div class="t">{{event}}</div><div class="d">{{detail}}</div></div>
  ... 4-5 items ...
</div>

B6 QUOTE:
<div class="quote-block">
  <p class="quote-text">"{{trích dẫn}}"</p>
  <p class="quote-attr">{{tác giả · vai trò}}</p>
</div>

B7 DATA VIZ:
<div class="visual-block" style="padding:40px;">
  <svg width="100%" height="320" viewBox="0 0 600 320">
    <rect x="40" y="220" width="80" height="80" fill="var(--accent)" />
    <rect x="160" y="160" width="80" height="140" fill="var(--accent2)" />
    <rect x="280" y="100" width="80" height="200" fill="var(--accent3)" />
    <rect x="400" y="60" width="80" height="240" fill="var(--accent)" />
  </svg>
  <p class="caption">{{label}}</p>
</div>

B8 HEADLINE BANNER (broadcast):
<div style="padding:60px;border-left:6px solid var(--accent);background:rgba(0,0,0,0.4);">
  <span class="badge" style="background:var(--accent);color:#000;">BREAKING</span>
  <h2 class="title-hero" style="margin:24px 0;">{{headline}}</h2>
  <p class="caption">{{source · timestamp}}</p>
</div>

═══════ AUDIO ═══════
<audio id="vN" src="assets/pN.wav" data-start="0" data-duration="10" data-volume="1"></audio>
(start/duration sẽ patch lại — placeholder OK)

═══════ NHẮC CUỐI ═══════
- TUYỆT ĐỐI tạo ĐỦ {scene_count} scene, id="scene1"…"scene{scene_count}". Đếm trước khi output.
- KHÔNG dùng Date.now / setTimeout / Math.random / fetch.
- KHÔNG redeclare CSS class đã có sẵn.
- OUTPUT: chỉ HTML từ <!doctype html> đến </html>. KHÔNG markdown fence."""


def merge_scenes_for_groq(scenes: list, target_count: int):
    """Combine adjacent scenes so the LLM has fewer, richer scenes to render.

    Returns a new list of ScenePayload with `target_count` entries (or fewer
    if the original list is shorter). Narrations get joined with " " between
    them; titles take the first scene's title; durations sum up. Used when
    we route to Groq and want to keep visual quality high.

    Note: this is purely about HTML rendering — TTS at build time still uses
    the ORIGINAL scenes (one wav per source scene) so audio timing is
    unaffected. The frontend should display the merged plan in the html
    preview but submit the original scenes to /build-video."""
    if len(scenes) <= target_count:
        return list(scenes)

    # Distribute as evenly as possible: e.g. 8 -> 5 means [2,2,2,1,1]
    n = len(scenes)
    base = n // target_count
    extra = n % target_count
    groups: list[list] = []
    cursor = 0
    for i in range(target_count):
        size = base + (1 if i < extra else 0)
        groups.append(scenes[cursor:cursor + size])
        cursor += size

    merged = []
    for i, grp in enumerate(groups):
        head = grp[0]
        title = head.title
        narration = " ".join(s.narration for s in grp)
        visualDesc = " · ".join(s.visualDescription for s in grp if s.visualDescription)
        duration = sum(s.duration for s in grp)
        # Prefer the first scene that has an image
        img_url = next((s.imageUrl for s in grp if s.imageUrl), None)
        img_query = next((s.imageQuery for s in grp if s.imageQuery), None)
        img_asset = next((s.imageAsset for s in grp if s.imageAsset), None)
        merged.append(ScenePayload(
            id=f"merged-{i+1}",
            index=i,
            title=title,
            narration=narration,
            visualDescription=visualDesc,
            duration=duration,
            imageQuery=img_query,
            imageUrl=img_url,
            imageAsset=img_asset,
        ))
    return merged


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


_BASE_CSS_MARKER = "/* === techbeat:base-css === */"


def inject_base_css(html: str, theme: dict) -> str:
    """Inject the framework CSS as the FIRST <style> in <head>, so the LLM's
    tiny override <style> (written later in <head>) wins under CSS cascade.

    The LLM no longer writes the variable block, body, root, scenes, or
    component classes — those live here. Idempotent: a marker comment guards
    against double-injection if the LLM happens to copy the framework anyway.
    """
    if _BASE_CSS_MARKER in html:
        return html
    block = f"<style>\n{_BASE_CSS_MARKER}\n{render_base_css(theme)}\n</style>\n"

    # Prefer: insert right after <head ...> so LLM-authored <style> later in
    # <head> overrides our defaults. Fall back to before </head> (worse cascade
    # but still functional) and then before <body> if there's no <head> at all.
    head_open = re.search(r"<head\b[^>]*>", html, flags=re.IGNORECASE)
    if head_open:
        idx = head_open.end()
        return html[:idx] + "\n" + block + html[idx:]
    if "<body" in html:
        return re.sub(r"(<body\b[^>]*>)", block + r"\1", html, count=1)
    return block + html


async def stream_composition_events(req: CompositionRequest) -> AsyncGenerator[dict, None]:
    """Yield raw event dicts: {type:'chunk',text} | {type:'done',html,scenes?} | {type:'error',message}"""
    import os as _os
    theme = get_theme(req.theme)
    full_text = ""
    finish_reason: str | None = None

    # Groq free tier struggles with 8 dense scenes — quality drops to bare
    # cards on empty backgrounds. We merge adjacent scenes into a smaller
    # set so the LLM has fewer scenes to render but each gets full token
    # budget. Build pipeline still uses ORIGINAL scenes for TTS — merged
    # scenes are only the HTML rendering surface.
    groq_max_scenes = int(_os.getenv("GROQ_MAX_SCENES", "5"))
    merged_scenes_for_groq = merge_scenes_for_groq(req.scenes, groq_max_scenes) if len(req.scenes) > groq_max_scenes else None

    try:
        # Build TWO user prompts — full (paid) and merged (groq) — picked at
        # request time by the kwargs factory.
        prompt_full = build_user_prompt(req)
        if merged_scenes_for_groq:
            req_for_groq = req.model_copy(update={
                "scenes": merged_scenes_for_groq,
                "totalDuration": sum(s.duration for s in merged_scenes_for_groq),
            })
            prompt_groq = build_user_prompt(req_for_groq)
            groq_scene_count = len(merged_scenes_for_groq)
        else:
            prompt_groq = prompt_full
            groq_scene_count = len(req.scenes)

        sys_full           = build_system_prompt_full(theme)
        sys_groq_premium   = build_system_prompt_groq_premium(theme, groq_scene_count)

        def _kwargs(provider_name: str) -> dict:
            if provider_name in ("groq", "groq-fast"):
                # Compact prompt + merged scenes + smaller budget for free-tier models
                return {
                    "messages": [
                        {"role": "system", "content": sys_groq_premium},
                        {"role": "user", "content": prompt_groq},
                    ],
                    "temperature": 0.75,
                    "max_tokens": 8000,
                    "stream": True,
                }
            return {
                "messages": [
                    {"role": "system", "content": sys_full},
                    {"role": "user", "content": prompt_full},
                ],
                "temperature": 0.7,
                "max_tokens": 24000,
                "stream": True,
            }

        stream, provider = await chat_completions_with_fallback(
            model_kind="composition",
            kwargs_factory=_kwargs,
        )
        if provider != "primary":
            extra = ""
            if provider in ("groq", "groq-fast") and merged_scenes_for_groq:
                extra = f" Đã gộp {len(req.scenes)} scene → {len(merged_scenes_for_groq)} scene để giữ chất lượng visual."
            yield {
                "type": "warning",
                "message": f"Primary LLM hết quota — đã chuyển sang {provider}.{extra}",
            }
        async for chunk in stream:
            if not chunk.choices:
                continue
            choice = chunk.choices[0]
            delta = choice.delta
            text = getattr(delta, "content", None)
            if text:
                full_text += text
                yield {"type": "chunk", "text": text}
            if getattr(choice, "finish_reason", None):
                finish_reason = choice.finish_reason

        html = strip_fences(full_text)
        if "<html" not in html.lower():
            yield {"type": "error", "message": "Không tìm thấy HTML hợp lệ trong response"}
            return

        # Auto-recover truncated output. Provider often drops the closing tags
        # when it hits max_tokens; the body before the cutoff is usually
        # complete enough that we can render. We close the document and let
        # the build pipeline inject placeholder scenes for any missing IDs.
        lower = html.lower()
        if "</html>" not in lower:
            print(f"[composition] HTML truncated (finish_reason={finish_reason}, "
                  f"len={len(html)}). Auto-closing and continuing.")

            # Find a safe truncation point — last complete tag — to avoid
            # leaving a half-written attribute or text node mid-stream.
            last_close = html.rfind(">")
            if last_close > 0:
                html = html[: last_close + 1]

            # Append whatever is missing in the right order.
            tail = ""
            if "</body>" not in html.lower():
                # Make sure root div is closed before </body>
                if html.count("<div") > html.count("</div"):
                    tail += "\n" + ("</div>" * (html.count("<div") - html.count("</div")))
                tail += "\n</body>"
            if "</html>" not in (html + tail).lower():
                tail += "\n</html>"
            html = html + tail
            yield {
                "type": "warning",
                "message": (
                    f"HTML bị cắt do LLM hết token (finish_reason={finish_reason}). "
                    f"Đã tự đóng tag và tiếp tục — scene thiếu sẽ được hệ thống điền placeholder."
                ),
            }

        # Inject framework CSS so the LLM's output stays small and consistent.
        html = inject_base_css(html, theme)

        # When groq merged scenes, the HTML only has the merged count.
        # Validate against the *actual* scenes the prompt asked for.
        if provider in ("groq", "groq-fast") and merged_scenes_for_groq:
            effective_scenes = merged_scenes_for_groq
        else:
            effective_scenes = list(req.scenes)

        expected = len(effective_scenes)
        missing: list[int] = []
        for i in range(1, expected + 1):
            if not re.search(rf'id\s*=\s*["\']scene{i}["\']', html):
                missing.append(i)
        if missing:
            print(f"[composition] WARNING: LLM produced HTML missing scenes {missing} of {expected}. "
                  f"Build pipeline will inject placeholder cards so audio stays in sync.")

        done_event: dict = {"type": "done", "html": html}
        if provider in ("groq", "groq-fast") and merged_scenes_for_groq:
            done_event["mergedScenes"] = [s.model_dump() for s in merged_scenes_for_groq]
            done_event["mergedTotalDuration"] = sum(s.duration for s in merged_scenes_for_groq)
        yield done_event
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


# ─────────────────────────  REGEN SINGLE SCENE  ─────────────────────────


def find_scene_block(html: str, scene_index: int) -> tuple[int, int] | None:
    """Locate the byte range of <div ... id="sceneN"> ... </div> in `html`.

    Walks open/close <div> tags starting from the scene's opening tag so we
    can splice in a replacement without using a real HTML parser. Returns
    None if the scene isn't found or the tags don't balance.
    """
    pattern = re.compile(rf'<div\b[^>]*\bid\s*=\s*["\']scene{scene_index}["\'][^>]*>', re.IGNORECASE)
    m = pattern.search(html)
    if not m:
        return None
    start = m.start()
    cursor = m.end()
    depth = 1  # we just consumed an opening <div ...>
    div_re = re.compile(r"</?div\b[^>]*>", re.IGNORECASE)
    while depth > 0:
        nm = div_re.search(html, cursor)
        if not nm:
            return None
        cursor = nm.end()
        if nm.group(0).lower().startswith("</div"):
            depth -= 1
        else:
            depth += 1
    return start, cursor


class RegenSceneRequest(BaseModel):
    fullHtml: str
    sceneIndex: int  # 1-based
    scene: ScenePayload  # the (possibly edited) scene the LLM should re-render
    theme: str | None = None


@router.post("/regen-scene")
async def regen_scene(body: RegenSceneRequest):
    """Re-generate the HTML of a single scene without touching the rest.

    The user has edited a scene's title/narration/image and wants to see
    the change reflected in the preview. We ask the LLM for ONLY the scene
    block, then splice it into the cached full HTML."""
    theme = get_theme(body.theme)

    # Find the existing scene's bounds so we can replace it
    bounds = find_scene_block(body.fullHtml, body.sceneIndex)
    if bounds is None:
        raise HTTPException(
            status_code=400,
            detail=f"Không tìm thấy #scene{body.sceneIndex} trong HTML đã có.",
        )

    image_clause = ""
    if body.scene.imageAsset:
        image_clause = f"\n  ImageAsset: {body.scene.imageAsset} → BẮT BUỘC dùng <img src=\"{body.scene.imageAsset}\">"
    elif body.scene.imageUrl:
        image_clause = f"\n  ImageUrl: {body.scene.imageUrl}"

    sys_msg = f"""Bạn re-generate MỘT scene HyperFrames.

Theme: {theme['name']}. CSS framework + GSAP timeline đã inject sẵn — đừng viết <style>/<script> ngoài scene wrapper.

CHỈ TRẢ VỀ 1 block HTML duy nhất, không kèm <html>/<head>/<body>:

<div class="scene LAYOUT" id="scene{body.sceneIndex}">
  <div class="layout">
    <div class="info-col">
      <div id="s{body.sceneIndex}-badge" class="badge">PHẦN {body.sceneIndex}</div>
      <h1 id="s{body.sceneIndex}-title" class="title-xl">{{tiêu đề}}</h1>
      <p id="s{body.sceneIndex}-subtitle" class="subtitle">{{phụ đề ngắn}}</p>
      <p id="s{body.sceneIndex}-desc" class="body-text">{{mô tả}}</p>
    </div>
    <div class="visual-col">{{visual content}}</div>
  </div>
  <div class="corner-bracket tl"></div><div class="corner-bracket tr"></div>
  <div class="corner-bracket bl"></div><div class="corner-bracket br"></div>
  <div class="top-line"></div>
  <span class="scene-num">{body.sceneIndex:02d}</span>
</div>

LAYOUT: split | centered | hero | magazine | data (chọn 1 phù hợp).

Class có sẵn (dùng, không tự viết): .badge, .title-xl/.title-hero, .subtitle, .body-text, .grad-text, .stat-hero, .visual-block, .img-frame, .img-caption, .terminal, .feat-grid, .feat-card, .compare, .tl-list, .tl-item, .quote-block.

OUTPUT: chỉ HTML thuần của 1 div.scene, KHÔNG markdown fence, KHÔNG giải thích."""

    user_msg = f"""Tiêu đề scene: {body.scene.title}
Narration: {body.scene.narration}
Visual: {body.scene.visualDescription}
Duration: {body.scene.duration}s{image_clause}

Sinh lại block <div class="scene ..." id="scene{body.sceneIndex}"> với nội dung trên."""

    try:
        resp, provider = await chat_completions_with_fallback(
            model_kind="composition",
            messages=[
                {"role": "system", "content": sys_msg},
                {"role": "user", "content": user_msg},
            ],
            temperature=0.7,
            max_tokens=3000,
            stream=False,
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"LLM regen scene thất bại: {e}")

    new_block = strip_fences(resp.choices[0].message.content or "").strip()
    # Sanity: must start with <div and reference the right id
    if not new_block.lower().startswith("<div"):
        # LLM might have wrapped it — try to extract first div block
        m = re.search(r"<div\b[\s\S]*</div>\s*$", new_block)
        if m:
            new_block = m.group(0)
        else:
            raise HTTPException(
                status_code=502,
                detail="LLM không trả về block <div> hợp lệ.",
            )
    if f'scene{body.sceneIndex}' not in new_block:
        raise HTTPException(
            status_code=502,
            detail=f"LLM trả về scene sai id (thiếu scene{body.sceneIndex}).",
        )

    start, end = bounds
    updated = body.fullHtml[:start] + new_block + body.fullHtml[end:]
    return {"html": updated, "provider": provider}
