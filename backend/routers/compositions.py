# -*- coding: utf-8 -*-
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
        "vibe": "Y2K aesthetic với bubble shapes, magenta-yellow contrast, holographic glow, sparkle stars, playful nhưng vẫn premium",
        "fx": "bubble shapes floating (border-radius CSS), sparkle star keyframes, holographic neon border glow, gradient shimmer text — KHÔNG dùng repeating-linear-gradient diagonal stripes",
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
  background-image: radial-gradient(circle, {accent}24 1.5px, transparent 1.5px);
  background-size: 48px 48px; opacity: 0.32;
  pointer-events: none; z-index: 0;
  animation: grid-sweep 12s linear infinite;
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

/* Frame-0 fallback */
#scene1 {{
  opacity: 1; visibility: visible;
}}

/* Standard layout patterns — expanded for video canvas */
.scene .layout {{
  display: grid; gap: 60px; height: 100%;
  padding: 60px 120px 100px; align-items: center;
  position: relative; z-index: 10;
}}
.scene.split .layout    {{ grid-template-columns: 1fr 1fr; }}
.scene.hero .layout     {{ grid-template-columns: 1.1fr 0.9fr; }}
.scene.centered .layout {{ grid-template-columns: 1fr; justify-items: center; text-align: center; }}
/* Bug2 fix: cascade text-align into info-col and all its direct children so body-text/caption inherit centering */
.scene.centered .info-col {{ align-items: center; text-align: center; }}
.scene.centered .info-col > * {{ text-align: center; }}
.scene.magazine .layout {{ grid-template-columns: 7fr 5fr; gap: 80px; }}
.scene.data .layout     {{ grid-template-columns: 1fr 1.4fr; }}

.info-col   {{
  display: flex; flex-direction: column; justify-content: center; gap: 28px;
  min-width: 0; max-height: 100%; overflow: visible;
}}
.visual-col {{
  display: flex; flex-direction: column; justify-content: center; gap: 24px;
  min-width: 0; max-width: 100%; max-height: 100%; overflow: visible;
}}

/* Inner content boxes must stay within their column.
   Lists inside visual-block (.compare, .feat-grid, etc.) get tightened so
   long bullet lists shrink instead of bleeding past the 1080 viewport. */
.visual-block, .terminal, .stat-list, .chat-box, .agent-grid,
.feat-grid, .feat-row, .compare, .tl-list, .quote-block, .tech-card {{
  max-height: 100%;
}}
.visual-block > *, .compare .col > * {{ min-height: 0; }}

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
  position: absolute; bottom: 24px; right: 40px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 8rem; font-weight: 800;
  color: var(--accent); opacity: 0.06; line-height: 1;
  pointer-events: none; z-index: 5;
}}

.status-pill {{
  position: absolute; top: 40px; left: 50%; transform: translateX(-50%);
  font-family: 'JetBrains Mono', monospace;
  font-size: 1.0rem; font-weight: 700;
  color: var(--accent3); background: {accent3}1a;
  border: 2px solid {accent3}4d;
  border-radius: 99px; padding: 8px 24px;
  letter-spacing: 0.18em; text-transform: uppercase; z-index: 20;
}}

/* Typography utilities — scaled up */
.badge {{
  display: inline-flex; align-items: center; gap: 10px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 1.0rem; font-weight: 700;
  color: var(--accent2); background: var(--surface);
  border: 2px solid var(--accent);
  border-radius: 99px; padding: 10px 24px;
  letter-spacing: 0.18em; text-transform: uppercase;
  width: fit-content;
}}

.title-xl {{
  font-size: clamp(4.0rem, 6.5vw, 6.5rem);
  font-weight: 900; line-height: 1.25; letter-spacing: -0.04em;
  color: var(--text1);
}}
.title-hero {{
  font-size: clamp(5.5rem, 8.5vw, 8.5rem);
  font-weight: 900; line-height: 1.2; letter-spacing: -0.05em;
  color: var(--text1);
}}
.subtitle {{
  font-size: 2.2rem; font-weight: 700;
  color: var(--accent2); line-height: 1.4;
}}
.body-text {{
  font-size: 1.6rem; line-height: 1.8;
  color: var(--text2); max-width: 720px;
  word-break: break-word;
}}
.caption {{
  font-family: 'JetBrains Mono', monospace;
  font-size: 1.2rem; color: var(--text2);
  letter-spacing: 0.1em; text-transform: uppercase;
}}

.grad-text {{
  background: linear-gradient(135deg, var(--accent), var(--accent2), var(--accent3));
  -webkit-background-clip: text; background-clip: text;
  -webkit-text-fill-color: transparent; color: transparent;
  /* Bug1 fix: force independent GPU layer to prevent parent blur bleeding into text rasterisation */
  will-change: transform; isolation: isolate; transform: translateZ(0);
  padding-bottom: 0.18em; margin-bottom: -0.18em;
}}
.outline-text {{
  -webkit-text-stroke: 2px var(--accent); color: transparent;
  padding-bottom: 0.18em; margin-bottom: -0.18em;
}}

/* Hero stat — for B1 BIG STAT pattern */
.stat-hero {{
  font-size: clamp(6.5rem, 9vw, 9.5rem);
  font-weight: 900; line-height: 1.25; letter-spacing: -0.05em;
  font-feature-settings: 'tnum';
  background: linear-gradient(135deg, var(--accent), var(--accent3));
  -webkit-background-clip: text; background-clip: text;
  -webkit-text-fill-color: transparent; color: transparent;
  padding-bottom: 0.18em; margin-bottom: -0.18em;
}}
.stat-suffix {{
  font-size: 3.0rem; font-weight: 700; color: var(--text2);
  margin-left: 0.4rem;
}}

/* Visual block — generic glass card wrapper */
.visual-block {{
  background: linear-gradient(135deg, var(--surface), {surface}b3);
  border: 2px solid {accent}33;
  border-radius: 32px;
  backdrop-filter: blur(12px);
  box-shadow: 0 40px 100px -20px var(--glow), inset 0 0 80px rgba(255,255,255,0.02);
  position: relative; overflow: visible;
  padding: 60px;
  width: 100%;
}}
.visual-block::before {{
  content: ''; position: absolute; top: 0; left: 0; right: 0; height: 1px;
  background: linear-gradient(90deg, transparent, var(--accent2), transparent);
  opacity: 0.6;
}}

/* Image frame — aspect ratio so visual-col never overflows its column */
.img-frame {{
  position: relative; border-radius: 24px;
  overflow: hidden; isolation: isolate;
  width: 100%; aspect-ratio: 16 / 10; max-height: 760px;
  box-shadow: 0 0 0 1px {accent}55, 0 30px 80px -20px var(--accent), 0 0 100px -30px var(--accent);
}}
.img-frame img {{
  width: 100%; height: 100%;
  object-fit: cover; object-position: center;
  display: block;
}}
.img-frame::after {{
  content: ''; position: absolute; inset: 0;
  background:
    linear-gradient(to bottom, rgba(0,0,0,0.35) 0%, transparent 25%),
    linear-gradient(to top, rgba(0,0,0,0.75) 0%, transparent 55%);
  pointer-events: none;
}}

.img-caption {{
  position: absolute; bottom: 24px; left: 24px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 1.1rem; color: var(--text1);
  background: rgba(0,0,0,0.75); backdrop-filter: blur(12px);
  border: 1px solid {accent}55;
  padding: 10px 20px; border-radius: 99px; z-index: 2;
}}

