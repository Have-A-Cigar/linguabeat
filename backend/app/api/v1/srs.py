from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.srs import ReviewRequest, ReviewResponse, ContextCard, SRSStats
from app.services.srs_service import SRSService

router = APIRouter(prefix="/srs", tags=["srs"])


@router.get("/due", response_model=list[ContextCard])
async def get_due_cards(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = SRSService(db)
    words = await service.get_due_words(current_user.id)
    return [
        ContextCard(
            user_word_id=w.id,
            word=w.word,
            translation=w.translation,
            context_subtitle=w.subtitle_text,
            context_timecode_sec=w.timecode_sec,
            context_track_id=w.track_id,
            due=w.due,
            stability=w.stability,
            reps=w.reps,
            lapses=w.lapses,
            state=w.state,
        )
        for w in words
    ]


@router.post("/review", response_model=ReviewResponse)
async def submit_review(
    body: ReviewRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = SRSService(db)
    try:
        uw = await service.apply_review(body.user_word_id, body.quality)
        await db.commit()
    except Exception as exc:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ReviewResponse(
        user_word_id=uw.id,
        stability=uw.stability,
        difficulty=uw.difficulty,
        reps=uw.reps,
        lapses=uw.lapses,
        state=uw.state,
        due=uw.due,
    )


@router.get("/stats", response_model=SRSStats)
async def get_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = SRSService(db)
    data = await service.get_stats(current_user.id)
    return SRSStats(**data)
