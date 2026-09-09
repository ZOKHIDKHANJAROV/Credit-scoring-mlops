"""PostgreSQL-backed append-only audit event storage."""

from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Integer, String, Text, create_engine, func, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from ai_engineering.schemas.audit import AuditEvent, AuditEventType


class Base(DeclarativeBase):
    pass


class AuditEventRow(Base):
    __tablename__ = "ai_engineering_audit_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_id: Mapped[str] = mapped_column(String(36), unique=True, index=True)
    event_type: Mapped[str] = mapped_column(String(64), index=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    trace_id: Mapped[str] = mapped_column(String(36), index=True)
    actor: Mapped[str] = mapped_column(String(128), default="ai-engineering-agent")
    action: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    tool_name: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    status: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    def to_schema(self) -> AuditEvent:
        return AuditEvent(
            event_id=self.event_id,
            event_type=AuditEventType(self.event_type),
            occurred_at=self.occurred_at,
            trace_id=self.trace_id,
            actor=self.actor,
            action=self.action,
            tool_name=self.tool_name,
            status=self.status,
            payload=self.payload or {},
            error=self.error,
        )


class AuditStore:
    """Persistent audit store with the same contract used by AuditService."""

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

    def append(self, event: AuditEvent) -> AuditEvent:
        row = AuditEventRow(
            event_id=event.event_id,
            event_type=event.event_type.value,
            occurred_at=event.occurred_at,
            trace_id=event.trace_id,
            actor=event.actor,
            action=event.action,
            tool_name=event.tool_name,
            status=event.status,
            payload=json.loads(json.dumps(event.payload, default=str)),
            error=event.error,
        )
        with Session(self.engine) as session:
            session.add(row)
            session.commit()
        return event

    def list(
        self,
        *,
        trace_id: str | None = None,
        event_type: AuditEventType | None = None,
        limit: int | None = None,
    ) -> list[AuditEvent]:
        if limit is not None and (limit < 1 or limit > 1000):
            raise ValueError("limit must be between 1 and 1000")

        with Session(self.engine) as session:
            order = AuditEventRow.occurred_at.asc() if trace_id is not None else AuditEventRow.occurred_at.desc()
            statement = select(AuditEventRow).order_by(order, AuditEventRow.id.asc())
            if trace_id is not None:
                statement = statement.where(AuditEventRow.trace_id == trace_id)
            if event_type is not None:
                statement = statement.where(AuditEventRow.event_type == event_type.value)
            if limit is not None:
                statement = statement.limit(limit)
            rows = session.scalars(statement).all()
            return [row.to_schema() for row in rows]

    def count(self) -> int:
        with Session(self.engine) as session:
            return int(session.scalar(select(func.count()).select_from(AuditEventRow)) or 0)

    def clear(self) -> None:
        with Session(self.engine) as session:
            session.query(AuditEventRow).delete()
            session.commit()
