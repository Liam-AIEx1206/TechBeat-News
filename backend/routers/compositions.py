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
  display: grid; gap: 80px; height: 100%;
  padding: 100px 120px; align-items: center;
  position: relative; z-index: 10;
}}
.scene.split .layout    {{ grid-template-columns: 1fr 1fr; }}
.scene.hero .layout     {{ grid-template-columns: 1fr; justify-items: start; }}
.scene.centered .layout {{ grid-template-columns: 1fr; justify-items: center; text-align: center; }}
.scene.magazine .layout {{ grid-template-columns: 7fr 5fr; gap: 80px; }}
.scene.data .layout     {{ grid-template-columns: 1fr 1.4fr; }}

.info-col   {{
  display: flex; flex-direction: column; justify-content: center; gap: 28px;
  min-width: 0; max-height: 100%; overflow: hidden;
}}
.visual-col {{
  display: flex; flex-direction: column; justify-content: center; gap: 24px;
  min-width: 0; max-width: 100%; max-height: 100%; overflow: hidden;
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
  position: absolute; bottom: 20px; right: 40px;
  font-family: 'JetBrains Mono', monospace;
  font-size: 9rem; font-weight: 800;
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
  font-weight: 900; line-height: 1.1; letter-spacing: -0.04em;
  color: var(--text1);
}}
.title-hero {{
  font-size: clamp(5.5rem, 8.5vw, 8.5rem);
  font-weight: 900; line-height: 1.0; letter-spacing: -0.05em;
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
}}
.outline-text {{
  -webkit-text-stroke: 2px var(--accent); color: transparent;
}}

