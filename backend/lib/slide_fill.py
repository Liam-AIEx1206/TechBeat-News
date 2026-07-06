# -*- coding: utf-8 -*-
"""Deterministic slide fill engine (nhánh A của luồng hybrid).

Nhét nội dung vào một layout SVG có SLOT định sẵn — KHÔNG cần LLM vẽ layout,
nên KHÔNG BAO GIỜ tràn/đè: toạ độ do người thiết kế template cố định, engine
chỉ đổ text/icon/ảnh vào và tự wrap + thu nhỏ font cho vừa ô (shrink-to-fit).

Cú pháp slot trong SVG template (file backend/templates/packs/<id>/fills/*.svg):

  Text (auto-fit):
    <text x="80" y="220" font-size="56" font-weight="bold" fill="__TEXT1__"
          font-family="Arial, Helvetica, sans-serif"
          data-slot="TITLE" data-fit-w="440" data-fit-h="180" data-min="30">{{TITLE}}</text>
    • data-fit-w  (BẮT BUỘC để auto-fit): bề rộng tối đa cho phép (px)
    • data-fit-h  (tuỳ chọn): chiều cao tối đa → vượt thì giảm font
    • data-min    (tuỳ chọn): cỡ font nhỏ nhất được phép (mặc định 0.6×font-size)
    • data-lh     (tuỳ chọn): line-height, mặc định 1.3
    Không có data-fit-w → chỉ thay chữ 1 dòng, không đo.

  Icon:  <use data-icon="{{ICON_1}}" x=".." y=".." width="48" height="48" fill="__ACCENT__"/>
  Image: <image href="{{IMAGE}}" x=".." y=".." width=".." height=".." .../>

  Nhóm lặp / ẩn khi rỗng:
    <g data-slot-group="CARD_2"> ... {{CARD_2_TITLE}} ... </g>
    Nếu MỌI slot bên trong nhóm đều rỗng → cả nhóm bị xoá (căn lại do template
    lo — thường các nhóm cùng cỡ nên xoá 1 nhóm là ổn về thẩm mỹ).

API chính: fill_svg(svg, values) -> svg đã điền.
"""
from __future__ import annotations

import html as _html
import re

# Ước lượng bề rộng glyph trung bình cho font sans ≈ 0.6×font-size mỗi ký tự.
# Hơi rộng rãi để tránh under-estimate (thà wrap sớm còn hơn tràn).
_GLYPH_W = 0.60
_DEFAULT_LH = 1.3

_RE_SLOT = re.compile(r"\{\{([A-Z0-9_]+)\}\}")
_RE_TEXT_SLOT = re.compile(
    r'<text\b([^>]*)>\s*(.*?)\s*</text>', re.IGNORECASE | re.DOTALL
)
_RE_GROUP = re.compile(
    r'<g\b[^>]*\bdata-slot-group="([^"]+)"[^>]*>(.*?)</g>',
    re.IGNORECASE | re.DOTALL,
)


