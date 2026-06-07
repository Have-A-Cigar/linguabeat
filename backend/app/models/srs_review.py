import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class SrsReview(Base):
    __tablename__ = "srs_reviews"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_word_id: Mapped[str] = mapped_column(String, ForeignKey("user_words.id"), nullable=False, index=True)
    reviewed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    quality: Mapped[int] = mapped_column(Integer, nullable=False)
    rating: Mapped[str] = mapped_column(String, nullable=False)          # Again/Hard/Good/Easy
    new_stability: Mapped[float] = mapped_column(Float, nullable=False)
    new_scheduled_days: Mapped[int] = mapped_column(Integer, nullable=False)
