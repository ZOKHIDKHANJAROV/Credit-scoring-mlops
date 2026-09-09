"""Persist correlation trace IDs on approval workflows.

Revision ID: 20260909_0002
Revises: 20260819_0001
"""

from alembic import op
import sqlalchemy as sa

revision = "20260909_0002"
down_revision = "20260819_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "ai_engineering_approvals",
        sa.Column("trace_id", sa.String(length=36), nullable=True),
    )
    op.execute(
        "UPDATE ai_engineering_approvals SET trace_id = approval_id WHERE trace_id IS NULL"
    )
    op.alter_column("ai_engineering_approvals", "trace_id", nullable=False)
    op.create_index(
        "ix_ai_engineering_approvals_trace_id",
        "ai_engineering_approvals",
        ["trace_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_ai_engineering_approvals_trace_id",
        table_name="ai_engineering_approvals",
    )
    op.drop_column("ai_engineering_approvals", "trace_id")