def _xml_escape(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def _attr(attrs: str, name: str) -> str | None:
    m = re.search(rf'{name}="([^"]*)"', attrs)
    return m.group(1) if m else None


def _attr_f(attrs: str, name: str) -> float | None:
    v = _attr(attrs, name)
    if v is None:
        return None
    try:
        return float(v)
    except ValueError:
        return None


def _est_width(text: str, font_size: float) -> float:
    return len(text) * font_size * _GLYPH_W


def _wrap(text: str, font_size: float, fit_w: float) -> list[str]:
    """Greedy word-wrap sao cho mỗi dòng ≤ fit_w ở cỡ font này."""
    words = text.split()
    if not words:
        return []
    lines: list[str] = []
    cur = words[0]
    for w in words[1:]:
        if _est_width(cur + " " + w, font_size) <= fit_w:
            cur += " " + w
        else:
            lines.append(cur)
            cur = w
    lines.append(cur)
    return lines


def _fit_text(value: str, attrs: str) -> tuple[float, list[str]]:
    """Trả (font_size, list dòng) đã wrap + thu nhỏ để vừa fit-w × fit-h."""
    base = _attr_f(attrs, "font-size") or 24.0
    fit_w = _attr_f(attrs, "data-fit-w")
    if not fit_w:
        return base, [value]  # không khai báo fit → 1 dòng, giữ nguyên cỡ
    fit_h = _attr_f(attrs, "data-fit-h")
    min_size = _attr_f(attrs, "data-min") or max(12.0, base * 0.6)
    lh = _attr_f(attrs, "data-lh") or _DEFAULT_LH

    size = base
    while True:
        lines = _wrap(value, size, fit_w)
        # Một từ đơn dài hơn fit_w ở cỡ hiện tại?
        too_wide = any(_est_width(ln, size) > fit_w + 0.5 for ln in lines)
        total_h = len(lines) * size * lh
        over_h = bool(fit_h) and total_h > fit_h + 0.5
        if (too_wide or over_h) and size > min_size:
            size = max(min_size, size - 2)
            continue
        return size, lines


def _rebuild_attrs(attrs: str, new_size: float) -> str:
    """Cập nhật font-size, gỡ các data-* nội bộ khỏi output cuối."""
    a = re.sub(r'\sfont-size="[^"]*"', "", attrs)
    a = re.sub(r'\sdata-(?:slot|fit-w|fit-h|min|lh)="[^"]*"', "", a)
    return f'{a.rstrip()} font-size="{new_size:g}"'


def _fill_text_elements(svg: str, values: dict[str, str]) -> str:
    def _repl(m: re.Match) -> str:
        attrs, inner = m.group(1), m.group(2)
        slot_m = _RE_SLOT.search(inner)
        if not slot_m:
            return m.group(0)  # <text> thường, không phải slot
        slot = slot_m.group(1)
        val = (values.get(slot) or "").strip()
        if not val:
            return ""  # slot rỗng → bỏ dòng chữ (nhóm rỗng đã xử lý riêng)
        size, lines = _fit_text(val, attrs)
        base_x = _attr(attrs, "x") or "0"
        out_attrs = _rebuild_attrs(attrs, size)
        if len(lines) == 1:
            return f"<text{out_attrs}>{_xml_escape(lines[0])}</text>"
        tspans = []
        for i, ln in enumerate(lines):
            dy = "0" if i == 0 else f"{size * (_attr_f(attrs, 'data-lh') or _DEFAULT_LH):g}"
            tspans.append(f'<tspan x="{base_x}" dy="{dy}">{_xml_escape(ln)}</tspan>')
        return f"<text{out_attrs}>{''.join(tspans)}</text>"

    return _RE_TEXT_SLOT.sub(_repl, svg)


def _group_is_empty(group_inner: str, values: dict[str, str]) -> bool:
    slots = _RE_SLOT.findall(group_inner)
    if not slots:
        return False
    return all(not (values.get(s) or "").strip() for s in slots)


def _remove_empty_groups(svg: str, values: dict[str, str]) -> str:
    def _repl(m: re.Match) -> str:
        return "" if _group_is_empty(m.group(2), values) else m.group(0)
    return _RE_GROUP.sub(_repl, svg)


def _fill_icons_images(svg: str, values: dict[str, str]) -> str:
    def _slot_sub(m: re.Match) -> str:
        slot = m.group(1)
        return _xml_escape((values.get(slot) or "").strip())
    # Chỉ thay các {{...}} còn lại trong attribute (icon/image href); text đã xử lý.
    return _RE_SLOT.sub(_slot_sub, svg)


def _drop_placeholder_elements(svg: str) -> str:
    """Sau khi thay slot: <use data-icon=""/> và <image href=""/> rỗng → gỡ bỏ
    để không để lại container/ảnh trống."""
    svg = re.sub(r'<use\b[^>]*\bdata-icon=""[^>]*/?>(?:\s*</use>)?', "", svg, flags=re.IGNORECASE)
    svg = re.sub(r'<image\b[^>]*\b(?:xlink:)?href=""[^>]*/?>(?:\s*</image>)?', "", svg, flags=re.IGNORECASE)
    return svg


def list_slots(svg: str) -> list[str]:
    """Trả về danh sách tên slot có trong template (dùng cho schema mapping)."""
    seen: list[str] = []
    for s in _RE_SLOT.findall(svg):
        if s not in seen:
            seen.append(s)
    return seen


def fill_svg(svg: str, values: dict[str, str]) -> str:
    """Điền values vào SVG template có slot. Thứ tự:
    1) xoá nhóm data-slot-group rỗng
    2) đổ text (auto-fit wrap + shrink)
    3) thay slot icon/image còn lại
    4) gỡ icon/image rỗng
    """
    svg = _remove_empty_groups(svg, values)
    svg = _fill_text_elements(svg, values)
    svg = _fill_icons_images(svg, values)
    svg = _drop_placeholder_elements(svg)
    # Dọn marker nội bộ khỏi các <g> giữ lại (vô hại khi render nhưng để sạch)
    svg = re.sub(r'\sdata-slot-group="[^"]*"', "", svg)
    return svg
