from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class ReviewRequest(BaseModel):
    user_word_id: str
    quality: int = Field(..., ge=0, le=5)


class ReviewResponse(BaseModel):
    user_word_id: str
    stability: Optional[float]
    difficulty: Optional[float]
    reps: int
    lapses: int
    state: str
    due: datetime


class ContextCard(BaseModel):
    user_word_id: str
    word: str
    translation: Optional[str]
    context_subtitle: Optional[str]
    context_timecode_sec: Optional[float]
    context_track_id: str
    due: datetime
    stability: Optional[float]
    reps: int
    lapses: int
    state: str


class SRSStats(BaseModel):
    due_today: int
    total: int
    new_learning: int
    in_review: int
