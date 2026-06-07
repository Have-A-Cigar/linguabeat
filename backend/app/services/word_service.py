from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.user_word import UserWord
from app.services.translation_service import translate


class WordService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def add_word(
        self,
        user_id: str,
        track_id: str,
        word: str,
        translation: str | None,
        subtitle_text: str | None,
        timecode_sec: float | None,
        target_lang: str = "en",
    ) -> UserWord:
        # Auto-translate if caller didn't provide a translation
        if not translation:
            translation = await translate(
                word=word,
                context=subtitle_text or word,
                target_lang=target_lang,
            )

        uw = UserWord(
            user_id=user_id,
            track_id=track_id,
            word=word,
            translation=translation,
            subtitle_text=subtitle_text,
            timecode_sec=timecode_sec,
            due=datetime.now(timezone.utc),
        )
        self.db.add(uw)
        await self.db.flush()
        return uw

    async def get_user_words(self, user_id: str) -> list[UserWord]:
        result = await self.db.execute(
            select(UserWord).where(UserWord.user_id == user_id)
        )
        return result.scalars().all()
