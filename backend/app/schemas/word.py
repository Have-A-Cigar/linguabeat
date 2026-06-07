from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class WordCreate(BaseModel):
    word: str
    track_id: str
    subtitle_text: Optional[str] = None
    timecode_sec: Optional[float] = None
    translation: Optional[str] = None


class WordRead(BaseModel):
    id: str
    word: str
    translation: Optional[str]
    track_id: str
    subtitle_text: Optional[str]
    timecode_sec: Optional[float]
    stability: Optional[float]
    reps: int
    lapses: int
    due: datetime
    state: str

    model_config = {"from_attributes": True}
