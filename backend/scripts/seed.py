"""Seed the database with deterministic test data.

Run from the ``backend/`` directory::

    python -m scripts.seed

Creates a superuser, two test tracks with timed lyrics, twenty vocabulary
words spread across realistic FSRS states, and a week of review history so
that streak and timeline endpoints have data to work with.

The script is idempotent: every entity is checked for existence first and
skipped if already present (upsert pattern).
"""

from __future__ import annotations

import asyncio
import random
from datetime import datetime, time, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.core.security import get_password_hash
from app.models.srs_review import SrsReview
from app.models.track import Track
from app.models.user import User
from app.models.user_word import UserWord

# Deterministic randomness so repeated runs stay stable.
random.seed(42)

TEST_USER_EMAIL = "test@linguabeat.ru"
TEST_USER_PASSWORD = "test1234"

TRACK_1_ID = "seed-track-0001"
TRACK_2_ID = "seed-track-0002"

# 20 simple Russian words with English translations.
WORDS: list[tuple[str, str]] = [
    ("река", "river"),
    ("весна", "spring"),
    ("поле", "field"),
    ("ночь", "night"),
    ("день", "day"),
    ("свет", "light"),
    ("путь", "path"),
    ("мир", "world"),
    ("дом", "house"),
    ("лес", "forest"),
    ("вода", "water"),
    ("огонь", "fire"),
    ("звезда", "star"),
    ("земля", "earth"),
    ("небо", "sky"),
    ("голос", "voice"),
    ("песня", "song"),
    ("время", "time"),
    ("жизнь", "life"),
    ("душа", "soul"),
]


def _lyrics(prefix: str) -> list[dict]:
    """Build a realistic timed-lyrics payload for a track."""
    lines = [
        f"{prefix} — первый куплет, тестовая строка",
        f"{prefix} — припев начинается здесь",
        f"{prefix} — вторая строка куплета",
        f"{prefix} — третья строка куплета",
        f"{prefix} — снова припев звучит",
        f"{prefix} — мостик перед финалом",
        f"{prefix} — предпоследняя строка",
        f"{prefix} — финальная строка песни",
    ]
    return [
        {"timecode": round(idx * 5.0, 1), "text": text}
        for idx, text in enumerate(lines)
    ]


async def _seed_user(db: AsyncSession) -> User:
    """Create (or fetch) the test superuser."""
    existing = await db.execute(select(User).where(User.email == TEST_USER_EMAIL))
    user = existing.scalar_one_or_none()
    if user is not None:
        print(f"[skip] user {TEST_USER_EMAIL} already exists")
        return user

    user = User(
        email=TEST_USER_EMAIL,
        hashed_password=get_password_hash(TEST_USER_PASSWORD),
        language_level="A2",
        is_active=True,
        is_superuser=True,
    )
    db.add(user)
    await db.flush()
    print(f"[ok]   created user {TEST_USER_EMAIL}")
    return user


async def _seed_track(
    db: AsyncSession, track_id: str, title: str
) -> Track:
    """Create (or fetch) a single test track."""
    existing = await db.execute(select(Track).where(Track.id == track_id))
    track = existing.scalar_one_or_none()
    if track is not None:
        print(f"[skip] track {title!r} already exists")
        return track

    track = Track(
        id=track_id,
        title=title,
        artist="Тест",
        duration_sec=180,
        genre="folk",
        audio_url=None,
        lyrics_json=_lyrics(title),
    )
    db.add(track)
    await db.flush()
    print(f"[ok]   created track {title!r}")
    return track


