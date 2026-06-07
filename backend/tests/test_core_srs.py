"""Smoke-тесты для FSRS-5 ядра LinguaBeat (fsrs v6)."""
import pytest
from datetime import datetime, timezone
from app.domain.core_srs import SRSScheduler, WordEntry, WordContext, Vocabulary, ReviewResult


def make_entry(
    word: str = "берёза",
    reps: int = 0,
    state: str = "Learning",
    stability: float | None = None,
    lapses: int = 0,
    step: int | None = 0,
) -> WordEntry:
    return WordEntry(
        word=word,
        translation="birch tree",
        context=WordContext(track_id="track-1", subtitle_text="В лесу берёза", timecode_sec=12.0),
        added_at=datetime.now(timezone.utc),
        reps=reps,
        state=state,
        stability=stability,
        lapses=lapses,
        step=step,
    )


def test_schedule_easy_new_card():
    entry = make_entry(reps=0, state="Learning", stability=None, step=0)
    updated = SRSScheduler.schedule(entry, quality=5)
    assert updated.reps == 1
    assert updated.stability is not None
    assert updated.stability > 0


def test_schedule_good_increases_reps():
    entry = make_entry(reps=0, state="Learning")
    updated = SRSScheduler.schedule(entry, quality=4)
    assert updated.reps == 1
    assert updated.lapses == 0


def make_review_entry(stability: float = 10.0, difficulty: float = 5.0, reps: int = 3) -> WordEntry:
    """Вспомогательная фабрика для карточки в состоянии Review (требует оба поля)."""
    e = make_entry(reps=reps, state="Review", stability=stability, step=None)
    # difficulty — обязательное поле для Review-state в FSRS
    from dataclasses import replace as dc_replace
    return dc_replace(e, difficulty=difficulty)


def test_schedule_again_increases_lapses():
    entry = make_review_entry()
    updated = SRSScheduler.schedule(entry, quality=0)
    assert updated.lapses == 1
    assert updated.state in ("Learning", "Relearning")


def test_schedule_easy_review_improves_stability():
    entry = make_review_entry(stability=10.0)
    updated = SRSScheduler.schedule(entry, quality=5)
    assert updated.stability is not None
    assert updated.stability > entry.stability


def test_invalid_quality_raises():
    entry = make_entry()
    with pytest.raises(ValueError):
        SRSScheduler.schedule(entry, quality=6)
    with pytest.raises(ValueError):
        SRSScheduler.schedule(entry, quality=-1)


def test_get_context_card_fields():
    entry = make_entry()
    card = SRSScheduler.get_context_card(entry)
    assert card["word"] == "берёза"
    assert card["context_subtitle"] == "В лесу берёза"
    assert card["context_timecode_sec"] == 12.0
    assert "due" in card
    assert "stability" in card
    assert "lapses" in card
    assert "state" in card


def test_vocabulary_new_word_immediately_due():
    vocab = Vocabulary()
    ctx = WordContext(track_id="t1", subtitle_text="Катюша", timecode_sec=5.0)
    vocab.add_word("катюша", "Katyusha", ctx)
    assert len(vocab) == 1
    due = vocab.get_due_words()
    assert len(due) == 1  # новая карточка сразу к показу


def test_vocabulary_no_duplicate():
    vocab = Vocabulary()
    ctx = WordContext(track_id="t1", subtitle_text="text", timecode_sec=1.0)
    e1 = vocab.add_word("слово", "word", ctx)
    e2 = vocab.add_word("слово", "word2", ctx)
    assert e1 is e2
    assert len(vocab) == 1


def test_invalid_state_raises():
    with pytest.raises(ValueError):
        WordEntry(
            word="тест",
            translation="test",
            context=WordContext(track_id="t", subtitle_text="s", timecode_sec=0),
            added_at=datetime.now(timezone.utc),
            state="New",  # не существует в v6
        )


def test_schedule_preserves_immutability():
    entry = make_entry()
    original_reps = entry.reps
    SRSScheduler.schedule(entry, quality=5)
    assert entry.reps == original_reps  # исходный объект не изменился
