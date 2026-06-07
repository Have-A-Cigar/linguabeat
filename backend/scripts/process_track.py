"""Offline track-processing pipeline for LinguaBeat.

Given an audio file and a plain-text lyrics file (one line = one strophe/line),
produce line-level timecodes and persist them to ``Track.lyrics_json``.

WhisperX is an *optional* dependency. When it is available the script performs
forced alignment to derive accurate word timings, which are then collapsed onto
the input lyric lines. When WhisperX (or its model download) is unavailable, the
script falls back to distributing the lyric lines evenly across the track
duration.

Run from the ``backend/`` directory::

    python -m scripts.process_track \
        --track-id <uuid> --audio path/to/song.mp3 --lyrics-txt path/to/lyrics.txt
"""

from __future__ import annotations

import argparse
import asyncio
import logging
from pathlib import Path

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.track import Track

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("process_track")


def _read_lyric_lines(lyrics_txt: Path) -> list[str]:
    """Read non-empty, stripped lines from the lyrics text file."""
    raw = lyrics_txt.read_text(encoding="utf-8")
    lines = [line.strip() for line in raw.splitlines() if line.strip()]
    if not lines:
        raise ValueError(f"Lyrics file {lyrics_txt} contains no usable lines")
    return lines


def _select_device() -> str:
    """Return 'cuda' when a GPU is available, otherwise 'cpu'."""
    try:
        import torch

        return "cuda" if torch.cuda.is_available() else "cpu"
    except Exception:  # noqa: BLE001 - torch optional / any import failure
        return "cpu"


def _align_with_whisperx(
    audio_path: Path, lines: list[str]
) -> list[dict[str, float | str]] | None:
    """Run WhisperX forced alignment and map word timings onto lyric lines.

    Returns a list of ``{"timecode": float, "text": str}`` (one entry per input
    line) or ``None`` when WhisperX is unavailable or yields no usable words.
    """
    try:
        import whisperx
    except ImportError:
        logger.warning("WhisperX not installed - using fallback timings")
        return None

    try:
        device = _select_device()
        logger.info("WhisperX device: %s", device)

        audio = whisperx.load_audio(str(audio_path))

        logger.info("Loading transcription model (large-v2, ru)")
        model = whisperx.load_model("large-v2", device, language="ru")
        result = model.transcribe(audio, language="ru")

        logger.info("Loading alignment model (ru)")
        align_model, metadata = whisperx.load_align_model(
            language_code="ru", device=device
        )
        aligned = whisperx.align(
            result["segments"],
            align_model,
            metadata,
            audio,
            device,
            return_char_alignments=False,
        )
    except Exception as exc:  # noqa: BLE001 - any runtime/model failure -> fallback
        logger.warning("WhisperX alignment failed (%s) - using fallback", exc)
        return None

    # Flatten word-level timestamps in order.
    words: list[dict] = []
    for segment in aligned.get("segments", []):
        for word in segment.get("words", []):
            start = word.get("start")
            if start is not None:
                words.append({"start": float(start), "word": str(word.get("word", ""))})

    if not words:
        logger.warning("WhisperX returned no word timings - using fallback")
        return None

    return _map_words_to_lines(words, lines)


def _map_words_to_lines(
    words: list[dict], lines: list[str]
) -> list[dict[str, float | str]]:
    """Assign each lyric line the start timecode of its first word.

    Words are consumed sequentially. Each line takes as many words as it
    contains (by whitespace count); the line's timecode is the start time of the
    first word allocated to it. This is robust to minor transcription drift.
    """
    segments: list[dict[str, float | str]] = []
    cursor = 0
    n_words = len(words)
    prev_timecode = 0.0

    for line in lines:
        token_count = max(1, len(line.split()))
        if cursor < n_words:
            timecode = float(words[cursor]["start"])
        else:
            timecode = prev_timecode
        segments.append({"timecode": round(timecode, 3), "text": line})
        prev_timecode = timecode
        cursor += token_count

    return segments


def _fallback_even(
    lines: list[str], duration_sec: int
) -> list[dict[str, float | str]]:
    """Distribute lyric lines evenly across the track duration."""
    n = len(lines)
    logger.warning(
        "Generating APPROXIMATE evenly-spaced timings for %d lines over %ds",
        n,
        duration_sec,
    )
    step = duration_sec / n if n else 0.0
    return [
        {"timecode": round(i * step, 3), "text": line} for i, line in enumerate(lines)
    ]


async def _load_track(session, track_id: str) -> Track | None:
    result = await session.execute(select(Track).where(Track.id == track_id))
    return result.scalar_one_or_none()


async def process(track_id: str, audio_path: Path, lyrics_txt: Path) -> int:
    """Run the pipeline and persist ``lyrics_json``. Returns process exit code."""
    if not audio_path.is_file():
        logger.error("Audio file not found: %s", audio_path)
        return 1
    if not lyrics_txt.is_file():
        logger.error("Lyrics file not found: %s", lyrics_txt)
        return 1

    lines = _read_lyric_lines(lyrics_txt)
    logger.info("Loaded %d lyric lines", len(lines))

    async with AsyncSessionLocal() as session:
        track = await _load_track(session, track_id)
        if track is None:
            logger.error("Track not found: %s", track_id)
            return 1

        logger.info("Processing track '%s' by %s", track.title, track.artist)

        segments = _align_with_whisperx(audio_path, lines)
        if segments is None:
            segments = _fallback_even(lines, track.duration_sec)
        else:
            logger.info("WhisperX alignment produced %d line segments", len(segments))

        track.lyrics_json = segments
        await session.commit()
        logger.info("Saved lyrics_json (%d segments) for track %s", len(segments), track_id)

    return 0


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Align lyrics to audio and store Track.lyrics_json."
    )
    parser.add_argument("--track-id", required=True, help="Track UUID to update")
    parser.add_argument("--audio", required=True, type=Path, help="Path to audio file")
    parser.add_argument(
        "--lyrics-txt",
        required=True,
        type=Path,
        help="Path to lyrics text file (one line per strophe/line)",
    )
    return parser.parse_args(argv)


async def _amain(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    return await process(args.track_id, args.audio, args.lyrics_txt)


def main(argv: list[str] | None = None) -> int:
    return asyncio.run(_amain(argv))


if __name__ == "__main__":
    raise SystemExit(main())