async def _seed_words(
    db: AsyncSession, user: User, track: Track
) -> list[UserWord]:
    """Create 20 vocabulary words spread across FSRS states.

    Distribution:
        * ~5 words due now (state Review, due in the past) — appear in Review.
        * ~8 words already learned (state Review, due in the future).
        * ~7 brand-new words (reps == 0, state Learning).
    """
    existing = await db.execute(
        select(UserWord).where(
            UserWord.user_id == user.id, UserWord.track_id == track.id
        )
    )
    already = existing.scalars().all()
    if already:
        print(f"[skip] {len(already)} user words already exist for track")
        return list(already)

    now = datetime.now(timezone.utc)
    words: list[UserWord] = []

    for idx, (word, translation) in enumerate(WORDS):
        subtitle = f"{track.title} — строка со словом «{word}»"
        timecode = float((idx % 8) * 5)

        if idx < 5:
            # Due now: studied before, scheduled in the past.
            uw = UserWord(
                user_id=user.id,
                track_id=track.id,
                word=word,
                translation=translation,
                subtitle_text=subtitle,
                timecode_sec=timecode,
                stability=round(random.uniform(2.0, 8.0), 2),
                difficulty=round(random.uniform(4.0, 7.0), 2),
                step=None,
                reps=random.randint(2, 6),
                lapses=random.randint(0, 1),
                state="Review",
                due=now - timedelta(days=random.randint(1, 3)),
                last_review=now - timedelta(days=random.randint(4, 10)),
            )
        elif idx < 13:
            # Learned: scheduled comfortably in the future.
            uw = UserWord(
                user_id=user.id,
                track_id=track.id,
                word=word,
                translation=translation,
                subtitle_text=subtitle,
                timecode_sec=timecode,
                stability=round(random.uniform(10.0, 40.0), 2),
                difficulty=round(random.uniform(3.0, 6.0), 2),
                step=None,
                reps=random.randint(3, 9),
                lapses=random.randint(0, 2),
                state="Review",
                due=now + timedelta(days=random.randint(5, 30)),
                last_review=now - timedelta(days=random.randint(1, 5)),
            )
        else:
            # Brand-new: never reviewed.
            uw = UserWord(
                user_id=user.id,
                track_id=track.id,
                word=word,
                translation=translation,
                subtitle_text=subtitle,
                timecode_sec=timecode,
                stability=None,
                difficulty=None,
                step=0,
                reps=0,
                lapses=0,
                state="Learning",
                due=now,
                last_review=None,
            )
        db.add(uw)
        words.append(uw)

    await db.flush()
    print(f"[ok]   created {len(words)} user words")
    return words


async def _seed_reviews(
    db: AsyncSession, words: list[UserWord]
) -> None:
    """Create 10 reviews across the last 7 days (2 per day)."""
    word_ids = [w.id for w in words]
    existing = await db.execute(
        select(SrsReview).where(SrsReview.user_word_id.in_(word_ids))
    )
    if existing.scalars().first() is not None:
        print("[skip] srs reviews already exist for seed words")
        return

    rating_names = {1: "Again", 2: "Again", 3: "Hard", 4: "Good"}
    now = datetime.now(timezone.utc)
    created = 0

    for day_offset in range(7):
        day = now - timedelta(days=day_offset)
        for _ in range(2):
            rating_value = random.randint(1, 4)
            reviewed_at = datetime.combine(
                day.date(),
                time(hour=random.randint(8, 21), minute=random.randint(0, 59)),
                tzinfo=timezone.utc,
            )
            review = SrsReview(
                user_word_id=random.choice(word_ids),
                reviewed_at=reviewed_at,
                quality=rating_value + 1,
                rating=rating_names[rating_value],
                new_stability=round(random.uniform(1.0, 30.0), 2),
                new_scheduled_days=random.randint(1, 30),
            )
            db.add(review)
            created += 1
            if created >= 10:
                break
        if created >= 10:
            break

    await db.flush()
    print(f"[ok]   created {created} srs reviews")


async def main() -> None:
    """Seed all test entities inside a single transaction."""
    async with AsyncSessionLocal() as db:
        user = await _seed_user(db)
        track_1 = await _seed_track(db, TRACK_1_ID, "Тестовая песня 1")
        await _seed_track(db, TRACK_2_ID, "Тестовая песня 2")
        words = await _seed_words(db, user, track_1)
        await _seed_reviews(db, words)
        await db.commit()
        print("[done] seed completed")


if __name__ == "__main__":
    asyncio.run(main())
