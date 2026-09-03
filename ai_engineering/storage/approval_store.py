"""PostgreSQL-backed approval store with explicit state-transition guards."""

from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Integer, String, Text, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from ai_engineering.schemas.approvals import ApprovalDecision, ApprovalRequest, ApprovalStatus


class Base(DeclarativeBase):
    pass


class ApprovalRequestRow(Base):
    __tablename__ = "ai_engineering_approvals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    approval_id: Mapped[str] = mapped_column(String(36), unique=True, index=True)
    action: Mapped[str] = mapped_column(String(200), index=True)
    reason: Mapped[str] = mapped_column(Text)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    status: Mapped[str] = mapped_column(String(32), index=True)
    execution_plan: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    decided_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    decision_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    execution_result: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    def to_schema(self) -> ApprovalRequest:
        return ApprovalRequest(
            approval_id=self.approval_id,
            action=self.action,
            reason=self.reason,
            requested_at=self.requested_at,
            status=ApprovalStatus(self.status),
            execution_plan=self.execution_plan or {},
            decided_at=self.decided_at,
            decided_by=self.decided_by,
            decision_comment=self.decision_comment,
            execution_result=self.execution_result,
        )


class InvalidApprovalTransition(ValueError):
    """Raised when an approval attempts an illegal state transition."""


class ApprovalStore:
    """Persistent approval state machine backed by PostgreSQL."""

    _TRANSITIONS: dict[ApprovalStatus, frozenset[ApprovalStatus]] = {
        ApprovalStatus.PENDING: frozenset({ApprovalStatus.APPROVED, ApprovalStatus.REJECTED}),
        ApprovalStatus.APPROVED: frozenset({ApprovalStatus.EXECUTING}),
        ApprovalStatus.REJECTED: frozenset(),
        ApprovalStatus.EXECUTING: frozenset({ApprovalStatus.COMPLETED, ApprovalStatus.FAILED}),
        ApprovalStatus.COMPLETED: frozenset(),
        ApprovalStatus.FAILED: frozenset(),
    }

    def __init__(self, database_url: str | None = None, auto_create: bool = True) -> None:
        self.database_url = database_url or os.getenv(
            "AI_AUDIT_DATABASE_URL",
            os.getenv(
                "MONITORING_DATABASE_URL",
                "postgresql+pg8000://mlflow:mlflow@127.0.0.1:55432/mlflow",
            ),
        )
        self.engine = create_engine(self.database_url, pool_pre_ping=True)
        if auto_create:
            self.create_tables()

    def create_tables(self) -> None:
        Base.metadata.create_all(self.engine)

    def create(self, request: ApprovalRequest) -> ApprovalRequest:
        if request.status != ApprovalStatus.PENDING:
            raise InvalidApprovalTransition("New approvals must start in pending state")

        row = ApprovalRequestRow(
            approval_id=request.approval_id,
            action=request.action,
            reason=request.reason,
            requested_at=request.requested_at,
            status=request.status.value,
            execution_plan=json.loads(json.dumps(request.execution_plan, default=str)),
        )
        with Session(self.engine) as session:
            session.add(row)
            try:
                session.commit()
            except Exception:
                session.rollback()
                raise
        return request

    def get(self, approval_id: str) -> ApprovalRequest | None:
        with Session(self.engine) as session:
            row = session.scalar(
                select(ApprovalRequestRow).where(ApprovalRequestRow.approval_id == approval_id)
            )
            return row.to_schema() if row is not None else None

    def list_pending(self) -> list[ApprovalRequest]:
        with Session(self.engine) as session:
            rows = session.scalars(
                select(ApprovalRequestRow)
                .where(ApprovalRequestRow.status == ApprovalStatus.PENDING.value)
                .order_by(ApprovalRequestRow.requested_at.asc())
            ).all()
            return [row.to_schema() for row in rows]

    def _sync_request(self, request: ApprovalRequest, updated: ApprovalRequest) -> ApprovalRequest:
        request.status = updated.status
        request.decided_at = updated.decided_at
        request.decided_by = updated.decided_by
        request.decision_comment = updated.decision_comment
        request.execution_result = updated.execution_result
        return request

    def decide(self, decision: ApprovalDecision, request: ApprovalRequest | None = None) -> ApprovalRequest:
        with Session(self.engine) as session:
            row = self._get_locked(session, decision.approval_id)
            target = ApprovalStatus.APPROVED if decision.approved else ApprovalStatus.REJECTED
            self._transition(row, target)
            row.decided_at = decision.decided_at
            row.decided_by = decision.decided_by
            row.decision_comment = decision.comment
            session.commit()
            updated = row.to_schema()
        return self._sync_request(request, updated) if request is not None else updated

    def mark_executing(self, approval_id: str, request: ApprovalRequest | None = None) -> ApprovalRequest:
        with Session(self.engine) as session:
            row = self._get_locked(session, approval_id)
            self._transition(row, ApprovalStatus.EXECUTING)
            session.commit()
            updated = row.to_schema()
        return self._sync_request(request, updated) if request is not None else updated

    def mark_completed(
        self, approval_id: str, result: dict, request: ApprovalRequest | None = None
    ) -> ApprovalRequest:
        with Session(self.engine) as session:
            row = self._get_locked(session, approval_id)
            self._transition(row, ApprovalStatus.COMPLETED)
            row.execution_result = json.loads(json.dumps(result, default=str))
            session.commit()
            updated = row.to_schema()
        return self._sync_request(request, updated) if request is not None else updated

    def mark_failed(
        self, approval_id: str, result: dict, request: ApprovalRequest | None = None
    ) -> ApprovalRequest:
        with Session(self.engine) as session:
            row = self._get_locked(session, approval_id)
            self._transition(row, ApprovalStatus.FAILED)
            row.execution_result = json.loads(json.dumps(result, default=str))
            session.commit()
            updated = row.to_schema()
        return self._sync_request(request, updated) if request is not None else updated

    def _get_locked(self, session: Session, approval_id: str) -> ApprovalRequestRow:
        row = session.scalar(
            select(ApprovalRequestRow)
            .where(ApprovalRequestRow.approval_id == approval_id)
            .with_for_update()
        )
        if row is None:
            raise KeyError(f"Approval not found: {approval_id}")
        return row

    def _transition(self, row: ApprovalRequestRow, target: ApprovalStatus) -> None:
        current = ApprovalStatus(row.status)
        allowed = self._TRANSITIONS[current]
        if target not in allowed:
            raise InvalidApprovalTransition(
                f"Invalid approval transition: {current.value} -> {target.value}"
            )
        row.status = target.value
