# -*- coding: utf-8 -*-
"""
Slide export pipeline: ScenePlan → LLM gen SVG → visual-review → svg_to_pptx → .pptx

Gen flow per slide (gen-slide-one):
  1. LLM sinh SVG theo layout archetype + design system (ported from PPT Master)
  2. Inject ảnh thật của scene, embed <use data-icon> thành vector
  3. VISUAL-REVIEW LOOP (à la PPT Master's visual_review.py): render SVG→PNG bằng
     Playwright, cho vision model NHÌN và tự sửa tràn chữ / đè icon / lệch khung —
     lặp tối đa SLIDE_REFINE_PASSES lần. Đây là mắt xích single-shot không thay được:
     model không đo được chiều rộng chữ nếu không thấy kết quả render.

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

# Cache loaded lib modules so module-level state (e.g. svg_render's shared
# browser) persists across requests instead of re-importing — and re-launching
# a Chromium — on every call.
_LIB_CACHE: dict = {}

def _load_lib(name: str):
    """Load a module from backend/lib/ by name, bypassing sys.path IDE issues."""
    cached = _LIB_CACHE.get(name)
    if cached is not None:
        return cached
    spec = _ilu.spec_from_file_location(
        name,
        Path(__file__).resolve().parent.parent / "lib" / f"{name}.py",
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot find lib/{name}.py")
    mod = _ilu.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    _LIB_CACHE[name] = mod
    # Also register under a stable name so other modules (e.g. app shutdown)
    # can reach the SAME instance and its live browser.
    sys.modules.setdefault(f"_slidelib_{name}", mod)
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

# ── SVG slide prompt (design system ported from PPT Master) ──────────────────

_SVG_SYSTEM = """\
You are a world-class presentation designer (think Canva premium templates / consulting decks).
Output ONE complete, publication-quality SVG slide.

═══════════ CANVAS ═══════════
width="1280" height="720" viewBox="0 0 1280 720"  ← EXACT, non-negotiable (Canva 16:9 / PPT 16:9)

═══════════ TECHNICAL RULES (HARD — any violation breaks PPTX export) ═══════════
• All coordinates absolute (x, y, width, height) — NO percentages (gradient stop offsets excepted)
• Colors: HEX only. Transparency = fill-opacity / stroke-opacity (NEVER rgba or fill="rgba(...)")
• Fonts: inline attributes only — NO <style>, NO class, NO @font-face
• Font stack MUST end with: Arial, Helvetica, sans-serif
• FORBIDDEN: <foreignObject>, <mask>, <script>, <animate*>, <textPath>, group opacity <g opacity="...">
  (set opacity on each child element individually, never on a <g>)
• <use> is allowed in EXACTLY ONE form: the icon placeholder <use data-icon="lib/name" .../> (see ICONS)
• NO HTML named entities (&nbsp; &mdash; &copy; ...) — write raw Unicode (— – © → ...).
  XML reserved chars in text MUST be escaped: &amp; &lt; &gt; (e.g. "R&amp;D", "x &lt; 5")
• clip-path allowed ONLY on <image> elements; <clipPath> lives in <defs> with a single shape child
• Every linearGradient / radialGradient / filter MUST be defined inside <defs>
• One logical text line = ONE <text> + multiple <tspan> children (NEVER adjacent <text> for same line)
• Wrap related elements in <g id="..."> groups (3–8 top-level groups per slide)
• NEVER invent external image URLs. The ONLY allowed <image> href value is the literal token
  __SLIDE_IMAGE__ — and only when the brief provides an IMAGE ASSET section
• SVG must be completely self-contained and valid XML

═══════════ ICONS (real vector icons — USE THEM) ═══════════
Icons are embedded as native vectors at export. Placeholder syntax:
  <use data-icon="LIBRARY/NAME" x="100" y="200" width="48" height="48" fill="#HEX"/>
• Size 32–56px. Pair each icon with its label/number on a consistent grid
• Use ONLY icon names from the APPROVED ICON LIST in the brief — never invent names
• Brand/company logos: data-icon="simple-icons/NAME" (approved brand list in brief), fill with brand-appropriate or TEXT1 color
• Icons go inside accent-tinted containers (circle/rounded-square 64–80px, fill ACCENT at fill-opacity 0.12–0.18,
  icon itself in full ACCENT) — this is the signature "premium template" look

═══════════ TYPOGRAPHY RAMP (deck-wide consistency) ═══════════
body = 28px  (base unit)
  footnote/label  : 16–18px
  annotation      : 20–22px
  body text       : 26–28px
  subtitle/lead   : 34–38px
  section title   : 44px
  slide title     : 54–60px
  hero/cover      : 84–110px
  hero KPI number : 72–96px
