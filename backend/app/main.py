"""LinguaBeat FastAPI application entry point."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.v1 import admin, auth, progress, srs, tracks, words
from app.core.config import settings
from app.landing import router as landing_router

app = FastAPI(
    title="LinguaBeat API",
    version="1.0.0",
    description="Web platform for learning Russian through music + FSRS.",
)

_STATIC_DIR = Path(__file__).resolve().parents[1] / "static"
_UPLOAD_AUDIO_DIR = Path(__file__).resolve().parents[1] / "uploads" / "audio"
_UPLOAD_AUDIO_DIR.mkdir(parents=True, exist_ok=True)
# Mount the more specific /static/audio BEFORE /static so uploaded audio
# is served from uploads/, not the generic static dir (Starlette matches
# mounts in registration order).
app.mount(
    "/static/audio",
    StaticFiles(directory=str(_UPLOAD_AUDIO_DIR)),
    name="audio",
)
app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(landing_router)

API_V1_PREFIX = "/api/v1"

app.include_router(auth.router, prefix=API_V1_PREFIX)
app.include_router(tracks.router, prefix=API_V1_PREFIX)
app.include_router(admin.router, prefix=API_V1_PREFIX)
app.include_router(words.router, prefix=API_V1_PREFIX)
app.include_router(srs.router, prefix=API_V1_PREFIX)
app.include_router(progress.router, prefix=API_V1_PREFIX)


@app.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    """Liveness probe."""
    return dict(status="ok", service="linguabeat")
