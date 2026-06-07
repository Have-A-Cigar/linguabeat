"""Add audio_url to tracks table.

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-07
"""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("tracks", sa.Column("audio_url", sa.String, nullable=True))


def downgrade() -> None:
    op.drop_column("tracks", "audio_url")
