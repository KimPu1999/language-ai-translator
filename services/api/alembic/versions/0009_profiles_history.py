"""add profile, preference privacy, and history indexes"""

import sqlalchemy as sa

from alembic import op

revision = "0009_profiles_history"
down_revision = "0008_authentication"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("display_name", sa.String(length=100), nullable=True))
    op.add_column(
        "user_preferences",
        sa.Column("history_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_index(
        "ix_translations_user_languages_created_at",
        "translations",
        ["user_id", "source_language_code", "target_language_code", "created_at"],
    )
    op.create_index(
        "ix_favorites_user_created_at", "favorites", ["user_id", "created_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_favorites_user_created_at", table_name="favorites")
    op.drop_index("ix_translations_user_languages_created_at", table_name="translations")
    op.drop_column("user_preferences", "history_enabled")
    op.drop_column("users", "display_name")
