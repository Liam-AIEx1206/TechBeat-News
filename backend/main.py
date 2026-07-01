import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

from dotenv import load_dotenv
load_dotenv()

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from routers.extract import router as extract_router
from routers.scenes import router as scenes_router
from routers.compositions import router as compositions_router
from routers.build import router as build_router
from routers.images import router as images_router
from routers.projects import router as projects_router
from routers.history import router as history_router
from routers.voices import router as voices_router
from routers.slides import router as slides_router
from routers.llm import log_provider_status

app = FastAPI(title="TechBeat API", version="2.0.0")

# Log active LLM providers immediately so you can see what's configured
log_provider_status()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
        os.getenv("FRONTEND_URL", ""),
    ],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

app.include_router(extract_router)
app.include_router(scenes_router)
app.include_router(compositions_router)
app.include_router(build_router)
app.include_router(images_router)
app.include_router(projects_router)
app.include_router(history_router)
app.include_router(voices_router)
app.include_router(slides_router)

# Serve rendered MP4 + assets — create dirs eagerly so the mount works on first
# render, not only after the folder happens to exist at startup.
project_path = os.getenv("HYPERFRAMES_PROJECT") or str(Path(__file__).resolve().parent.parent / "my-video")
project_dir = Path(project_path)
renders_dir = project_dir / "renders"
assets_dir = project_dir / "assets"
sessions_dir = project_dir / "sessions"
renders_dir.mkdir(parents=True, exist_ok=True)
assets_dir.mkdir(parents=True, exist_ok=True)
sessions_dir.mkdir(parents=True, exist_ok=True)
slides_dir = project_dir / "slides"
slides_dir.mkdir(parents=True, exist_ok=True)
app.mount("/renders", StaticFiles(directory=str(renders_dir)), name="renders")
app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")
app.mount("/sessions", StaticFiles(directory=str(sessions_dir)), name="sessions")
app.mount("/slides", StaticFiles(directory=str(slides_dir)), name="slides")

# Serve static history
history_dir = project_dir / "history"
history_dir.mkdir(exist_ok=True)
(history_dir / "htmls").mkdir(exist_ok=True)
(history_dir / "videos").mkdir(exist_ok=True)
app.mount("/static-history", StaticFiles(directory=str(history_dir)), name="static-history")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/status")
def system_status():
    from middleware.concurrency import limiter
    return {
        "render_slots_total": limiter.max_renders,
        "render_slots_available": limiter._render_sem._value,
        "render_queue": limiter.render_queue_size,
        "llm_slots_total": limiter.max_llm_calls,
        "llm_slots_available": limiter._llm_sem._value,
    }


import asyncio
import time
import shutil

async def cleanup_old_sessions():
    """Xoá thư mục session quá 30 phút."""
    while True:
        await asyncio.sleep(600)  # chạy mỗi 10 phút
        s_dir = Path(project_path) / "sessions"
        if not s_dir.exists():
            continue
        cutoff = time.time() - 1800  # 30 phút
        for d in s_dir.iterdir():
            if d.is_dir() and d.stat().st_mtime < cutoff:
                try:
                    shutil.rmtree(d, ignore_errors=True)
                    print(f"[cleanup] Deleted old session directory: {d.name}")
                except Exception as e:
                    print(f"[cleanup ERROR] Failed to delete {d.name}: {e}")


@app.on_event("startup")
async def startup():
    asyncio.create_task(cleanup_old_sessions())
