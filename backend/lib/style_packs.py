# -*- coding: utf-8 -*-
"""Style-pack loader — nạp "style" theo format oh-my-ppt (arcsin1/oh-my-ppt,
Apache-2.0) để user CHỌN PHONG CÁCH thay vì chỉ chọn màu.

Mỗi style là một thư mục thả vào  backend/templates/styles/<style-id>/  gồm
đúng 3 file như oh-my-ppt sinh ra:

    style.json     — metadata (label, labelEn, description, category, aliases…)
    SKILL.md       — bản đặc tả thiết kế cho LLM đọc (màu, typography, hoạ tiết,
                     layout patterns, hạn chế). ĐÂY là linh hồn của style.
    preview.html   — trang demo 16:9 inline-CSS (dùng làm thumbnail chọn style)

Loader ĐỌC KHOAN DUNG (không phụ thuộc field nội bộ chính xác của style.json):
- metadata lấy best-effort từ style.json (thiếu thì suy từ tên thư mục / SKILL.md)
- SKILL.md đọc nguyên văn → chèn vào prompt sinh slide làm design-spec
- palette: best-effort trích mã hex trong SKILL.md/style.json để map sang token
  __ACCENT__… cho reference SVG. Thiếu thì dùng palette dark trung tính; LLM vẫn
  bám màu theo prose trong SKILL.md (nguồn màu chính xác nhất).
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

_STYLES_DIR = Path(__file__).resolve().parent.parent / "templates" / "styles"

_RE_HEX = re.compile(r'#([0-9a-fA-F]{6})\b')

# Palette trung tính khi style không lộ đủ màu — LLM vẫn dùng màu từ SKILL.md.
_NEUTRAL_PALETTE = {
    "bg": "#0b0b12", "bg2": "#14141f", "surface": "#1b1b28",
    "accent": "#6366f1", "accent2": "#818cf8", "accent3": "#a5b4fc",
    "text1": "#f5f5fa", "text2": "#a1a1b3",
}
_PALETTE_KEYS = ("bg", "bg2", "surface", "accent", "accent2", "accent3", "text1", "text2")


@dataclass
class Style:
    id: str
    label: str
    label_en: str = ""
    description: str = ""
    category: str = ""
    aliases: list[str] = field(default_factory=list)
    skill_md: str = ""
    palette: dict = field(default_factory=lambda: dict(_NEUTRAL_PALETTE))
    has_preview: bool = False

    def public(self) -> dict:
        """Payload gọn cho frontend (không kèm SKILL.md dài / preview HTML)."""
        return {
            "id": self.id,
            "label": self.label,
            "labelEn": self.label_en,
            "description": self.description,
            "category": self.category,
            "palette": self.palette,
            "hasPreview": self.has_preview,
        }


def _luminance(hex6: str) -> float:
    r, g, b = int(hex6[0:2], 16), int(hex6[2:4], 16), int(hex6[4:6], 16)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _saturation(hex6: str) -> float:
    r, g, b = (int(hex6[i:i+2], 16) / 255 for i in (0, 2, 4))
    mx, mn = max(r, g, b), min(r, g, b)
    return 0.0 if mx == 0 else (mx - mn) / mx


def _derive_palette(hexes: list[str], declared: dict | None) -> dict:
    """Ưu tiên palette khai báo tường minh trong style.json; nếu không, suy
    heuristic từ danh sách hex thu được (tối nhất→nền, sáng nhất→chữ, bão hoà
    nhất→accent). Fail-soft về palette trung tính."""
    pal = dict(_NEUTRAL_PALETTE)
    if declared:
        for k in _PALETTE_KEYS:
            v = declared.get(k)
            if isinstance(v, str) and _RE_HEX.fullmatch("#" + v.lstrip("#")):
                pal[k] = "#" + v.lstrip("#").lower()
        return pal
    uniq = []
    for h in hexes:
        h = h.lower()
        if h not in uniq:
            uniq.append(h)
    if len(uniq) < 3:
        return pal
    by_lum = sorted(uniq, key=lambda h: _luminance(h))
    darkest, brightest = by_lum[0], by_lum[-1]
    accent = max(uniq, key=lambda h: _saturation(h) * (0.4 + 0.6 * _luminance(h) / 255))
    pal["bg"] = "#" + darkest
    pal["bg2"] = "#" + by_lum[1] if len(by_lum) > 1 else pal["bg2"]
    pal["surface"] = "#" + by_lum[min(2, len(by_lum) - 1)]
    pal["text1"] = "#" + brightest
    pal["text2"] = "#" + by_lum[max(0, len(by_lum) - 2)]
    pal["accent"] = "#" + accent
    # accent2/3: các hex bão hoà kế tiếp, khác accent
    sats = sorted((h for h in uniq if "#" + h != pal["accent"]),
                  key=lambda h: _saturation(h), reverse=True)
    if sats:
        pal["accent2"] = "#" + sats[0]
    if len(sats) > 1:
        pal["accent3"] = "#" + sats[1]
    return pal


def _load_one(d: Path) -> Style | None:
    if not d.is_dir():
        return None
    meta: dict = {}
    sj = d / "style.json"
    if sj.exists():
        try:
            meta = json.loads(sj.read_text(encoding="utf-8"))
        except Exception:
            meta = {}
    skill = ""
    for name in ("SKILL.md", "skill.md"):
        p = d / name
        if p.exists():
            skill = p.read_text(encoding="utf-8")
            break
    if not skill and not meta:
        return None  # thư mục không phải style pack

    hexes = _RE_HEX.findall(skill) + _RE_HEX.findall(json.dumps(meta))
    declared = meta.get("palette") or meta.get("colors") or meta.get("theme")
    palette = _derive_palette(hexes, declared if isinstance(declared, dict) else None)

    # oh-my-ppt: name = {"zh": "...", "en": "..."}; cũng chấp nhận label dạng chuỗi.
    nm = meta.get("name")
    label_en = ""
    if isinstance(nm, dict):
        label = nm.get("en") or nm.get("zh") or ""
        label_en = str(nm.get("en") or "")
    elif isinstance(nm, str):
        label = nm
    else:
        label = meta.get("label") or ""
    if not label:
        label = d.name.replace("-", " ").replace("_", " ").title()
    if not label_en:
        label_en = str(meta.get("labelEn") or meta.get("label_en") or "")

    return Style(
        id=str(meta.get("style") or d.name),
        label=str(label),
        label_en=label_en,
        description=str(meta.get("description") or meta.get("styleCase") or "")[:400],
        category=str(meta.get("category") or ""),
        aliases=[str(a) for a in (meta.get("aliases") or []) if isinstance(a, str)],
        skill_md=skill,
        palette=palette,
        has_preview=(d / "preview.html").exists(),
    )


# Cache theo mtime thư mục để hot-add style không cần restart.
_cache: dict[str, tuple[float, Style]] = {}


def list_styles() -> list[Style]:
    if not _STYLES_DIR.is_dir():
        return []
    out: list[Style] = []
    for d in sorted(_STYLES_DIR.iterdir()):
        if not d.is_dir():
            continue
        try:
            mtime = max((f.stat().st_mtime for f in d.iterdir()), default=0.0)
        except OSError:
            mtime = 0.0
        cached = _cache.get(d.name)
        if cached and cached[0] == mtime:
            out.append(cached[1])
            continue
        st = _load_one(d)
        if st:
            _cache[d.name] = (mtime, st)
            out.append(st)
    return out


def get_style(style_id: str | None) -> Style | None:
    if not style_id:
        return None
    for s in list_styles():
        if s.id == style_id:
            return s
    return None


def preview_path(style_id: str) -> Path | None:
    p = _STYLES_DIR / style_id / "preview.html"
    return p if p.exists() else None
