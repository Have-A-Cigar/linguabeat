from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.models.user_word import UserWord
from app.schemas.word import WordCreate, WordRead
from app.services.word_service import WordService

router = APIRouter(prefix="/words", tags=["words"])


@router.get("", response_model=list[WordRead])
async def list_words(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[WordRead]:
    result = await db.execute(
        select(UserWord).where(UserWord.user_id == current_user.id)
    )
    return list(result.scalars().all())


@router.post("", response_model=WordRead, status_code=201)
async def add_word(
    body: WordCreate,
    lang: str = Query(default="en", description="Target language for auto-translation"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> WordRead:
    # Prevent duplicates per user (same word, any track)
    existing = await db.execute(
        select(UserWord).where(
            UserWord.user_id == current_user.id,
            UserWord.word == body.word,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Word already in vocabulary")

    svc = WordService(db)
    uw = await svc.add_word(
        user_id=current_user.id,
        track_id=body.track_id,
        word=body.word,
        translation=body.translation,
        subtitle_text=body.subtitle_text,
        timecode_sec=body.timecode_sec,
        target_lang=lang,
    )
    await db.commit()
    await db.refresh(uw)
    return WordRead.model_validate(uw)


@router.get("/{word_id}", response_model=WordRead)
async def get_word(
    word_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> WordRead:
    result = await db.execute(
        select(UserWord).where(
            UserWord.id == word_id,
            UserWord.user_id == current_user.id,
        )
    )
    uw = result.scalar_one_or_none()
    if not uw:
        raise HTTPException(status_code=404, detail="Word not found")
    return WordRead.model_validate(uw)


@router.delete("/{word_id}", status_code=204)
async def delete_word(
    word_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    result = await db.execute(
        select(UserWord).where(
            UserWord.id == word_id,
            UserWord.user_id == current_user.id,
        )
    )
    uw = result.scalar_one_or_none()
    if not uw:
        raise HTTPException(status_code=404, detail="Word not found")
    await db.delete(uw)
    await db.commit()
