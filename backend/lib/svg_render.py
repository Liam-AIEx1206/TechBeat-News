# -*- coding: utf-8 -*-
"""Render an SVG string to a PNG (bytes) via headless Chromium.

Used by the slide visual-review loop (routers/slides.py): after the LLM emits
an SVG we render it exactly as a browser would, hand the PNG back to a vision
model, and let it see + fix overflow / clipping / element collisions — the
same render→review→fix loop PPT Master's visual_review.py drives.

Chromium (with proper Vietnamese/CJK font shaping) beats cairosvg here, which
is why we render through Playwright rather than a pure-Python rasterizer.
"""
from __future__ import annotations

import asyncio
import os
from pathlib import Path

_CANVAS_W = 1280
_CANVAS_H = 720

# Serialize browser access; one shared browser is cheaper than launch-per-call.
_launch_lock = asyncio.Lock()
_browser = None  # type: ignore[var-annotated]
_playwright = None  # type: ignore[var-annotated]


def _chromium_executable() -> str | None:
    """Honor the pre-provisioned Chromium if the env pins one."""
    for env in ("PLAYWRIGHT_CHROMIUM_EXECUTABLE", "CHROMIUM_PATH"):
        v = os.getenv(env)
        if v and Path(v).exists():
            return v
    base = os.getenv("PLAYWRIGHT_BROWSERS_PATH")
    if base:
        for cand in Path(base).glob("chromium*/chrome-linux/chrome"):
            return str(cand)
    return None


async def _get_browser():
    global _browser, _playwright
    if _browser is not None and _browser.is_connected():
        return _browser
    async with _launch_lock:
        if _browser is not None and _browser.is_connected():
            return _browser
        from playwright.async_api import async_playwright
        _playwright = await async_playwright().start()
        launch_kwargs = {
            "headless": True,
            "args": ["--no-sandbox", "--disable-setuid-sandbox", "--disable-gpu"],
        }
        exe = _chromium_executable()
        if exe:
            launch_kwargs["executable_path"] = exe
        _browser = await _playwright.chromium.launch(**launch_kwargs)
        return _browser


def _wrap_html(svg: str) -> str:
    """Wrap the SVG so it fills a 1280×720 viewport with no margins."""
    return (
        "<!doctype html><html><head><meta charset='utf-8'>"
        "<style>*{margin:0;padding:0}html,body{width:1280px;height:720px;"
        "overflow:hidden;background:#000}svg{display:block;width:1280px;height:720px}"
        "</style></head><body>" + svg + "</body></html>"
    )


async def render_svg_to_png(svg: str, *, timeout_ms: int = 8000) -> bytes | None:
    """Render an SVG string to PNG bytes at 1280×720. Returns None on failure."""
    if not svg or "<svg" not in svg:
        return None
    try:
        browser = await _get_browser()
        page = await browser.new_page(
            viewport={"width": _CANVAS_W, "height": _CANVAS_H},
            device_scale_factor=1,
        )
        try:
            await page.set_content(_wrap_html(svg), wait_until="load", timeout=timeout_ms)
            # Give webfont/layout a beat to settle.
            await page.wait_for_timeout(150)
            return await page.screenshot(
                type="png",
                clip={"x": 0, "y": 0, "width": _CANVAS_W, "height": _CANVAS_H},
            )
        finally:
            await page.close()
    except Exception as e:  # pragma: no cover — render is best-effort
        print(f"[svg_render] render failed: {e}")
        return None


async def shutdown() -> None:
    """Release the shared browser (call on app shutdown)."""
    global _browser, _playwright
    try:
        if _browser is not None:
            await _browser.close()
    finally:
        _browser = None
    try:
        if _playwright is not None:
            await _playwright.stop()
    finally:
        _playwright = None
