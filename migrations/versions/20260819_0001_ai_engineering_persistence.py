"""Create AI Engineering approval and audit tables.

Revision ID: 20260819_0001
Revises:
"""

from alembic import op
import sqlalchemy as sa

revision = "20260819_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ai_engineering_approvals",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("approval_id", sa.String(length=36), nullable=False),
        sa.Column("action", sa.String(length=200), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("execution_plan", sa.JSON(), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("decided_by", sa.String(length=128), nullable=True),
        sa.Column("decision_comment", sa.Text(), nullable=True),
        sa.Column("execution_result", sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("approval_id"),
    )
    op.create_index("ix_ai_engineering_approvals_approval_id", "ai_engineering_approvals", ["approval_id"])
    op.create_index("ix_ai_engineering_approvals_action", "ai_engineering_approvals", ["action"])
    op.create_index("ix_ai_engineering_approvals_requested_at", "ai_engineering_approvals", ["requested_at"])
    op.create_index("ix_ai_engineering_approvals_status", "ai_engineering_approvals", ["status"])

    op.create_table(
        "ai_engineering_audit_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("event_id", sa.String(length=36), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("trace_id", sa.String(length=36), nullable=False),
        sa.Column("actor", sa.String(length=128), nullable=False),
        sa.Column("action", sa.String(length=128), nullable=True),
        sa.Column("tool_name", sa.String(length=128), nullable=True),
        sa.Column("status", sa.String(length=64), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_id"),
    )
    for name, column in (
        ("event_id", "event_id"),
        ("event_type", "event_type"),
        ("occurred_at", "occurred_at"),
        ("trace_id", "trace_id"),
        ("action", "action"),
        ("tool_name", "tool_name"),
        ("status", "status"),
    ):
        op.create_index(f"ix_ai_engineering_audit_events_{name}", "ai_engineering_audit_events", [column])


def downgrade() -> None:
    for name in (
        "event_id", "event_type", "occurred_at", "trace_id", "action", "tool_name", "status"
    ):
        op.drop_index(f"ix_ai_engineering_audit_events_{name}", table_name="ai_engineering_audit_events")
    op.drop_table("ai_engineering_audit_events")

    for name in ("approval_id", "action", "requested_at", "status"):
        op.drop_index(f"ix_ai_engineering_approvals_{name}", table_name="ai_engineering_approvals")
    op.drop_table("ai_engineering_approvals")
