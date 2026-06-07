"""
core_srs.py — SRS ядро LinguaBeat на алгоритме FSRS-5 (fsrs v6).

FSRS показывает на 25% меньше повторений при том же retention 90%
по данным 350 млн сессий Anki (Ye et al., 2022).

Инновационность LinguaBeat: слово запоминается вместе с таймкодом, строфой
и треком. Карточка повторения воспроизводит именно этот контекст — повторение
происходит в том же фонетическом и эмоциональном окружении.

Python 3.11+. Требует: fsrs>=4.0.0
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from typing import Optional

from fsrs import Card, Rating, Scheduler, State as FSRSState

_SCHEDULER = Scheduler()


# ---------------------------------------------------------------------------
# Quality (0–5) → FSRS Rating
# ---------------------------------------------------------------------------


def quality_to_rating(quality: int) -> Rating:
    """Маппинг SM-2-совместимой шкалы 0–5 в 4 оценки FSRS."""
    if quality <= 2:
        return Rating.Again
    if quality == 3:
        return Rating.Hard
    if quality == 4:
        return Rating.Good
    return Rating.Easy  # quality == 5


# ---------------------------------------------------------------------------
# Доменные сущности
# ---------------------------------------------------------------------------


@dataclass
class Track:
    """Музыкальный трек — источник лингвистического контекста."""

    id: str
    title: str
    artist: str
    duration_sec: float

    def __post_init__(self) -> None:
        if self.duration_sec <= 0:
            raise ValueError(f"duration_sec должно быть положительным, получено: {self.duration_sec}")


@dataclass
class Subtitle:
    """Строка субтитров, привязанная к конкретному моменту трека."""

    track_id: str
    start_sec: float
    end_sec: float
    text: str

    def __post_init__(self) -> None:
        if self.end_sec <= self.start_sec:
            raise ValueError(
                f"end_sec ({self.end_sec}) должно быть больше start_sec ({self.start_sec})"
            )
        if not self.text.strip():
            raise ValueError("text субтитра не может быть пустым")

    @property
    def duration_sec(self) -> float:
        return self.end_sec - self.start_sec


@dataclass
class WordContext:
    """Контекст, в котором пользователь впервые встретил слово."""

    track_id: str
    subtitle_text: str
    timecode_sec: float

    def __post_init__(self) -> None:
        if self.timecode_sec < 0:
            raise ValueError(f"timecode_sec не может быть отрицательным: {self.timecode_sec}")


@dataclass
class WordEntry:
    """Запись слова в персональном словаре с FSRS-5 состоянием (fsrs v6).

    FSRS поля (v6):
        stability     — «устойчивость» памяти (сколько дней до 90% retention); None для новых
        difficulty    — внутренняя сложность слова (0–10); None для новых
        step          — шаг в фазе Learning/Relearning; None в фазе Review
        reps          — суммарно успешных повторений (tracked locally)
        lapses        — количество «провалов» с рейтингом Again (tracked locally)
        state         — Learning | Review | Relearning
        due           — UTC-datetime следующего показа
        last_review   — UTC-datetime последнего повторения
    """

    word: str
    translation: str
    context: WordContext
    added_at: datetime
    # FSRS-5 state (v6 API)
    stability: Optional[float] = None
    difficulty: Optional[float] = None
    step: Optional[int] = 0
    reps: int = 0
    lapses: int = 0
    state: str = "Learning"
    due: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_review: Optional[datetime] = None
    enrichments: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.word.strip():
            raise ValueError("word не может быть пустым")
        valid_states = {"Learning", "Review", "Relearning"}
        if self.state not in valid_states:
            raise ValueError(f"state должен быть одним из {valid_states}, получено: {self.state!r}")


@dataclass
class ReviewResult:
    """Результат одного сеанса повторения.

    quality 0–5:
        0–2 → Again (забыто)
        3   → Hard  (с трудом)
        4   → Good  (нормально)
        5   → Easy  (легко)
    """

    word: str
    quality: int
    reviewed_at: datetime

    def __post_init__(self) -> None:
        if not 0 <= self.quality <= 5:
            raise ValueError(f"quality должно быть от 0 до 5, получено: {self.quality}")


# ---------------------------------------------------------------------------
# SRS-планировщик
# ---------------------------------------------------------------------------


class SRSScheduler:
    """FSRS-5 планировщик интервального повторения (fsrs v6 Scheduler)."""

    @staticmethod
    def schedule(
        entry: WordEntry,
        quality: int,
        reviewed_on: Optional[datetime] = None,
    ) -> WordEntry:
        """Обновляет запись слова по результату повторения (FSRS-5).

        Args:
            entry: Текущая запись слова.
            quality: Оценка 0–5.
            reviewed_on: Время повторения (UTC); если None — текущее UTC.

        Returns:
            Новый WordEntry с обновлёнными FSRS-полями (неизменяемый).
        """
        if not 0 <= quality <= 5:
            raise ValueError(f"quality должно быть от 0 до 5, получено: {quality}")

        now = reviewed_on or datetime.now(timezone.utc)
        rating = quality_to_rating(quality)

        # Reconstruct FSRS Card from stored state
        card = Card()
        card.state = FSRSState[entry.state]
        card.step = entry.step
        card.stability = entry.stability
        # FSRS asserts difficulty is not None for Review/Relearning state
        card.difficulty = entry.difficulty if entry.difficulty is not None else 5.0
        card.due = entry.due
        card.last_review = entry.last_review

        updated_card, _ = _SCHEDULER.review_card(card, rating, now)

        return replace(
            entry,
            stability=updated_card.stability,
            difficulty=updated_card.difficulty,
            step=updated_card.step,
            state=updated_card.state.name,
            due=updated_card.due,
            last_review=updated_card.last_review,
            reps=entry.reps + (0 if rating == Rating.Again else 1),
            lapses=entry.lapses + (1 if rating == Rating.Again else 0),
        )

    @staticmethod
    def get_context_card(entry: WordEntry) -> dict:
        """Формирует карточку повторения с музыкальным контекстом.

        Ключевая нетривиальная часть LinguaBeat: карточка содержит строфу
        с таймкодом — повторение происходит в том же фонетическом контексте.
        """
        ctx = entry.context
        result: dict = {
            "word": entry.word,
            "translation": entry.translation,
            "context_subtitle": ctx.subtitle_text,
            "context_timecode_sec": ctx.timecode_sec,
            "context_track_id": ctx.track_id,
            "due": entry.due.isoformat(),
            "stability": round(entry.stability, 4) if entry.stability is not None else None,
            "difficulty": round(entry.difficulty, 4) if entry.difficulty is not None else None,
            "reps": entry.reps,
            "lapses": entry.lapses,
            "state": entry.state,
        }
        if entry.enrichments:
            result["enrichments"] = entry.enrichments
        return result


# ---------------------------------------------------------------------------
# Персональный словарь
# ---------------------------------------------------------------------------


class Vocabulary:
    """Персональный словарь с FSRS-планировщиком."""

    def __init__(self) -> None:
        self.words: dict[str, WordEntry] = {}

    def add_word(
        self,
        word: str,
        translation: str,
        context: WordContext,
        added_at: Optional[datetime] = None,
    ) -> WordEntry:
        """Добавляет слово. Если уже есть — возвращает существующее."""
        if word in self.words:
            return self.words[word]

        entry = WordEntry(
            word=word,
            translation=translation,
            context=context,
            added_at=added_at or datetime.now(timezone.utc),
            due=datetime.now(timezone.utc),  # новое слово сразу к показу
        )
        self.words[word] = entry
        return entry

    def get_due_words(self, as_of: Optional[datetime] = None) -> list[WordEntry]:
        """Слова к повторению на указанный момент (по умолчанию — сейчас)."""
        target = as_of or datetime.now(timezone.utc)
        due = [e for e in self.words.values() if e.due <= target]
        due.sort(key=lambda e: e.due)
        return due

    def apply_review(self, result: ReviewResult) -> WordEntry:
        """Применяет результат повторения."""
        if result.word not in self.words:
            raise KeyError(f"Слово '{result.word}' не найдено в словаре")

        entry = self.words[result.word]
        updated = SRSScheduler.schedule(entry, result.quality, result.reviewed_at)
        self.words[result.word] = updated
        return updated

    def __len__(self) -> int:
        return len(self.words)

    def __repr__(self) -> str:
        return f"Vocabulary({len(self.words)} слов)"
