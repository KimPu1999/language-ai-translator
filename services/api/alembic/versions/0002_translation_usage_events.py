"""add non-sensitive translation usage events"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0002_translation_usage_events"
down_revision = "0001_phase1a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "translation_usage_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("request_id", sa.String(length=64), nullable=False),
        sa.Column("operation", sa.String(length=32), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("source_language", sa.String(length=32), nullable=True),
        sa.Column("target_language", sa.String(length=32), nullable=True),
        sa.Column("character_count", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column("error_code", sa.String(length=100), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index(
        "ix_translation_usage_events_created_at", "translation_usage_events", ["created_at"]
    )
    op.create_index(
        "ix_translation_usage_events_provider_created_at",
        "translation_usage_events",
        ["provider", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_translation_usage_events_provider_created_at", table_name="translation_usage_events"
    )
    op.drop_index("ix_translation_usage_events_created_at", table_name="translation_usage_events")
    op.drop_table("translation_usage_events")
