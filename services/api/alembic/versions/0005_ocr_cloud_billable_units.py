"""track provider billable OCR units"""

import sqlalchemy as sa

from alembic import op

revision = "0005_ocr_cloud_billable_units"
down_revision = "0004_ocr_usage_events"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "ocr_usage_events",
        sa.Column("billable_units", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("ocr_usage_events", "billable_units")
