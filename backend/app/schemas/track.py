from typing import Any
from pydantic import BaseModel


class LyricLine(BaseModel):
    timecode: float
    text: str


class TrackRead(BaseModel):
    id: str
    title: str
    artist: str
    duration_sec: int
    genre: str | None = None
    audio_url: str | None = None

    model_config = {"from_attributes": True}


class TrackDetail(TrackRead):
    lyrics: list[LyricLine] | None = None

    @classmethod
    def from_orm_with_lyrics(cls, track: Any) -> "TrackDetail":
        lines = None
        if track.lyrics_json:
            lines = [LyricLine(**l) for l in track.lyrics_json]
        return cls(
            id=track.id,
            title=track.title,
            artist=track.artist,
            duration_sec=track.duration_sec,
            genre=track.genre,
            audio_url=getattr(track, "audio_url", None),
            lyrics=lines,
        )
