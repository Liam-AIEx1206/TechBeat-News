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

app = FastAPI(title="VideoAI Backend", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(extract_router)
app.include_router(scenes_router)
app.include_router(compositions_router)
app.include_router(build_router)
app.include_router(images_router)

# Serve rendered MP4 + assets
project_path = os.getenv("HYPERFRAMES_PROJECT") or str(Path(__file__).resolve().parent.parent / "my-video")
project_dir = Path(project_path)
if (project_dir / "renders").exists():
    app.mount("/renders", StaticFiles(directory=str(project_dir / "renders")), name="renders")
if (project_dir / "assets").exists():
    app.mount("/assets", StaticFiles(directory=str(project_dir / "assets")), name="assets")


@app.get("/health")
def health():
    return {"status": "ok"}