/* Hero stat — for B1 BIG STAT pattern */
.stat-hero {{
  font-size: clamp(6.5rem, 9vw, 9.5rem);
  font-weight: 900; line-height: 1.1; letter-spacing: -0.05em;
  font-feature-settings: 'tnum';
  background: linear-gradient(135deg, var(--accent), var(--accent3));
  -webkit-background-clip: text; background-clip: text;
  -webkit-text-fill-color: transparent; color: transparent;
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
.feat-card .d  {{ font-size: 1.15rem; color: var(--text2); line-height: 1.6; word-break: break-word; }}

/* Comparison — for B4 */
.compare {{ display: grid; grid-template-columns: 1fr 1fr; gap: 32px; min-height: 0; width: 100%; }}
.compare .col {{ padding: 40px; border-radius: 28px; border: 2px solid {accent}33; background: var(--surface); transition: all 0.3s ease; overflow: visible; word-break: break-word; }}
.compare .col:hover {{ border-color: var(--accent2); transform: scale(1.02); }}
.compare .col h4 {{ font-family: 'JetBrains Mono', monospace; font-size: 1.2rem; letter-spacing: 0.18em; text-transform: uppercase; color: var(--accent2); margin-bottom: 24px; }}
.compare .col li {{ list-style: none; padding: 12px 0; color: var(--text2); font-size: 1.3rem; line-height: 1.6; word-break: break-word; overflow-wrap: anywhere; }}
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
.quote-block {{ position: relative; padding: 80px 60px; width: 100%; }}
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
  font-size: 1.2rem; color: var(--text2); opacity: 0.85;
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
.glass-card .desc {{ font-size: 1.2rem; color: var(--text2); line-height: 1.6; }}

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
  border-radius: 28px; padding: 32px;
  position: relative; overflow: hidden;
  transition: all 0.4s cubic-bezier(0.25, 0.8, 0.25, 1);
}}
.bento-cell.wide {{ grid-column: span 2; }}
.bento-cell.tall {{ grid-row: span 2; }}
.bento-cell.hero {{ grid-column: span 2; grid-row: span 2; background: linear-gradient(135deg, var(--surface), {accent}1a); border-color: {accent}66; }}
.bento-cell:hover {{ transform: translateY(-4px); border-color: var(--accent2); }}

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
.terminal .cursor {{
  animation: cursor-blink 0.9s infinite step-end;
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
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
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

Class có sẵn (DÙNG, không tự viết):
LAYOUT: .scene/.split/.centered/.hero/.magazine/.data, .layout, .info-col, .visual-col
TEXT: .badge, .title-xl, .title-hero, .subtitle, .body-text, .caption, .grad-text, .outline-text, .mega-num
VISUAL BLOCKS: .visual-block, .img-frame, .img-caption, .terminal, .feat-grid, .feat-card, .compare, .tl-list, .tl-item, .quote-block, .quote-text, .stat-list, .stat-list-card, .chat-box, .chat-bubble, .agent-grid, .agent-card, .tech-card, .glass-card, .feat-row, .bento-grid, .bento-cell, .hero-stat-banner
CHROME: .corner-bracket (tl/tr/bl/br), .top-line, .scene-num, .scanlines, .status-pill
DECORATIVES (lấp đầy không gian): .float-orb-lg/.float-orb-md/.float-orb-sm, .aurora-glow, .animated-grid, .retro-grid, .light-rays, .particle-field, .ghost-text, .marquee-strip, .y2k-sparkle, .glow-orb
ANIMATIONS: .breath, .shimmer-fast, .glow-card, .glow-border, .glow-text

🌌 LẤP ĐẦY KHÔNG GIAN — MỖI scene 2-5 decoratives (position:absolute):
  • 1 .float-orb-lg/aurora-glow (background presence)
  • 1 .animated-grid/retro-grid/light-rays (texture)
  • 1 .ghost-text với thematic word (depth)
  • 2-3 .y2k-sparkle hoặc .float-orb-sm rải rác

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

🎬 SCENE 1 = OPENING HERO (BẮT BUỘC ấn tượng):
- Scene #1 PHẢI là class="scene centered" hoặc class="scene hero" — KHÔNG được để trống visual-col chỉ vài chữ.
- BẮT BUỘC có: title-hero gradient cực to (.title-hero.grad-text), 2-3 badge/status-pill stack ngang, eyebrow .caption, decorative effect (status-pill phía trên + corner-bracket + breath animation).
- Nếu không có ảnh ở scene 1 → dùng VISUAL pattern B14 (tech-card) HOẶC B13 (3-column glass cards) HOẶC B11 (stat-list) ở visual-col để LẤP ĐẦY màn hình. KHÔNG được chỉ hiển thị 1 box logo nhỏ chính giữa.

📐 CHỐNG CONTENT TRÀN KHUNG 1080px (BẮT BUỘC):
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
- TUYỆT ĐỐI không dùng repeating-linear-gradient diagonal/angled stripes cho background của .scene, #root, body — chỉ dùng cho decorative nhỏ (border, badge)."""


def build_system_prompt_full(theme: dict) -> str:
    """Rich prompt - for paid providers (Pinkyne, Anthropic) where token cost
    is fine. Asks for more elaborate decoration, motion, and creative
    visuals while still leveraging the server-injected CSS framework."""
    return f"""Bạn là chuyên gia thiết kế giao diện AWWWARDS & UI/UX PRO MAX — sinh ra HTML cinematic, lung linh, gây ấn tượng WOW tuyệt đối. Sinh `index.html` HOÀN CHỈNH cho theme **{theme['name']}**.

⚠️ TỐI ƯU HÓA TOKEN ĐỂ TRÁNH BỊ CẮT CỤT (TRUNCATED):
- Để tránh bị giới hạn 4096-token cắt cụt HTML giữa chừng (khiến hệ thống phải chèn placeholder basic cho các scene cuối 6, 7, 8):
  - Hãy viết mã HTML cực kỳ gọn gàng, súc tích.
  - KHÔNG viết custom CSS dài dòng hay lặp lại trong thẻ <style>. TẬN DỤNG 100% các class CSS tiện ích cực mạnh có sẵn trong framework (như .feat-grid, .terminal, .stat-list, .compare, .tl-list...).
  - Chỉ viết tối đa 30 dòng CSS override trong <style> cho các hiệu ứng/keyframes thực sự đặc biệt.
  - Tránh viết comment code dài dòng hay giải thích bằng văn bản ở đầu/cuối response.

⚠️ NGÔN NGỮ: TIẾNG VIỆT có dấu đầy đủ. Giữ NGUYÊN VĂN narration/title/visualDescription. Tiếng Anh chỉ cho class CSS / comment / tên biến.

═══════════════════════════════════════
🎯 BẠN CHỈ VIẾT: HTML structure + <style> override (≤30 dòng cho scene-specific). KHÔNG VIẾT <script> GSAP timeline.
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
- ⚠️ QUY TẮC TUYỆT ĐỐI CHỐNG THIẾU ẢNH (BẮT BUỘC):
  - TUYỆT ĐỐI KHÔNG DÙNG THẺ <img> HOẶC CLASS .img-frame NẾU TRONG PROMPT NGƯỜI DÙNG KHÔNG CÓ DÒNG `IllustrationImage: assets/...`.
  - Nếu không có dòng `IllustrationImage: assets/...`, cấm tuyệt đối việc tự tạo đường dẫn ảnh giả. Bắt buộc dùng mock visual phong phú hoàn toàn bằng HTML/CSS (B1-B8, B11-B15) để lấp đầy .visual-col. Việc để xuất hiện khung đen trống hoặc icon ảnh lỗi là cấm kỵ.
- Chúng ta sử dụng framework có sẵn các class động cực kỳ lung linh:
  - `.breath`: Tạo chuyển động bay bổng, nhịp thở êm ái. Hãy áp dụng cho các card như `.visual-block`, `.terminal`, `.feat-card`, `.compare`, `.quote-block` hoặc các ảnh `.img-frame`.
  - `.glow-card`: Viền neon lung linh tỏa sáng rực rỡ, kèm hiệu ứng 3D co giãn phóng to khi rê chuột cực kỳ mượt mà.
  - `.shimmer-fast`: Tạo hiệu ứng vệt sáng quét ngang thời thượng trên card (rất hợp với `.stat-list-card`).
  - `.y2k-sparkle`: Chèn ngôi sao lấp lánh vector retro. Ví dụ chèn vào trong visual block: `<span class="y2k-sparkle" style="top: 15%; left: 10%;"></span>`. Lưu ý: Container chứa ngôi sao sparkle phải có `position: relative`!
  - `.terminal .cursor`: Dùng class `cursor` nhấp nháy cho terminal: `<div>$ <span class="cursor"></span></div>`.
- 🛡️ CHỐNG ĐÈ CHỮ / MẤT NÉT GLOW:
  - Do có hiệu ứng viền phát sáng (box-shadow neon) rực rỡ, chúng ta đã set `overflow: visible` cho `.visual-block` và `.stat-list-card`. Tuyệt đối KHÔNG override lại thành `overflow: hidden` trên các card này, để ánh sáng viền không bị cắt cụt.
  - Hãy căn chỉnh khoảng cách, padding hợp lý để các card không nằm quá sát lề màn hình hoặc đè lên nhau.
  - Với các con số thống kê hoặc chữ dài, tuyệt đối không lạm dụng các size chữ quá khổng lồ hoặc nhồi nhét quá nhiều chữ trong các khối hẹp để tránh chữ bị đè chèn lấp nhau.

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

4. LAYOUT FREEDOM (chọn layout phù hợp content, KHÔNG ép split mặc định):
   - .scene.split    → 2 cột info|visual (dùng khi có ảnh thật assets/sceneN.jpg)
   - .scene.centered → 1 cột center text + mega-num/stat-banner ở giữa
   - .scene.hero     → title cực to căn trái, decoratives full-bleed
   - .scene.magazine → 7:5 asymmetric (text trái, visual phải kéo dài)
   - .scene.data     → info nhỏ + visual lớn (cho data viz/bento)
   - Bạn ĐƯỢC PHÉP tự do chọn layout. Mỗi scene KHÁC NHAU. KHÔNG lặp .split 8 lần liên tiếp.

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

B) NẾU KHÔNG có ảnh — CHỌN 1 PATTERN, ĐA DẠNG GIỮA CÁC SCENE, KHÔNG ĐƯỢC ĐỂ TRỐNG:

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

   KHÔNG ĐƯỢC để visual-col trống.

═══════════════════════════════════════
TYPOGRAPHY & GLOWS (DÙNG sẵn):
═══════════════════════════════════════
- .badge, .title-xl, .title-hero, .stat-hero, .grad-text, .glow-border, .glow-text

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
- TUYỆT ĐỐI không override class .scanlines bằng màu sắc rực rỡ có opacity lớn (như var(--accent) 1px, transparent 2px), vì sẽ gây nhòe màn hình, rung giật và Moiré effect. Hãy sử dụng .scanlines mặc định vô cùng tinh tế của hệ thống.
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

═══════════════════════════════════════
✨ HIỆU ỨNG ĐỘNG & BIỆN PHÁP CHỐNG ĐÈ CHỮ / CLIPPING (QUAN TRỌNG):
═══════════════════════════════════════
- ⚠️ QUY TẮC TUYỆT ĐỐI CHỐNG THIẾU ẢNH (BẮT BUỘC):
  - TUYỆT ĐỐI KHÔNG DÙNG THẺ <img> HOẶC CLASS .img-frame NẾU TRONG PROMPT NGƯỜI DÙNG KHÔNG CÓ DÒNG `IllustrationImage: assets/...`.
  - Nếu không có dòng `IllustrationImage: assets/...`, cấm tuyệt đối việc tự tạo đường dẫn ảnh giả. Bắt buộc dùng mock visual phong phú hoàn toàn bằng HTML/CSS (B1-B8, B11-B15) để lấp đầy .visual-col. Việc để xuất hiện khung đen trống hoặc icon ảnh lỗi là cấm kỵ.
- Chúng ta sử dụng framework có sẵn các class động cực kỳ lung linh:
  - `.breath`: Tạo chuyển động bay bổng, nhịp thở êm ái. Hãy áp dụng cho các card như `.visual-block`, `.terminal`, `.feat-card`, `.compare`, `.quote-block` hoặc các ảnh `.img-frame`.
  - `.glow-card`: Viền neon lung linh tỏa sáng rực rỡ, kèm hiệu ứng 3D co giãn phóng to khi rê chuột cực kỳ mượt mà.
  - `.shimmer-fast`: Tạo hiệu ứng vệt sáng quét ngang thời thượng trên card (rất hợp với `.stat-list-card`).
  - `.y2k-sparkle`: Chèn ngôi sao lấp lánh vector retro. Ví dụ chèn vào trong visual block: `<span class="y2k-sparkle" style="top: 15%; left: 10%;"></span>`. Lưu ý: Container chứa ngôi sao sparkle phải có `position: relative`!
  - `.terminal .cursor`: Dùng class `cursor` nhấp nháy cho terminal: `<div>$ <span class="cursor"></span></div>`.
- 🛡️ CHỐNG ĐÈ CHỮ / MẤT NÉT GLOW:
  - Do có hiệu ứng viền phát sáng (box-shadow neon) rực rỡ, chúng ta đã set `overflow: visible` cho `.visual-block` và `.stat-list-card`. Tuyệt đối KHÔNG override lại thành `overflow: hidden` trên các card này, để ánh sáng viền không bị cắt cụt.
  - Hãy căn chỉnh khoảng cách, padding hợp lý để các card không nằm quá sát lề màn hình hoặc đè lên nhau.
  - Với các con số thống kê hoặc chữ dài, tuyệt đối không lạm dụng các size chữ quá khổng lồ hoặc nhồi nhét quá nhiều chữ trong các khối hẹp để tránh chữ bị đè chèn lấp nhau.

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
- TUYỆT ĐỐI không override class .scanlines bằng màu sắc rực rỡ có opacity lớn (như var(--accent) 1px, transparent 2px), vì sẽ gây nhòe màn hình, rung giật và Moiré effect. Hãy sử dụng .scanlines mặc định vô cùng tinh tế của hệ thống.
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
                "\n  ⚠️ Title PHẢI dùng .title-hero.grad-text hoặc .mega-num cực to."
                "\n  ⚠️ Có 2-3 .badge dạng tech tags (Edge AI · Privacy First · Real-time...) thay vì viết text dài."
                "\n  ⚠️ Mục tiêu: 3 giây đầu cinematic AWWWARDS quality — KHÔNG mockup nháp."
            )
        elif not is_first and not s.imageAsset:
            lines.append(
                "  🌌 SCENE NÀY (không ảnh) — BẮT BUỘC LẤP ĐẦY KHÔNG GIAN:"
                "\n  ⚠️ Background PHẢI có 2-4 ambient decoratives (.float-orb-md/.aurora-glow/.animated-grid/.ghost-text/.particle-field/.y2k-sparkle)."
                "\n  ⚠️ Visual-col dùng pattern phong phú (B1-B15) phù hợp với nội dung scene."
                "\n  ⚠️ Đa dạng layout — không lặp .split. Cân nhắc .centered/.hero/.magazine/.data tùy nội dung."
            )

        if s.imageAsset:
            lines.append(
                f"  IllustrationImage: {s.imageAsset}"
                f"\n  ⚠️ Ảnh PHẢI nằm trong <div class=\"img-frame\"><img src=\"{s.imageAsset}\" alt=\"\"><span class=\"img-caption\">caption tiếng Việt</span></div>."
                f"\n  ✅ TỰ DO chọn layout: .scene.split / .magazine / .data / .hero / .centered / bento — đa dạng giữa các scene."
                f"\n  ✅ Có thể đảo: ảnh BÊN TRÁI thay vì phải; ảnh dưới title; ảnh trong bento-cell."
                f"\n  ✗ KHÔNG: full-bleed background, position:absolute cho img, text overlay trực tiếp lên ảnh."
                f"\n  ✗ KHÔNG: lặp lại cùng 1 layout với scene ảnh khác — mỗi scene KHÁC NHAU."
            )
        elif not is_first:
            lines.append(
                f"  ⚠️ CẢNH BÁO: SCENE NÀY TUYỆT ĐỐI KHÔNG CÓ ẢNH MINH HỌA."
                f"\n  ⚠️ TUYỆT ĐỐI KHÔNG DÙNG THẺ <img> HOẶC CLASS .img-frame HOẶC BẤT KỲ ĐƯỜNG DẪN ẢNH NÀO."
                f"\n  ⚠️ BẮT BUỘC DÙNG MOCK VISUAL HTML/CSS (B1-B8, B11-B15) ĐỂ ĐIỀN VÀO .visual-col."
            )

        if is_last:
            lines.append(
                "  📐 SCENE CUỐI — CHỐNG OVERFLOW BẮT BUỘC:"
                "\n  ⚠️ Toàn bộ content visual-col PHẢI vừa trong khung 1920×1080 (chiều cao usable ~880px sau padding)."
                "\n  ⚠️ Nếu có danh sách bullet/feature > 4 mục → CẮT XUỐNG tối đa 4 mục."
                "\n  ⚠️ Padding visual-block ≤ 48px. Title trong card ≤ 2rem. Bullet ≤ 1.2rem."
                "\n  ⚠️ KHÔNG được để box content bị cắt mất ở mép dưới scene."
            )
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
                    "max_tokens": 16000,
                    "stream": True,
                }
            return {
                "messages": [
                    {"role": "system", "content": sys_full},
                    {"role": "user", "content": prompt_full},
                ],
                "temperature": 0.7,
                "max_tokens": 16000,
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
