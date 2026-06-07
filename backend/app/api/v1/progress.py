"""Progress endpoints: vocabulary breakdown, streak and review timeline."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.srs_review import SrsReview
from app.models.user import User
from app.models.user_word import UserWord

router = APIRouter(prefix="/progress", tags=["progress"])


class ProgressOut(BaseModel):
    """Vocabulary breakdown for the current user."""

    learned: int
    in_progress: int
    new: int


class StreakOut(BaseModel):
    """Consecutive-day review streak."""

    streak_days: int
    last_active: str | None


class TimelinePoint(BaseModel):
    """Number of reviews on a single calendar day."""

    date: str
    count: int


class TimelineOut(BaseModel):
    """Daily review counts for the last 30 days."""

    data: list[TimelinePoint]


@router.get("", response_model=ProgressOut)
async def get_progress(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ProgressOut:
    """Return how many words are learned, in progress, or brand-new.

    A word is *learned* once it reaches the ``Review`` state, *in progress*
    while it is still being drilled (``Learning``/``Relearning``), and *new*
    when it has never been reviewed (``reps == 0``).
    """
    learned = (
        await db.execute(
            select(func.count())
            .select_from(UserWord)
            .where(
                UserWord.user_id == current_user.id,
                UserWord.state == "Review",
            )
        )
    ).scalar_one()

    in_progress = (
        await db.execute(
            select(func.count())
            .select_from(UserWord)
            .where(
                UserWord.user_id == current_user.id,
                UserWord.state.in_(("Learning", "Relearning")),
                UserWord.reps > 0,
            )
        )
    ).scalar_one()

    new = (
        await db.execute(
            select(func.count())
            .select_from(UserWord)
            .where(
                UserWord.user_id == current_user.id,
                UserWord.reps == 0,
            )
        )
    ).scalar_one()

    return ProgressOut(learned=learned, in_progress=in_progress, new=new)


@router.get("/streak", response_model=StreakOut)
async def get_streak(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StreakOut:
    """Return the number of consecutive days with at least one review.

    The streak is counted backwards from today: today (or, if there was no
    activity today, yesterday) starts the chain and every preceding day with
    at least one review extends it.
    """
    result = await db.execute(
        select(SrsReview.reviewed_at)
        .join(UserWord, SrsReview.user_word_id == UserWord.id)
        .where(UserWord.user_id == current_user.id)
        .order_by(SrsReview.reviewed_at.desc())
    )
    timestamps = result.scalars().all()

    if not timestamps:
        return StreakOut(streak_days=0, last_active=None)

    active_days: set[date] = {ts.astimezone(timezone.utc).date() for ts in timestamps}
    last_active = max(timestamps).astimezone(timezone.utc)

    today = datetime.now(timezone.utc).date()
    # Allow the streak to anchor on today or yesterday.
    if today in active_days:
        cursor = today
    elif (today - timedelta(days=1)) in active_days:
        cursor = today - timedelta(days=1)
    else:
        return StreakOut(streak_days=0, last_active=last_active.isoformat())

    streak_days = 0
    while cursor in active_days:
        streak_days += 1
        cursor -= timedelta(days=1)

    return StreakOut(streak_days=streak_days, last_active=last_active.isoformat())


@router.get("/timeline", response_model=TimelineOut)
async def get_timeline(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TimelineOut:
    """Return per-day review counts for the last 30 days (gaps filled with 0)."""
    today = datetime.now(timezone.utc).date()
    window_start = today - timedelta(days=29)
    window_start_dt = datetime.combine(
        window_start, datetime.min.time(), tzinfo=timezone.utc
    )

    result = await db.execute(
        select(SrsReview.reviewed_at)
        .join(UserWord, SrsReview.user_word_id == UserWord.id)
        .where(
            UserWord.user_id == current_user.id,
            SrsReview.reviewed_at >= window_start_dt,
        )
    )
    timestamps = result.scalars().all()

    counts: dict[date, int] = {}
    for ts in timestamps:
        day = ts.astimezone(timezone.utc).date()
        counts[day] = counts.get(day, 0) + 1

    data = [
        TimelinePoint(
            date=(window_start + timedelta(days=offset)).isoformat(),
            count=counts.get(window_start + timedelta(days=offset), 0),
        )
        for offset in range(30)
    ]

    return TimelineOut(data=data)
