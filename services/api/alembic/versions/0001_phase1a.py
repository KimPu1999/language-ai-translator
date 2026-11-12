"""phase 1a core schema and language seed"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0001_phase1a"
down_revision = None
branch_labels = None
depends_on = None
LANGUAGES = [
    ("en", "English"),
    ("my", "Burmese"),
    ("th", "Thai"),
    ("zh-Hans", "Simplified Chinese"),
    ("ja", "Japanese"),
    ("ko", "Korean"),
]


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_table(
        "languages",
        sa.Column("code", sa.String(32), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("is_source_enabled", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("is_target_enabled", sa.Boolean(), server_default=sa.true(), nullable=False),
    )
    op.create_table(
        "translations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "source_language_code", sa.String(32), sa.ForeignKey("languages.code"), nullable=False
        ),
        sa.Column(
            "target_language_code", sa.String(32), sa.ForeignKey("languages.code"), nullable=False
        ),
        sa.Column("source_text", sa.Text(), nullable=False),
        sa.Column("translated_text", sa.Text(), nullable=False),
        sa.Column("provider", sa.String(64), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_translations_user_created_at", "translations", ["user_id", "created_at"])
    op.create_table(
        "favorites",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "translation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("translations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("user_id", "translation_id", name="uq_favorites_user_translation"),
    )
    op.create_index("ix_favorites_user_id", "favorites", ["user_id"])
    values = ", ".join(f"('{code}', '{name}', TRUE, TRUE)" for code, name in LANGUAGES)
    op.execute(
        "INSERT INTO languages (code, name, is_source_enabled, is_target_enabled) "
        f"VALUES {values} ON CONFLICT (code) DO NOTHING"
    )


def downgrade() -> None:
    op.drop_index("ix_favorites_user_id", table_name="favorites")
    op.drop_table("favorites")
    op.drop_index("ix_translations_user_created_at", table_name="translations")
    op.drop_table("translations")
    op.drop_table("languages")
    op.drop_table("users")