Structural roles (title / body / subtitle / footnote) keep ONE size deck-wide — same-role drift looks amateur.
line-height: 1.45 for dense blocks, 1.7 for large-type/breathing blocks.
NEVER shrink below 20px for content text. Widen/heighten the container — don't shrink the font.
Lift key numbers/contrasts inline with <tspan fill="ACCENT" font-weight="bold">.

═══════════ DESIGN PRINCIPLES (what separates premium from AI-boring) ═══════════
1. ONE focal point per slide — a hero number, an image, a key phrase. Never a uniform wall of equal boxes.
2. Proportion follows information weight, not preset ratios. Asymmetric splits (3:7, 4:6) read as designed;
   defaulting everything to symmetric grids produces the "AI-generated" look.
3. 60-30-10 color discipline: BG family ~60%, surface/text ~30%, ACCENT ≤10% reserved for what matters.
4. Whitespace is a design element: ≥40px breathing room between unrelated groups.
5. Depth layers: background wash → ghost element → content cards → accent highlights.
   Ghost element = oversized number/word/shape, fill TEXT1 or ACCENT at fill-opacity 0.04–0.08, placed off-grid.
6. Decorative micro-geometry (pick 2–4 max): accent corner brackets, thin rules (1px, 10–15% opacity),
   dot grids (3×3 to 5×5, r=2–3, 15–25% opacity), diagonal accent stripe, small outlined chips/badges.
7. Numbered markers: big index digits ("01" "02" "03") in ACCENT bold, or inside outlined circles.
8. Real content only — every text string comes from the brief. NO lorem ipsum, NO "placeholder".
9. Vietnamese text: keep diacritics intact, break lines at natural word boundaries (2–6 words per visual line
   for titles), never mid-word.

═══════════ SHADOW RECIPE ═══════════
Use ONLY when an element genuinely floats above the background. Max 2 tiers:
  resting  → stdDeviation="8" dy="4" flood-opacity="0.08"
  raised   → stdDeviation="14" dy="8" flood-opacity="0.16"
Flat peer-grid cards get NO shadow. Dark BG: skip shadows (invisible anyway) — use 1px light borders
(stroke TEXT2 at stroke-opacity 0.12–0.2) or slightly lighter surface fills to separate cards instead.

═══════════ SPACING & LAYOUT ═══════════
Safe margins: left/right 80px, top 60px, bottom 50px → content area 1120×610
Card padding: 32–48px inside; card radius: 16–24px
Column gutters: 24px for 2-col, 20px for 3-col, 16px for 4-col
Proximity: tight spacing within a group; clear separation between groups

