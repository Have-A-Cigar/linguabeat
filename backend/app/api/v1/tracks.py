from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.track import Track
from app.schemas.track import TrackRead, TrackDetail

router = APIRouter(prefix="/tracks", tags=["tracks"])


@router.get("", response_model=list[TrackRead])
async def list_tracks(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[TrackRead]:
    result = await db.execute(select(Track).order_by(Track.title))
    tracks = result.scalars().all()
    return [TrackRead.model_validate(t) for t in tracks]


@router.get("/{track_id}", response_model=TrackDetail)
async def get_track(
    track_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TrackDetail:
    result = await db.execute(select(Track).where(Track.id == track_id))
    track = result.scalar_one_or_none()
    if not track:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Track not found")
    return TrackDetail.from_orm_with_lyrics(track)


@router.post("/{track_id}/sessions", status_code=201)
async def start_session(
    track_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    return {"track_id": track_id, "status": "started"}
