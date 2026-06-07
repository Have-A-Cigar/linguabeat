"""Admin-only endpoints (track ingestion)."""

from __future__ import annotations

import uuid
from pathlib import Path

import aiofiles
from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import is_admin
from app.core.database import get_db
from app.models.track import Track
from app.models.user import User
from app.schemas.track import TrackRead

router = APIRouter(prefix="/admin", tags=["admin"])

# backend/uploads/audio — raw uploads; exposed via the /static/audio mount in main.py
UPLOAD_AUDIO_DIR = Path(__file__).resolve().parents[3] / "uploads" / "audio"


@router.post("/tracks", response_model=TrackRead, status_code=status.HTTP_201_CREATED)
async def create_track(
    audio: UploadFile = File(...),
    title: str = Form(...),
    artist: str = Form(...),
    duration_sec: int = Form(...),
    lyrics_txt: str = Form(...),
    genre: str | None = Form(None),
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(is_admin),
) -> TrackRead:
    """Upload an audio file and register a new track.

    The raw lyrics text (``lyrics_txt``) is accepted but not aligned here;
    word-level alignment is performed later by ``scripts/process_track.py``,
    so ``lyrics_json`` is created as ``None``.
    """
    track_id = str(uuid.uuid4())

    UPLOAD_AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    dest = UPLOAD_AUDIO_DIR / f"{track_id}.mp3"

    async with aiofiles.open(dest, "wb") as out:
        while chunk := await audio.read(1024 * 1024):
            await out.write(chunk)

    track = Track(
        id=track_id,
        title=title,
        artist=artist,
        duration_sec=duration_sec,
        genre=genre,
        lyrics_json=None,
        audio_url=f"/static/audio/{track_id}.mp3",
    )
    db.add(track)
    await db.commit()
    await db.refresh(track)

    return TrackRead.model_validate(track)
