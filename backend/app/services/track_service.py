from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.track import Track


class TrackService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_all(self, genre: str | None = None) -> list[Track]:
        q = select(Track)
        if genre:
            q = q.where(Track.genre == genre)
        result = await self.db.execute(q)
        return result.scalars().all()

    async def get_by_id(self, track_id: str) -> Track | None:
        result = await self.db.execute(select(Track).where(Track.id == track_id))
        return result.scalar_one_or_none()
