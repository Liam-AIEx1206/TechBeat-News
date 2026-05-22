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

app = FastAPI(title="TechBeat API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
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

# Serve rendered MP4 + assets
project_path = os.getenv("HYPERFRAMES_PROJECT") or str(Path(__file__).resolve().parent.parent / "my-video")
project_dir = Path(project_path)
if (project_dir / "renders").exists():
    app.mount("/renders", StaticFiles(directory=str(project_dir / "renders")), name="renders")
if (project_dir / "assets").exists():
    app.mount("/assets", StaticFiles(directory=str(project_dir / "assets")), name="assets")

# Serve static history
history_dir = project_dir / "history"
history_dir.mkdir(exist_ok=True)
(history_dir / "htmls").mkdir(exist_ok=True)
(history_dir / "videos").mkdir(exist_ok=True)
app.mount("/static-history", StaticFiles(directory=str(history_dir)), name="static-history")


@app.get("/health")
def health():
    return {"status": "ok"}
