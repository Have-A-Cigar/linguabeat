"""Initial schema: users, tracks, user_words (FSRS-5 v6), srs_reviews, listening_sessions.

Revision ID: 0001
Revises:
Create Date: 2026-06-07
"""
from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("email", sa.String, nullable=False),
        sa.Column("hashed_password", sa.String, nullable=False),
        sa.Column("language_level", sa.String, nullable=False, server_default="A1"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "tracks",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("title", sa.String, nullable=False),
        sa.Column("artist", sa.String, nullable=False),
        sa.Column("duration_sec", sa.Integer, nullable=False),
        sa.Column("genre", sa.String, nullable=True),
        sa.Column("lyrics_json", sa.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )

    op.create_table(
        "user_words",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("user_id", sa.String, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("track_id", sa.String, sa.ForeignKey("tracks.id"), nullable=False),
        sa.Column("word", sa.String, nullable=False),
        sa.Column("translation", sa.String, nullable=True),
        sa.Column("subtitle_text", sa.String, nullable=True),
        sa.Column("timecode_sec", sa.Float, nullable=True),
        # FSRS-5 state columns (fsrs v6)
        sa.Column("stability", sa.Float, nullable=True),
        sa.Column("difficulty", sa.Float, nullable=True),
        sa.Column("step", sa.Integer, nullable=True, server_default="0"),
        sa.Column("reps", sa.Integer, nullable=False, server_default="0"),
        sa.Column("lapses", sa.Integer, nullable=False, server_default="0"),
        sa.Column("state", sa.String, nullable=False, server_default="Learning"),
        sa.Column("due", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("last_review", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )
    op.create_index("ix_user_words_user_id", "user_words", ["user_id"])
    op.create_index("ix_user_words_due", "user_words", ["due"])

    op.create_table(
        "srs_reviews",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("user_word_id", sa.String, sa.ForeignKey("user_words.id"), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("quality", sa.Integer, nullable=False),
        sa.Column("rating", sa.String, nullable=False),
        sa.Column("new_stability", sa.Float, nullable=False),
        sa.Column("new_scheduled_days", sa.Integer, nullable=False),
    )
    op.create_index("ix_srs_reviews_user_word_id", "srs_reviews", ["user_word_id"])

    op.create_table(
        "listening_sessions",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("user_id", sa.String, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("track_id", sa.String, sa.ForeignKey("tracks.id"), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("duration_sec", sa.Integer, nullable=True),
    )


def downgrade() -> None:
    op.drop_table("listening_sessions")
    op.drop_table("srs_reviews")
    op.drop_table("user_words")
    op.drop_table("tracks")
    op.drop_table("users")