/* Terminal block — for B2 CODE pattern */
.terminal {{
  font-family: 'JetBrains Mono', monospace;
  background: rgba(0,0,0,0.65); border: 2px solid {accent}44;
  border-radius: 24px; padding: 40px 48px;
  font-size: 1.35rem; line-height: 1.8; color: var(--text2);
  box-shadow: 0 20px 50px -10px var(--glow);
  width: 100%;
}}
.terminal .dots {{ display: flex; gap: 10px; margin-bottom: 24px; }}
.terminal .dots i {{ width: 16px; height: 16px; border-radius: 50%; display: block; }}
.terminal .dots i:nth-child(1) {{ background: #ef4444; }}
.terminal .dots i:nth-child(2) {{ background: #fbbf24; }}
.terminal .dots i:nth-child(3) {{ background: #22c55e; }}
.terminal .k {{ color: var(--accent3); font-weight: 600; }}
.terminal .s {{ color: var(--accent2); }}
.terminal .c {{ color: var(--text2); opacity: 0.6; }}
.terminal .cursor {{ display: inline-block; width: 12px; height: 1.1em; background: var(--accent); vertical-align: -2px; }}

/* Feature grid — for B3 */
.feat-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 24px; width: 100%; }}
.feat-card {{
  padding: 32px; border-radius: 24px;
  background: linear-gradient(135deg, var(--surface), {surface}80);
  border: 1px solid {accent}33;
  transition: all 0.3s ease;
}}
.feat-card:hover {{
  transform: translateY(-4px);
  border-color: var(--accent2);
  box-shadow: 0 15px 40px -10px var(--glow);
}}
.feat-card .ic {{ font-size: 3rem; margin-bottom: 16px; }}
.feat-card .t  {{ font-weight: 700; color: var(--text1); margin-bottom: 8px; font-size: 1.5rem; }}
.feat-card .d  {{ font-size: 1.5rem; color: var(--text2); line-height: 1.6; word-break: break-word; }}

/* Comparison — for B4 */
.compare {{ display: grid; grid-template-columns: 1fr 1fr; gap: 32px; min-height: 0; width: 100%; }}
.compare .col {{ padding: 40px; border-radius: 28px; border: 2px solid {accent}33; background: var(--surface); transition: all 0.3s ease; overflow: visible; word-break: break-word; }}
.compare .col:hover {{ border-color: var(--accent2); transform: scale(1.02); }}
.compare .col h4 {{ font-family: 'JetBrains Mono', monospace; font-size: 1.2rem; letter-spacing: 0.18em; text-transform: uppercase; color: var(--accent2); margin-bottom: 24px; }}
.compare .col li {{ list-style: none; padding: 12px 0; color: var(--text2); font-size: 1.6rem; line-height: 1.6; word-break: break-word; overflow-wrap: anywhere; }}
.compare .col li::before {{ content: '✓ '; color: var(--accent3); font-weight: 700; }}
.compare .col.bad li::before {{ content: '✗ '; color: #ef4444; }}

/* Timeline — for B5 */
.tl-list {{ position: relative; padding-left: 48px; width: 100%; }}
.tl-list::before {{ content: ''; position: absolute; left: 12px; top: 0; bottom: 0; width: 3px; background: linear-gradient(to bottom, var(--accent), {accent}33); }}
.tl-item {{ position: relative; padding: 16px 0 28px; }}
.tl-item::before {{ content: ''; position: absolute; left: -43px; top: 20px; width: 20px; height: 20px; border-radius: 50%; background: var(--accent); box-shadow: 0 0 0 6px {accent}33; }}
.tl-item .y {{ font-family: 'JetBrains Mono', monospace; font-size: 1.2rem; color: var(--accent2); letter-spacing: 0.1em; }}
.tl-item .t {{ font-size: 1.6rem; font-weight: 700; color: var(--text1); margin: 8px 0; }}
.tl-item .d {{ color: var(--text2); font-size: 1.3rem; line-height: 1.6; word-break: break-word; }}

/* Quote — for B6 */
.quote-block {{ position: relative; padding: 40px 60px; width: 100%; }}
.quote-block::before {{
  content: '"'; position: absolute; left: -20px; top: -60px;
  font-size: 18rem; line-height: 1; color: var(--accent);
  opacity: 0.18; font-family: Georgia, serif;
}}
.quote-text {{ font-size: 2.5rem; font-style: italic; line-height: 1.6; color: var(--text1); max-width: 800px; word-break: break-word; }}
.quote-attr {{ font-family: 'JetBrains Mono', monospace; font-size: 1.3rem; color: var(--accent2); margin-top: 32px; letter-spacing: 0.1em; }}
.quote-attr::before {{ content: '— '; }}

/* Glass stat-list (horizontal stack cards like 4x, 12x, 50% column) */
.stat-list {{
  display: flex; flex-direction: column; gap: 24px; width: 100%;
}}
.stat-list-card {{
  display: flex; align-items: center; gap: 32px; flex-wrap: wrap;
  padding: 32px 36px; border-radius: 28px;
  background: linear-gradient(135deg, {surface}a3, {surface}66);
  border: 1px solid {accent}33;
  backdrop-filter: blur(12px);
  box-shadow: 0 15px 45px -10px var(--glow), inset 0 0 40px rgba(255,255,255,0.01);
  position: relative; overflow: visible;
  transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
}}
.stat-list-card:hover {{
  transform: translateY(-4px) scale(1.01);
  box-shadow: 0 20px 50px -5px var(--accent), inset 0 0 40px rgba(255,255,255,0.02);
  border-color: var(--accent2);
}}
.stat-list-card::before {{
  content: ''; position: absolute; top: 0; left: 0; right: 0; height: 1px;
  background: linear-gradient(90deg, transparent, var(--accent2), transparent);
  opacity: 0.5;
}}
.stat-list-card .ic-wrap {{
  display: flex; align-items: center; justify-content: center;
  width: 76px; height: 76px; border-radius: 18px;
  background: {accent}1c; border: 2px solid {accent}4d;
  color: var(--accent2); font-size: 2.2rem; flex-shrink: 0;
}}
.stat-list-card .num {{
  font-size: 4.2rem; font-weight: 900;
  color: var(--accent); font-family: 'JetBrains Mono', monospace;
  line-height: 1; min-width: 120px; text-shadow: 0 0 15px var(--glow);
  flex-shrink: 0;
}}
.stat-list-card .details {{
  display: flex; flex-direction: column; gap: 6px;
  min-width: 0; flex: 1;
}}
.stat-list-card .title {{
  font-size: 1.6rem; font-weight: 700; color: var(--text1); line-height: 1.3;
}}
.stat-list-card .desc {{
  font-size: 1.5rem; color: var(--text2); opacity: 0.85;
}}

/* ───────────────── PREMIUM COMPONENT EXTENSIONS (FROM IMAGE REFERENCE) ───────────────── */

/* Chat Dialogue Simulator (Scene 1) */
.chat-box {{
  display: flex; flex-direction: column; gap: 20px; width: 100%; position: relative;
}}
.chat-bubble {{
  padding: 24px 28px; border-radius: 24px; max-width: 85%; line-height: 1.6; font-size: 1.35rem;
  box-shadow: 0 15px 35px rgba(0,0,0,0.35); position: relative;
  border: 1px solid rgba(255,255,255,0.08); color: var(--text1);
}}
.chat-bubble.user {{
  align-self: flex-end;
  background: linear-gradient(135deg, rgba(236,72,153,0.15), rgba(236,72,153,0.05));
  border-color: rgba(236, 72, 153, 0.3);
}}
.chat-bubble.ai {{
  align-self: flex-start;
  background: linear-gradient(135deg, var(--surface), rgba(0,0,0,0.45));
  border-color: {accent}4d;
}}
.chat-bubble .sender-tag {{
  font-family: 'JetBrains Mono', monospace; font-size: 0.85rem; font-weight: 700;
  margin-bottom: 8px; letter-spacing: 0.1em; text-transform: uppercase;
}}
.chat-bubble.user .sender-tag {{ color: var(--accent2); }}
.chat-bubble.ai .sender-tag {{ color: var(--accent3); }}
.chat-footer-pill {{
  align-self: center; font-family: 'JetBrains Mono', monospace; font-size: 1.1rem;
  padding: 12px 28px; border-radius: 99px; background: rgba(0,0,0,0.45);
  border: 1px solid rgba(255,255,255,0.08); color: var(--text2); text-align: center;
  width: 100%; margin-top: 12px;
}}

/* 3-Column Glass Row (Scene 2) */
.feat-row {{
  display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 28px; width: 100%; margin-top: 40px;
}}
.glass-card {{
  padding: 40px 32px; border-radius: 28px; text-align: center;
  background: linear-gradient(135deg, var(--surface), {surface}66);
  border: 1px solid {accent}22; backdrop-filter: blur(16px);
  transition: all 0.3s ease; position: relative; overflow: visible;
}}
.glass-card:hover {{
  transform: translateY(-8px); border-color: var(--accent2);
  box-shadow: 0 25px 60px -10px var(--glow);
}}
.glass-card .emoji {{ font-size: 3.5rem; margin-bottom: 20px; display: block; filter: drop-shadow(0 0 8px var(--glow)); }}
.glass-card .title {{ font-size: 1.55rem; font-weight: 700; color: var(--text1); margin-bottom: 12px; }}
.glass-card .desc {{ font-size: 1.5rem; color: var(--text2); line-height: 1.6; }}

/* Google I/O tech card (Scene 3) */
.tech-card {{
  background: linear-gradient(135deg, rgba(15,10,25,0.85), rgba(5,3,10,0.95));
  border: 2px solid {accent}4d; border-radius: 32px; padding: 48px;
  box-shadow: 0 40px 100px -15px var(--glow); position: relative; width: 100%;
}}
.tech-card .brand {{
  font-size: 3.8rem; font-weight: 900; letter-spacing: -0.02em; margin-bottom: 20px;
  background: linear-gradient(90deg, #4285F4, #EA4335, #FBBC05, #34A853);
  -webkit-background-clip: text; background-clip: text; -webkit-text-fill-color: transparent;
}}
.tech-card .meta {{
  display: flex; align-items: center; gap: 12px; font-family: 'JetBrains Mono', monospace;
  font-size: 1.15rem; color: var(--accent3); margin-bottom: 28px;
}}
.tech-card .bullets {{
  display: flex; flex-direction: column; gap: 14px; margin-bottom: 36px;
  font-size: 1.35rem; color: var(--text2); line-height: 1.7; text-align: left;
}}
.tech-card .tags {{
  display: flex; flex-wrap: wrap; gap: 12px;
}}
.tech-card .tag {{
  font-family: 'JetBrains Mono', monospace; font-size: 0.95rem; font-weight: 600;
  padding: 8px 18px; border-radius: 99px;
  background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.12);
  color: var(--text1);
}}

/* Multi-Agent Collaboration Coordinator (Scene 5) */
.agent-grid {{
  display: grid; grid-template-columns: 1fr 1fr; gap: 24px; width: 100%; position: relative;
}}
.agent-card {{
  padding: 32px; border-radius: 24px;
  background: linear-gradient(135deg, var(--surface), {surface}66);
  border: 1px solid {accent}33; position: relative; text-align: left;
}}
.agent-card .header-wrap {{
  display: flex; align-items: center; gap: 16px; margin-bottom: 16px;
}}
.agent-card .icon {{ font-size: 2.8rem; filter: drop-shadow(0 0 6px var(--glow)); }}
.agent-card .role {{
  font-family: 'JetBrains Mono', monospace; font-size: 1.05rem; font-weight: 700;
  letter-spacing: 0.1em; text-transform: uppercase; color: var(--accent2);
}}
.agent-card .desc {{
  font-size: 1.25rem; color: var(--text2); line-height: 1.6;
}}
.agent-grid-center-pill {{
  position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%);
  font-family: 'JetBrains Mono', monospace; font-size: 1.05rem; font-weight: 700;
  color: #000; background: var(--accent3); border: 2px solid var(--accent);
  padding: 10px 24px; border-radius: 99px; z-index: 5;
  box-shadow: 0 0 25px var(--accent3);
  letter-spacing: 0.1em; text-transform: uppercase;
}}

/* Glow and animation helpers */
.glow-border {{ box-shadow: 0 0 30px -4px var(--accent); }}
.glow-text {{ text-shadow: 0 0 20px var(--accent2); }}
.glow-orb {{ position: absolute; border-radius: 50%; filter: blur(80px); pointer-events: none; }}

/* ═══════════════════════════════════════════════════
   MAGIC-UI INSPIRED AMBIENT LAYERS
   Use absolutely-positioned inside .scene to fill empty space.
   ═══════════════════════════════════════════════════ */

/* Floating colored orbs — 3 sizes for depth (with gentle breathing animation) */
@keyframes orb-breath {{
  0%, 100% {{ transform: scale(1) translate(0, 0); }}
  50% {{ transform: scale(1.08) translate(20px, -15px); }}
}}
.float-orb-lg {{
  position: absolute; width: 720px; height: 720px; border-radius: 50%;
  filter: blur(120px); opacity: 0.48; pointer-events: none; z-index: 0;
  animation: orb-breath 12s ease-in-out infinite;
}}
.float-orb-md {{
  position: absolute; width: 420px; height: 420px; border-radius: 50%;
  filter: blur(90px); opacity: 0.38; pointer-events: none; z-index: 0;
  animation: orb-breath 10s ease-in-out infinite;
  animation-delay: -3s;
}}
.float-orb-sm {{
  position: absolute; width: 220px; height: 220px; border-radius: 50%;
  filter: blur(60px); opacity: 0.32; pointer-events: none; z-index: 0;
  animation: orb-breath 8s ease-in-out infinite;
  animation-delay: -5s;
}}

/* Animated grid pattern — adds depth + tech feel */
.animated-grid {{
  position: absolute; inset: 0; pointer-events: none; z-index: 0; opacity: 0.55;
  background-image:
    linear-gradient(rgba(255,255,255,0.075) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255,255,255,0.075) 1px, transparent 1px);
  background-size: 64px 64px;
  animation: grid-sweep 14s linear infinite;
  mask-image: radial-gradient(ellipse 70% 70% at 50% 50%, #000 0%, transparent 80%);
  -webkit-mask-image: radial-gradient(ellipse 70% 70% at 50% 50%, #000 0%, transparent 80%);
}}

/* Retro perspective grid — y2k/synthwave floor */
.retro-grid {{
  position: absolute; left: 0; right: 0; bottom: 0; height: 50%;
  pointer-events: none; z-index: 0; opacity: 0.45;
  background-image:
    linear-gradient(var(--accent2) 1px, transparent 1px),
    linear-gradient(90deg, var(--accent2) 1px, transparent 1px);
  background-size: 80px 80px;
  transform: perspective(600px) rotateX(60deg);
  transform-origin: bottom;
  mask-image: linear-gradient(to top, #000 0%, transparent 100%);
  -webkit-mask-image: linear-gradient(to top, #000 0%, transparent 100%);
}}

/* Aurora wave — soft gradient blob that drifts */
@keyframes aurora-drift {{
  0%, 100% {{ transform: translate(0, 0) rotate(0deg); }}
  33% {{ transform: translate(30px, -20px) rotate(20deg); }}
  66% {{ transform: translate(-25px, 15px) rotate(-15deg); }}
}}
.aurora-glow {{
  position: absolute; width: 80%; height: 60%; border-radius: 50%;
  filter: blur(140px); opacity: 0.48; pointer-events: none; z-index: 0;
  animation: aurora-drift 18s ease-in-out infinite;
  background: radial-gradient(circle, var(--accent) 0%, var(--accent2) 40%, transparent 70%);
}}

/* Light rays — radial beams from top */
.light-rays {{
  position: absolute; top: -40%; left: 50%; transform: translateX(-50%);
  width: 1500px; height: 1500px; pointer-events: none; z-index: 0; opacity: 0.35;
  background: conic-gradient(from 180deg at 50% 50%,
    transparent 0deg, var(--accent) 30deg, transparent 60deg,
    transparent 120deg, var(--accent2) 150deg, transparent 180deg,
    transparent 240deg, var(--accent3) 270deg, transparent 300deg);
  filter: blur(60px);
  mask-image: radial-gradient(circle, #000 0%, transparent 60%);
  -webkit-mask-image: radial-gradient(circle, #000 0%, transparent 60%);
}}

/* Ghost text — large thematic word at very low opacity */
.ghost-text {{
  position: absolute; font-family: 'Inter', system-ui, sans-serif;
  font-size: clamp(18rem, 28vw, 32rem); font-weight: 900;
  color: var(--accent); opacity: 0.085; line-height: 0.85;
  letter-spacing: -0.05em; pointer-events: none; user-select: none;
  z-index: 0; white-space: nowrap;
  animation: floating 16s ease-in-out infinite;
}}

/* Marquee strip — auto-scrolling tags/keywords */
@keyframes marquee-scroll {{
  0% {{ transform: translateX(0); }}
  100% {{ transform: translateX(-50%); }}
}}
.marquee-strip {{
  position: absolute; left: 0; right: 0; overflow: hidden;
  display: flex; gap: 0; pointer-events: none; z-index: 1;
  mask-image: linear-gradient(90deg, transparent 0%, #000 8%, #000 92%, transparent 100%);
  -webkit-mask-image: linear-gradient(90deg, transparent 0%, #000 8%, #000 92%, transparent 100%);
}}
.marquee-strip .track {{
  display: flex; gap: 36px; white-space: nowrap;
  animation: marquee-scroll 28s linear infinite;
  padding-right: 36px;
}}
.marquee-strip .pill {{
  display: inline-flex; align-items: center; gap: 10px;
  font-family: 'JetBrains Mono', monospace; font-size: 1.05rem; font-weight: 700;
  letter-spacing: 0.16em; text-transform: uppercase;
  color: var(--accent2); background: rgba(255,255,255,0.04);
  border: 1px solid {accent}33; border-radius: 99px;
  padding: 10px 22px;
}}
.marquee-strip .pill::before {{
  content: "◆"; color: var(--accent3); font-size: 0.7em;
}}

/* Big number callout — for hero scene with stat focus */
.mega-num {{
  font-family: 'Inter', system-ui, sans-serif;
  font-size: clamp(10rem, 18vw, 18rem);
  font-weight: 900; line-height: 0.9; letter-spacing: -0.06em;
  background: linear-gradient(135deg, var(--accent) 0%, var(--accent2) 40%, var(--accent3) 100%);
  -webkit-background-clip: text; background-clip: text;
  -webkit-text-fill-color: transparent; color: transparent;
  text-shadow: 0 0 80px var(--glow);
}}

/* Particle field — small dots randomly placed for cosmic texture */
.particle-field {{
  position: absolute; inset: 0; pointer-events: none; z-index: 0; opacity: 0.5;
  background-image:
    radial-gradient(2px 2px at 20% 30%, var(--accent3), transparent),
    radial-gradient(1px 1px at 40% 70%, var(--accent2), transparent),
    radial-gradient(1.5px 1.5px at 60% 20%, var(--accent), transparent),
    radial-gradient(1px 1px at 80% 80%, var(--accent3), transparent),
    radial-gradient(2px 2px at 30% 90%, var(--accent2), transparent),
    radial-gradient(1px 1px at 90% 50%, var(--accent), transparent),
    radial-gradient(1.5px 1.5px at 10% 60%, var(--accent3), transparent),
    radial-gradient(1px 1px at 70% 10%, var(--accent2), transparent);
  background-size: 100% 100%;
  animation: floating 20s ease-in-out infinite;
}}

/* Hero stat banner — full-bleed centered showcase */
.hero-stat-banner {{
  position: absolute; inset: 0;
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  text-align: center; gap: 32px; z-index: 5;
  padding: 100px 120px;
}}

/* Bento grid — for dashboards / feature showcases */
.bento-grid {{
  display: grid; grid-template-columns: repeat(4, 1fr); grid-auto-rows: minmax(180px, auto);
  gap: 24px; width: 100%;
}}
.bento-cell {{
  background: linear-gradient(135deg, var(--surface), {surface}80);
  border: 1px solid {accent}33;
  border-top: 3px solid {accent};
  border-radius: 28px; padding: 32px;
  position: relative; overflow: hidden;
  transition: all 0.4s cubic-bezier(0.25, 0.8, 0.25, 1);
}}
/* Bug3 fix: distinct accent colors per cell position + icon/title/desc sub-selectors */
.bento-cell:nth-child(2) {{ border-top-color: var(--accent2); }}
.bento-cell:nth-child(3) {{ border-top-color: #38bdf8; }}
.bento-cell:nth-child(4) {{ border-top-color: #4ade80; }}
.bento-cell:nth-child(5) {{ border-top-color: #f472b6; }}
.bento-cell .ic  {{ font-size: 3.2rem; margin-bottom: 14px; display: block; filter: drop-shadow(0 0 8px var(--glow)); }}
.bento-cell .t   {{ font-size: 1.55rem; font-weight: 700; color: var(--text1); margin-bottom: 8px; }}
.bento-cell .d   {{ font-size: 1.5rem; color: var(--text2); line-height: 1.5; }}
.bento-cell.wide {{ grid-column: span 2; }}
.bento-cell.tall {{ grid-row: span 2; }}
.bento-cell.hero {{ grid-column: span 2; grid-row: span 2; background: linear-gradient(135deg, var(--surface), {accent}1a); border-color: {accent}66; border-top-color: {accent}; }}
.bento-cell:hover {{ transform: translateY(-4px); border-color: var(--accent2); box-shadow: 0 20px 50px -10px var(--glow); }}

/* Premium UI/UX Pro Max Animations & Shimmers */
@keyframes floating {{
  0%, 100% {{ transform: translateY(0px) rotate(0deg); }}
  50% {{ transform: translateY(-12px) rotate(0.5deg); }}
}}
@keyframes pulse-sparkle {{
  0%, 100% {{ opacity: 0.2; transform: scale(0.7); filter: drop-shadow(0 0 2px var(--accent3)); }}
  50% {{ opacity: 1; transform: scale(1.2); filter: drop-shadow(0 0 10px var(--accent3)); }}
}}
@keyframes grid-sweep {{
  0% {{ background-position: 0 0; }}
  100% {{ background-position: 48px 48px; }}
}}
@keyframes shimmer-sweep {{
  0% {{ left: -150%; }}
  100% {{ left: 150%; }}
}}
@keyframes cursor-blink {{
  0%, 100% {{ opacity: 0; }}
  50% {{ opacity: 1; }}
}}
.cursor-blink {{
  animation: cursor-blink 0.8s step-end infinite;
  color: var(--accent);
  margin-left: 4px;
  display: inline-block;
}}
.cursor-solid {{
  animation: none;
  opacity: 1;
  color: var(--accent);
  margin-left: 4px;
  display: inline-block;
}}
.cursor-hide {{
  animation: none;
  opacity: 0;
  margin-left: 4px;
  display: inline-block;
}}

.breath {{
  animation: floating 6s ease-in-out infinite;
}}
.shimmer-fast {{
  position: relative;
  overflow: hidden;
}}
.shimmer-fast::after {{
  content: '';
  position: absolute;
  top: 0;
  left: -150%;
  width: 50%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255,255,255,0.22), transparent);
  transform: skewX(-25deg);
  animation: shimmer-sweep 3.2s infinite ease-in-out;
  pointer-events: none;
}}
.y2k-sparkle {{
  position: absolute;
  width: 28px;
  height: 28px;
  background: var(--accent3);
  clip-path: polygon(50% 0%, 62% 38%, 100% 50%, 62% 62%, 50% 100%, 38% 62%, 0% 50%, 38% 38%);
  animation: pulse-sparkle 2.2s infinite ease-in-out;
  pointer-events: none;
  z-index: 10;
}}
.glow-card {{
  border: 1px solid {accent}33;
  box-shadow: 0 10px 40px 0 var(--glow);
  transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
}}
.glow-card:hover {{
  border-color: var(--accent2);
  box-shadow: 0 20px 60px -5px var(--accent), 0 0 30px var(--accent2);
  transform: translateY(-6px) scale(1.015);
}}
/* Premium UX/UI Custom layouts */
.accent-bar {{
  width: 80px; height: 4px; background: var(--accent);
  border-radius: 2px; margin-top: 16px;
  box-shadow: 0 0 12px var(--accent);
}}
.formula-stack {{
  display: flex; align-items: center; gap: 12px; flex-wrap: wrap;
  margin: 32px 0; font-family: 'JetBrains Mono', monospace; font-weight: 700;
}}
.formula-pill {{
  display: inline-flex; align-items: center; gap: 8px;
  padding: 10px 24px; border-radius: 99px; font-size: 1.2rem;
  border: 2px solid rgba(255,255,255,0.1);
  color: var(--text1); text-transform: uppercase;
}}
.formula-pill.pink {{ background: rgba(236,72,153,0.15); border-color: rgba(236,72,153,0.4); color: #f472b6; }}
.formula-pill.yellow {{ background: rgba(253,224,71,0.15); border-color: rgba(253,224,71,0.4); color: #fde047; }}
.formula-pill.green {{ background: rgba(74,222,128,0.15); border-color: rgba(74,222,128,0.4); color: #4ade80; }}
.formula-pill.blue {{ background: rgba(56,189,248,0.15); border-color: rgba(56,189,248,0.4); color: #38bdf8; }}
.formula-operator {{
  font-size: 1.6rem; color: rgba(255,255,255,0.3); padding: 0 4px;
}}
.command-pill {{
  display: flex; align-items: center; gap: 16px;
  background: rgba(253,224,71,0.06); border: 2px solid rgba(253,224,71,0.25);
  padding: 18px 32px; border-radius: 16px; font-size: 1.35rem;
  color: #fde047; font-weight: 600; margin-bottom: 24px; width: 100%;
}}
.step-list {{
  display: flex; flex-direction: column; gap: 16px; width: 100%;
}}
.step-item {{
  display: flex; align-items: flex-start; gap: 20px; font-size: 1.8rem; line-height: 1.6;
  color: var(--text1, #e8e8f0);
}}
.step-circle {{
  display: flex; align-items: center; justify-content: center;
  width: 38px; height: 38px; border-radius: 50%;
  background: var(--accent); color: #fff; font-weight: 800;
  font-size: 1.4rem; flex-shrink: 0; margin-top: 2px;
}}
.bento-3x2 {{
  display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; width: 100%;
}}

/* ── Contrast safety net — override any LLM-generated low-contrast text ── */
.scene .body-text,
.scene .subtitle,
.scene .caption,
.scene .feat-card p,
.scene .feat-card li,
.scene .feat-card div,
.scene .visual-block p,
.scene .visual-block li,
.scene .visual-block div:not(.stat-hero):not(.stat-suffix):not([class*="bracket"]):not(.layout):not(.info-col):not(.visual-col),
.scene .tl-item .t,
.scene .tl-item div,
.scene .quote-text,
.scene .compare p,
.scene .compare div,
.scene .stat-list-card div:not(.stat-hero):not(.stat-suffix),
.scene .bento-cell p,
.scene .bento-cell div,
.scene .step-item,
.scene .step-item div,
.scene .step-list,
.scene .command-pill,
.scene .formula-pill,
.scene p,
.scene li,
.scene span:not(.scene-num):not(.icon):not(.cursor):not([class*="bracket"]):not(.badge):not(.stat-suffix) {{
  color: var(--text1, #e8e8f0) !important;
  text-shadow: 0 1px 6px rgba(0,0,0,0.8);
}}
.scene .body-text,
.scene .subtitle,
.scene .caption {{
  font-size: max(1.4rem, 1em);
}}
.scene .stat-hero,
.scene .stat-suffix {{
  color: var(--accent, #f97316) !important;
  text-shadow: 0 0 20px rgba(249,115,22,0.4);
}}
/* NUCLEAR override: any inline dark color forced to white */
.scene [style*="color:#0"],
.scene [style*="color: #0"],
.scene [style*="color:#1"],
.scene [style*="color: #1"],
.scene [style*="color:#2"],
.scene [style*="color: #2"],
.scene [style*="color:#3"],
.scene [style*="color: #3"],
.scene [style*="color:#4"],
.scene [style*="color: #4"],
.scene [style*="color:#5"],
.scene [style*="color: #5"],
.scene [style*="color:rgb(0"],
.scene [style*="color: rgb(0"],
.scene [style*="color:rgba(0"],
.scene [style*="color: rgba(0"],
.scene [style*="color:black"],
.scene [style*="color: black"] {{
  color: var(--text1, #e8e8f0) !important;
  text-shadow: 0 1px 6px rgba(0,0,0,0.85) !important;
}}
.scene [style*="color:#fff"],
.scene [style*="color: #fff"],
.scene [style*="color:white"],
.scene [style*="color: white"] {{
  text-shadow: 0 1px 6px rgba(0,0,0,0.7) !important;
}}

/* Chunked Subtitle Styles — one short line at a time, fades in/out */
.techbeat-subtitles {{
  position: absolute;
  bottom: 72px;
  left: 50%;
  transform: translateX(-50%);
  width: auto;
  max-width: 90%;
  z-index: 1000;
  pointer-events: none;
  text-align: center;
}}
.sub-scene {{
  display: none;
  position: relative;
  min-height: 80px;
}}
.sub-chunk {{
  display: none;
  opacity: 0;
  position: relative;
  font-family: 'Inter', system-ui, -apple-system, sans-serif;
  font-size: 2.4rem;
  font-weight: 600;
  color: #ffffff;
  text-shadow: 0 0 14px rgba(0, 0, 0, 0.95), 0 4px 12px rgba(0, 0, 0, 0.8);
  letter-spacing: -0.01em;
  line-height: 1.3;
  white-space: normal;
  padding: 14px 36px;
  border-radius: 14px;
  background: linear-gradient(180deg, rgba(0, 0, 0, 0.45), rgba(0, 0, 0, 0.65));
  backdrop-filter: blur(6px);
  -webkit-backdrop-filter: blur(6px);
  border: 1px solid rgba(255, 255, 255, 0.08);
  box-shadow: 0 12px 32px -8px rgba(0, 0, 0, 0.6);
  max-width: 1400px;
}}
/* Active chunk: accent underline shimmer */
.sub-chunk::before {{
  content: "";
  position: absolute;
  left: 20%;
  right: 20%;
  bottom: 6px;
  height: 2px;
  background: linear-gradient(90deg, transparent, var(--accent, #f97316), transparent);
  opacity: 0.55;
  border-radius: 2px;
}}

/* ── Word-level karaoke (Whisper mode) ── */
.sub-line {{
  display: none;
  opacity: 0;
  position: relative;
  font-family: 'Inter', system-ui, -apple-system, sans-serif;
  font-size: 2.4rem;
  font-weight: 600;
  color: rgba(255,255,255,0.75);
  text-shadow: 0 0 14px rgba(0,0,0,0.95), 0 4px 12px rgba(0,0,0,0.8);
  letter-spacing: -0.01em;
  line-height: 1.3;
  white-space: normal;
  padding: 14px 36px;
  border-radius: 14px;
  background: linear-gradient(180deg, rgba(0,0,0,0.45), rgba(0,0,0,0.65));
  backdrop-filter: blur(6px);
  -webkit-backdrop-filter: blur(6px);
  border: 1px solid rgba(255,255,255,0.08);
  box-shadow: 0 12px 32px -8px rgba(0,0,0,0.6);
}}
.sub-line::before {{
  content: "";
  position: absolute;
  left: 20%; right: 20%; bottom: 6px;
  height: 2px;
  background: linear-gradient(90deg, transparent, #f97316, transparent);
  opacity: 0.6;
  border-radius: 2px;
}}
.sub-word {{
  display: inline;
  color: rgba(255,255,255,0.85);
  text-shadow: 0 1px 4px rgba(0,0,0,0.8);
  transition: none;
}}
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
- <style> override TỐI ĐA 60 dòng (chỉ scene-specific tweaks & keyframe animations).
- KHÔNG viết <script> chứa gsap.timeline (sẽ bị strip server-side).
- KHÔNG redeclare CSS class đã có sẵn.

CSS framework + GSAP timeline + Inter/JetBrains Mono font đã được inject server-side.

Class có sẵn (DÙNG, không tự viết):
LAYOUT: .scene/.split/.centered/.hero/.magazine/.data, .layout, .info-col, .visual-col
TEXT: .badge, .title-xl, .title-hero, .subtitle, .body-text, .caption, .grad-text, .outline-text, .mega-num
VISUAL BLOCKS: .visual-block, .img-frame, .img-caption, .terminal, .feat-grid, .feat-card, .compare, .tl-list, .tl-item, .quote-block, .quote-text, .stat-list, .stat-list-card, .chat-box, .chat-bubble, .agent-grid, .agent-card, .tech-card, .glass-card, .feat-row, .bento-grid, .bento-cell, .hero-stat-banner
CHROME: .corner-bracket (tl/tr/bl/br), .top-line, .scene-num, .scanlines, .status-pill
DECORATIVES: .float-orb-lg/.float-orb-md/.float-orb-sm, .aurora-glow, .animated-grid, .retro-grid, .light-rays, .particle-field, .ghost-text, .marquee-strip, .y2k-sparkle, .glow-orb
ANIMATIONS: .breath, .shimmer-fast, .glow-card, .glow-border, .glow-text

🌌 LẤP ĐẦY KHÔNG GIAN — MỖI scene 2-5 decoratives (position:absolute):
  • 1 .float-orb-lg/aurora-glow (background presence)
  • 1 .animated-grid/retro-grid/light-rays (texture)
  • 1 .ghost-text với thematic word (depth)
  • 2-3 .y2k-sparkle hoặc .float-orb-sm rải rác

🎨 THẨM MỸ CAO CẤP & HOẠT ẢNH CSS (STYLE LIKE A PRO):
- Tự do viết thêm các CSS keyframes tinh tế vào thẻ `<style>` để trang hoàng cho các visual block:
  - `@keyframes pulse-soft {{ 0%, 100% {{ transform: scale(1); filter: drop-shadow(0 0 10px var(--glow)); }} 50% {{ transform: scale(1.03); filter: drop-shadow(0 0 25px var(--accent)); }} }}`
  - `@keyframes shine-sweep {{ 0% {{ left: -100%; }} 100% {{ left: 100%; }} }}`
  - Áp dụng các keyframe này qua animation class tùy biến của riêng bạn!
- TẬN DỤNG hoàn hảo hệ màu CSS variables có sẵn: `var(--bg)`, `var(--bg2)`, `var(--surface)`, `var(--accent)`, `var(--accent2)`, `var(--accent3)`, `var(--text1)`, `var(--text2)`, `var(--glow)`.

🎬 SCENE #1 BẮT BUỘC HERO CINEMATIC (không split logo nhỏ):
  Dùng .scene.hero hoặc .scene.centered + .hero-stat-banner + 3-4 decoratives + .title-hero.grad-text/.mega-num + 2-3 .badge stack.

🔒 QUY TẮC ẢNH (an toàn, vẫn sáng tạo):
- Khi user prompt liệt kê IllustrationImage → ảnh PHẢI nằm trong <div class="img-frame"><img src="..."><span class="img-caption">...</span></div>.
- Bạn được TỰ DO chọn layout phù hợp:
  • .scene.split (50/50) — text bên này, ảnh bên kia (đảo trái/phải tùy ý)
  • .scene.magazine (7:5) — text 60%, ảnh 40% kéo dọc
  • .scene.data (1:1.4) — text nhỏ, ảnh lớn
  • .scene.hero — ảnh trong card phụ + title overlay phía dưới ảnh hoặc bên cạnh
  • .scene.centered — ảnh trung tâm với caption, text phía trên/dưới
  • Bento — ảnh ở 1 cell .bento-cell, text/stats ở các cell khác
- TUYỆT ĐỐI KHÔNG:
  ✗ <img> hay background-image full-bleed cho .scene (đè text)
  ✗ position:absolute cho .img-frame/img (ảnh tràn ra ngoài)
  ✗ Text overlay trực tiếp lên ảnh (caption nằm trong .img-frame thì OK)
- Mục tiêu: đa dạng layout giữa các scene, không lặp .split 8 lần.

⌨️ HIỆU ỨNG CHỮ HOẠT HÌNH CAO CẤP (PREMIUM GSAP EFFECTS):
- Hệ thống đã tích hợp hiệu ứng đánh chữ thông minh bằng thuộc tính HTML (bạn KHÔNG cần viết script):
  • ⌨️ **Typewriter (Đánh chữ từng phím)**: Thêm thuộc tính `data-effect="typewriter"` vào thẻ chữ và chèn ngay sau nó con trỏ `<span class="cursor-blink">|</span>` để nhấp nháy đồng bộ.
    Ví dụ: `<h1 id="sN-title" class="title-xl grad-text" data-effect="typewriter">Tiêu đề scene</h1><span class="cursor-blink">|</span>`
  • 🔄 **Word Rotation (Xoay từ khóa)**: Thêm `data-effect="word-rotate"` cùng danh sách từ cách nhau bằng dấu phẩy qua `data-words="từ_1,từ_2,từ_3"`.
    Ví dụ: `<span class="grad-text" data-effect="word-rotate" data-words="Tốc độ, Tiết kiệm, Bảo mật">Tốc độ</span><span class="cursor-blink">|</span>`
  • Cấm tạo con trỏ nhấp nháy mà không có thuộc tính `data-effect` đi kèm.

⚖️ QUY TẮC CÂN BẰNG THỊ GIÁC & CỐT LÕI BỐ CỤC (CHỐNG CHE KHUẤT CHỮ):
- **Cấm đặt Decoratives sai chỗ (Lỗi nghiêm trọng):** Tất cả background decoratives (.float-orb-*, .aurora-glow, .animated-grid, .retro-grid, .light-rays, .ghost-text, .particle-field) **CẤM TUYỆT ĐỐI** đặt bên trong `.visual-col` hoặc `.info-col`. Chúng **PHẢI** được đặt làm con trực tiếp của thẻ `.scene` (ngay trước thẻ đóng `</div>` của `.scene`) để tránh đè lên các cột chữ chính.
- **Quy định nghiêm ngặt về `.ghost-text` (Watermark nền):**
  * Chỉ được chứa **MỘT từ đơn cực ngắn từ 3-6 ký tự** (Ví dụ: "GSAP", "CORE", "FUTURE", "SPEED", "DATA"). Cấm tuyệt đối viết các cụm từ dài (như "Future of Animation") làm ghost-text vì kích thước chữ cực to sẽ tràn màn hình che sạch nội dung chính của slide.
  * Bắt buộc phải đặt ở góc lề ngoài qua inline style, ví dụ: style="bottom: -8%; right: -5%;" hoặc style="top: -10%; left: -5%;". CẤM đặt ở giữa màn hình hoặc các tọa độ 20%, 30%, 40% vì sẽ che khuất văn bản.
  * **CẤM override font-size quá to:** Mặc định class `.ghost-text` đã được định nghĩa font-size siêu lớn trong hệ thống. Cấm tuyệt đối dùng inline style để chỉnh font-size to hơn hoặc đặt vị trí đè lên các cột văn bản chính.
- **Chống Slide Trống & Nội Dung Đơn Điệu (Scene 3 & 4 fix):**
  * Khi dùng Mock Visual biểu đồ hoặc danh sách (B1-B8, B11-B20), **cấm** để cột chữ (info-col) trống trải chỉ có Title và Subtitle. Bắt buộc chèn thêm các tag mini stack ngang hoặc các khối bổ trợ ngăn nắp bên dưới mô tả.
  * Mỗi phần tử trong feature grid, bento grid, hay step list phải cực kỳ giàu chi tiết: bắt buộc có emoji sinh động + tiêu đề màu nổi bật + mô tả ít nhất 2 dòng + ví dụ nội dung thực tế (mock code, progress bar, tags), xếp ngăn nắp, đối xứng, đồng đều, không bị lệch.
  * **CẤM TUYỆT ĐỐI sử dụng placeholder mặc định hoặc copy-paste vô căn cứ:** Mỗi khối trực quan trong `.visual-col` phải mang thông tin/số liệu/dữ liệu thực tiễn được trích xuất trực tiếp từ kịch bản của scene (Ví dụ: nếu nói về GSAP thì phải có các thư viện thật như TweenLite, TweenMax, hoặc benchmark thật. Cấm bê nguyên văn placeholder "Benchmark 2024", "cost efficiency" của hệ thống vào).
- **Cân bằng khi có Ảnh Minh Họa (Scene 5 fix):** Khi dùng ảnh minh họa (`.img-frame`), cấm để cột chữ (`info-col`) trống trải chỉ có Title và Desc 1 dòng đơn điệu. Bắt buộc chèn thêm các thành phần bổ trợ ở dưới cột chữ như: một nhóm 2-3 badge mini stack ngang (`.badge`) chứa các tag kỹ thuật, hoặc một `.stat-list-card` mini hiển thị chỉ số liên quan đến ảnh, hoặc một timeline ngắn 2 mốc (`.tl-list`).
- **Đảm bảo Tương Phản & Độ Đọc Được của Chữ (Legibility & Contrast):**
  * Tất cả text chính dùng `var(--text1)`, phụ dùng `var(--text2)`.
  * Cấm tuyệt đối dùng màu chữ tối (màu xám tối `#333`, màu đen, hay opacity quá thấp < 0.5) trên nền tối.
  * Nếu text nằm trên bất kỳ gradient hoặc background sáng nào, bắt buộc thêm `text-shadow: 0 2px 8px rgba(0,0,0,0.9);` để đảm bảo người xem đọc được rõ nét từng chữ.

🎬 SCENE 1 = OPENING HERO (BẮT BUỘC ấn tượng):
- Scene #1 PHẢI là class="scene centered" hoặc class="scene hero" — KHÔNG được để trống visual-col chỉ vài chữ.
- BẮT BUỘC có: title-hero gradient cực to (.title-hero.grad-text) có thể dùng `data-effect="word-rotate"`, 2-3 badge/status-pill stack ngang, eyebrow .caption, decorative effect (status-pill phía trên + corner-bracket + breath animation).
- Nếu không có ảnh ở scene 1 → dùng VISUAL pattern B14 (tech-card) HOẶC B13 (3-column glass cards) HOẶC B11 (stat-list) ở visual-col để LẤP ĐẦY màn hình. KHÔNG được chỉ hiển thị 1 box logo nhỏ chính giữa.

🎨 BẮT BUỘC KHI DÙNG .bento-grid & CÁC KHỐI TRỰC QUAN (Bug3 fix & Tăng Cường Nội Dung):
- Mỗi .bento-cell PHẢI có ít nhất: <div class="ic">EMOJI</div> + <div class="t">tiêu đề</div> + <div class="d">mô tả ngắn</div>
- Mỗi cell dùng màu accent KHÁC NHAU qua inline style "border-top-color": cell 1=#eab308, cell 2=#38bdf8, cell 3=#4ade80, cell 4=#f472b6
- KHÔNG được để cell chỉ có 1 dòng text trần. Tối thiểu icon + tiêu đề + mô tả.
- Ví dụ đúng: <div class="bento-cell" style="border-top-color:#38bdf8"><div class="ic">⚡</div><div class="t">Tạo nhanh</div><div class="d">Xuất video trong 60 giây</div></div>

📝 THÊM VÍ DỤ NỘI DUNG THỰC TẾ (REAL-WORLD PREVIEWS / CODE / DATA):
- Để các khối trực quan không bị đơn điệu chỉ có chữ và icon, hãy chèn thêm các khối ví dụ nội dung thực tế (mock previews) bên dưới mô tả để lấp đầy không gian trống cực kỳ cinematic và chân thực:
  - Nếu nói về Code / Tech Stack: Chèn một khối `<pre style="font-family:'JetBrains Mono';font-size:0.9rem;opacity:0.85;margin-top:10px;">` hoặc `.terminal` có code React/TypeScript/JSON thực tế (ví dụ: code config, function export, dependency tag).
  - Nếu nói về Community / GitHub: Chèn mockup danh sách commit log mini, contributor list, contributors avatars mockup, pull request status pill hoặc tags `#github #pull-request`.
  - Nếu nói về Performance / Stats / Features: Chèn thanh tiến trình `<div class="progress-bar" style="width:100%;height:6px;background:rgba(255,255,255,0.1);border-radius:3px;margin-top:10px;overflow:hidden;"><div class="fill" style="width:85%;height:100%;background:var(--accent2);"></div></div>` hoặc các tag badge mini `<span class="badge-mini" style="font-size:0.8rem;padding:2px 8px;background:rgba(255,255,255,0.06);border-radius:4px;margin-right:6px;">#feature</span>` stack ngang.

🏁 SCENE CUỐI BẮT BUỘC (Bug4 fix):
- Scene cuối LUÔN dùng layout .scene.centered HOẶC .scene.hero với visual-col đầy đủ.
- visual-col CỦA SCENE CUỐI PHẢI chọn 1 trong 2 bố cục để tránh tràn dọc: HOẶC là 1 khối .quote-block duy nhất cực kỳ trang trọng, HOẶC là một nhóm card trực quan ngăn nắp (như 1 .stat-list có 2 stat-list-card, hoặc .feat-row có 3 glass-card). CẤM TUYỆT ĐỐI nhồi nhét cả trích dẫn và card tính năng trên cùng slide.
- Ví dụ visual-col scene cuối tối thiểu:
  <div class="stat-list">
    <div class="stat-list-card"><div class="ic-wrap">🚀</div><div class="num">10x</div><div class="details"><div class="title">Nhanh hơn</div><div class="desc">So với pipeline cũ</div></div></div>
    <div class="stat-list-card"><div class="ic-wrap">🌐</div><div class="num">∞</div><div class="details"><div class="title">Khả năng mở rộng</div><div class="desc">Không giới hạn scene</div></div></div>
  </div>


- Toàn bộ nội dung mỗi scene PHẢI vừa trong viewport 1920×1080. KHÔNG được để content dài hơn chiều cao 880px (sau khi trừ padding).
- Nếu danh sách bullet/feature dài hơn 4 dòng → CẮT GỌN xuống tối đa 4 mục, mỗi mục ngắn gọn.
- Title trong visual-block không lấy font-size > 2rem; bullet list không > 1.2rem để tránh tràn xuống.

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

<div class="scene LAYOUT" id="sceneN">  <!-- LAYOUT = chọn 1 trong: split, centered, hero, magazine, data -->
  <div class="layout">
    <div class="info-col">
      <div id="sN-badge" class="badge">PHẦN N</div>
      <h1 id="sN-title" class="title-xl">{{tiêu đề}}</h1>
      <p id="sN-subtitle" class="subtitle">{{phụ đề CỰC NGẮN ≤ 8 chữ}}</p>
      <p id="sN-desc" class="body-text">{{TỐI ĐA 1 dòng ngắn — KHÔNG copy narration}}</p>
    </div>
    <div class="visual-col">{{VISUAL}}</div>
  </div>
  <!-- 2-5 decoratives ở đây: .float-orb-md, .aurora-glow, .ghost-text, .y2k-sparkle... -->
  <div class="corner-bracket tl"></div><div class="corner-bracket tr"></div>
  <div class="corner-bracket bl"></div><div class="corner-bracket br"></div>
  <div class="top-line"></div>
  <span class="scene-num">0N</span>
</div>

BẮT BUỘC:
- 4 element id="sN-badge"/"sN-title"/"sN-subtitle"/"sN-desc" trong mỗi scene
- Mỗi scene MỘT LAYOUT KHÁC NHAU. Đa dạng split/centered/hero/magazine/data — KHÔNG lặp .split liên tục
- ⚠️ TUYỆT ĐỐI KHÔNG copy nguyên văn narration vào sN-desc. Narration đã hiển thị qua phụ đề karaoke phía dưới — copy lại sẽ ĐÈ NHAU XẤU XÍ.
- sN-subtitle ≤ 8 chữ (1 cụm danh từ hoặc tagline)
- sN-desc ≤ 12 chữ (1 dòng tóm tắt KHÁC narration — ví dụ: "Cảm biến WiFi · Edge AI" thay vì "Hệ thống dùng cảm biến WiFi kết hợp...")
- Dồn nội dung chi tiết vào VISUAL-COL (feat-grid, stat-list, terminal, chat-box, agent-grid...) — không nhồi text vào info-col

═══════ AUDIO ═══════
<audio id="vN" src="assets/pN.wav" data-start="0" data-duration="10" data-volume="1"></audio>
(start/duration sẽ được patch lại — placeholder OK.)

═══════ VISUAL-COL — chọn 1 pattern, ĐA DẠNG, KHÔNG để trống ═══════

A) Có IllustrationImage:
<div class="img-frame"><img src="{{path}}" alt=""><span class="img-caption">{{caption}}</span></div>

═══════ NHẮC CUỐI ═══════
- TUYỆT ĐỐI không override class .scanlines bằng màu sắc rực rỡ có opacity lớn (như var(--accent) 1px, transparent 2px), vì sẽ gây nhòe màn hình, rung giật và Moiré effect. Hãy sử dụng .scanlines mặc định vô cùng tinh tế của hệ thống.
- TUYỆT ĐỐI không dùng repeating-linear-gradient diagonal/angled stripes cho background của .scene, #root, body — chỉ dùng cho decorative nhỏ (border, badge).
- ĐỌC ĐƯỢC (CONTRAST): body text ≥ 1.4rem dùng var(--text1)/var(--text2). KHÔNG dùng màu tối trên nền tối. Text trên ảnh phải có text-shadow đậm."""


def build_system_prompt_full(theme: dict, scene_count: int = 0) -> str:
    """Rich prompt - for paid providers (Pinkyne, Anthropic) where token cost
    is fine. Asks for more elaborate decoration, motion, and creative
    visuals while still leveraging the server-injected CSS framework."""
    return f"""Bạn là chuyên gia thiết kế giao diện AWWWARDS & UI/UX PRO MAX — sinh ra HTML cinematic, lung linh, gây ấn tượng WOW tuyệt đối. Sinh `index.html` HOÀN CHỈNH cho theme **{theme['name']}**.

⚠️ TỐI ƯU HÓA TOKEN ĐỂ TRÁNH BỊ CẮT CỤT (TRUNCATED):
- Để tránh bị giới hạn 4096-token cắt cụt HTML giữa chừng (khiến hệ thống phải chèn placeholder basic cho các scene cuối 6, 7, 8):
  - Hãy viết mã HTML cực kỳ gọn gàng, súc tích.
  - KHÔNG viết custom CSS dài dòng hay lặp lại trong thẻ <style>. TẬN DỤNG 100% các class CSS tiện ích cực mạnh có sẵn trong framework (như .feat-grid, .terminal, .stat-list, .compare, .tl-list...).
  - Chỉ viết tối đa 35 dòng CSS override trong <style> cho các hiệu ứng/keyframes thực sự đặc biệt.
  - Tránh viết comment code dài dòng hay giải thích bằng văn bản ở đầu/cuối response.

⚠️ NGÔN NGỮ: TIẾNG VIỆT có dấu đầy đủ. Giữ NGUYÊN VĂN narration/title/visualDescription. Tiếng Anh chỉ cho class CSS / comment / tên biến.

═══════════════════════════════════════
🎯 BẠN CHỈ VIẾT: HTML structure + <style> override (≤35 dòng cho scene-specific). KHÔNG VIẾT <script> GSAP timeline.
═══════════════════════════════════════

HỆ THỐNG ĐÃ LO SẴN — KHÔNG CẦN BẠN VIẾT LẠI:
✅ CSS framework đầy đủ (variables theme, layouts, typography, decorative chrome) đã được inject server-side trước HTML của bạn.
✅ GSAP timeline với fade in/out scene, audio sync, scene visibility lifecycle sẽ được inject server-side với duration thật từ TTS.
✅ Font Inter + JetBrains Mono đã link sẵn.

⚠️ TUYỆT ĐỐI KHÔNG VIẾT `<script>` chứa `gsap.timeline`.

═══════════════════════════════════════
THEME — {theme['name'].upper()}
═══════════════════════════════════════

VIBE: {theme['vibe']}

ƯU TIÊN visual effects: {theme['fx']}.

CSS variables đã có (DÙNG var(--xxx), KHÔNG hardcode hex):
--bg, --bg2, --surface, --accent, --accent2, --accent3, --text1, --text2, --glow

═══════════════════════════════════════
✨ HIỆU ỨNG ĐỘNG & BIỆN PHÁP CHỐNG ĐÈ CHỮ / CLIPPING (QUAN TRỌNG):
═══════════════════════════════════════
- ⚠️ QUY TẮC BỐ CỤC CHỐNG ĐÈ CHỮ & CHE KHUẤT SCENE (BẮT BUỘC):
  • SCENE 1 (Opening/Intro): BẮT BUỘC bọc toàn bộ nội dung mô tả, chữ trắng trong cột trực quan của Scene 1 vào các khối card thiết kế cao cấp (như `.tech-card B14`, `.feat-card`, hoặc `.glass-card`) có nền màu tối/kính mờ để làm nổi bật và chống đè chữ. Hãy dùng hiệu ứng xuất hiện lần lượt bằng animation delay để lấp đầy không gian.
  • SCENE 2 (Xếp chồng dọc 3 ô): Nếu có 3 ô/thẻ nội dung (ví dụ các card tính năng "Tạm dừng cập nhật", "Chọn ngày cập nhật", "Giảm thiểu lỗi cập nhật" ở Scene 2), CẤM TUYỆT ĐỐI xếp hàng ngang. BẮT BUỘC xếp chồng dọc từ trên xuống dưới sử dụng `.stat-list` (với các `.stat-list-card shimmer-fast glow-card` có delay tăng dần) hoặc hàng dọc `.feat-column`. Điều này giúp tận dụng không gian dọc hoàn hảo, không bao giờ bị che khuất Badge "Phần 2" hoặc bị cắt xén ở trên.
  • SCENE 3, 4, 5 (Cấm chữ trắng trần & dùng hoạt ảnh lần lượt): CẤM TUYỆT ĐỐI viết các dòng chữ trắng trần/đơn điệu (naked text lines) trực tiếp trong `.visual-col` cho Scene 3, Scene 4 và Scene 5. Bắt buộc phải bọc mọi dòng mô tả/thành phần vào trong các ô có cấu trúc đẹp mắt có nền như `.glass-card`, `.feat-card`, `.stat-list-card`, hoặc `.step-item` và thiết lập thuộc tính `style="animation-delay: X.Xs"` để chúng xuất hiện tuần tự/lần lượt (staggered entrance) cực kỳ lung linh, chuyên nghiệp.

- ⚠️ QUY TẮC TUYỆT ĐỐI CHỐNG THIẾU ẢNH (BẮT BUỘC):
  - TUYỆT ĐỐI KHÔNG DÙNG THẺ <img> HOẶC CLASS .img-frame NẾU TRONG PROMPT NGƯỜI DÙNG KHÔNG CÓ DÒNG `IllustrationImage: assets/...`.
  - Nếu không có dòng `IllustrationImage: assets/...`, cấm tuyệt đối việc tự tạo đường dẫn ảnh giả. Bắt buộc dùng mock visual phong phú hoàn toàn bằng HTML/CSS (B1-B8, B11-B15) để lấp đầy .visual-col. Việc để xuất hiện khung đen trống hoặc icon ảnh lỗi là cấm kỵ.
- Chúng ta sử dụng framework có sẵn các class động cực kỳ lung linh:
  - `.breath`: Tạo chuyển động bay bổng, nhịp thở êm ái. Hãy áp dụng cho các card như `.visual-block`, `.terminal`, `.feat-card`, `.compare`, `.quote-block` hoặc các ảnh `.img-frame`.
  - `.glow-card`: Viền neon lung linh tỏa sáng rực rỡ, kèm hiệu ứng 3D co giãn phóng to khi rê chuột cực kỳ mượt mà.
  - `.shimmer-fast`: Tạo hiệu ứng vệt sáng quét ngang thời thượng trên card (rất hợp với `.stat-list-card`).
  - `.y2k-sparkle`: Chèn ngôi sao lấp lánh vector retro. Ví dụ chèn vào trong visual block: `<span class="y2k-sparkle" style="top: 15%; left: 10%;"></span>`. Lưu ý: Container chứa ngôi sao sparkle phải có `position: relative`!
  - `.terminal .cursor`: Dùng class `cursor` nhấp nháy cho terminal: `<div>$ <span class="cursor"></span></div>`.
- 🎨 HƯỚNG DẪN VIẾT KEYFRAMES & CUSTOM STYLING (STYLE LIKE A PRO):
  Để tạo hoạt ảnh và phong cách độc bản Awwwards cực đỉnh mà không cần dùng script, bạn BẮT BUỘC tự viết thêm các keyframe CSS tinh tế trong `<style>`:
  • 🌟 **Neon Border Glow Sweep (Quét sáng viền neon)**:
    `@keyframes neon-glow {{ 0%, 100% {{ border-color: rgba(255,255,255,0.08); box-shadow: 0 0 15px var(--glow); }} 50% {{ border-color: var(--accent2); box-shadow: 0 0 35px var(--accent); }} }}`
    (Áp dụng cho `.visual-block`, `.tech-card`, `.feat-card`).
  • 🌊 **Aurora Grid Mesh Drift (Sóng ánh sáng trôi lững lờ)**:
    `@keyframes aurora-mesh {{ 0%, 100% {{ transform: translate(0, 0) scale(1) rotate(0deg); }} 50% {{ transform: translate(30px, -20px) scale(1.05) rotate(5deg); }} }}`
    (Áp dụng cho `.aurora-glow` hoặc các gradient orbs).
  • 💫 **Y2K Retro Blink Stars (Ngôi sao lấp lánh kiểu Y2K)**:
    `@keyframes star-blink {{ 0%, 100% {{ opacity: 0.2; transform: scale(0.7) rotate(0deg); }} 50% {{ opacity: 1; transform: scale(1.2) rotate(45deg); }} }}`
    (Áp dụng cho `.y2k-sparkle` để tạo nhấp nháy retro).
  • 🎨 **Kinetic Font Gradient (Chữ chuyển màu sống động)**:
    `@keyframes grad-shift {{ 0% {{ background-position: 0% 50%; }} 50% {{ background-position: 100% 50%; }} 100% {{ background-position: 0% 50%; }} }}`
    (Cho chữ gradient có `background-size: 200% auto; animation: grad-shift 6s ease infinite`).
- 💎 MỸ THUẬT THEME ĐẶC TRƯNG:
  • *Cyberpunk / Sci-fi (cam, cyan, pulse)*: Dùng viền neon sắc nét, matrix scan lines, ascii elements, chat simulator, terminal code.
  • *Luxury Magazine (gold-editorial)*: Dùng chữ serif drop-cap thanh lịch, border cực mỏng sang trọng (`1px solid rgba(234,179,8,0.15)`), chữ champagne gold gradient.
  • *Calm Glassmorphism (aurora-mint, y2k-magenta)*: Dùng card bo tròn mềm mại (`border-radius:32px`), orbs lung linh, `backdrop-filter: blur(20px)`, nhịp thở `.breath` nhẹ nhàng.
- 🛡️ CHỐNG ĐÈ CHỮ / MẤT NÉT GLOW:
  - Do có hiệu ứng viền phát sáng (box-shadow neon) rực rỡ, chúng ta đã set `overflow: visible` cho `.visual-block` và `.stat-list-card`. Tuyệt đối KHÔNG override lại thành `overflow: hidden` trên các card này, để ánh sáng viền không bị cắt cụt.
  - Hãy căn chỉnh khoảng cách, padding hợp lý để các card không nằm quá sát lề màn hình hoặc đè lên nhau.
  - Với các con số thống kê hoặc chữ dài, tuyệt đối không lạm dụng các size chữ quá khổng lồ hoặc nhồi nhét quá nhiều chữ trong các khối hẹp để tránh chữ bị đè chèn lấp nhau.

- ⌨️ HIỆU ỨNG CHỮ HOẠT HÌNH CAO CẤP (PREMIUM GSAP EFFECTS):
  Hệ thống đã tích hợp sẵn hiệu ứng đánh chữ thông minh bằng thuộc tính HTML (bạn KHÔNG cần viết script):
  • ⌨️ **Typewriter (Đánh chữ từng phím)**: Thêm thuộc tính `data-effect="typewriter"` vào thẻ chữ và chèn ngay sau nó con trỏ `<span class="cursor-blink">|</span>` để nhấp nháy đồng bộ tự động.
    Ví dụ: `<h1 id="sN-title" class="title-xl grad-text" data-effect="typewriter">Tiêu đề scene</h1><span class="cursor-blink">|</span>`
  • 🔄 **Word Rotation (Xoay từ khóa)**: Thêm `data-effect="word-rotate"` cùng danh sách từ cách nhau bằng dấu phẩy qua `data-words="từ_1,từ_2,từ_3"`.
    Ví dụ: `<span class="grad-text" data-effect="word-rotate" data-words="Tốc độ, Tiết kiệm, Bảo mật">Tốc độ</span><span class="cursor-blink">|</span>`
  • Cấm tuyệt đối việc tạo con trỏ nhấp nháy mà không có thuộc tính `data-effect` đi kèm.

- ⚖️ QUY TẮC CÂN BẰNG THỊ GIÁC & CỐT LÕI BỐ CỤC (CHỐNG CHE KHUẤT CHỮ & TRÀN VIỀN):
  • **Cấm đặt Decoratives sai chỗ (Lỗi cực kỳ nghiêm trọng):** Tất cả background decoratives (.float-orb-*, .aurora-glow, .animated-grid, .retro-grid, .light-rays, .ghost-text, .particle-field) **CẤM TUYỆT ĐỐI** đặt bên trong `.visual-col` hoặc `.info-col`. Chúng **PHẢI** được đặt làm con trực tiếp của thẻ `.scene` (ngay trước thẻ đóng `</div>` của `.scene`) để làm nền phía sau, không được chen vào các cột nội dung làm đè và che khuất chữ.
  • **Chống tràn dọc và che khuất bởi phụ đề (BẮT BUỘC):**
    * **Mật độ nội dung:** Mọi nội dung của slide bắt buộc phải nằm gọn gàng trong chiều cao viewport khả dụng để không bao giờ đè lên phụ đề ở vùng dưới đáy màn hình (cách đáy 150px).
    * **Quy tắc tuyệt đối cho `.scene.centered` (layout căn giữa):** CẤM TUYỆT ĐỐI nhồi nhét đồng thời cả khối trích dẫn `.quote-block` và các thẻ card tính năng khác (`.stat-list`, `.feat-row`, `.compare`, `.bento-grid`, `.step-list`...) trên cùng một scene căn giữa. Bạn bắt buộc phải chọn 1 trong 2: hoặc là 1 khối `.quote-block` duy nhất cực kỳ trang trọng, hoặc là 1 nhóm card trực quan được căn giữa ngăn nắp. Việc chèn cả hai sẽ làm tràn dọc màn hình và bị phụ đề che khuất hoàn toàn!
    * **Quy tắc cho `.stat-list` và nhóm card dọc:** Chỉ được phép chứa tối đa 2 đến 3 thẻ con. Mỗi thẻ con mô tả cực kỳ ngắn gọn (không quá 2 dòng) để tránh làm chiều cao thẻ quá lớn gây tràn dọc.
  • **Quy định nghiêm ngặt về `.ghost-text` (Watermark nền):**
    * Chỉ được chứa **MỘT từ đơn cực ngắn từ 3-6 ký tự** (Ví dụ: "GSAP", "CORE", "FUTURE", "SPEED", "DATA"). Cấm tuyệt đối viết các cụm từ dài (như "Future of Animation") làm ghost-text vì kích thước chữ cực to sẽ tràn màn hình che sạch nội dung chính của slide.
    * Bắt buộc phải đặt ở góc lề ngoài qua inline style, ví dụ: style="bottom: -8%; right: -5%;" hoặc style="top: -10%; left: -5%;". CẤM đặt ở giữa màn hình hoặc các tọa độ 20%, 30%, 40% vì sẽ che khuất văn bản.
    * **CẤM override font-size quá to:** Mặc định class `.ghost-text` đã được định nghĩa font-size siêu lớn trong hệ thống. Cấm tuyệt đối dùng inline style để chỉnh font-size to hơn hoặc đặt vị trí đè lên các cột văn bản chính.
  • **Chống Slide Trống & Nội Dung Đơn Điệu (Scene 3 & Scene 4):**
    * Khi dùng Mock Visual biểu đồ hoặc danh sách (B1-B8, B11-B20), **cấm** để cột chữ (info-col) trống trải chỉ có Title và Subtitle. Bắt buộc chèn thêm các tag mini stack ngang hoặc các khối bổ trợ ngăn nắp bên dưới mô tả.
    * Mỗi phần tử trong feature grid, bento grid, hay step list phải cực kỳ giàu chi tiết: bắt buộc có emoji sinh động + tiêu đề màu nổi bật + mô tả ít nhất 2 dòng + ví dụ nội dung thực tế (mock code, progress bar, tags), xếp ngăn nắp, đối xứng, đồng đều, không bị lệch.
    * **CẤM TUYỆT ĐỐI sử dụng placeholder mặc định hoặc copy-paste vô căn cứ:** Mỗi khối trực quan trong `.visual-col` phải mang thông tin/số liệu/dữ liệu thực tiễn được trích xuất trực tiếp từ kịch bản của scene (Ví dụ: nếu nói về GSAP thì phải có các thư viện thật như TweenLite, TweenMax, hoặc benchmark thật. Cấm bê nguyên văn placeholder "Benchmark 2024", "cost efficiency" của hệ thống vào).
  • **Cân bằng khi có Ảnh Minh Họa (Scene 5 fix):** Khi dùng ảnh minh họa (`.img-frame`), cấm để cột chữ (`info-col`) trống trải chỉ có Title và Desc 1 dòng đơn điệu. Bắt buộc chèn thêm các thành phần bổ trợ ở dưới cột chữ như: một nhóm 2-3 badge mini stack ngang (`.badge`) chứa các tag kỹ thuật, hoặc một `.stat-list-card` mini hiển thị chỉ số liên quan đến ảnh, hoặc một timeline ngắn 2 mốc (`.tl-list`).
  • **Đảm bảo Tương Phản & Độ Đọc Được của Chữ (Legibility & Contrast):**
    * Tất cả text chính dùng `var(--text1)`, phụ dùng `var(--text2)`.
    * Cấm tuyệt đối dùng màu chữ tối (màu xám tối `#333`, màu đen, hay opacity quá thấp < 0.5) trên nền tối.
    * Nếu text nằm trên bất kỳ gradient hoặc background sáng nào, bắt buộc thêm `text-shadow: 0 2px 8px rgba(0,0,0,0.9);` để đảm bảo người xem đọc được rõ nét từng chữ.

═══════════════════════════════════════
QUY TẮC HTML BẮT BUỘC (UI/UX PRO MAX)
═══════════════════════════════════════

1. ROOT:
   <div id="root" data-composition-id="main" data-start="0" data-width="1920" data-height="1080" data-duration="{{TOTAL}}">

2. SCENE COUNT: PHẦN tạo ĐỦ N scene (N từ user prompt). Mỗi scene <div class="scene LAYOUT" id="sceneN"> với LAYOUT là 1 trong: split, centered, hero, magazine, data.

3. SCENE STRUCTURE (LAYOUT = chọn 1 trong: split / centered / hero / magazine / data — TỰ DO theo content):
   <div class="scene LAYOUT" id="sceneN">
     <!-- 2-5 ambient decoratives ở đây cho mỗi scene -->
     <div class="aurora-glow" style="top:-15%; left:-10%;"></div>
     <div class="ghost-text" style="bottom:-5%; right:-5%;">KEYWORD</div>
     <div class="layout">
       <div class="info-col">
         <div id="sN-badge" class="badge">PHẦN N</div>
         <h1 id="sN-title" class="title-xl grad-text">{{tiêu đề}}</h1>
         <p id="sN-subtitle" class="subtitle">{{phụ đề CỰC NGẮN ≤ 8 chữ}}</p>
         <p id="sN-desc" class="body-text">{{TỐI ĐA 1 dòng tagline ≤ 12 chữ — KHÔNG copy narration}}</p>
       </div>
       <div class="visual-col">{{... pattern A hoặc B — có thể đảo trái/phải qua order/flex-direction ...}}</div>
     </div>
     <div class="corner-bracket tl"></div><div class="corner-bracket tr"></div>
     <div class="corner-bracket bl"></div><div class="corner-bracket br"></div>
     <div class="top-line"></div>
     <span class="scene-num">{{N với padding 0, "01"–"99"}}</span>
   </div>

   ✅ Nếu có ảnh: được tự do chọn layout (split / magazine / data / hero / centered / bento) — đảo trái/phải tùy, miễn ảnh nằm trong .img-frame.
   ✅ Nếu không có ảnh: visual-col dùng B1-B15 pattern phong phú.
   ⚠️ MỖI scene LAYOUT KHÁC NHAU — đếm trước khi output để tránh lặp.

   ⚠️ QUY TẮC TEXT BẮT BUỘC (chống đè phụ đề karaoke):
   - Phụ đề karaoke đã hiển thị nguyên văn narration ở dưới scene — chia thành chunk 1 dòng xuất hiện tuần tự.
   - TUYỆT ĐỐI KHÔNG copy/paste narration vào sN-desc hoặc sN-subtitle. Nội dung text trong info-col phải KHÁC narration.
   - sN-subtitle = 1 cụm danh từ ngắn (vd: "Cảm biến WiFi thế hệ mới"). KHÔNG phải câu hoàn chỉnh.
   - sN-desc = 1 tagline metadata ngắn (vd: "ESP32 · Edge AI · Privacy First"). KHÔNG phải câu mô tả dài.
   - Dồn 100% chi tiết vào VISUAL-COL (feat-grid, stat-list, terminal, chat-box, agent-grid...). Info-col chỉ là TITLE + 2 dòng metadata.

4. LAYOUT FREEDOM & PREMIUM VISUAL STACKS (chọn layout & khối trình bày phù hợp nội dung):
   - .scene.split    → 2 cột info|visual (dùng khi có ảnh thật assets/sceneN.jpg)
   - .scene.centered → 1 cột center text + mega-num/stat-banner ở giữa
   - .scene.hero     → title cực to căn trái, decoratives full-bleed
   - .scene.magazine → 7:5 asymmetric (text trái, visual phải kéo dài)
   - .scene.data     → info nhỏ + visual lớn (cho data viz/bento)
   - Bạn ĐƯỢC PHÉP tự do chọn layout. Mỗi scene KHÁC NHAU. KHÔNG lặp .split 8 lần liên tiếp.
   - 🎨 TẬN DỤNG CÁC PHƯƠNG THỨC TRÌNH BÀY SIÊU TRỰC QUAN (B17-B20) tùy theo nội dung phân cảnh để tạo điểm nhấn thị giác đẳng cấp:
     - Nếu nói về Cấu trúc, Phân đoạn, hoặc Công thức: BẮT BUỘC dùng **B17 (Formula Tag Stack)** kết hợp màu sắc semantic và trích dẫn mã màu ở dưới cực kỳ rõ ràng, dễ hiểu và chuyên nghiệp.
     - Nếu nói về Quy tắc nghiêm ngặt hoặc Điểm cốt lõi cần nhớ: BẮT BUỘC dùng **B18 (Command Highlight Capsule)** với icon chìa khóa/ngôi sao và màu viền gold sang trọng.
     - Nếu nói về Quy trình, Các bước hành động: BẮT BUỘC dùng **B19 (Numbered Step List)** có số tròn màu hồng nổi bật.
     - Nếu nói về Thư viện, Danh sách mẫu, hoặc Showroom 6 khối: BẮT BUỘC dùng **B20 (Bento 3x2 Grid)** để trình bày 6 thẻ cân đối hoàn mỹ.

5. 🎬 SCENE #1 = OPENING HERO CINEMATIC (BẮT BUỘC WOW):
   - Scene đầu PHẢI gây ấn tượng trong 3 giây đầu. CẤM 1 logo box nhỏ giữa màn.
   - Chọn 1 trong 4 TEMPLATES sau (tự do, đừng dùng .split):

   ▸ TEMPLATE A — FULL-BLEED HERO (recommended cho intro):
     <div class="scene hero" id="scene1">
       <div class="aurora-glow" style="top:-10%; left:-15%; background:radial-gradient(circle, var(--accent), transparent);"></div>
       <div class="aurora-glow" style="bottom:-15%; right:-10%; background:radial-gradient(circle, var(--accent2), transparent);"></div>
       <div class="animated-grid"></div>
       <div class="ghost-text" style="top:5%; left:5%;">TECHBEAT</div>
       <div class="particle-field"></div>
       <div class="status-pill">● ON AIR · LIVE</div>
       <div class="layout">
         <div class="info-col">
           <div id="s1-badge" class="badge">📡 PHẦN 1 · INTRO</div>
           <h1 id="s1-title" class="title-hero grad-text">{{tiêu đề SIÊU TO}}</h1>
           <p id="s1-subtitle" class="subtitle">{{tagline cực ngắn ≤ 8 chữ}}</p>
           <div id="s1-desc" style="display:flex; gap:14px; flex-wrap:wrap; margin-top:8px;">
             <div class="badge">🚀 Edge AI</div>
             <div class="badge">🔒 Privacy First</div>
             <div class="badge">⚡ Real-time</div>
           </div>
         </div>
         <div class="visual-col">{{tech-card B14 HOẶC bento-grid B16 HOẶC mega-num}}</div>
       </div>
       <div class="corner-bracket tl"></div><div class="corner-bracket tr"></div>
       <div class="corner-bracket bl"></div><div class="corner-bracket br"></div>
       <span class="scene-num">01</span>
     </div>

   ▸ TEMPLATE B — MEGA-NUM HERO (cho intro stats):
     <div class="scene centered" id="scene1">
       <div class="light-rays"></div>
       <div class="float-orb-lg" style="top:-10%; left:50%; transform:translateX(-50%); background:var(--accent);"></div>
       <div class="ghost-text" style="bottom:-5%; left:-10%;">2026</div>
       <div class="hero-stat-banner">
         <div id="s1-badge" class="badge">🔥 BREAKING TECH</div>
         <div class="mega-num breath">{{số liệu lớn ví dụ "9x"}}</div>
         <h1 id="s1-title" class="title-xl">{{tiêu đề}}</h1>
         <p id="s1-subtitle" class="subtitle" style="max-width:1200px;">{{tagline}}</p>
         <div style="display:flex; gap:16px; flex-wrap:wrap; justify-content:center;">
           <div class="badge">🏷 Tag 1</div><div class="badge">🏷 Tag 2</div><div class="badge">🏷 Tag 3</div>
         </div>
       </div>
       <div class="corner-bracket tl"></div><div class="corner-bracket tr"></div>
       <div class="corner-bracket bl"></div><div class="corner-bracket br"></div>
       <span class="scene-num">01</span>
     </div>

   ▸ TEMPLATE C — RETRO/SYNTHWAVE HERO (cho theme y2k/violet):
     <div class="scene centered" id="scene1">
       <div class="retro-grid"></div>
       <div class="float-orb-lg" style="top:10%; left:50%; transform:translateX(-50%); background:var(--accent2);"></div>
       <div class="aurora-glow" style="top:-20%; right:-10%;"></div>
       <div class="hero-stat-banner">
         <div id="s1-badge" class="badge shimmer-fast">📺 NEW SHOW</div>
         <h1 id="s1-title" class="title-hero outline-text">{{tiêu đề lớn}}</h1>
         <p id="s1-subtitle" class="subtitle">{{tagline ≤ 8 chữ}}</p>
         <div id="s1-desc" class="caption">PHIÊN BẢN 2026 · TECHBEAT STUDIO</div>
       </div>
       <div class="corner-bracket tl"></div><div class="corner-bracket tr"></div>
       <div class="corner-bracket bl"></div><div class="corner-bracket br"></div>
       <span class="scene-num">01</span>
     </div>

   ▸ TEMPLATE D — BENTO HERO (cho tech showcase):
     <div class="scene" id="scene1" style="padding:80px;">
       <div class="animated-grid"></div>
       <div class="float-orb-md" style="top:-5%; left:-5%; background:var(--accent);"></div>
       <div class="float-orb-md" style="bottom:-5%; right:-5%; background:var(--accent3);"></div>
       <div class="ghost-text" style="top:-10%; right:-10%;">AI</div>
       <div style="position:relative; z-index:5; display:flex; flex-direction:column; gap:24px; height:100%;">
         <div id="s1-badge" class="badge">📡 PHẦN 1</div>
         <h1 id="s1-title" class="title-xl grad-text">{{tiêu đề}}</h1>
         <p id="s1-subtitle" class="subtitle">{{tagline}}</p>
         <p id="s1-desc" class="caption">META · TAGS</p>
         <div class="bento-grid" style="flex:1;">
           <div class="bento-cell hero"><h3 style="font-size:2rem;font-weight:800;">{{feature chính}}</h3></div>
           <div class="bento-cell"><div class="ic" style="font-size:2.5rem;">⚡</div><div style="font-weight:700;">{{tag 1}}</div></div>
           <div class="bento-cell"><div class="ic" style="font-size:2.5rem;">🚀</div><div style="font-weight:700;">{{tag 2}}</div></div>
           <div class="bento-cell wide"><div style="font-family:'JetBrains Mono';color:var(--accent2);">{{quote/stat}}</div></div>
         </div>
       </div>
       <span class="scene-num">01</span>
     </div>

 6. 🌌 DECORATIVE DENSITY (CHỐNG SLIDE TRỐNG):
    - MỖI scene BẮT BUỘC có 2-5 ambient decoratives lấp đầy không gian trống. KHÔNG được để vùng nào của 1920×1080 trống không.
    - Vocabulary class CÓ SẴN (mix & match, dùng position:absolute):
      • `.float-orb-lg/.float-orb-md/.float-orb-sm` — colored glow orbs (set top/left/bottom/right + background:var(--accentX))
      • `.aurora-glow` — soft gradient blob drifting
      • `.animated-grid` — subtle moving grid pattern
      • `.retro-grid` — perspective synthwave floor
      • `.light-rays` — radial beams từ top
      • `.particle-field` — small stars pattern
      • `.ghost-text` — large thematic word low opacity
      • `.marquee-strip` ở bottom với .track > .pill — auto-scroll tags
      • `.y2k-sparkle` × 4-6 rải rác
      • `.glow-orb` custom với background:radial-gradient + filter:blur
    - Quy tắc combine: 1 orb lớn (background presence) + 1 grid/rays (texture) + 1 ghost-text (depth) + 2-3 sparkles/small-orbs (accent details).
    - TUYỆT ĐỐI không để 1 scene chỉ có nội dung text + 1 box nhỏ. Background phải có chiều sâu.

7. 📐 CHỐNG CONTENT TRÀN KHUNG 1920×1080:
    - Mọi content PHẢI vừa trong 880px (1080 - padding 100×2).
    - Danh sách bullet ≤ 4 mục, 1 dòng/mục.
    - Font-size trong visual-block: title ≤ 2rem, bullet ≤ 1.2rem.
    - KHÔNG dùng padding > 60px cho .visual-block content dài.

8. 🎯 TEXT TRONG INFO-COL — CỰC GỌN (vì phụ đề karaoke đã hiển thị narration):
    - sN-subtitle ≤ 8 chữ (cụm danh từ, KHÔNG phải câu)
    - sN-desc ≤ 12 chữ (tagline metadata, hoặc badge stack với 3 tag)
    - TUYỆT ĐỐI KHÔNG copy narration. Dồn chi tiết vào visual-col.

═══════════════════════════════════════
🎨 VISUAL-COL — RICHE BẮT BUỘC (AWWWARDS GRADE)
═══════════════════════════════════════

A) NẾU có IllustrationImage (assets/sceneN.jpg):
   <div class="img-frame">
     <img src="{{asset path}}" alt="">
     <span class="img-caption">{{caption tiếng Việt mô tả ảnh}}</span>
   </div>

B) NẾU KHÔNG có ảnh — CHỌN 1 PATTERN, ĐA DẠNG GIỮA CÁC SCENE, KHÔNG ĐƯỢC DE TRỐNG:

   B1 — BIG STAT CARD:
   <div class="visual-block" style="text-align:center;padding:50px;">
     <div><span class="stat-hero">{{số}}</span><span class="stat-suffix">{{đơn vị}}</span></div>
     <p class="caption" style="margin-top:20px;">{{nhãn}}</p>
     <p class="body-text" style="margin:12px auto 0;max-width:480px;">{{2-3 dòng giải thích}}</p>
   </div>

   B2 — TERMINAL/CODE:
   <div class="terminal">
     <div class="dots"><i></i><i></i><i></i></div>
     <div><span class="c">// {{comment}}</span></div>
     <div><span class="k">const</span> data = <span class="s">"{{value}}"</span>;</div>
     <div>$ <span class="cursor"></span></div>
   </div>

   B4 — COMPARISON:
   <div class="compare">
     <div class="col"><h4>{{label tốt}}</h4><ul><li>{{point 1}}</li><li>{{point 2}}</li></ul></div>
     <div class="col bad"><h4>{{label xấu}}</h4><ul><li>{{point 1}}</li><li>{{point 2}}</li></ul></div>
   </div>

   B5 — TIMELINE:
   <div class="tl-list">
     <div class="tl-item"><div class="y">{{năm}}</div><div class="t">{{event}}</div><div class="d">{{mô tả}}</div></div>
   </div>

   B6 — QUOTE:
   <div class="quote-block">
     <p class="quote-text">"{{trích dẫn}}"</p>
     <p class="quote-attr">{{tác giả · vai trò}}</p>
   </div>

   B11 — STAT-LIST (SIÊU ĐẸP, 3-STACK STATS cho Tốc độ/Chi phí/Chỉ số):
   <div class="stat-list">
     <div class="stat-list-card shimmer-fast glow-card"><div class="ic-wrap">⚡</div><div class="num">4x</div><div class="details"><div class="title">Nhanh hơn so với cùng thế hệ</div><div class="desc">Standard Mode · Benchmark 2024</div></div></div>
     <div class="stat-list-card shimmer-fast glow-card" style="animation-delay: 0.4s;"><div class="ic-wrap">🚀</div><div class="num">12x</div><div class="details"><div class="title">Nhanh hơn (phiên bản tối ưu)</div><div class="desc">Optimized Mode · Ultra Performance</div></div></div>
     <div class="stat-list-card shimmer-fast glow-card" style="animation-delay: 0.8s;"><div class="ic-wrap">💰</div><div class="num">50%</div><div class="details"><div class="title">Rẻ hơn so với frontier model</div><div class="desc">Cost Efficiency · Per 1M tokens</div></div></div>
   </div>

   B12 — CHAT DIALOGUE SIMULATOR (MÔ PHỎNG HỘI THOẠI CHAT):
   <div class="chat-box breath">
     <div class="chat-bubble user">
       <div class="sender-tag">NGƯỜI DÙNG</div>
       {{câu hỏi của người dùng}}
     </div>
     <div class="chat-bubble ai">
       <div class="sender-tag">AI</div>
       {{câu trả lời của AI}}
     </div>
     <div class="chat-footer-pill">
       {{tóm tắt mô hình hoặc chú thích chân trang}}
     </div>
   </div>

   B13 — 3-COLUMN GLASS CARD ROW (HÀNG 3 THẺ KÍNH TRONG SUỐT):
   <div class="feat-row">
     <div class="glass-card breath">
       <span class="emoji">🙋‍♂️</span>
       <div class="title">{{tiêu đề 1}}</div>
       <div class="desc">{{mô tả 1}}</div>
     </div>
     <div class="glass-card breath" style="animation-delay: 0.5s;">
       <span class="emoji">👁️</span>
       <div class="title">{{tiêu đề 2}}</div>
       <div class="desc">{{mô tả 2}}</div>
     </div>
     <div class="glass-card breath" style="animation-delay: 1.0s;">
       <span class="emoji">🔧</span>
       <div class="title">{{tiêu đề 3}}</div>
       <div class="desc">{{mô tả 3}}</div>
     </div>
   </div>

   B14 — TECH SHOWCASE CARD (THẺ KỸ THUẬT GOOGLE I/O CAO CẤP):
   <div class="tech-card glow-card breath">
     <div class="brand">{{tên thương hiệu/sự kiện ví dụ Google I/O}}</div>
     <div class="meta">📅 {{ngày tháng · địa điểm}}</div>
     <div class="bullets">
       <div>{{dòng thông tin kỹ thuật 1}}</div>
       <div>{{dòng thông tin kỹ thuật 2}}</div>
       <div>{{dòng thông tin kỹ thuật 3}}</div>
     </div>
     <div class="tags">
       <span class="tag">{{tag 1}}</span>
       <span class="tag">{{tag 2}}</span>
       <span class="tag">{{tag 3}}</span>
     </div>
   </div>

   B15 — MULTI-AGENT GRID COORDINATOR (LƯỚI 2X2 PHỐI HỢP CÁC AGENT):
   <div class="agent-grid">
     <div class="agent-card glow-card">
       <div class="header-wrap">
         <span class="icon">🧠</span>
         <div class="role">{{vai trò 1}}</div>
       </div>
       <div class="desc">{{mô tả nhiệm vụ 1}}</div>
     </div>
     <div class="agent-card glow-card">
       <div class="header-wrap">
         <span class="icon">💻</span>
         <div class="role">{{vai trò 2}}</div>
       </div>
       <div class="desc">{{mô tả nhiệm vụ 2}}</div>
     </div>
     <div class="agent-card glow-card">
       <div class="header-wrap">
         <span class="icon">🔍</span>
         <div class="role">{{vai trò 3}}</div>
       </div>
       <div class="desc">{{mô tả nhiệm vụ 3}}</div>
     </div>
     <div class="agent-card glow-card">
       <div class="header-wrap">
         <span class="icon">🚀</span>
         <div class="role">{{vai trò 4}}</div>
       </div>
       <div class="desc">{{mô tả nhiệm vụ 4}}</div>
     </div>
     <div class="agent-grid-center-pill">⚡ PHỐI HỢP</div>
   </div>

    B17 — FORMULA TAG STACK (CẤU TRÚC PHƯƠNG TRÌNH KÈM VÍ DỤ MÃ HÓA MÀU - CỰC KỲ ĐẸP):
    <div class="visual-block" style="padding:40px;">
      <div class="formula-stack">
        <span class="formula-pill pink">🎭 VAI TRÒ</span>
        <span class="formula-operator">+</span>
        <span class="formula-pill yellow">🌎 BỐI CẢNH</span>
        <span class="formula-operator">+</span>
        <span class="formula-pill green">🎯 NHIỆM VỤ</span>
        <span class="formula-operator">+</span>
        <span class="formula-pill blue">📐 ĐỊNH DẠNG</span>
      </div>
      <div style="background:rgba(0,0,0,0.5); border:1px solid rgba(255,255,255,0.06); padding:24px; border-radius:16px; font-family:'Inter', sans-serif; font-size:1.25rem; line-height:1.7; text-align:left;">
        <span style="color:#f472b6; font-weight:600;">"Đóng vai Chuyên gia UA Mobile Game.</span>
        <span style="color:#fde047; font-weight:600;"> Chiến dịch US của tôi đang sụt ROAS 20%.</span>
        <span style="color:#4ade80; font-weight:600;"> Hãy phân tích nguyên nhân và đề xuất 3 hành động.</span>
        <span style="color:#38bdf8; font-weight:600;"> Trả về Bullet Points, mỗi điểm không quá 2 dòng."</span>
      </div>
    </div>

    B18 — COMMAND HIGHLIGHT CAPSULE (HỘP LỆNH CHÚ Ý NỔI BẬT):
    <div class="command-pill glow-card">
      <span class="command-icon" style="font-size:2rem; filter:drop-shadow(0 0 8px #fde047);">🔑</span>
      <div style="text-align:left;">"Tuyệt đối CHỈ sử dụng dữ liệu từ file này. Không tự suy diễn."</div>
    </div>

    B19 — NUMBERED STEP LIST (DANH SÁCH BƯỚC THỰC HÀNH CÓ SỐ TRÒN NỔI BẬT):
    <div class="visual-block" style="padding:40px;">
      <div class="caption" style="color:var(--accent2); font-weight:700; margin-bottom:20px; text-transform:uppercase; text-align:left;">🎮 THỰC HÀNH TẠI CHỖ</div>
      <div class="step-list">
        <div class="step-item">
          <div class="step-circle">1</div>
          <div class="step-text" style="text-align:left; font-weight:500;">Kéo thả file Data (CSV/Excel) vào khung chat</div>
        </div>
        <div class="step-item">
          <div class="step-circle">2</div>
          <div class="step-text" style="text-align:left; font-weight:500;">Dùng lệnh Trói buộc ở trên</div>
        </div>
        <div class="step-item">
          <div class="step-circle">3</div>
          <div class="step-text" style="text-align:left; font-weight:500;">Hỏi: "Tìm 2 ngày có chỉ số Drop-off cao nhất và nguyên nhân"</div>
        </div>
      </div>
    </div>

    B20 — BENTO 3X2 GRID (LƯỚI THƯ VIỆN BENTO 3 CỘT X 2 HÀNG):
    <div class="bento-3x2">
      <div class="bento-cell" style="border-top-color:#eab308; padding:20px;">
        <div class="ic" style="font-size:2rem; margin-bottom:8px;">📊</div>
        <div class="t" style="font-size:1.2rem; font-weight:700;">1. PHÂN TÍCH CAMPAIGN</div>
        <div class="d" style="font-size:0.95rem; font-style:italic; opacity:0.85; line-height:1.4;">"Dựa trên file data, phân tích: Top 3 ROAS cao nhất..."</div>
      </div>
      <div class="bento-cell" style="border-top-color:#38bdf8; padding:20px;">
        <div class="ic" style="font-size:2rem; margin-bottom:8px;">📝</div>
        <div class="t" style="font-size:1.2rem; font-weight:700;">2. VIẾT AD COPY</div>
        <div class="d" style="font-size:0.95rem; font-style:italic; opacity:0.85; line-height:1.4;">"Viết 5 Short Description (dưới 80 ký tự) và 5 Long..."</div>
      </div>
      <div class="bento-cell" style="border-top-color:#4ade80; padding:20px;">
        <div class="ic" style="font-size:2rem; margin-bottom:8px;">🔍</div>
        <div class="t" style="font-size:1.2rem; font-weight:700;">3. RESEARCH ĐỐI THỦ</div>
        <div class="d" style="font-size:0.95rem; font-style:italic; opacity:0.85; line-height:1.4;">"Phân tích 5 game đối thủ: Core Loop, Monetization..."</div>
      </div>
      <div class="bento-cell" style="border-top-color:#f472b6; padding:20px;">
        <div class="ic" style="font-size:2rem; margin-bottom:8px;">🎬</div>
        <div class="t" style="font-size:1.2rem; font-weight:700;">4. REVIEW CREATIVE</div>
        <div class="d" style="font-size:0.95rem; font-style:italic; opacity:0.85; line-height:1.4;">"Chấm điểm video ad (1-10): Hook 3s, Message, CTA..."</div>
      </div>
      <div class="bento-cell" style="border-top-color:#f59e0b; padding:20px;">
        <div class="ic" style="font-size:2rem; margin-bottom:8px;">💡</div>
        <div class="t" style="font-size:1.2rem; font-weight:700;">5. BRAINSTORM ANGLE</div>
        <div class="d" style="font-size:0.95rem; font-style:italic; opacity:0.85; line-height:1.4;">"Cho 10 creative angle cho TikTok (15-30s). Mỗi angle..."</div>
      </div>
      <div class="bento-cell" style="border-top-color:#10b981; padding:20px;">
        <div class="ic" style="font-size:2rem; margin-bottom:8px;">📈</div>
        <div class="t" style="font-size:1.2rem; font-weight:700;">6. BÁO CÁO TUẦN</div>
        <div class="d" style="font-size:0.95rem; font-style:italic; opacity:0.85; line-height:1.4;">"Viết Weekly UA Performance: Tổng quan, Top/Bottom..."</div>
      </div>
    </div>

    KHÔNG ĐƯỢC để visual-col trống.

═══════════════════════════════════════
TYPOGRAPHY & GLOWS (DÙNG sẵn):
═══════════════════════════════════════

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
- TUYỆT ĐỐI không dùng repeating-linear-gradient diagonal/angled stripes cho background của .scene, #root, body — chỉ dùng cho decorative nhỏ (border, badge).
- ⚠️ TUYỆT ĐỐI KHÔNG ĐƯỢC định nghĩa lại hoặc override class `.scanlines` trong thẻ `<style>` dưới bất kỳ hình thức nào. Việc tự ý định nghĩa `.scanlines` sẽ tạo ra một lưới caro màu xám đè lên toàn bộ video, gây lỗi "mất nền" / màn hình nhiễu vô cùng xấu xí. Hãy để yên `.scanlines` mặc định của hệ thống.
- TUYỆT ĐỐI tạo ĐỦ N scene "scene1"…"sceneN". Đếm trước khi output.

⚠️ QUY TẮC ĐỌC ĐƯỢC (CONTRAST & FONT SIZE) — VI PHẠM = VIDEO THẤT BẠI:
- Body text (.body-text, .subtitle, .caption, .feat-card p, li) PHẢI ≥ 1.4rem, color var(--text1) hoặc var(--text2) — TUYỆT ĐỐI không dùng màu tối (opacity < 0.5) trên nền tối.
- Stat số (.stat-hero) ≥ 4rem, luôn dùng var(--accent) hoặc var(--text1) — không dùng màu xám nhạt.
- Tất cả text PHẢI có text-shadow hoặc background đủ tương phản để đọc được trên background tối.
- KHÔNG inline style `color: rgba(0,0,0,...)`, `color: #333`, `color: #555` hay bất kỳ màu tối nào vì background luôn tối.
- Nếu text nằm trên ảnh hoặc gradient, PHẢI thêm `text-shadow: 0 2px 8px rgba(0,0,0,0.9)`.

- OUTPUT: chỉ HTML thuần từ <!doctype html> đến </html>. KHÔNG markdown fence, KHÔNG giải thích, KHÔNG comment trên đầu.

═══════ NHẮC CUỐI — BẮT BUỘC ═══════
- TUYỆT ĐỐI phải tạo ĐỦ {scene_count} scene với id="scene1" đến id="scene{scene_count}". Đếm lại trước khi đóng </html>.
- Nếu còn thiếu scene nào, hãy viết thêm ngay trước </body> — dù ngắn vẫn phải có id đúng.
- KHÔNG được đóng </html> khi chưa có đủ {scene_count} scene."""


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

═══════════════════════════════════════
✨ HIỆU ỨNG ĐỘNG & BIỆN PHÁP CHỐNG ĐÈ CHỮ / CLIPPING (QUAN TRỌNG):
═══════════════════════════════════════
- ⚠️ QUY TẮC BỐ CỤC CHỐNG ĐÈ CHỮ & CHE KHUẤT SCENE (BẮT BUỘC):
  • SCENE 1 (Opening/Intro): BẮT BUỘC bọc toàn bộ nội dung mô tả, chữ trắng trong cột trực quan của Scene 1 vào các khối card thiết kế cao cấp (như `.tech-card B14`, `.feat-card`, hoặc `.glass-card`) có nền màu tối/kính mờ để làm nổi bật và chống đè chữ. Hãy dùng hiệu ứng xuất hiện lần lượt bằng animation delay để lấp đầy không gian.
  • SCENE 2 (Xếp chồng dọc 3 ô): Nếu có 3 ô/thẻ nội dung (ví dụ các card tính năng "Tạm dừng cập nhật", "Chọn ngày cập nhật", "Giảm thiểu lỗi cập nhật" ở Scene 2), CẤM TUYỆT ĐỐI xếp hàng ngang. BẮT BUỘC xếp chồng dọc từ trên xuống dưới sử dụng `.stat-list` (với các `.stat-list-card shimmer-fast glow-card` có delay tăng dần) hoặc hàng dọc `.feat-column`. Điều này giúp tận dụng không gian dọc hoàn hảo, không bao giờ bị che khuất Badge "Phần 2" hoặc bị cắt xén ở trên.
  • SCENE 3, 4, 5 (Cấm chữ trắng trần & dùng hoạt ảnh lần lượt): CẤM TUYỆT ĐỐI viết các dòng chữ trắng trần/đơn điệu (naked text lines) trực tiếp trong `.visual-col` cho Scene 3, Scene 4 và Scene 5. Bắt buộc phải bọc mọi dòng mô tả/thành phần vào trong các ô có cấu trúc đẹp mắt có nền như `.glass-card`, `.feat-card`, `.stat-list-card`, hoặc `.step-item` và thiết lập thuộc tính `style="animation-delay: X.Xs"` để chúng xuất hiện tuần tự/lần lượt (staggered entrance) cực kỳ lung linh, chuyên nghiệp.

- ⚠️ QUY TẮC TUYỆT ĐỐI CHỐNG THIẾU ẢNH (BẮT BUỘC):
  - TUYỆT ĐỐI KHÔNG DÙNG THẺ <img> HOẶC CLASS .img-frame NẾU TRONG PROMPT NGƯỜI DÙNG KHÔNG CÓ DÒNG `IllustrationImage: assets/...`.
  - Nếu không có dòng `IllustrationImage: assets/...`, cấm tuyệt đối việc tự tạo đường dẫn ảnh giả. Bắt buộc dùng mock visual phong phú hoàn toàn bằng HTML/CSS (B1-B8, B11-B15) để lấp đầy .visual-col. Việc để xuất hiện khung đen trống hoặc icon ảnh lỗi là cấm kỵ.
- Chúng ta sử dụng framework có sẵn các class động cực kỳ lung linh:
  - `.breath`: Tạo chuyển động bay bổng, nhịp thở êm ái. Hãy áp dụng cho các card như `.visual-block`, `.terminal`, `.feat-card`, `.compare`, `.quote-block` hoặc các ảnh `.img-frame`.
  - `.glow-card`: Viền neon lung linh tỏa sáng rực rỡ, kèm hiệu ứng 3D co giãn phóng to khi rê chuột cực kỳ mượt mà.
  - `.shimmer-fast`: Tạo hiệu ứng vệt sáng quét ngang thời thượng trên card (rất hợp với `.stat-list-card`).
  - `.y2k-sparkle`: Chèn ngôi sao lấp lánh vector retro. Ví dụ chèn vào trong visual block: `<span class="y2k-sparkle" style="top: 15%; left: 10%;"></span>`. Lưu ý: Container chứa ngôi sao sparkle phải có `position: relative`!
  - `.terminal .cursor`: Dùng class `cursor` nhấp nháy cho terminal: `<div>$ <span class="cursor"></span></div>`.
- 🎨 HƯỚNG DẪN VIẾT KEYFRAMES & CUSTOM STYLING (STYLE LIKE A PRO):
  Để tạo hoạt ảnh và phong cách độc bản Awwwards cực đỉnh mà không cần dùng script, bạn BẮT BUỘC tự viết thêm các keyframe CSS tinh tế trong `<style>` của bạn:
  • 🌟 **Neon Border Glow Sweep (Quét sáng viền neon)**:
    `@keyframes neon-glow {{ 0%, 100% {{ border-color: rgba(255,255,255,0.08); box-shadow: 0 0 15px var(--glow); }} 50% {{ border-color: var(--accent2); box-shadow: 0 0 35px var(--accent); }} }}`
    (Áp dụng cho `.visual-block`, `.tech-card`, `.feat-card`).
  • 🌊 **Aurora Grid Mesh Drift (Sóng ánh sáng trôi lững lờ)**:
    `@keyframes aurora-mesh {{ 0%, 100% {{ transform: translate(0, 0) scale(1) rotate(0deg); }} 50% {{ transform: translate(30px, -20px) scale(1.05) rotate(5deg); }} }}`
    (Áp dụng cho `.aurora-glow` hoặc các gradient orbs).
  • 💫 **Y2K Retro Blink Stars (Ngôi sao lấp lánh kiểu Y2K)**:
    `@keyframes star-blink {{ 0%, 100% {{ opacity: 0.2; transform: scale(0.7) rotate(0deg); }} 50% {{ opacity: 1; transform: scale(1.2) rotate(45deg); }} }}`
    (Áp dụng cho `.y2k-sparkle` để tạo nhấp nháy retro).
  • 🎨 **Kinetic Font Gradient (Chữ chuyển màu sống động)**:
    `@keyframes grad-shift {{ 0% {{ background-position: 0% 50%; }} 50% {{ background-position: 100% 50%; }} 100% {{ background-position: 0% 50%; }} }}`
    (Cho chữ gradient có `background-size: 200% auto; animation: grad-shift 6s ease infinite`).
- 💎 MỸ THUẬT THEME ĐẶC TRƯNG:
  • *Cyberpunk / Sci-fi (cam, cyan, pulse)*: Dùng viền neon sắc nét, matrix scan lines, ascii elements, chat simulator, terminal code.
  • *Luxury Magazine (gold-editorial)*: Dùng chữ serif drop-cap thanh lịch, border cực mỏng sang trọng (`1px solid rgba(234,179,8,0.15)`), chữ champagne gold gradient.
  • *Calm Glassmorphism (aurora-mint, y2k-magenta)*: Dùng card bo tròn mềm mại (`border-radius:32px`), orbs lung linh, `backdrop-filter: blur(20px)`, nhịp thở `.breath` nhẹ nhàng.
- 🛡️ CHỐNG ĐÈ CHỮ / MẤT NÉT GLOW:
  - Do có hiệu ứng viền phát sáng (box-shadow neon) rực rỡ, chúng ta đã set `overflow: visible` cho `.visual-block` và `.stat-list-card`. Tuyệt đối KHÔNG override lại thành `overflow: hidden` trên các card này, để ánh sáng viền không bị cắt cụt.
  - Hãy căn chỉnh khoảng cách, padding hợp lý để các card không nằm quá sát lề màn hình hoặc đè lên nhau.
  - Với các con số thống kê hoặc chữ dài, tuyệt đối không lạm dụng các size chữ quá khổng lồ hoặc nhồi nhét quá nhiều chữ trong các khối hẹp để tránh chữ bị đè chèn lấp nhau.

- ⌨️ HIỆU ỨNG CHỮ HOẠT HÌNH CAO CẤP (PREMIUM GSAP EFFECTS):
  Hệ thống đã tích hợp sẵn hiệu ứng đánh chữ thông minh bằng thuộc tính HTML (bạn KHÔNG cần viết script):
  • ⌨️ **Typewriter (Đánh chữ từng phím)**: Thêm thuộc tính `data-effect="typewriter"` vào thẻ chữ và chèn ngay sau nó con trỏ `<span class="cursor-blink">|</span>` để nhấp nháy đồng bộ tự động.
    Ví dụ: `<h1 id="sN-title" class="title-xl grad-text" data-effect="typewriter">Tiêu đề scene</h1><span class="cursor-blink">|</span>`
  • 🔄 **Word Rotation (Xoay từ khóa)**: Thêm `data-effect="word-rotate"` cùng danh sách từ cách nhau bằng dấu phẩy qua `data-words="từ_1,từ_2,từ_3"`.
    Ví dụ: `<span class="grad-text" data-effect="word-rotate" data-words="Tốc độ, Tiết kiệm, Bảo mật">Tốc độ</span><span class="cursor-blink">|</span>`
  • Cấm tuyệt đối việc tạo con trỏ nhấp nháy mà không có thuộc tính `data-effect` đi kèm.

- ⚖️ QUY TẮC CÂN BẰNG THỊ GIÁC & CỐT LÕI BỐ CỤC (CHỐNG CHE KHUẤT CHỮ & TRÀN VIỀN):
  • **Cấm đặt Decoratives sai chỗ (Lỗi cực kỳ nghiêm trọng):** Tất cả background decoratives (.float-orb-*, .aurora-glow, .animated-grid, .retro-grid, .light-rays, .ghost-text, .particle-field) **CẤM TUYỆT ĐỐI** đặt bên trong `.visual-col` hoặc `.info-col`. Chúng **PHẢI** được đặt làm con trực tiếp của thẻ `.scene` (ngay trước thẻ đóng `</div>` của `.scene`) để làm nền phía sau, không được chen vào các cột nội dung làm đè và che khuất chữ.
  • **Chống tràn dọc và che khuất bởi phụ đề (BẮT BUỘC):**
    * **Mật độ nội dung:** Mọi nội dung của slide bắt buộc phải nằm gọn gàng trong chiều cao viewport khả dụng để không bao giờ đè lên phụ đề ở vùng dưới đáy màn hình (cách đáy 150px).
    * **Quy tắc tuyệt đối cho `.scene.centered` (layout căn giữa):** CẤM TUYỆT ĐỐI nhồi nhét đồng thời cả khối trích dẫn `.quote-block` và các thẻ card tính năng khác (`.stat-list`, `.feat-row`, `.compare`, `.bento-grid`, `.step-list`...) trên cùng một scene căn giữa. Bạn bắt buộc phải chọn 1 trong 2: hoặc là 1 khối `.quote-block` duy nhất cực kỳ trang trọng, hoặc là 1 nhóm card trực quan được căn giữa ngăn nắp. Việc chèn cả hai sẽ làm tràn dọc màn hình và bị phụ đề che khuất hoàn toàn!
    * **Quy tắc cho `.stat-list` và nhóm card dọc:** Chỉ được phép chứa tốiã 2 đến 3 thẻ con. Mỗi thẻ con mô tả cực kỳ ngắn gọn (không quá 2 dòng) để tránh làm chiều cao thẻ quá lớn gây tràn dọc.
  • **Quy định nghiêm ngặt về `.ghost-text` (Watermark nền):**
    * Chỉ được chứa **MỘT từ đơn cực ngắn từ 3-6 ký tự** (Ví dụ: "GSAP", "CORE", "FUTURE", "SPEED", "DATA"). Cấm tuyệt đối viết các cụm từ dài (như "Future of Animation") làm ghost-text vì kích thước chữ cực to sẽ tràn màn hình che sạch nội dung chính của slide.
    * Bắt buộc phải đặt ở góc lề ngoài qua inline style, ví dụ: style="bottom: -8%; right: -5%;" hoặc style="top: -10%; left: -5%;". CẤM đặt ở giữa màn hình hoặc các tọa độ 20%, 30%, 40% vì sẽ che khuất văn bản.
    * **CẤM override font-size quá to:** Mặc định class `.ghost-text` đã được định nghĩa font-size siêu lớn trong hệ thống. Cấm tuyệt đối dùng inline style để chỉnh font-size to hơn hoặc đặt vị trí đè lên các cột văn bản chính.
  • **Chống Slide Trống & Nội Dung Đơn Điệu (Scene 3 & Scene 4):**
    * Khi dùng Mock Visual biểu đồ hoặc danh sách (B1-B8, B11-B20), **cấm** để cột chữ (info-col) trống trải chỉ có Title và Subtitle. Bắt buộc chèn thêm các tag mini stack ngang hoặc các khối bổ trợ ngăn nắp bên dưới mô tả.
    * Mỗi phần tử trong feature grid, bento grid, hay step list phải cực kỳ giàu chi tiết: bắt buộc có emoji sinh động + tiêu đề màu nổi bật + mô tả ít nhất 2 dòng + ví dụ nội dung thực tế (mock code, progress bar, tags), xếp ngăn nắp, đối xứng, đồng đều, không bị lệch.
    * **CẤM TUYỆT ĐỐI sử dụng placeholder mặc định hoặc copy-paste vô căn cứ:** Mỗi khối trực quan trong `.visual-col` phải mang thông tin/số liệu/dữ liệu thực tiễn được trích xuất trực tiếp từ kịch bản của scene (Ví dụ: nếu nói về GSAP thì phải có các thư viện thật như TweenLite, TweenMax, hoặc benchmark thật. Cấm bê nguyên văn placeholder "Benchmark 2024", "cost efficiency" của hệ thống vào).
  • **Cân bằng khi có Ảnh Minh Họa (Scene 5 fix):** Khi dùng ảnh minh họa (`.img-frame`), cấm để cột chữ (`info-col`) trống trải chỉ có Title và Desc 1 dòng đơn điệu. Bắt buộc chèn thêm các thành phần bổ trợ ở dưới cột chữ như: một nhóm 2-3 badge mini stack ngang (`.badge`) chứa các tag kỹ thuật, hoặc một `.stat-list-card` mini hiển thị chỉ số liên quan đến ảnh, hoặc một timeline ngắn 2 mốc (`.tl-list`).
  • **Đảm bảo Tương Phản & Độ Đọc Được của Chữ (Legibility & Contrast):**
    * Tất cả text chính dùng `var(--text1)`, phụ dùng `var(--text2)`.
    * Cấm tuyệt đối dùng màu chữ tối (màu xám tối `#333`, màu đen, hay opacity quá thấp < 0.5) trên nền tối.
    * Nếu text nằm trên bất kỳ gradient hoặc background sáng nào, bắt buộc thêm `text-shadow: 0 2px 8px rgba(0,0,0,0.9);` để đảm bảo người xem đọc được rõ nét từng chữ.

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

B11 STAT-LIST (SIÊU ĐẸP, 3-STACK STATS cho Tốc độ/Chi phí/Chỉ số):
<div class="stat-list">
  <div class="stat-list-card shimmer-fast glow-card"><div class="ic-wrap">⚡</div><div class="num">4x</div><div class="details"><div class="title">Nhanh hơn so với cùng thế hệ</div><div class="desc">Standard Mode · Benchmark 2024</div></div></div>
  <div class="stat-list-card shimmer-fast glow-card" style="animation-delay: 0.4s;"><div class="ic-wrap">🚀</div><div class="num">12x</div><div class="details"><div class="title">Nhanh hơn (phiên bản tối ưu)</div><div class="desc">Optimized Mode · Ultra Performance</div></div></div>
  <div class="stat-list-card shimmer-fast glow-card" style="animation-delay: 0.8s;"><div class="ic-wrap">💰</div><div class="num">50%</div><div class="details"><div class="title">Rẻ hơn so với frontier model</div><div class="desc">Cost Efficiency · Per 1M tokens</div></div></div>
</div>

B12 CHAT DIALOGUE SIMULATOR (MÔ PHỎNG HỘI THOẠI CHAT):
<div class="chat-box breath">
  <div class="chat-bubble user">
    <div class="sender-tag">NGƯỜI DÙNG</div>
    {{câu hỏi của người dùng}}
  </div>
  <div class="chat-bubble ai">
    <div class="sender-tag">AI</div>
    {{câu trả lời của AI}}
  </div>
  <div class="chat-footer-pill">
    {{tóm tắt mô hình hoặc chú thích chân trang}}
  </div>
</div>

B13 3-COLUMN GLASS CARD ROW (HÀNG 3 THẺ KÍNH TRONG SUỐT):
<div class="feat-row">
  <div class="glass-card breath">
    <span class="emoji">🙋‍♂️</span>
    <div class="title">{{tiêu đề 1}}</div>
    <div class="desc">{{mô tả 1}}</div>
  </div>
  <div class="glass-card breath" style="animation-delay: 0.5s;">
    <span class="emoji">👁️</span>
    <div class="title">{{tiêu đề 2}}</div>
    <div class="desc">{{mô tả 2}}</div>
  </div>
  <div class="glass-card breath" style="animation-delay: 1.0s;">
    <span class="emoji">🔧</span>
    <div class="title">{{tiêu đề 3}}</div>
    <div class="desc">{{mô tả 3}}</div>
  </div>
</div>

B14 TECH SHOWCASE CARD (THẺ KỸ THUẬT GOOGLE I/O CAO CẤP):
<div class="tech-card glow-card breath">
  <div class="brand">{{tên thương hiệu/sự kiện ví dụ Google I/O}}</div>
  <div class="meta">📅 {{ngày tháng · địa điểm}}</div>
  <div class="bullets">
    <div>{{dòng thông tin kỹ thuật 1}}</div>
    <div>{{dòng thông tin kỹ thuật 2}}</div>
    <div>{{dòng thông tin kỹ thuật 3}}</div>
  </div>
  <div class="tags">
    <span class="tag">{{tag 1}}</span>
    <span class="tag">{{tag 2}}</span>
    <span class="tag">{{tag 3}}</span>
  </div>
</div>

B15 MULTI-AGENT GRID COORDINATOR (LƯỚI 2X2 PHỐI HỢP CÁC AGENT):
<div class="agent-grid">
  <div class="agent-card glow-card">
    <div class="header-wrap">
      <span class="icon">🧠</span>
      <div class="role">{{vai trò 1}}</div>
    </div>
    <div class="desc">{{mô tả nhiệm vụ 1}}</div>
  </div>
  <div class="agent-card glow-card">
    <div class="header-wrap">
      <span class="icon">💻</span>
      <div class="role">{{vai trò 2}}</div>
    </div>
    <div class="desc">{{mô tả nhiệm vụ 2}}</div>
  </div>
  <div class="agent-card glow-card">
    <div class="header-wrap">
      <span class="icon">🔍</span>
      <div class="role">{{vai trò 3}}</div>
    </div>
    <div class="desc">{{mô tả nhiệm vụ 3}}</div>
  </div>
  <div class="agent-card glow-card">
    <div class="header-wrap">
      <span class="icon">🚀</span>
      <div class="role">{{vai trò 4}}</div>
    </div>
    <div class="desc">{{mô tả nhiệm vụ 4}}</div>
  </div>
  <div class="agent-grid-center-pill">⚡ PHỐI HỢP</div>
</div>

═══════ AUDIO ═══════
<audio id="vN" src="assets/pN.wav" data-start="0" data-duration="10" data-volume="1"></audio>
(start/duration sẽ patch lại — placeholder OK)

═══════ NHẮC CUỐI ═══════
- TUYỆT ĐỐI tạo ĐỦ {scene_count} scene, id="scene1"…"scene{scene_count}". Đếm trước khi output.
- KHÔNG dùng Date.now / setTimeout / Math.random / fetch.
- KHÔNG redeclare CSS class đã có sẵn.
- TUYỆT ĐỐI không dùng repeating-linear-gradient diagonal/angled stripes cho background của .scene, #root, body — chỉ dùng cho decorative nhỏ (border, badge).
- ⚠️ TUYỆT ĐỐI KHÔNG ĐƯỢC định nghĩa lại hoặc override class `.scanlines` trong thẻ `<style>` dưới bất kỳ hình thức nào. Việc tự ý định nghĩa `.scanlines` sẽ tạo ra một lưới caro màu xám đè lên toàn bộ video, gây lỗi "mất nền" / màn hình nhiễu vô cùng xấu xí. Hãy để yên `.scanlines` mặc định của hệ thống.
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
        is_first = s.index == 0
        is_last = s.index == len(req.scenes) - 1
        lines.append(
            f"\n[Scene {s.index + 1}] start={cursor}s, duration={s.duration}s, end={cursor + s.duration}s"
        )
        lines.append(f"  Title: {s.title}")
        lines.append(f"  Narration: {s.narration}")
        lines.append(f"  Visual: {s.visualDescription}")
        if s.imageQuery:
            lines.append(f"  ImageQuery: {s.imageQuery}")

        if is_first and not s.imageAsset:
            lines.append(
                "  🎬 SCENE MỞ ĐẦU — BẮT BUỘC CINEMATIC HERO:"
                "\n  ⚠️ CHỌN 1 trong 4 TEMPLATE A/B/C/D ở system prompt (FULL-BLEED / MEGA-NUM / RETRO / BENTO HERO)."
                "\n  ⚠️ TUYỆT ĐỐI không dùng .scene.split với info-col + 1 logo box nhỏ — quá đơn điệu, không gây WOW."
                "\n  ⚠️ BẮT BUỘC kết hợp ÍT NHẤT 3 ambient decoratives: .aurora-glow + .animated-grid (hoặc .retro-grid hoặc .light-rays) + .ghost-text + .float-orb-lg."
                "\n  ⚠️ CẤM ĐẶT DECORATIVES TRONG .visual-col hoặc .info-col: Tất cả background decoratives (.float-orb-*, .aurora-glow, .animated-grid, .retro-grid, .light-rays, .ghost-text, .particle-field) PHẢI là con trực tiếp của thẻ .scene (ngay trước thẻ đóng </div> của .scene) làm nền phía sau, không được chen vào các cột nội dung làm đè và che khuất chữ."
                "\n  ⚠️ BẮT BUỘC dùng VISUAL pattern B14 (tech-card) HOẶC B13 (3-column glass cards) HOẶC B11 (stat-list) ở .visual-col để LẤP ĐẦY màn hình. CẤM TUYỆT ĐỐI bỏ trống .visual-col hoặc chỉ nhồi nhét badges tự do không theo pattern."
                "\n  ⚠️ Title PHẢI dùng .title-hero.grad-text hoặc .mega-num cực to."
                "\n  ⚠️ Có 2-3 .badge dạng tech tags (Edge AI · Privacy First · Real-time...) thay vì viết text dài."
                "\n  ⚠️ Mục tiêu: 3 giây đầu cinematic AWWWARDS quality — KHÔNG mockup nháp."
            )
        elif not is_first and not s.imageAsset:
            lines.append(
                "  🌌 SCENE NÀY (không ảnh) — BẮT BUỘC LẤP ĐẦY KHÔNG GIAN BẰNG KHỐI TRỰC QUAN:"
                "\n  ⚠️ CẤM TUYỆT ĐỐI bỏ trống hoặc chỉ đặt ambient decoratives trong .visual-col. Bạn BẮT BUỘC phải chọn 1 visual pattern thực tế (từ B1 đến B15, B17 đến B20) và điền nội dung, số liệu thực tế dựa trên kịch bản (narration / visualDescription) của scene này. Không dùng các từ/số liệu placeholder mặc định không liên quan."
                "\n  ⚠️ CẤM ĐẶT DECORATIVES TRONG .visual-col hoặc .info-col: Tất cả background decoratives (.float-orb-*, .aurora-glow, .animated-grid, .retro-grid, .light-rays, .ghost-text, .particle-field) PHẢI là con trực tiếp của thẻ .scene (ngay trước thẻ đóng </div> của .scene) làm nền phía sau, không được chen vào các cột nội dung làm đè và che khuất chữ."
                "\n  ⚠️ Background PHẢI có 2-4 ambient decoratives (.float-orb-md/.aurora-glow/.animated-grid/.ghost-text/.particle-field/.y2k-sparkle)."
                "\n  ⚠️ Mỗi phần tử trong feature grid, bento grid, hay step list phải cực kỳ giàu chi tiết: bắt buộc có emoji sinh động + tiêu đề màu nổi bật + mô tả ít nhất 2 dòng + ví dụ nội dung thực tế (mock code, progress bar, tags), xếp ngăn nắp, đối xứng, đồng đều, không bị lệch."
                "\n  ⚠️ Đa dạng layout — không lặp .split. Cân nhắc .centered/.hero/.magazine/.data tùy nội dung."
            )

        if s.imageAsset:
            lines.append(
                f"  IllustrationImage: {s.imageAsset}"
                f"\n  ⚠️ BẮT BUỘC dùng EXACT HTML này (copy nguyên): <div class=\"img-frame\"><img src=\"{s.imageAsset}\" alt=\"\"><span class=\"img-caption\">[caption tiếng Việt ngắn ≤10 chữ]</span></div>"
                f"\n  ⚠️ <img> PHẢI nằm BÊN TRONG .img-frame — KHÔNG đặt thẳng dưới .visual-col hay .scene."
                f"\n  ⚠️ Dùng layout `.scene.split` (50/50 text–ảnh) HOẶC `.scene.magazine` (7:5). KHÔNG dùng .hero, .centered, .data, .bento cho scene có ảnh."
                f"\n  ⚠️ .img-frame nằm trong .visual-col, KHÔNG được nằm trong .info-col hay tràn ra ngoài."
                f"\n  ✗ TUYỆT ĐỐI KHÔNG: <img> full-bleed background của .scene, position:absolute trên <img>, background-image url(...) lên #root/.scene, text overlay trực tiếp lên ảnh."
                f"\n  ✗ TUYỆT ĐỐI KHÔNG: width/height 100vw/100vh trên img, object-fit: cover trên cả màn hình."
                f"\n  ✗ KHÔNG lặp lại cùng 1 layout với scene ảnh khác — đa dạng split/magazine giữa các scene có ảnh."
            )
        elif not is_first:
            lines.append(
                f"  ⚠️ CẢNH BÁO: SCENE NÀY TUYỆT ĐỐI KHÔNG CÓ ẢNH MINH HỌA."
                f"\n  ⚠️ TUYỆT ĐỐI KHÔNG DÙNG THẺ <img> HOẶC CLASS .img-frame HOẶC BẤT KỲ ĐƯỜNG DẪN ẢNH NÀO."
                f"\n  ⚠️ BẮT BUỘC DÙNG MOCK VISUAL HTML/CSS (B1-B8, B11-B15) ĐỂ ĐIỀN VÀO .visual-col."
            )

        if is_last:
            lines.append(
                "  📐 SCENE CUỐI — CHỐNG OVERFLOW & BẮT BUỘC ĐỘC ĐÁO:"
                "\n  ⚠️ visual-col CỦA SCENE CUỐI PHẢI có: 1 .quote-block VÀ ít nhất 2-3 .feat-row/.agent-card hoặc 1 .stat-list với 2 stat-list-card ĐỂ KHÔNG TRỐNG. Cấm tuyệt đối chỉ nhồi ambient decoratives hay bỏ trống."
                "\n  ⚠️ CẤM ĐẶT DECORATIVES TRONG .visual-col hoặc .info-col: Tất cả background decoratives (.float-orb-*, .aurora-glow, .animated-grid, .retro-grid, .light-rays, .ghost-text, .particle-field) PHẢI là con trực tiếp của thẻ .scene (ngay trước thẻ đóng </div> của .scene) làm nền phía sau, không được chen vào các cột nội dung làm đè và che khuất chữ."
                "\n  ⚠️ Toàn bộ content visual-col PHẢI vừa trong khung 1920×1080 (chiều cao usable ~880px sau padding)."
                "\n  ⚠️ Nếu có danh sách bullet/feature > 4 mục → CẮT XUỐNG tối đa 4 mục."
                "\n  ⚠️ Padding visual-block ≤ 48px. Title trong card ≤ 2rem. Bullet ≤ 1.2rem."
                "\n  ⚠️ KHÔNG được để box content bị cắt mất ở mép dưới scene."
            )
        cursor += s.duration
    lines.append(
        f"\n⚠️ ĐẢM BẢO TƯƠNG PHẢN MÀU SẮC & ĐỘ ĐỌC ĐƯỢC CỰC CAO:"
        f"\n  - Font chữ và phông nền phải tương phản rõ rệt. Chữ chính sử dụng var(--text1), chữ phụ sử dụng var(--text2). CẤM dùng màu chữ tối như đen/xám tối trên nền tối."
        f"\n  - Nếu text nằm trên bất kỳ gradient hoặc element phát sáng nào, bắt buộc thêm text-shadow: 0 2px 8px rgba(0,0,0,0.9);"
        f"\n  - Thiết kế xếp các khối ngăn nắp, đồng đều, đối xứng tuyệt đối không bị lệch dòng hay chồng chéo."
        f"\n\nSinh composition HTML hoàn chỉnh dài đúng {cursor} giây với {len(req.scenes)} scene như trên. "
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


def extract_scene_layout_and_pattern(scene_html: str) -> tuple[str | None, str | None]:
    layout = None
    class_match = re.search(r'class\s*=\s*["\']([^"\']+)["\']', scene_html)
    if class_match:
        classes = class_match.group(1).split()
        for l in ["split", "centered", "hero", "magazine", "data"]:
            if l in classes:
                layout = l
                break

    pattern = None
    if "stat-hero" in scene_html:
        pattern = "B1 BIG STAT"
    elif "terminal" in scene_html:
        pattern = "B2 TERMINAL"
    elif "feat-grid" in scene_html:
        pattern = "B3 FEATURE GRID"
    elif "compare" in scene_html:
        pattern = "B4 COMPARE"
    elif "tl-list" in scene_html or "tl-item" in scene_html:
        pattern = "B5 TIMELINE"
    elif "quote-block" in scene_html or "quote-text" in scene_html:
        pattern = "B6 QUOTE"
    elif "stat-list" in scene_html:
        pattern = "B11 STAT-LIST"
    elif "chat-box" in scene_html or "chat-bubble" in scene_html:
        pattern = "B12 CHAT DIALOGUE"
    elif "feat-row" in scene_html or "glass-card" in scene_html:
        pattern = "B13 3-COLUMN GLASS CARD ROW"
    elif "tech-card" in scene_html:
        pattern = "B14 TECH-CARD"
    elif "step-list" in scene_html or "step-item" in scene_html:
        pattern = "B19 NUMBERED STEP LIST"

    return layout, pattern


def fallback_scene_html(s: ScenePayload, theme: dict) -> str:
    n = s.index + 1
    emojis = ["✨", "⚡", "🚀", "💫", "🎯", "🔥", "💎", "🌟"]
    emoji = emojis[(n - 1) % len(emojis)]
    
    title_class = "title-hero" if n == 1 else "title-xl"
    title_style = ' style="font-weight: 900 !important;"' if n == 1 else ""

    if s.imageAsset:
        visual_col_content = f'<div class="img-frame"><img src="{s.imageAsset}" alt=""><span class="img-caption">{s.title[:10]}</span></div>'
        layout = "split"
    else:
        truncated_narration = s.narration[:220].replace('"', '&quot;') + ("…" if len(s.narration) > 220 else "")
        visual_col_content = f'<div class="visual-block glow-card breath" style="text-align:center;padding:40px;"><p class="body-text" style="font-size:1.5rem;line-height:1.6;color:var(--text2);">{truncated_narration}</p></div>'
        layout = "centered"
        
    return f"""
  <div class="scene {layout}" id="scene{n}">
    <div class="aurora-glow" style="top:-15%; left:-10%;"></div>
    <div class="layout">
      <div class="info-col">
        <div id="s{n}-badge" class="badge">{emoji} PHẦN {n}</div>
        <h1 id="s{n}-title" class="{title_class} grad-text"{title_style} data-effect="typewriter">{s.title}</h1><span class="cursor-blink">|</span>
        <p id="s{n}-subtitle" class="subtitle">{s.title[:20]}...</p>
        <p id="s{n}-desc" class="body-text">{s.narration[:100]}...</p>
      </div>
      <div class="visual-col">
        {visual_col_content}
      </div>
    </div>
    <div class="corner-bracket tl"></div><div class="corner-bracket tr"></div>
    <div class="corner-bracket bl"></div><div class="corner-bracket br"></div>
    <div class="top-line"></div>
    <span class="scene-num">{n:02d}</span>
  </div>"""


def build_system_prompt_single_scene(theme: dict, scene_index: int, total_scenes: int, previous_context: dict) -> str:
    title_class = "title-hero" if scene_index == 1 else "title-xl"
    title_style = ' style="font-weight: 900 !important;"' if scene_index == 1 else ""

    prev_info = ""
    if scene_index > 1:
        prev_layout = previous_context.get("layout") or "Chưa rõ"
        prev_pattern = previous_context.get("visual_pattern") or "Chưa rõ"
        prev_info = (
            f"\n⚠️ THIẾT KẾ CỦA SCENE TRƯỚC (SCENE {scene_index - 1}):"
            f"\n  - Layout đã dùng: {prev_layout}"
            f"\n  - Visual pattern đã dùng: {prev_pattern}"
            f"\n  👉 BẮT BUỘC KHÔNG LẶP LẠI: Bạn phải chọn layout và visual pattern KHÁC cho scene này để giữ sự đa dạng."
        )

    return f"""Bạn là chuyên gia thiết kế giao diện AWWWARDS & UI/UX PRO MAX — sinh ra HTML cinematic, lung linh, gây ấn tượng WOW tuyệt đối.
Nhiệm vụ của bạn là sinh ra duy nhất mã HTML của block `<div class="scene ...">` cho Scene {scene_index} (trong tổng số {total_scenes} scene) cho theme **{theme['name']}**.

⚠️ QUY TẮC PHẢN HỒI (RẤT QUAN TRỌNG):
- CHỈ trả về duy nhất 1 block HTML bắt đầu bằng `<div class="scene LAYOUT"` và kết thúc bằng `</div>` tương ứng của scene đó.
- Tuyệt đối KHÔNG bọc thẻ `<html>`, `<head>`, `<body>` hay `#root` ở ngoài.
- Tuyệt đối KHÔNG trả về code Javascript hay script GSAP timeline (như `<script>gsap.timeline...</script>`).
- Tuyệt đối KHÔNG viết giải thích dài dòng bằng văn bản, chỉ trả về code HTML.
- KHÔNG dùng markdown code fences (như ```html) nếu có thể, hoặc nếu dùng thì chỉ bọc duy nhất block HTML đó.
- Bạn có thể viết tối đa 25 dòng CSS override trong thẻ `<style>` đặt NGAY BÊN TRONG thẻ `.scene` để tạo hiệu ứng/keyframes đặc biệt chỉ cho riêng scene này.

⚠️ NGÔN NGỮ: TIẾNG VIỆT có dấu đầy đủ. Giữ NGUYÊN VĂN narration/title/visualDescription. Tiếng Anh chỉ cho class CSS / comment / tên biến.

⚠️ THÔNG TIN THEME — {theme['name'].upper()}
- VIBE: {theme['vibe']}
- ƯU TIÊN visual effects: {theme['fx']}
- Dùng các biến màu CSS có sẵn (KHÔNG hardcode mã màu hex):
  `var(--bg)`, `var(--bg2)`, `var(--surface)`, `var(--accent)`, `var(--accent2)`, `var(--accent3)`, `var(--text1)`, `var(--text2)`, `var(--glow)`
{prev_info}

═══════════════════════════════════════
✨ HIỆU ỨNG ĐỘNG & BIỆN PHÁP CHỐNG ĐÈ CHỮ / CLIPPING (QUAN TRỌNG):
═══════════════════════════════════════
- ⚠️ QUY TẮC BỐ CỤC CHỐNG ĐÈ CHỮ & CHE KHUẤT SCENE (BẮT BUỘC):
  • SCENE 1 (Opening/Intro): BẮT BUỘC bọc toàn bộ nội dung mô tả, chữ trắng trong cột trực quan của Scene 1 vào các khối card thiết kế cao cấp (như `.tech-card B14`, `.feat-card`, hoặc `.glass-card`) có nền màu tối/kính mờ để làm nổi bật và chống đè chữ. Hãy dùng hiệu ứng xuất hiện lần lượt bằng animation delay để lấp đầy không gian.
  • SCENE 2 (Xếp chồng dọc 3 ô): Nếu có 3 ô/thẻ nội dung, CẤM TUYỆT ĐỐI xếp hàng ngang. BẮT BUỘC xếp chồng dọc từ trên xuống dưới sử dụng `.stat-list` (với các `.stat-list-card shimmer-fast glow-card` có delay tăng dần) hoặc hàng dọc `.feat-column`. Điều này giúp tận dụng không gian dọc hoàn hảo, không bao giờ bị che khuất Badge hoặc bị cắt xén ở trên.
  • SCENE 3, 4, 5 (Cấm chữ trắng trần & dùng hoạt ảnh lần lượt): CẤM TUYỆT ĐỐI viết các dòng chữ trắng trần/đơn điệu (naked text lines) trực tiếp trong `.visual-col` cho Scene 3, Scene 4 và Scene 5. Bắt buộc phải bọc mọi dòng mô tả/thành phần vào trong các ô có cấu trúc đẹp mắt có nền như `.glass-card`, `.feat-card`, `.stat-list-card`, hoặc `.step-item` và thiết lập thuộc tính `style="animation-delay: X.Xs"` để chúng xuất hiện tuần tự/lần lượt (staggered entrance) cực kỳ lung linh, chuyên nghiệp.

- Chúng ta sử dụng framework có sẵn các class động cực kỳ lung linh:
  - `.breath`: Tạo chuyển động bay bổng, nhịp thở êm ái. Hãy áp dụng cho các card như `.visual-block`, `.terminal`, `.feat-card`, `.compare`, `.quote-block` hoặc các ảnh `.img-frame`.
  - `.glow-card`: Viền neon lung linh tỏa sáng rực rỡ, kèm hiệu ứng 3D co giãn phóng to khi rê chuột cực kỳ mượt mà.
  - `.shimmer-fast`: Tạo hiệu ứng vệt sáng quét ngang thời thượng trên card (rất hợp với `.stat-list-card`).
  - `.y2k-sparkle`: Chèn ngôi sao lấp lánh vector retro. Ví dụ chèn vào trong visual block: `<span class="y2k-sparkle" style="top: 15%; left: 10%;"></span>`. Lưu ý: Container chứa ngôi sao sparkle phải có `position: relative`!
  - `.terminal .cursor`: Dùng class `cursor` nhấp nháy cho terminal: `<div>$ <span class="cursor"></span></div>`.

- 🎨 HƯỚNG DẪN VIẾT KEYFRAMES & CUSTOM STYLING (STYLE LIKE A PRO):
  Để tạo hoạt ảnh và phong cách độc bản Awwwards cực đỉnh mà không cần dùng script, bạn BẮT BUỘC tự viết thêm các keyframe CSS tinh tế trong `<style>` đặt ngay bên trong thẻ `.scene`:
  • 🌟 **Neon Border Glow Sweep (Quét sáng viền neon)**:
    `@keyframes neon-glow {{ 0%, 100% {{ border-color: rgba(255,255,255,0.08); box-shadow: 0 0 15px var(--glow); }} 50% {{ border-color: var(--accent2); box-shadow: 0 0 35px var(--accent); }} }}`
    (Áp dụng cho `.visual-block`, `.tech-card`, `.feat-card`).
  • 🌊 **Aurora Grid Mesh Drift (Sóng ánh sáng trôi lững lờ)**:
    `@keyframes aurora-mesh {{ 0%, 100% {{ transform: translate(0, 0) scale(1) rotate(0deg); }} 50% {{ transform: translate(30px, -20px) scale(1.05) rotate(5deg); }} }}`
    (Áp dụng cho `.aurora-glow` hoặc các gradient orbs).
  • 💫 **Y2K Retro Blink Stars (Ngôi sao lấp lánh kiểu Y2K)**:
    `@keyframes star-blink {{ 0%, 100% {{ opacity: 0.2; transform: scale(0.7) rotate(0deg); }} 50% {{ opacity: 1; transform: scale(1.2) rotate(45deg); }} }}`
    (Áp dụng cho `.y2k-sparkle` để tạo nhấp nháy retro).
  • 🎨 **Kinetic Font Gradient (Chữ chuyển màu sống động)**:
    `@keyframes grad-shift {{ 0% {{ background-position: 0% 50%; }} 50% {{ background-position: 100% 50%; }} 100% {{ background-position: 0% 50%; }} }}`
    (Cho chữ gradient có `background-size: 200% auto; animation: grad-shift 6s ease infinite`).

- ⚖️ QUY TẮC CÂN BẰNG THỊ GIÁC & CỐT LÕI BỐ CỤC (CHỐNG CHE KHUẤT CHỮ & TRÀN VIỀN):
  • **Cấm đặt Decoratives sai chỗ (Lỗi cực kỳ nghiêm trọng):** Tất cả background decoratives (.float-orb-*, .aurora-glow, .animated-grid, .retro-grid, .light-rays, .ghost-text, .particle-field) **CẤM TUYỆT ĐỐI** đặt bên trong `.visual-col` hoặc `.info-col`. Chúng **PHẢI** được đặt làm con trực tiếp của thẻ `.scene` (ngay trước thẻ đóng `</div>` của `.scene`) để làm nền phía sau, không được chen vào các cột nội dung làm đè và che khuất chữ.
  • **Chống tràn dọc và che khuất bởi phụ đề (BẮT BUỘC):**
    * **Mật độ nội dung:** Mọi nội dung của slide bắt buộc phải nằm gọn gàng trong chiều cao viewport khả dụng để không bao giờ đè lên phụ đề ở vùng dưới đáy màn hình (cách đáy 150px).
    * **Quy tắc tuyệt đối cho `.scene.centered` (layout căn giữa):** CẤM TUYỆT ĐỐI nhồi nhét đồng thời cả khối trích dẫn `.quote-block` và các thẻ card tính năng khác (`.stat-list`, `.feat-row`, `.compare`, `.bento-grid`, `.step-list`...) trên cùng một scene căn giữa. Bạn bắt buộc phải chọn 1 trong 2: hoặc là 1 khối `.quote-block` duy nhất cực kỳ trang trọng, hoặc là 1 nhóm card trực quan được căn giữa ngăn nắp. Việc chèn cả hai sẽ làm tràn dọc màn hình và bị phụ đề che khuất hoàn toàn!
    * **Quy tắc cho `.stat-list` và nhóm card dọc:** Chỉ được phép chứa tối đa 2 đến 3 thẻ con. Mỗi thẻ con mô tả cực kỳ ngắn gọn (không quá 2 dòng) để tránh làm chiều cao thẻ quá lớn gây tràn dọc.
  • **Quy định nghiêm ngặt về `.ghost-text` (Watermark nền):**
    * Chỉ được chứa **MỘT từ đơn cực ngắn từ 3-6 ký tự** (Ví dụ: "GSAP", "CORE", "FUTURE", "SPEED", "DATA"). Cấm tuyệt đối viết các cụm từ dài làm ghost-text vì kích thước chữ cực to sẽ tràn màn hình che sạch nội dung chính của slide.
    * Bắt buộc phải đặt ở góc lề ngoài qua inline style, ví dụ: style="bottom: -8%; right: -5%;" hoặc style="top: -10%; left: -5%;". CẤM đặt ở giữa màn hình hoặc các tọa độ 20%, 30%, 40% vì sẽ che khuất văn bản.
    * **CẤM override font-size quá to:** Mặc định class `.ghost-text` đã được định nghĩa font-size siêu lớn trong hệ thống. Cấm tuyệt đối dùng inline style để chỉnh font-size to hơn hoặc đặt vị trí đè lên các cột văn bản chính.
  • **Chống Slide Trống & Nội Dung Đơn Điệu (Scene 3 & Scene 4):**
    * Khi dùng Mock Visual biểu đồ hoặc danh sách (B1-B8, B11-B20), **cấm** để cột chữ (info-col) trống trải chỉ có Title và Subtitle. Bắt buộc chèn thêm các tag mini stack ngang hoặc các khối bổ trợ ngăn nắp bên dưới mô tả.
    * Mỗi phần tử trong feature grid, bento grid, hay step list phải cực kỳ giàu chi tiết: bắt buộc có emoji sinh động + tiêu đề màu nổi bật + mô tả ít nhất 2 dòng + ví dụ nội dung thực tế (mock code, progress bar, tags), xếp ngăn nắp, đối xứng, đồng đều, không bị lệch.
    * **CẤM TUYỆT ĐỐI sử dụng placeholder mặc định hoặc copy-paste vô căn cứ:** Mỗi khối trực quan trong `.visual-col` phải mang thông tin/số liệu/dữ liệu thực tiễn được trích xuất trực tiếp từ kịch bản của scene.
  • **Cân bằng khi có Ảnh Minh Họa (Scene 5 fix):** Khi dùng ảnh minh họa (`.img-frame`), cấm để cột chữ (`info-col`) trống trải chỉ có Title và Desc 1 dòng đơn điệu. Bắt buộc chèn thêm các thành phần bổ trợ ở dưới cột chữ như: một nhóm 2-3 badge mini stack ngang (`.badge`) chứa các tag kỹ thuật, hoặc một `.stat-list-card` mini hiển thị chỉ số liên quan đến ảnh, hoặc một timeline ngắn 2 mốc (`.tl-list`).
  • **Đảm bảo Tương Phản & Độ Đọc Được của Chữ (Legibility & Contrast):**
    * Tất cả text chính dùng `var(--text1)`, phụ dùng `var(--text2)`.
    * Cấm tuyệt đối dùng màu chữ tối (màu xám tối `#333`, màu đen, hay opacity quá thấp < 0.5) trên nền tối.
    * Nếu text nằm trên bất kỳ gradient hoặc background sáng nào, bắt buộc thêm `text-shadow: 0 2px 8px rgba(0,0,0,0.9);` để đảm bảo người xem đọc được rõ nét từng chữ.

- ⌨️ HIỆU ỨNG CHỮ HOẠT HÌNH CAO CẤP:
  Hệ thống đã tích hợp sẵn hiệu ứng đánh chữ thông minh bằng thuộc tính HTML (bạn KHÔNG cần viết script):
  • ⌨️ **Typewriter (Đánh chữ từng phím)**: Thêm thuộc tính `data-effect="typewriter"` vào thẻ chữ và chèn ngay sau nó con trỏ `<span class="cursor-blink">|</span>` để nhấp nháy đồng bộ tự động.
    Ví dụ: `<h1 id="sN-title" class="title-xl grad-text" data-effect="typewriter">Tiêu đề scene</h1><span class="cursor-blink">|</span>`
  • 🔄 **Word Rotation (Xoay từ khóa)**: Thêm `data-effect="word-rotate"` cùng danh sách từ cách nhau bằng dấu phẩy qua `data-words="từ_1,từ_2,từ_3"`.
    Ví dụ: `<span class="grad-text" data-effect="word-rotate" data-words="Tốc độ, Tiết kiệm, Bảo mật">Tốc độ</span><span class="cursor-blink">|</span>`
  • Cấm tuyệt đối việc tạo con trỏ nhấp nháy mà không có thuộc tính `data-effect` đi kèm.

═══════════════════════════════════════
QUY TẮC HTML BẮT BUỘC CHO SCENE {scene_index} (QUYẾT ĐỊNH VẺ ĐẸP):
═══════════════════════════════════════

1. BẮT BUỘC có lớp wrapper đúng định dạng:
   `<div class="scene LAYOUT" id="scene{scene_index}">`
   Với LAYOUT là 1 trong: split, centered, hero, magazine, data.

2. Cấu trúc chuẩn bên trong `.layout`:
   ```html
   <div class="scene LAYOUT" id="scene{scene_index}">
     <style>
       /* Có thể viết tối đa 25 dòng CSS override / custom keyframe tại đây để làm đẹp riêng scene này */
     </style>
     <!-- 2-5 ambient decoratives ở đây cho scene này -->
     <div class="aurora-glow" style="top:-15%; left:-10%;"></div>
     <div class="ghost-text" style="bottom:-5%; right:-5%;">KEYWORD</div>
     
     <div class="layout">
       <div class="info-col">
         <div id="s{scene_index}-badge" class="badge">PHẦN {scene_index}</div>
         <h1 id="s{scene_index}-title" class="{title_class} grad-text"{title_style} data-effect="typewriter">{{Tiêu đề}}</h1><span class="cursor-blink">|</span>
         <p id="s{scene_index}-subtitle" class="subtitle">{{phụ đề CỰC NGẮN ≤ 8 chữ}}</p>
         <p id="s{scene_index}-desc" class="body-text">{{TỐI ĐA 1 dòng tagline ≤ 12 chữ — KHÔNG copy narration}}</p>
       </div>
       <div class="visual-col">
         <!-- Bắt buộc dùng 1 trong các visual pattern chi tiết B1-B20 dưới đây -->
       </div>
     </div>
     <div class="corner-bracket tl"></div><div class="corner-bracket tr"></div>
     <div class="corner-bracket bl"></div><div class="corner-bracket br"></div>
     <div class="top-line"></div>
     <span class="scene-num">{scene_index:02d}</span>
   </div>
   ```

3. 🎬 NẾU LÀ SCENE MỞ ĐẦU (SCENE 1) - BẮT BUỘC WOW HERO:
   - Đây là phân cảnh giới thiệu nội dung chính của cả buổi thuyết trình. Tiêu đề chính (Title) của Scene 1 BẮT BUỘC PHẢI cực kỳ lớn, in đậm và nổi bật để tạo tác động mạnh mẽ (WOW effect) ngay lập tức.
   - BẮT BUỘC dùng class `.title-hero.grad-text` cho thẻ h1 của Scene 1 (không dùng `.title-xl`), và thêm CSS inline style `style="font-weight: 900 !important;"` để in đậm tối đa tiêu đề.
   - Hãy chọn 1 trong các TEMPLATES sau (tự do, đừng dùng .split):
   ▸ TEMPLATE A — FULL-BLEED HERO (intro):
     `<div class="scene hero" id="scene1">` có các background đầy đủ, status-pill, badges, particle-field và tech-card B14 hoặc bento-grid B16 lấp đầy không gian.
   ▸ TEMPLATE B — MEGA-NUM HERO (intro stats):
     `<div class="scene centered" id="scene1">` có mega-num cực lớn và hero-stat-banner.
   ▸ TEMPLATE C — RETRO/SYNTHWAVE HERO (intro theme y2k):
     `<div class="scene centered" id="scene1">` có retro-grid và outline-text.
   ▸ TEMPLATE D — BENTO HERO (tech showcase):
     `<div class="scene" id="scene1" style="padding:80px;">` có bento-grid 4 ô cực đẹp.

4. 🌌 DECORATIVE DENSITY (CHỐNG SLIDE TRỐNG):
   - MỖI scene BẮT BUỘC có 2-5 ambient decoratives lấp đầy không gian trống:
     • `.float-orb-lg/.float-orb-md/.float-orb-sm` — colored glow orbs
     • `.aurora-glow` — soft gradient blob drifting
     • `.animated-grid` — subtle moving grid pattern
     • `.retro-grid` — perspective synthwave floor
     • `.particle-field` — small stars pattern
     • `.ghost-text` — large thematic word (chỉ 1 từ 3-6 ký tự)
     • `.y2k-sparkle` × 4-6 rải rác
   - Quy tắc combine: 1 orb lớn + 1 grid/rays + 1 ghost-text + 2-3 sparkles/small-orbs.

5. 🎯 TEXT TRONG INFO-COL — CỰC GỌN:
   - sN-subtitle ≤ 8 chữ (cụm danh từ, KHÔNG phải câu)
   - sN-desc ≤ 12 chữ (tagline metadata)
   - TUYỆT ĐỐI KHÔNG copy narration. Dồn chi tiết vào visual-col.

═══════════════════════════════════════
🎨 DỰA TRÊN THÔNG TIN HÌNH ẢNH — CHỌN PHƯƠNG THỨC TRÌNH BÀY PHÙ HỢP:
═══════════════════════════════════════

A) NẾU scene CÓ ẢNH MINH HỌA (IllustrationImage):
   Bắt buộc đặt ảnh trong `.img-frame`:
   ```html
   <div class="img-frame">
     <img src="..." alt="">
     <span class="img-caption">{{caption tiếng Việt mô tả ảnh}}</span>
   </div>
   ```

B) NẾU scene KHÔNG CÓ ẢNH MINH HỌA (BẮT BUỘC MOCK VISUAL BẬC THẦY):
   Hãy chọn 1 trong các visual pattern sau để điền vào `.visual-col`, cấm tuyệt đối để trống:

   ▸ B1 — BIG STAT CARD (Chỉ số lớn):
     ```html
     <div class="visual-block" style="text-align:center;padding:50px;">
       <div><span class="stat-hero">90</span><span class="stat-suffix">%</span></div>
       <p class="caption" style="margin-top:20px;">{{nhãn}}</p>
       <p class="body-text" style="margin:12px auto 0;max-width:480px;">{{giải thích}}</p>
     </div>
     ```

   ▸ B2 — TERMINAL/CODE (Trình giả lập terminal cực ngầu):
     ```html
     <div class="terminal">
       <div class="dots"><i></i><i></i><i></i></div>
       <div><span class="c">// {{comment}}</span></div>
       <div><span class="k">const</span> data = <span class="s">"{{value}}"</span>;</div>
       <div>$ <span class="cursor"></span></div>
     </div>
     ```

   ▸ B4 — COMPARISON (Bảng so sánh):
     ```html
     <div class="compare">
       <div class="col"><h4>{{label tốt}}</h4><ul><li>{{point 1}}</li><li>{{point 2}}</li></ul></div>
       <div class="col bad"><h4>{{label xấu}}</h4><ul><li>{{point 1}}</li><li>{{point 2}}</li></ul></div>
     </div>
     ```

   ▸ B5 — TIMELINE (Trình tự thời gian):
     ```html
     <div class="tl-list">
       <div class="tl-item"><div class="y">{{năm}}</div><div class="t">{{event}}</div><div class="d">{{mô tả}}</div></div>
     </div>
     ```

   ▸ B6 — QUOTE (Trích dẫn cao cấp):
     ```html
     <div class="quote-block">
       <p class="quote-text">"{{trích dẫn}}"</p>
       <p class="quote-attr">{{tác giả · vai trò}}</p>
     </div>
     ```

   ▸ B11 — STAT-LIST (Danh sách 3 thẻ card chỉ số quét sáng neon cực sang):
     ```html
     <div class="stat-list">
       <div class="stat-list-card shimmer-fast glow-card"><div class="ic-wrap">⚡</div><div class="num">4x</div><div class="details"><div class="title">{{tiêu đề}}</div><div class="desc">{{mô tả}}</div></div></div>
       <div class="stat-list-card shimmer-fast glow-card" style="animation-delay: 0.4s;"><div class="ic-wrap">🚀</div><div class="num">12x</div><div class="details"><div class="title">{{tiêu đề 2}}</div><div class="desc">{{mô tả 2}}</div></div></div>
       <div class="stat-list-card shimmer-fast glow-card" style="animation-delay: 0.8s;"><div class="ic-wrap">💰</div><div class="num">50%</div><div class="details"><div class="title">{{tiêu đề 3}}</div><div class="desc">{{mô tả 3}}</div></div></div>
     </div>
     ```

   ▸ B12 — CHAT DIALOGUE SIMULATOR (Mô phỏng hội thoại AI Chat):
     ```html
     <div class="chat-box breath">
       <div class="chat-bubble user"><div class="sender-tag">NGƯỜI DÙNG</div>{{câu hỏi}}</div>
       <div class="chat-bubble ai"><div class="sender-tag">AI</div>{{câu trả lời}}</div>
       <div class="chat-footer-pill">{{chú thích}}</div>
     </div>
     ```

   ▸ B13 — 3-COLUMN GLASS CARD ROW (Hàng 3 thẻ kính):
     ```html
     <div class="feat-row">
       <div class="glass-card breath"><span class="emoji">🙋‍♂️</span><div class="title">{{t1}}</div><div class="desc">{{d1}}</div></div>
       <div class="glass-card breath" style="animation-delay: 0.5s;"><span class="emoji">👁️</span><div class="title">{{t2}}</div><div class="desc">{{d2}}</div></div>
       <div class="glass-card breath" style="animation-delay: 1.0s;"><span class="emoji">🔧</span><div class="title">{{t3}}</div><div class="desc">{{d3}}</div></div>
     </div>
     ```

   ▸ B14 — TECH SHOWCASE CARD (Thẻ kỹ thuật Google I/O cực xịn):
     ```html
     <div class="tech-card glow-card breath">
       <div class="brand">{{tên thương hiệu/sự kiện}}</div>
       <div class="meta">📅 {{ngày tháng · địa điểm}}</div>
       <div class="bullets"><div>{{dòng 1}}</div><div>{{dòng 2}}</div></div>
       <div class="tags"><span class="tag">{{tag1}}</span><span class="tag">{{tag2}}</span></div>
     </div>
     ```

   ▸ B17 — FORMULA TAG STACK (Phương trình khối màu):
     ```html
     <div class="visual-block" style="padding:40px;">
       <div class="formula-stack">
         <span class="formula-pill pink">🎭 VAI TRÒ</span><span class="formula-operator">+</span>
         <span class="formula-pill yellow">🌎 BỐI CẢNH</span><span class="formula-operator">+</span>
         <span class="formula-pill green">🎯 NHIỆM VỤ</span>
       </div>
       <div style="background:rgba(0,0,0,0.5); border:1px solid rgba(255,255,255,0.06); padding:24px; border-radius:16px; font-size:1.25rem; text-align:left; color:white;">
         <span style="color:#f472b6; font-weight:600;">{{mã màu 1}}</span>
         <span style="color:#fde047; font-weight:600;">{{mã màu 2}}</span>
         <span style="color:#4ade80; font-weight:600;">{{mã màu 3}}</span>
       </div>
     </div>
     ```

   ▸ B18 — COMMAND HIGHLIGHT CAPSULE (Hộp lệnh chú ý):
     ```html
     <div class="command-pill glow-card">
       <span class="command-icon" style="font-size:2rem; filter:drop-shadow(0 0 8px #fde047);">🔑</span>
       <div style="text-align:left;">"{{Lệnh chú ý quan trọng}}"</div>
     </div>
     ```

   ▸ B19 — NUMBERED STEP LIST (Danh sách quy trình các bước có số tròn nổi bật):
     ```html
     <div class="visual-block" style="padding:40px;">
       <div class="caption" style="color:var(--accent2); font-weight:700; margin-bottom:20px; text-transform:uppercase; text-align:left;">🎮 QUY TRÌNH THỰC HIỆN</div>
       <div class="step-list">
         <div class="step-item"><div class="step-circle">1</div><div class="step-text" style="text-align:left; font-weight:500;">{{bước 1}}</div></div>
         <div class="step-item"><div class="step-circle">2</div><div class="step-text" style="text-align:left; font-weight:500;">{{bước 2}}</div></div>
         <div class="step-item"><div class="step-circle">3</div><div class="step-text" style="text-align:left; font-weight:500;">{{bước 3}}</div></div>
       </div>
     </div>
     ```

   ▸ B20 — BENTO 3X2 GRID (Lưới Bento 6 ô thư viện đối xứng hoàn mỹ):
     ```html
     <div class="bento-3x2">
       <div class="bento-cell" style="border-top-color:#eab308; padding:20px;">
         <div class="ic">📊</div><div class="t">1. {{tiêu đề 1}}</div><div class="d">{{mô tả 1}}</div>
       </div>
       <div class="bento-cell" style="border-top-color:#38bdf8; padding:20px;">
         <div class="ic">📝</div><div class="t">2. {{tiêu đề 2}}</div><div class="d">{{mô tả 2}}</div>
       </div>
       <div class="bento-cell" style="border-top-color:#4ade80; padding:20px;">
         <div class="ic">🔍</div><div class="t">3. {{tiêu đề 3}}</div><div class="d">{{mô tả 3}}</div>
       </div>
       <div class="bento-cell" style="border-top-color:#f472b6; padding:20px;">
         <div class="ic">🎬</div><div class="t">4. {{tiêu đề 4}}</div><div class="d">{{mô tả 4}}</div>
       </div>
       <div class="bento-cell" style="border-top-color:#f59e0b; padding:20px;">
         <div class="ic">💡</div><div class="t">5. {{tiêu đề 5}}</div><div class="d">{{mô tả 5}}</div>
       </div>
       <div class="bento-cell" style="border-top-color:#10b981; padding:20px;">
         <div class="ic">📈</div><div class="t">6. {{tiêu đề 6}}</div><div class="d">{{mô tả 6}}</div>
       </div>
     </div>
     ```

- OUTPUT: chỉ trả về mã HTML sạch của khối `<div class="scene ...">` bắt đầu và kết thúc đúng, KHÔNG markdown code blocks bên ngoài, KHÔNG bọc thẻ html/head/body, KHÔNG giải thích.
"""


def build_user_prompt_single_scene(s: ScenePayload, previous_context: dict, is_first: bool, is_last: bool) -> str:
    lines = [
        f"Tiêu đề scene: {s.title}",
        f"Narration: {s.narration}",
        f"Visual Description: {s.visualDescription}",
        f"Duration: {s.duration} giây",
        f"Index: {s.index}",
    ]
    if s.imageQuery:
        lines.append(f"ImageQuery: {s.imageQuery}")
    
    if s.imageAsset:
        lines.append(
            f"IllustrationImage: {s.imageAsset}"
            f"\n  ⚠️ BẮT BUỘC dùng EXACT HTML này (copy nguyên): <div class=\"img-frame\"><img src=\"{s.imageAsset}\" alt=\"\"><span class=\"img-caption\">[caption tiếng Việt ngắn ≤10 chữ]</span></div>"
            f"\n  ⚠️ <img> PHẢI nằm BÊN TRONG .img-frame — KHÔNG đặt thẳng dưới .visual-col hay .scene."
            f"\n  ⚠️ Dùng layout `.scene.split` (50/50 text–ảnh) HOẶC `.scene.magazine` (7:5). KHÔNG dùng .hero, .centered, .data, .bento cho scene có ảnh."
            f"\n  ⚠️ .img-frame nằm trong .visual-col, KHÔNG được nằm trong .info-col hay tràn ra ngoài."
        )
    else:
        lines.append(
            f"  ⚠️ CẢNH BÁO: SCENE NÀY TUYỆT ĐỐI KHÔNG CÓ ẢNH MINH HỌA."
            f"\n  ⚠️ TUYỆT ĐỐI KHÔNG DÙNG THẺ <img> HOẶC CLASS .img-frame HOẶC BẤT KỲ ĐƯỜNG DẪN ẢNH NÀO."
            f"\n  ⚠️ BẮT BUỘC DÙNG MOCK VISUAL HTML/CSS (B1-B8, B11-B15, B19, B20) ĐỂ ĐIỀN VÀO .visual-col."
        )
        
    if is_first:
        lines.append(
            "\n  🎬 SCENE MỞ ĐẦU — BẮT BUỘC CINEMATIC HERO:"
            "\n  ⚠️ Chọn layout .scene.hero hoặc .scene.centered."
            "\n  ⚠️ Title BẮT BUỘC PHẢI cực kỳ lớn và in đậm (font-weight: 900). Sử dụng: <h1 id=\"s1-title\" class=\"title-hero grad-text\" style=\"font-weight: 900 !important;\" data-effect=\"typewriter\">[Tên tiêu đề chính]</h1>"
            "\n  ⚠️ BẮT BUỘC có `.status-pill` ở trên cùng và ít nhất 3 ambient decoratives."
        )
    elif is_last:
        lines.append(
            "\n  📐 SCENE CUỐI — CHỐNG OVERFLOW & BẮT BUỘC ĐỘC ĐÁO:"
            "\n  ⚠️ visual-col CỦA SCENE CUỐI PHẢI có: 1 .quote-block VÀ ít nhất 2-3 .feat-row/.agent-card hoặc 1 .stat-list với 2 stat-list-card ĐỂ KHÔNG TRỐNG."
        )
        
    lines.append(
        f"\nSinh block HTML cho scene {s.index + 1}."
    )
    return "\n".join(lines)


_BASE_CSS_MARKER = "/* === techbeat:base-css === */"


def inject_base_css(html: str, theme: dict) -> str:
    """Inject the framework CSS as the FIRST <style> in <head>, so the LLM's
    tiny override <style> (written later in <head>) wins under CSS cascade.

    The LLM no longer writes the variable block, body, root, scenes, or
    component classes — those live here. Idempotent: a marker comment guards
    against double-injection if the LLM happens to copy the framework anyway.
    """
    # ── Neutralize any illegal .scanlines overrides written by the LLM ──
    def _repl_style(m):
        sanitized = re.sub(r'\.scanlines\b', '.scanlines-disabled-by-system', m.group(1))
        return f"<style>{sanitized}</style>"
    html = re.sub(r'<style\b[^>]*>(.*?)</style>', _repl_style, html, flags=re.DOTALL | re.IGNORECASE)

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


async def _materialise_scene_images(scenes: list, project_root: Path) -> list:
    """Download / decode every scene's `imageUrl` into an actual file under
    `assets/sceneN.<ext>` and populate `imageAsset`.

    Why: the LLM's image instructions are gated on `imageAsset` (a real
    file path). When the user picks an image in the preview stage, only
    `imageUrl` is set — it might be a data URL, blob URL, or HTTPS URL.
    Without materialising, the LLM is told "no image" for every scene and
    the generated HTML has no <img> tags at all.

    Returns a NEW list of ScenePayload with `imageAsset` set where possible.
    Never raises — image fetch failures degrade gracefully (scene treated
    as image-less by the LLM).
    """
    import base64 as _b64
    import re as _re
    import httpx as _httpx

    assets_dir = project_root / "assets"
    assets_dir.mkdir(exist_ok=True)

    out: list = []
    async with _httpx.AsyncClient(timeout=15.0, follow_redirects=True) as http:
        for s in scenes:
            asset_rel = s.imageAsset  # respect any already-set value
            url = s.imageUrl or ""

            if not asset_rel and url.startswith("data:image/"):
                m = _re.match(r"^data:image/([a-z0-9+.-]+);base64,(.+)$", url, _re.IGNORECASE)
                if m:
                    ext_raw = m.group(1).lower()
                    ext = {"jpeg": "jpg", "svg+xml": "svg"}.get(ext_raw, ext_raw)
                    if ext not in ("jpg", "png", "webp", "gif", "svg"):
                        ext = "jpg"
                    try:
                        raw = _b64.b64decode(m.group(2))
                        local = assets_dir / f"scene{s.index + 1}.{ext}"
                        local.write_bytes(raw)
                        asset_rel = f"assets/{local.name}"
                        print(f"[preview] decoded uploaded image scene {s.index + 1} → {asset_rel}")
                    except Exception as e:
                        print(f"[preview] decode data URL scene {s.index + 1} failed: {e}")

            elif not asset_rel and url.startswith(("http://", "https://")):
                ext = ".jpg"
                low = url.lower().split("?")[0]
                for cand in (".png", ".webp", ".jpeg", ".jpg", ".gif"):
                    if low.endswith(cand):
                        ext = ".jpg" if cand == ".jpeg" else cand
                        break
                local = assets_dir / f"scene{s.index + 1}{ext}"
                try:
                    resp = await http.get(
                        url,
                        headers={"User-Agent": "Mozilla/5.0", "Referer": "https://duckduckgo.com/"},
                    )
                    if resp.status_code == 200 and resp.content:
                        local.write_bytes(resp.content)
                        asset_rel = f"assets/{local.name}"
                        print(f"[preview] downloaded HTTPS image scene {s.index + 1} → {asset_rel}")
                except Exception as e:
                    print(f"[preview] download scene {s.index + 1} failed: {e}")

            out.append(s.model_copy(update={"imageAsset": asset_rel}))
    return out


def inject_missing_scene_placeholders(html: str, scenes: list[ScenePayload], missing: list[int]) -> str:
    placeholders = []
    emojis = ["✨", "⚡", "🚀", "💫", "🎯", "🔥", "💎", "🌟"]
    for idx in missing:
        n = idx
        scene_payload = next((s for s in scenes if s.index == n), None)
        if not scene_payload and n <= len(scenes):
            scene_payload = scenes[n - 1]
            
        title = scene_payload.title if scene_payload else ""
        narration = scene_payload.narration if scene_payload else ""
        scene_num_padded = f"{n:02d}"
        emoji = emojis[(n - 1) % len(emojis)]
        
        narration_p = ""
        if narration:
            truncated_narration = narration[:220].replace('"', '&quot;') + ("…" if len(narration) > 220 else "")
            narration_p = f'<p id="s{n}-desc" class="body-text" style="max-width:1000px;margin:0 auto;font-size:1.5rem;line-height:1.6;color:var(--text2,#a09db8);">{truncated_narration}</p>'
        
        ph = (
            f'\n  <!-- SCENE {n} (Fallback) -->'
            f'\n  <div class="scene scene-fallback centered" id="scene{n}" style="position:absolute;inset:0;opacity:0;visibility:hidden;background:linear-gradient(135deg,var(--bg,#08080f),var(--bg2,#0f0f1a));">'
            f'\n    <div class="corner-bracket tl"></div><div class="corner-bracket tr"></div>'
            f'\n    <div class="corner-bracket bl"></div><div class="corner-bracket br"></div>'
            f'\n    <div class="top-line"></div>'
            f'\n    <span class="scene-num">{scene_num_padded}</span>'
            f'\n    <div class="layout" style="padding:100px 140px;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;gap:36px;">'
            f'\n      <div id="s{n}-badge" class="badge" style="margin:0 auto;">{emoji} &nbsp; PHẦN {n}</div>'
            f'\n      <h1 id="s{n}-title" class="title-xl grad-text" style="max-width:1400px;margin:0 auto;">{title or f"Nội dung phân cảnh {n}"}</h1>'
            f'\n      {narration_p}'
            f'\n      <div style="display:flex;gap:16px;margin-top:20px;flex-wrap:wrap;justify-content:center;">'
            f'\n        <div class="badge" style="background:var(--surface,#141420);">📺 &nbsp; ON AIR</div>'
            f'\n        <div class="badge" style="background:var(--surface,#141420);">▶ &nbsp; SCENE {scene_num_padded}</div>'
            f'\n        <div class="badge" style="background:var(--surface,#141420);">🎬 &nbsp; TECHBEAT</div>'
            f'\n      </div>'
            f'\n    </div>'
            f'\n  </div>'
        )
        placeholders.append(ph)
        
    placeholder_str = "".join(placeholders)
    
    # Chèn placeholders vào trước thẻ đóng </div> cuối cùng của #root
    lower_html = html.lower()
    body_idx = lower_html.rfind("</body>")
    if body_idx != -1:
        div_idx = html[:body_idx].rfind("</div>")
        if div_idx != -1:
            return html[:div_idx] + placeholder_str + "\n" + html[div_idx:]
            
    return html + placeholder_str


async def stream_composition_events(req: CompositionRequest) -> AsyncGenerator[dict, None]:
    """Yield raw event dicts: {type:'chunk',text} | {type:'done',html,scenes?} | {type:'error',message}"""
    import os as _os
    theme = get_theme(req.theme)

    # ── Materialise images FIRST so the LLM gets real file paths ────────
    try:
        materialised = await _materialise_scene_images(req.scenes, get_project_root())
        req = req.model_copy(update={"scenes": materialised})
    except Exception as e:
        print(f"[preview] image materialisation skipped: {e}")

    try:
        scenes_html = []
        previous_context = {
            "layout": None,
            "visual_pattern": None,
            "used_layouts": [],
            "used_patterns": []
        }

        for idx_zero, s in enumerate(req.scenes):
            idx = idx_zero + 1
            is_first = (idx == 1)
            is_last = (idx == len(req.scenes))

            sys_single = build_system_prompt_single_scene(theme, idx, len(req.scenes), previous_context)
            prompt_single = build_user_prompt_single_scene(s, previous_context, is_first, is_last)

            def _kwargs(provider_name: str) -> dict:
                return {
                    "messages": [
                        {"role": "system", "content": sys_single},
                        {"role": "user", "content": prompt_single},
                    ],
                    "temperature": 0.7 if provider_name == "primary" else 0.75,
                    "max_tokens": 4000,
                    "stream": True,
                }

            try:
                stream, provider, model = await chat_completions_with_fallback(
                    model_kind="composition",
                    kwargs_factory=_kwargs,
                )

                yield {"type": "model_info", "provider": provider, "model": model}

                scene_text = ""
                async for chunk in stream:
                    if not chunk.choices:
                        continue
                    choice = chunk.choices[0]
                    delta = choice.delta
                    text = getattr(delta, "content", None)
                    if text:
                        scene_text += text
                        yield {"type": "chunk", "text": text}

                scene_html = strip_fences(scene_text).strip()
                if not scene_html.lower().startswith("<div"):
                    m = re.search(r"<div\b[\s\S]*</div>\s*$", scene_html)
                    if m:
                        scene_html = m.group(0)

                layout, pattern = extract_scene_layout_and_pattern(scene_html)
                previous_context["layout"] = layout
                previous_context["visual_pattern"] = pattern
                if layout:
                    previous_context["used_layouts"].append(layout)
                if pattern:
                    previous_context["used_patterns"].append(pattern)

                scenes_html.append(scene_html)
                print(f"[composition] Scene {idx}/{len(req.scenes)} generated: layout={layout}, pattern={pattern} ({provider}/{model})")

            except Exception as e:
                print(f"[composition] Scene {idx}/{len(req.scenes)} generation failed: {e}. Using fallback.")
                yield {
                    "type": "warning",
                    "message": f"Scene {idx} sinh thất bại ({e}). Đã dùng fallback HTML.",
                }
                fb_html = fallback_scene_html(s, theme)
                scenes_html.append(fb_html)

        # Assemble the full HTML boilerplate
        scenes_combined = "\n\n  ".join(scenes_html)
        base_css = render_base_css(theme)

        html = f"""<!doctype html>
<html lang="vi">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{req.title}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=JetBrains+Mono:wght@400;600;800&display=swap" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
<style>
/* === techbeat:base-css === */
{base_css}

/* Custom scene-specific animations */
@keyframes neon-glow {{
  0%, 100% {{ border-color: rgba(255,255,255,0.08); box-shadow: 0 0 15px var(--glow); }}
  50% {{ border-color: var(--accent2); box-shadow: 0 0 35px var(--accent); }}
}}
@keyframes aurora-mesh {{
  0%, 100% {{ transform: translate(0, 0) scale(1) rotate(0deg); }}
  50% {{ transform: translate(30px, -20px) scale(1.05) rotate(5deg); }}
}}
@keyframes star-blink {{
  0%, 100% {{ opacity: 0.2; transform: scale(0.7) rotate(0deg); }}
  50% {{ opacity: 1; transform: scale(1.2) rotate(45deg); }}
}}
@keyframes grad-shift {{
  0% {{ background-position: 0% 50%; }}
  50% {{ background-position: 100% 50%; }}
  100% {{ background-position: 0% 50%; }}
}}

/* Compact styling for comparison layout to prevent overflow */
.compare .col {{
  padding: 24px !important;
}}
.compare .col li {{
  font-size: 1.25rem !important;
  padding: 6px 0 !important;
}}
.compare .col li ul li {{
  font-size: 1.15rem !important;
  padding: 4px 0 !important;
}}
.compare .col h4 {{
  margin-bottom: 12px !important;
}}
.compare .terminal {{
  padding: 20px 24px !important;
  font-size: 1.1rem !important;
}}
</style>
</head>
<body>
<div id="root" data-composition-id="main" data-start="0" data-width="1920" data-height="1080" data-duration="{req.totalDuration}">
  <div class="scanlines"></div>
  
  {scenes_combined}
  
</div>
</body>
</html>"""

        html = inject_base_css(html, theme)
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


def sanitize_scene_wrapper(scene_html: str, idx: int) -> str:
    """Ensure the root element of the scene always has class="scene LAYOUT" and id="sceneN"."""
    scene_html = scene_html.strip()
    if not scene_html.lower().startswith("<div"):
        m = re.search(r"<div\b[\s\S]*</div>\s*$", scene_html, re.IGNORECASE)
        if m:
            scene_html = m.group(0)
        else:
            return scene_html

    tag_match = re.match(r'^(<div\b[^>]*>)', scene_html, re.IGNORECASE)
    if not tag_match:
        return scene_html

    tag = tag_match.group(1)

    # 1. Enforce id="sceneN"
    if f'id="scene{idx}"' not in tag and f"id='scene{idx}'" not in tag:
        # Strip any existing id to avoid duplicates
        tag = re.sub(r'\bid\s*=\s*["\'][^"\']*["\']', '', tag, flags=re.IGNORECASE)
        tag = tag.rstrip('>').rstrip('/') + f' id="scene{idx}">'

    # 2. Enforce class="scene ..."
    class_match = re.search(r'\bclass\s*=\s*["\']([^"\']*)["\']', tag, re.IGNORECASE)
    if class_match:
        classes = class_match.group(1).split()
        if "scene" not in classes:
            classes.insert(0, "scene")
        tag = re.sub(r'\bclass\s*=\s*["\']([^"\']*)["\']', f'class="{" ".join(classes)}"', tag, flags=re.IGNORECASE)
    else:
        tag = tag.rstrip('>').rstrip('/') + ' class="scene">'

    # Make sure we normalize closing bracket
    if not tag.endswith(">"):
        tag += ">"

    return tag + scene_html[tag_match.end():]


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

    # ── Resolve image source ─────────────────────────────────────────────
    # Reuse the shared image materialiser so data URLs (upload) AND https
    # URLs (Openverse) both get downloaded/decoded to assets/sceneN.<ext>
    # before the LLM is told about them. Without this, the regen call ends
    # up sending the raw imageUrl (megabytes for data URLs, or unfetched
    # https for search results) and the LLM either explodes on token limit
    # or skips the image entirely.
    materialised_scenes = await _materialise_scene_images([body.scene], get_project_root())
    effective_asset = materialised_scenes[0].imageAsset if materialised_scenes else body.scene.imageAsset

    image_clause = ""
    if effective_asset:
        image_clause = (
            f"\n  IllustrationImage: {effective_asset}"
            f"\n  ⚠️ BẮT BUỘC dùng EXACT HTML: <div class=\"img-frame\"><img src=\"{effective_asset}\" alt=\"\"><span class=\"img-caption\">[caption ≤10 chữ]</span></div>"
            f"\n  ⚠️ Layout PHẢI là .scene.split hoặc .scene.magazine — KHÔNG .hero/.centered/.bento."
            f"\n  ✗ TUYỆT ĐỐI KHÔNG full-bleed background image, position:absolute trên <img>, hay background-image url(...) lên #root/.scene."
        )

    total_scenes = len(re.findall(r'id=["\']scene\d+["\']', body.fullHtml)) or body.sceneIndex
    sys_msg = build_system_prompt_single_scene(theme, body.sceneIndex, total_scenes, {})
    user_msg = build_user_prompt_single_scene(
        body.scene,
        {},
        body.sceneIndex == 1,
        body.sceneIndex == total_scenes
    )

    try:
        resp, provider, model = await chat_completions_with_fallback(
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
            
    # Normalize wrapper class and id programmatically before validation
    new_block = sanitize_scene_wrapper(new_block, body.sceneIndex)
    
    if f'scene{body.sceneIndex}' not in new_block:
        raise HTTPException(
            status_code=502,
            detail=f"LLM trả về scene sai id (thiếu scene{body.sceneIndex}).",
        )

    start, end = bounds
    updated = body.fullHtml[:start] + new_block + body.fullHtml[end:]
    return {"html": updated, "provider": provider}


# ─────────────────────────  GEN SCENE ONE  ─────────────────────────


class GenSceneOneRequest(BaseModel):
    title: str
    scenes: list[ScenePayload]
    totalDuration: float
    theme: str | None = None
    sceneIndex: int  # 1-based — scene cần gen lần này
    existingHtml: str | None = None  # HTML đã có (từ scene 1..N-1), None nếu là scene 1
    previousContext: dict | None = None  # layout/pattern của scene trước


def _build_boilerplate(title: str, total_duration: float, theme: dict, base_css: str) -> str:
    """Tạo HTML boilerplate rỗng (chưa có scene nào) để append scene vào sau."""
    return f"""<!doctype html>
<html lang="vi">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=JetBrains+Mono:wght@400;600;800&display=swap" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
<style>
/* === techbeat:base-css === */
{base_css}

/* Custom scene-specific animations */
@keyframes neon-glow {{
  0%, 100% {{ border-color: rgba(255,255,255,0.08); box-shadow: 0 0 15px var(--glow); }}
  50% {{ border-color: var(--accent2); box-shadow: 0 0 35px var(--accent); }}
}}
@keyframes aurora-mesh {{
  0%, 100% {{ transform: translate(0, 0) scale(1) rotate(0deg); }}
  50% {{ transform: translate(30px, -20px) scale(1.05) rotate(5deg); }}
}}
@keyframes star-blink {{
  0%, 100% {{ opacity: 0.2; transform: scale(0.7) rotate(0deg); }}
  50% {{ opacity: 1; transform: scale(1.2) rotate(45deg); }}
}}
@keyframes grad-shift {{
  0% {{ background-position: 0% 50%; }}
  50% {{ background-position: 100% 50%; }}
  100% {{ background-position: 0% 50%; }}
}}

/* Compact styling for comparison layout to prevent overflow */
.compare .col {{
  padding: 24px !important;
}}
.compare .col li {{
  font-size: 1.25rem !important;
  padding: 6px 0 !important;
}}
.compare .col li ul li {{
  font-size: 1.15rem !important;
  padding: 4px 0 !important;
}}
.compare .col h4 {{
  margin-bottom: 12px !important;
}}
.compare .terminal {{
  padding: 20px 24px !important;
  font-size: 1.1rem !important;
}}
</style>
</head>
<body>
<div id="root" data-composition-id="main" data-start="0" data-width="1920" data-height="1080" data-duration="{total_duration}">
  <div class="scanlines"></div>

<!-- __SCENES_PLACEHOLDER__ -->

</div>
</body>
</html>"""


def _append_scene_to_html(existing_html: str, scene_html: str) -> str:
    """Append một scene block vào trước <!-- __SCENES_PLACEHOLDER__ --> hoặc trước </div></body>."""
    placeholder = "<!-- __SCENES_PLACEHOLDER__ -->"
    if placeholder in existing_html:
        return existing_html.replace(placeholder, scene_html + "\n\n" + placeholder, 1)
    # fallback: chèn trước </div> cuối trước </body>
    body_idx = existing_html.lower().rfind("</body>")
    if body_idx != -1:
        div_idx = existing_html[:body_idx].rfind("</div>")
        if div_idx != -1:
            return existing_html[:div_idx] + "\n" + scene_html + "\n" + existing_html[div_idx:]
    return existing_html + "\n" + scene_html


@router.post("/gen-scene-one")
async def gen_scene_one(body: GenSceneOneRequest):
    """Gen 1 scene duy nhất, trả về HTML cập nhật ngay.

    - sceneIndex=1, existingHtml=None → tạo boilerplate + gen scene 1
    - sceneIndex>1, existingHtml=... → gen scene mới + append vào existingHtml

    Response: { html, sceneIndex, totalScenes, done, provider, model, layout, visualPattern }
    """
    theme = get_theme(body.theme)
    total = len(body.scenes)
    idx = body.sceneIndex  # 1-based

    if idx < 1 or idx > total:
        raise HTTPException(status_code=400, detail=f"sceneIndex={idx} ngoài phạm vi 1..{total}")

    # 0-based index trong mảng scenes
    s = body.scenes[idx - 1]
    is_first = idx == 1
    is_last = idx == total

    # Materialise ảnh cho scene này
    try:
        materialised = await _materialise_scene_images([s], get_project_root())
        s = materialised[0]
    except Exception as e:
        print(f"[gen-scene-one] image materialise failed for scene {idx}: {e}")

    # Lấy previous context từ body hoặc mặc định
    prev_ctx = body.previousContext or {"layout": None, "visual_pattern": None, "used_layouts": [], "used_patterns": []}

    sys_prompt = build_system_prompt_single_scene(theme, idx, total, prev_ctx)
    user_prompt = build_user_prompt_single_scene(s, prev_ctx, is_first, is_last)

    def _kwargs(provider_name: str) -> dict:
        return {
            "messages": [
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.7 if provider_name == "primary" else 0.75,
            "max_tokens": 4000,
            "stream": False,
        }

    scene_html: str | None = None
    provider = "unknown"
    model = "unknown"

    try:
        resp, provider, model = await chat_completions_with_fallback(
            model_kind="composition",
            kwargs_factory=_kwargs,
        )
        raw = resp.choices[0].message.content or ""
        scene_html = strip_fences(raw).strip()
        if not scene_html.lower().startswith("<div"):
            m = re.search(r"<div\b[\s\S]*</div>\s*$", scene_html)
            if m:
                scene_html = m.group(0)
            else:
                scene_html = None
                
        # Normalize wrapper class and id programmatically
        if scene_html:
            scene_html = sanitize_scene_wrapper(scene_html, idx)
    except Exception as e:
        print(f"[gen-scene-one] LLM failed for scene {idx}: {e}")

    # Fallback nếu LLM thất bại
    if not scene_html:
        scene_html = fallback_scene_html(s, theme)

    # Trích layout / pattern để trả về cho frontend (dùng làm previousContext lần sau)
    layout, visual_pattern = extract_scene_layout_and_pattern(scene_html)

    # Ghép HTML
    if is_first or not body.existingHtml:
        base_css = render_base_css(theme)
        html = _build_boilerplate(body.title, body.totalDuration, theme, base_css)
        html = _append_scene_to_html(html, scene_html)
    else:
        html = _append_scene_to_html(body.existingHtml, scene_html)

    print(f"[gen-scene-one] Scene {idx}/{total} done: layout={layout}, pattern={visual_pattern} ({provider}/{model})")

    return {
        "html": html,
        "sceneIndex": idx,
        "totalScenes": total,
        "done": is_last,
        "provider": provider,
        "model": model,
        "layout": layout,
        "visualPattern": visual_pattern,
        "newContext": {
            "layout": layout,
            "visual_pattern": visual_pattern,
            "used_layouts": (prev_ctx.get("used_layouts") or []) + ([layout] if layout else []),
            "used_patterns": (prev_ctx.get("used_patterns") or []) + ([visual_pattern] if visual_pattern else []),
        },
    }
