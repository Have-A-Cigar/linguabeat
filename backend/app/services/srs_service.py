"""SRS Service — тонкая обёртка над FSRS-ядром core_srs.py."""
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.domain.core_srs import SRSScheduler, WordEntry, WordContext, quality_to_rating
from app.models.user_word import UserWord
from app.models.srs_review import SrsReview


class SRSService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_due_words(self, user_id: str) -> list[UserWord]:
        now = datetime.now(timezone.utc)
        result = await self.db.execute(
            select(UserWord).where(
                UserWord.user_id == user_id,
                UserWord.due <= now,
            )
        )
        return list(result.scalars().all())

    async def apply_review(self, user_word_id: str, quality: int) -> UserWord:
        result = await self.db.execute(
            select(UserWord).where(UserWord.id == user_word_id)
        )
        uw = result.scalar_one()

        entry = WordEntry(
            word=uw.word,
            translation=uw.translation or "",
            context=WordContext(
                track_id=uw.track_id,
                subtitle_text=uw.subtitle_text or "",
                timecode_sec=uw.timecode_sec or 0.0,
            ),
            added_at=uw.created_at,
            stability=uw.stability,
            difficulty=uw.difficulty,
            step=uw.step,
            reps=uw.reps,
            lapses=uw.lapses,
            state=uw.state,
            due=uw.due,
            last_review=uw.last_review,
        )

        updated = SRSScheduler.schedule(entry, quality)

        uw.stability = updated.stability
        uw.difficulty = updated.difficulty
        uw.step = updated.step
        uw.reps = updated.reps
        uw.lapses = updated.lapses
        uw.state = updated.state
        uw.due = updated.due
        uw.last_review = updated.last_review

        review = SrsReview(
            user_word_id=user_word_id,
            quality=quality,
            rating=quality_to_rating(quality).name,
            new_stability=updated.stability or 0.0,
            new_scheduled_days=max(0, (updated.due - datetime.now(timezone.utc)).days),
        )
        self.db.add(review)
        return uw

    async def get_stats(self, user_id: str) -> dict:
        now = datetime.now(timezone.utc)
        due_count = (await self.db.execute(
            select(func.count()).where(UserWord.user_id == user_id, UserWord.due <= now)
        )).scalar()
        total = (await self.db.execute(
            select(func.count()).where(UserWord.user_id == user_id)
        )).scalar()
        new_learning = (await self.db.execute(
            select(func.count()).where(UserWord.user_id == user_id, UserWord.state == "Learning")
        )).scalar()
        in_review = (await self.db.execute(
            select(func.count()).where(UserWord.user_id == user_id, UserWord.state == "Review")
        )).scalar()
        return {
            "due_today": due_count,
            "total": total,
            "new_learning": new_learning,
            "in_review": in_review,
        }
