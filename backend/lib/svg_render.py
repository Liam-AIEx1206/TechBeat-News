# -*- coding: utf-8 -*-
"""Render an SVG string to a PNG (bytes) via headless Chromium.

Used by the slide visual-review loop (routers/slides.py): after the LLM emits
an SVG we render it exactly as a browser would, hand the PNG back to a vision
model, and let it see + fix overflow / clipping / element collisions — the
same render→review→fix loop PPT Master's visual_review.py drives.

Architecture note (Windows compatibility): the ASYNC Playwright API spawns the
driver with asyncio.create_subprocess_exec, which raises NotImplementedError
on Windows when the running loop is a SelectorEventLoop — exactly what uvicorn
runs on the main thread there (see ThreadAwareEventLoopPolicy in main.py:
"Selector on main thread, Proactor on workers"). So we do what the video
pipeline does: run the SYNC Playwright API inside one dedicated worker thread
that owns the browser for the process lifetime; async callers submit jobs via
a queue and await a future. Works identically on Linux/Docker.
"""
from __future__ import annotations

import asyncio
import os
import queue
import sys
import threading
from pathlib import Path

_CANVAS_W = 1280
_CANVAS_H = 720

_worker: "_RenderWorker | None" = None
_worker_lock = threading.Lock()


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


def _wrap_html(svg: str) -> str:
    """Wrap the SVG so it fills a 1280×720 viewport with no margins."""
    return (
        "<!doctype html><html><head><meta charset='utf-8'>"
        "<style>*{margin:0;padding:0}html,body{width:1280px;height:720px;"
        "overflow:hidden;background:#000}svg{display:block;width:1280px;height:720px}"
        "</style></head><body>" + svg + "</body></html>"
    )


class _RenderWorker(threading.Thread):
    """Dedicated thread that owns the sync-Playwright browser and serves
    render jobs from a queue. One per process, lazily started."""

    daemon = True

    def __init__(self) -> None:
        super().__init__(name="svg-render-worker")
        self.jobs: "queue.Queue[tuple | None]" = queue.Queue()
        self.ready = threading.Event()
        self.startup_error: Exception | None = None

    def run(self) -> None:  # noqa: C901 — linear worker loop
        if sys.platform == "win32":
            # Thread cần Proactor loop để sync-Playwright spawn được driver
            # (phòng khi event-loop policy của app không tự cấp cho thread).
            try:
                asyncio.set_event_loop(asyncio.ProactorEventLoop())
            except Exception:
                pass
        try:
            from playwright.sync_api import sync_playwright
            launch_kwargs: dict = {
                "headless": True,
                "args": ["--no-sandbox", "--disable-setuid-sandbox", "--disable-gpu"],
            }
            exe = _chromium_executable()
            if exe:
                launch_kwargs["executable_path"] = exe
            with sync_playwright() as p:
                browser = p.chromium.launch(**launch_kwargs)
                self.ready.set()
                while True:
                    job = self.jobs.get()
                    if job is None:
                        break
                    svg, timeout_ms, fut, loop = job
                    png: bytes | None = None
                    try:
                        page = browser.new_page(
                            viewport={"width": _CANVAS_W, "height": _CANVAS_H},
                            device_scale_factor=1,
                        )
                        try:
                            page.set_content(_wrap_html(svg), wait_until="load", timeout=timeout_ms)
                            page.wait_for_timeout(150)  # cho layout/glyph ổn định
                            png = page.screenshot(
                                type="png",
                                clip={"x": 0, "y": 0, "width": _CANVAS_W, "height": _CANVAS_H},
                            )
                        finally:
                            page.close()
                    except Exception as e:
                        print(f"[svg_render] render failed: {e}")
                    _resolve(fut, loop, png)
                browser.close()
        except Exception as e:
            self.startup_error = e
            self.ready.set()
            print(f"[svg_render] ⚠ worker không khởi động được Chromium: {e}\n"
                  f"[svg_render]   → chạy `playwright install chromium` rồi restart backend.")
            # Trả None cho mọi job đang chờ để caller không treo.
            while True:
                try:
                    job = self.jobs.get_nowait()
                except queue.Empty:
                    break
                if job is not None:
                    _, _, fut, loop = job
                    _resolve(fut, loop, None)


def _resolve(fut: asyncio.Future, loop: asyncio.AbstractEventLoop, value) -> None:
    def _set() -> None:
        if not fut.done():
            fut.set_result(value)
    try:
        loop.call_soon_threadsafe(_set)
    except RuntimeError:
        pass  # caller's loop already closed


def _get_worker() -> "_RenderWorker":
    global _worker
    with _worker_lock:
        # Tombstone: worker chết vì lỗi khởi động (thiếu Chromium…) thì KHÔNG
        # tự spawn lại liên tục — env hỏng cần con người sửa + restart.
        if _worker is None or (not _worker.is_alive() and _worker.startup_error is None and not _worker.ready.is_set()):
            _worker = _RenderWorker()
            _worker.start()
        elif not _worker.is_alive() and _worker.startup_error is None and _worker.ready.is_set():
            # Worker từng chạy OK nhưng browser/thread chết giữa chừng → thử lại 1 lần mới.
            _worker = _RenderWorker()
            _worker.start()
        return _worker


async def render_svg_to_png(svg: str, *, timeout_ms: int = 8000) -> bytes | None:
    """Render an SVG string to PNG bytes at 1280×720. Returns None on failure."""
    if not svg or "<svg" not in svg:
        return None
    worker = _get_worker()
    loop = asyncio.get_running_loop()
    # Chờ browser sẵn sàng mà không block event loop
    await loop.run_in_executor(None, worker.ready.wait, 45)
    if worker.startup_error is not None or not worker.ready.is_set():
        return None
    fut: asyncio.Future = loop.create_future()
    worker.jobs.put((svg, timeout_ms, fut, loop))
    try:
        return await asyncio.wait_for(fut, timeout=timeout_ms / 1000 + 25)
    except asyncio.TimeoutError:
        print("[svg_render] render timeout — bỏ qua pass này")
        return None


async def shutdown() -> None:
    """Release the render worker + browser (call on app shutdown)."""
    global _worker
    with _worker_lock:
        w, _worker = _worker, None
    if w is not None and w.is_alive():
        w.jobs.put(None)
        await asyncio.get_running_loop().run_in_executor(None, w.join, 10)