═══════════ ANTI-OVERFLOW (the #1 cause of ugly slides — obey strictly) ═══════════
You cannot see your output, so budget text conservatively. Rough width: a glyph ≈ 0.55×font-size px.
• A text string must FIT inside its container width. Estimate width = chars × font-size × 0.55.
  If it exceeds the container, DO ONE OF: (a) wrap into multiple <tspan x=".." dy="1.3em"> lines,
  (b) drop one ramp step, (c) widen the container. NEVER let text cross a card/canvas edge.
• Card titles: with 3 cards (~360px each, ~300px usable) keep the title ≤ ~10 chars at 30–34px,
  OR wrap to 2 lines. A long word like "Backtesting"/"Hiệu quả đầu tư" at 44px WILL overflow a
  narrow card — use ≤32px and/or wrap. Reserve 44–60px titles for full-width headers only.
• ICON ↔ TEXT: never place an icon and a text baseline at the same coordinates. Put the icon
  (and its tinted container) ABOVE the label (icon bottom ≥12px above text top) or to its LEFT
  (icon right edge + 12px ≤ text x). An icon overlapping the title is a hard failure.
• Every element's bounding box stays within 0–1280 × 0–720, honoring the safe margins.
• Body lines in a column: wrap so no line exceeds the column width; 2–4 short lines beat 1 wide line.

═══════════ IMAGE PLACEMENT (only when brief has IMAGE ASSET) ═══════════
<image href="__SLIDE_IMAGE__" x=".." y=".." width=".." height=".." preserveAspectRatio="xMidYMid slice"
       clip-path="url(#imgClip)"/>
with <clipPath id="imgClip"><rect x=".." y=".." width=".." height=".." rx="20"/></clipPath> in <defs>.
Full-bleed background variant: cover the whole canvas, then a scrim <rect> (BG fill, fill-opacity 0.55–0.8,
or a vertical gradient scrim) so text stays readable on top.

═══════════ OUTPUT ═══════════
Return ONLY the raw SVG code — start with <svg and end with </svg>.
NO markdown fences, NO explanation, NO comments outside the SVG.
"""

# ── Icon whitelists (files guaranteed to exist in backend/templates/icons/) ──

_ICON_LIBS: dict[str, str] = {
    "chunk-filled": (
        "activity arrow-down arrow-left arrow-right arrow-up bolt book box bug building calendar camera car "
        "chart-bar chart-line chart-pie clock cloud code coin credit-card crown cube database diamond dna eye "
        "file filter flag folder gift git-branch git-merge globe heart home key keyboard layers leaf link map "
        "map-pin moon mouse phone plane play plug power recycle robot rocket server shield shield-check ship "
        "sparkles star sun target terminal trophy truck user users video wallet wifi x"
    ),
    "tabler-filled": (
        "alert-circle alert-triangle award battery bolt book briefcase bug bulb calendar camera car chart-area "
        "chart-dots chart-pie check circle-check clock cloud coin credit-card crown dashboard database "
        "device-mobile diamond download external-link eye file file-text filter flag flask folder function gauge "
        "gift globe graph heart home hourglass info-circle key keyboard leaf link lock mail map-pin message "
        "message-circle microscope mood-happy mood-smile moon mouse phone photo plane player-play pointer "
        "presentation puzzle search send settings shield shield-check sitemap sparkles stack star sun thumb-down "
        "thumb-up trophy truck user video world x zoom"
    ),
    "phosphor-duotone": (
        "arrow-down arrow-left arrow-right arrow-up atom barcode book brain briefcase broadcast bug calendar "
        "camera car chart-bar chart-line chart-pie check clock cloud code coin coins cpu credit-card crown cube "
        "currency-dollar database device-mobile devices diamond dna download eye file file-text fingerprint flag "
        "flask folder function gauge gear gift git-branch git-merge globe graph heart hourglass key keyboard leaf "
        "link lock map-pin medal moon mouse notebook package phone plant play plug power presentation pulse "
        "recycle repeat robot rocket scan share shield shield-check stack star sun target terminal trophy truck "
        "upload user users video wallet x"
    ),
}

_BRAND_ICONS = (
    "amazon amd android anthropic apple binance bitcoin claude discord docker ethereum facebook github gitlab "
    "google huggingface instagram intel ios javascript kubernetes linux mastercard meta microsoft netflix "
    "nextdotjs nodedotjs nvidia openai openjdk paypal python pytorch react samsung slack sony spacex stripe "
    "telegram tensorflow tesla tiktok typescript ubuntu visa x youtube zoom"
)

# One stylistic icon library per deck, matched to theme personality
_THEME_ICON_LIB: dict[str, str] = {
    "cyber-orange": "chunk-filled",
    "matrix-green": "chunk-filled",
    "brutalist-bold": "chunk-filled",
    "bento-minimal": "chunk-filled",
    "iceberg-tech": "chunk-filled",
    "neon-green-overdrive": "chunk-filled",
    "crimson-broadcast": "chunk-filled",
    "space-odyssey": "phosphor-duotone",
    "ocean-depths": "phosphor-duotone",
    "violet-pulse": "phosphor-duotone",
    "neo-cyan": "phosphor-duotone",
    "y2k-magenta": "phosphor-duotone",
    "forest-eco": "tabler-filled",
    "pop-candy": "tabler-filled",
    "aurora-mint": "tabler-filled",
    "sunset-glow": "tabler-filled",
    "gold-editorial": "tabler-filled",
}
_DEFAULT_ICON_LIB = "phosphor-duotone"


# ── Layout archetypes (pattern library from PPT Master §V) ───────────────────

_LAYOUTS: dict[str, str] = {
    "cover_hero": """LAYOUT: COVER / HERO OPENER — the deck's first impression, an impact page
- Pick ONE concrete hook: the core claim as a provocative headline, OR a hero number, OR the image as full-bleed backdrop
- Full-bleed background: gradient wash of BG→BG2 (or __SLIDE_IMAGE__ full-bleed + scrim if IMAGE ASSET given)
- Huge title 84–110px bold TEXT1, broken into 1–3 natural lines, left-aligned at x=80 or centered — NOT cramped
- Kicker label ABOVE title: small caps 18–20px ACCENT letter-spacing 3–6, with a small icon or 40px accent rule
- Subtitle/lead 34–38px TEXT2 below, max 2 lines
- Meta strip near bottom: deck name · date · brand chip (small outlined rounded rect)
- Depth: one ghost element (giant translucent digit/word/geometric ring) + 1–2 decorative accents (corner bracket, dot grid)
- NO bullet lists on the cover. Generous whitespace is the point""",

    "split_asym": """LAYOUT: ASYMMETRIC SPLIT (3:7 or 4:6) — editorial content page
- LEFT narrow column (~380–450px): kicker + slide title 54–60px bold (2–3 lines), short lead 26–28px TEXT2,
  vertical accent bar 4–6px full column height at x=80, slide number ghost digit bottom-left
- RIGHT wide zone: the substance — 2–4 content blocks, each = icon in tinted container + bold label 30–32px + 1–2 lines 26px TEXT2
  OR (if IMAGE ASSET given) a large rounded image panel (rx=20, slice) with a caption chip overlapping its bottom edge
- Blocks separated by whitespace or 1px rules (12% opacity), NOT four identical boxes — vary block heights with content
- Footer: thin rule + deck title 16px TEXT2 left, page number right""",

    "card_grid": """LAYOUT: FEATURE CARD GRID — parallel points with icons
- Header zone: slide title 54px bold TEXT1 left at x=80 + short subtitle 26px TEXT2; accent rule 4px under title (120–200px wide, not full-width)
- Body: 2–3 cards (NOT 4 equal boxes). Make ONE card the lead: wider or accent-bordered or accent-tinted fill
- Each card: rounded rect rx=20 fill BG2, 1px border TEXT2 at 12% opacity; inside → icon (48px, ACCENT, in tinted 72px circle/rounded square),
  card label 30px bold TEXT1, 2–3 lines 24–26px TEXT2, optional small metric 40px ACCENT bold
- Big index digits "01 02 03" in ACCENT at fill-opacity 0.15, 64px, top-right corner of each card
- One ghost element or dot grid in a corner for depth; footer meta strip""",

    "kpi_stats": """LAYOUT: KPI / DATA SPOTLIGHT — numbers are the heroes
- Header: slide title 54px bold + kicker; accent rule
- HERO METRIC ZONE: 1 dominant number 84–96px ACCENT bold (with unit/% in 40px) + one-line takeaway 28px —
  this is the focal point, give it ~40% of the canvas
- Supporting: 2–3 secondary KPIs 48–56px bold TEXT1 with 20px labels, arranged in a row or stacked panel (BG2 card)
- Add ONE simple native chart drawn with rects/circles/paths: horizontal bar comparison (3–5 bars, rounded rx=6,
  lead bar in ACCENT others in TEXT2 at 30% opacity, value labels at bar ends) OR a donut arc (stroke-dasharray on circle)
- Trend arrows: data-icon arrow-up / trending icons next to deltas, green/ACCENT for positive
- Every number inline in text gets <tspan fill="ACCENT" font-weight="bold">""",

    "timeline_process": """LAYOUT: TIMELINE / PROCESS FLOW — sequence with direction
- Header: slide title 54px bold + kicker; accent rule
- Horizontal flow of 3–5 steps across the content area: each step = node circle (64–72px, fill ACCENT at 0.12–0.18
  fill-opacity, 2px ACCENT stroke) containing an icon or step digit, connected by lines or chevron arrows
  (data-icon arrow-right, or path with marker) — the spine sits around y=330–380
- Under each node: step label 28px bold TEXT1 + 1–2 lines 22–24px TEXT2 (alternate above/below the spine if 5 steps for rhythm)
- Highlight the current/final step: full ACCENT node + slightly larger
- Ghost digit of step count in a corner; footer meta strip""",

    "comparison": """LAYOUT: COMPARISON / VERSUS — two sides face off
- Header: slide title 54px bold centered or left + kicker
- Two panels split ~48/48 with a center divider zone: "VS" badge (56–64px circle, ACCENT fill, bold white text) or vertical gradient rule
- Each panel: rounded card rx=24, LEFT panel BG2 fill, RIGHT panel accent-tinted (ACCENT fill-opacity 0.08) or bordered 2px ACCENT —
  visual asymmetry marks the winner/newer side
- Panel header: icon + name 32px bold; then 3–4 rows of icon (check/x 24px) + point 24–26px
- Bottom takeaway strip: one-line verdict 26px with ACCENT tspan highlights""",

    "quote_breathing": """LAYOUT: QUOTE / BREATHING PAGE — one idea lands with weight
- 40–60% of the canvas is intentional whitespace; single-column centered or golden-ratio off-center placement
- Giant decorative quote mark 200–280px ACCENT at fill-opacity 0.12 behind/above the text
- The key statement 44–56px bold TEXT1, broken into 2–4 balanced lines; highlight 1–3 words with ACCENT tspan
- Attribution/context line 24px TEXT2 with a 40px accent rule prefix
- Optional small image chip or brand icon; one subtle decorative element (dot grid or ring) — nothing else
- NO cards, NO bullet lists — restraint IS the design""",

    "ending_cta": """LAYOUT: CLOSING / TAKEAWAY — the final impression, NOT a generic "thank you"
- Full-bleed gradient BG→BG2 (or image + scrim if IMAGE ASSET given)
- The ONE takeaway the audience leaves with: 64–84px bold, 1–3 lines, ACCENT tspan on the key phrase
- Supporting line 28px TEXT2: what to do next / why it matters
- 2–3 compact info chips (outlined rounded rects with small icons): source, brand, date
- Ghost element + decorative accents echoing the cover (visual bookend)
- Small "cảm ơn đã theo dõi"-style sign-off 20px TEXT2 allowed as a footnote, never as the headline""",
}

# Content-driven layout signals (Vietnamese + English)
_RE_NUMBERS = re.compile(r'\d+(?:[.,]\d+)?\s*(?:%|tỷ|triệu|nghìn|usd|đô|billion|million|[kmb]\b)|\d{4}', re.IGNORECASE)
_RE_SEQUENCE = re.compile(r'bước|giai đoạn|quy trình|lộ trình|timeline|trước tiên|tiếp theo|sau đó|cuối cùng|roadmap|phase|step', re.IGNORECASE)
_RE_VERSUS = re.compile(r'so sánh|so với|đối đầu|versus|\bvs\.?\b|hơn hẳn|thay vì|khác biệt giữa|comparison|trong khi', re.IGNORECASE)
_RE_QUOTE = re.compile(r'[“”"]|khẳng định|tuyên bố|phát biểu|cho biết|nhấn mạnh|chia sẻ rằng', re.IGNORECASE)


def _pick_layout(scene: "ScenePayload", slide_num: int, total_slides: int, used: list[str]) -> str:
    """Choose a layout archetype: position first, then content signals, then variety."""
    if slide_num == 1:
        return "cover_hero"
    if slide_num == total_slides and total_slides > 2:
        return "ending_cta"

    text = f"{scene.title} {scene.narration} {scene.visualDescription}"
    # Versus phải là tín hiệu mạnh (tiêu đề nhắc so sánh, hoặc ≥2 lần trong nội dung)
    # để tránh false-positive kiểu "tăng 15% so với 2025".
    strong_versus = _RE_VERSUS.search(scene.title) or len(_RE_VERSUS.findall(text)) >= 2
    if strong_versus and "comparison" not in used[-2:]:
        return "comparison"
    if len(_RE_SEQUENCE.findall(text)) >= 2 and "timeline_process" not in used[-2:]:
        return "timeline_process"
    if len(_RE_NUMBERS.findall(text)) >= 3 and "kpi_stats" not in used[-2:]:
        return "kpi_stats"
    if _RE_QUOTE.search(text) and "quote_breathing" not in used and slide_num >= 3:
        return "quote_breathing"

    # Rotate the editorial workhorses, avoiding immediate repeats
    for cand in ("split_asym", "card_grid", "kpi_stats", "timeline_process"):
        if cand not in used[-2:]:
            return cand
    return "split_asym"


def _icon_block(theme_id: str | None) -> str:
    lib = _THEME_ICON_LIB.get(theme_id or "", _DEFAULT_ICON_LIB)
    return f"""=== APPROVED ICON LIST (use 2–6 icons per slide; ONLY these names) ===
Stylistic library for this deck: "{lib}" → <use data-icon="{lib}/NAME" .../>
Available NAMEs:
{_ICON_LIBS[lib]}

Brand logos (only when a company/product is explicitly mentioned): <use data-icon="simple-icons/NAME" .../>
Available brands:
{_BRAND_ICONS}"""


def _build_svg_prompt(
    scene: "ScenePayload",
    theme_id: str | None,
    slide_num: int,
    total_slides: int,
    layout_key: str | None = None,
    outline: list[str] | None = None,
) -> str:
    t = get_theme(theme_id)
    layout = _LAYOUTS.get(layout_key or "", "") or _LAYOUTS["split_asym"]

    # Parse narration into concise bullet points
    sentences = [s.strip() for s in re.split(r'[.。!?！？\n]', scene.narration) if len(s.strip()) > 10]
    bullets = "\n".join(f"  • {s}" for s in sentences[:5])

    outline_block = ""
    if outline:
        marked = [
            f"  {i+1}. {ti}" + ("   ← THIS SLIDE" if i == slide_num - 1 else "")
            for i, ti in enumerate(outline)
        ]
        outline_block = "\n=== DECK OUTLINE (for narrative coherence) ===\n" + "\n".join(marked) + "\n"

    image_block = ""
    if scene.imageUrl and scene.imageUrl.startswith(("http://", "https://", "data:image/")):
        image_block = """
=== IMAGE ASSET (real photo/illustration available for this slide) ===
Include EXACTLY ONE <image href="__SLIDE_IMAGE__" ...> element (keep the token literally — it is substituted later).
Give it real visual weight per the layout: full-bleed backdrop with scrim (cover/closing), a large rounded
panel ~40–55% of the canvas (split layouts), or a wide banner card. Always preserveAspectRatio="xMidYMid slice"
+ rounded clipPath (unless full-bleed).
"""

    return f"""=== SLIDE {slide_num} of {total_slides} ===

TITLE: {scene.title}

CONTENT BULLETS:
{bullets}

VISUAL DESCRIPTION: {scene.visualDescription}
{outline_block}
=== COLOR PALETTE (USE ONLY THESE HEX VALUES) ===
BG (background):        {t['bg']}
BG2 (card/surface):     {t['bg2']}
ACCENT (primary):       {t['accent']}
ACCENT2 (secondary):    {t['accent2']}
ACCENT3 (tertiary):     {t['accent3']}
TEXT1 (heading):        {t['text1']}
TEXT2 (body/muted):     {t['text2']}
STYLE VIBE:             {t['vibe']}
{image_block}
{_icon_block(theme_id)}

=== REQUIRED LAYOUT FOR THIS SLIDE ===
{layout}

=== SLIDE CONTEXT ===
Slide {slide_num} of {total_slides} — {"Opening slide" if slide_num == 1 else "Closing slide" if slide_num == total_slides else "Content slide"}

Now generate the complete SVG (1280×720). Return ONLY raw SVG, no explanation."""


# ── /gen-slide-one ────────────────────────────────────────────────────────────

def _layout_for_index(scenes: list["ScenePayload"], idx: int) -> str:
    """Deterministic layout pick: replay picks 0..idx so separate per-slide
    requests still produce a coherent, non-repeating deck rhythm."""
    total = len(scenes)
    used: list[str] = []
    for i in range(idx + 1):
        used.append(_pick_layout(scenes[i], i + 1, total, used))
    return used[-1]


_IMAGE_TOKEN = "__SLIDE_IMAGE__"
_RE_IMAGE_EL = re.compile(r'<image\b[^>]*>(?:\s*</image>)?', re.IGNORECASE)


def _inject_scene_image(svg: str, scene: "ScenePayload") -> str:
    """Substitute the __SLIDE_IMAGE__ token with the scene's real image URL.
    Drops <image> elements the LLM emitted without a usable asset (token left
    dangling, or hallucinated external URLs)."""
    url = scene.imageUrl or ""
    has_asset = url.startswith(("http://", "https://", "data:image/"))

    def _clean(m: re.Match) -> str:
        el = m.group(0)
        if _IMAGE_TOKEN in el:
            return el.replace(_IMAGE_TOKEN, url.replace("&", "&amp;")) if has_asset else ""
        href = re.search(r'(?:xlink:)?href="([^"]*)"', el)
        if href and href.group(1).startswith(("http://", "https://")):
            return ""  # hallucinated external URL — remove
        return el

    return _RE_IMAGE_EL.sub(_clean, svg)


def _embed_icons_svg(svg: str) -> str:
    """Embed <use data-icon> placeholders server-side so browser preview and
    PPTX export both render real vectors. Fail-soft: returns input on error."""
    try:
        fin = _load_lib("finalize_svg")
        return fin.embed_icons_in_svg_string(svg)
    except Exception:
        return svg


# ── Visual-review loop (render → vision critique → fix), à la PPT Master ─────

_REFINE_SYSTEM = """\
You are a meticulous presentation-design QA engineer with a pixel-perfect eye.
You are shown a RENDERED PNG (1280×720) of an SVG slide AND its exact SVG source.
Your ONE job: find and FIX every visual defect, then return the corrected SVG.

DEFECTS TO HUNT (in priority order):
1. TEXT OVERFLOW / CLIPPING — any text whose glyphs cross its container edge or the
   canvas edge, or get cut off. This is the #1 defect. Fixes: shrink the font one
   ramp step, wrap the string into multiple <tspan> lines (dy≈1.3×font-size), widen/
   heighten the container, or shorten wording while keeping meaning. A single long
   word that overflows a narrow card → move to a wider layout or reduce its size.
2. ELEMENT COLLISION / OVERLAP — icons sitting ON TOP of text, text over text, an
   icon container overlapping a title. Icons must sit ABOVE or to the LEFT of their
   label with a clear ≥12px gap — NEVER at the same coordinates as text.
3. OFF-CANVAS content — anything positioned partly/fully outside 0–1280 × 0–720.
   Pull it back inside the 80/60/50px safe margins.
4. IMBALANCE — one column crammed while half the canvas is empty; elements not
   aligned to a shared grid; wildly uneven card heights. Rebalance to use the space.
5. ILLEGIBILITY — text color too close to its background; text over a busy image
   region with no scrim.

HARD CONSTRAINTS (keep them — they gate PPTX export):
• Keep viewBox="0 0 1280 720" and width/height exactly.
• Preserve ALL textual content and every <image> href verbatim (you may re-position/
  resize, never delete meaning or swap image URLs). Icons already embedded as paths
  stay as-is; do not reintroduce <use data-icon>.
• HEX colors only; opacity via fill-opacity/stroke-opacity (no rgba). No <style>,
  <foreignObject>, <mask>, <script>, group opacity. Font stacks end in Arial, Helvetica, sans-serif.
• Only rework layout/sizing/wrapping/positioning/color — do NOT redesign from scratch.

OUTPUT PROTOCOL:
• If the slide is already clean (no defect above), reply with EXACTLY: NO_CHANGES_NEEDED
• Otherwise return ONLY the full corrected SVG — start with <svg, end with </svg>.
  No markdown fences, no explanation.
"""


async def _refine_svg_visually(
    svg: str, scene: "ScenePayload", max_passes: int = 1
) -> tuple[str, int]:
    """Render the SVG, let a vision model see + fix layout defects, repeat.

    Returns (possibly-improved svg, passes_applied). Fully fail-soft: any render
    or LLM hiccup returns the best SVG produced so far."""
    import base64 as _b64

    try:
        renderer = _load_lib("svg_render")
    except Exception as e:
        print(f"[slides] svg_render unavailable, skip refine: {e}")
        return svg, 0

    applied = 0
    for _ in range(max(0, max_passes)):
        png = await renderer.render_svg_to_png(svg)
        if not png:
            break
        b64 = _b64.b64encode(png).decode("ascii")
        instruction = (
            "Here is the rendered slide (PNG) and its SVG source. "
            "Fix every visual defect per your rules — especially text overflow, "
            "clipping, and icon/text collisions — then return the corrected SVG "
            "(or NO_CHANGES_NEEDED).\n\n"
            f"SLIDE TITLE (for context): {scene.title}\n\n"
            "=== CURRENT SVG SOURCE ===\n" + svg
        )
        content = [
            {"type": "text", "text": instruction},
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
        ]
        try:
            def _kwargs(_provider: str) -> dict:
                return {
                    "messages": [
                        {"role": "system", "content": _REFINE_SYSTEM},
                        {"role": "user", "content": content},
                    ],
                    "temperature": 0.3,
                    "max_tokens": 8000,
                    "stream": False,
                }
            async with limiter._llm_sem:
                resp, _prov, _model = await chat_completions_with_fallback(
                    model_kind="composition", kwargs_factory=_kwargs
                )
        except Exception as e:
            print(f"[slides] visual-refine LLM call failed: {e}")
            break

        raw = (resp.choices[0].message.content or "").strip()  # type: ignore[union-attr]
        if not raw or "NO_CHANGES_NEEDED" in raw.upper()[:64]:
            break
        fixed = _extract_svg(raw)
        if not fixed or "<svg" not in fixed:
            break
        fixed = _inject_scene_image(fixed, scene)
        fixed = _embed_icons_svg(fixed)
        svg = fixed
        applied += 1

    return svg, applied


class GenSlideOneRequest(BaseModel):
    title: str
    scenes: list[ScenePayload]
    totalDuration: float
    theme: str | None = None
    sceneIndex: int          # 0-based
    sessionId: str | None = None
    refinePasses: int | None = None  # None → env SLIDE_REFINE_PASSES (default 1)


def _refine_passes(req_value: int | None) -> int:
    if req_value is not None:
        return max(0, min(3, req_value))
    import os
    try:
        return max(0, min(3, int(os.getenv("SLIDE_REFINE_PASSES", "1"))))
    except ValueError:
        return 1


@router.post("/gen-slide-one")
async def gen_slide_one(body: GenSlideOneRequest):
    """Gen SVG cho 1 slide. Trả JSON {svg, sceneIndex, provider, model}."""
    if body.sceneIndex < 0 or body.sceneIndex >= len(body.scenes):
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="sceneIndex out of range")

    scene = body.scenes[body.sceneIndex]
    total = len(body.scenes)
    layout_key = _layout_for_index(body.scenes, body.sceneIndex)
    outline = [s.title for s in body.scenes]
    prompt = _build_svg_prompt(
        scene, body.theme, body.sceneIndex + 1, total,
        layout_key=layout_key, outline=outline,
    )

    async with limiter._llm_sem:
        def _kwargs(_provider: str) -> dict:
            return {
                "messages": [
                    {"role": "system", "content": _SVG_SYSTEM},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.65,
                "max_tokens": 8000,
                "stream": False,
            }
        resp, provider, model = await chat_completions_with_fallback(
            model_kind="composition", kwargs_factory=_kwargs
        )

    raw: str = (resp.choices[0].message.content or "")  # type: ignore[union-attr]
    svg = _extract_svg(raw)
    svg = _inject_scene_image(svg, scene)
    svg = _embed_icons_svg(svg)

    # Visual-review loop: render → vision model sees + fixes overflow/collision → repeat.
    # This is the mechanism (à la PPT Master's visual_review) that a single LLM pass
    # cannot replace — the model literally cannot measure text width without seeing it.
    refined = 0
    passes = _refine_passes(body.refinePasses)
    if passes > 0:
        svg, refined = await _refine_svg_visually(svg, scene, max_passes=passes)

    return {
        "svg": svg, "sceneIndex": body.sceneIndex, "layout": layout_key,
        "refinePasses": refined, "provider": provider, "model": model,
    }


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

_RE_REMOTE_HREF = re.compile(r'((?:xlink:)?href=")(https?://[^"]+)(")')


async def _localize_remote_images(svg_paths: list[Path], assets_dir: Path) -> int:
    """Download remote <image> hrefs to assets_dir and rewrite them as relative
    paths, so svg_finalize.align_embed_images can Base64-inline them (PPTX
    cannot follow remote URLs). Returns number of images downloaded."""
    import html as _html
    import httpx

    downloaded: dict[str, str] = {}  # url -> relative href
    count = 0
    async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as http:
        for svg_path in svg_paths:
            content = svg_path.read_text(encoding="utf-8")
            urls = {_html.unescape(m.group(2)) for m in _RE_REMOTE_HREF.finditer(content)}
            if not urls:
                continue
            for url in urls:
                if url in downloaded:
                    continue
                ext = ".jpg"
                low = url.lower().split("?")[0]
                for cand in (".png", ".webp", ".jpeg", ".jpg", ".gif"):
                    if low.endswith(cand):
                        ext = ".jpg" if cand == ".jpeg" else cand
                        break
                try:
                    resp = await http.get(url, headers={
                        "User-Agent": "Mozilla/5.0",
                        "Referer": "https://duckduckgo.com/",
                    })
                    if resp.status_code == 200 and resp.content:
                        assets_dir.mkdir(parents=True, exist_ok=True)
                        local = assets_dir / f"img_{len(downloaded)+1:02d}{ext}"
                        local.write_bytes(resp.content)
                        downloaded[url] = f"../assets/{local.name}"
                        count += 1
                except Exception as e:
                    print(f"[slides] Tải ảnh lỗi ({url[:80]}): {e}")

            def _rewrite(m: re.Match) -> str:
                raw_url = _html.unescape(m.group(2))
                rel = downloaded.get(raw_url)
                return f"{m.group(1)}{rel}{m.group(3)}" if rel else m.group(0)

            new_content = _RE_REMOTE_HREF.sub(_rewrite, content)
            if new_content != content:
                svg_path.write_text(new_content, encoding="utf-8")
    return count


class BuildSlidesRequest(BaseModel):
    title: str
    scenes: list[ScenePayload]
    svgs: list[str]          # SVG string mỗi slide (index khớp với scenes)
    theme: str | None = None
    sessionId: str | None = None
    slideFormat: str = "ppt169"  # canvas format cho pptx_builder (PPT 16:9 = 1280×720)


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

    # 2a. Localize remote images (http/https) → slides/assets/ so the
    #     align-embed pass can Base64-inline them for PPTX.
    yield sse({"type": "status", "message": "Đang tải ảnh slide về local..."})
    try:
        localized = await _localize_remote_images(svg_paths, slides_dir / "assets")
        if localized:
            yield sse({"type": "status", "message": f"Đã tải {localized} ảnh."})
    except Exception as e:
        yield sse({"type": "warning", "message": f"Tải ảnh bỏ qua: {e}"})

    yield sse({"type": "status", "message": "Đang xử lý SVG (embed icons + ảnh)..."})

    # 2b. Finalize SVG: embed <use data-icon> icons + align/Base64-embed <image>
    try:
        fin = _load_lib("finalize_svg")
        for svg_path in svg_paths:
            fin.finalize_svg_file(svg_path)
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

        # pptx_builder tra notes theo SVG filename STEM (không có .svg)
        slide_notes = {
            f"slide_{i+1:02d}": req.scenes[i].narration
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
