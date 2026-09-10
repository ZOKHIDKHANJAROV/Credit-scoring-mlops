"""Persist execution lease start timestamps for stale recovery.

Revision ID: 20260910_0003
Revises: 20260909_0002
"""

from alembic import op
import sqlalchemy as sa

revision = "20260910_0003"
down_revision = "20260909_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "ai_engineering_approvals",
        sa.Column("execution_started_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("ai_engineering_approvals", "execution_started_at")
