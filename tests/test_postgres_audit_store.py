from datetime import datetime, timedelta, timezone

from ai_engineering.schemas.audit import AuditEvent, AuditEventType
from ai_engineering.storage.audit_store import AuditEventRow, AuditStore


def make_event(trace_id: str = "trace-1", occurred_at: datetime | None = None) -> AuditEvent:
    return AuditEvent(
        event_type=AuditEventType.TOOL_RESULT,
        occurred_at=occurred_at or datetime.now(timezone.utc),
        trace_id=trace_id,
        tool_name="monitoring_get_retrain_signal",
        status="completed",
        payload={"retrain_required": True},
    )


def test_audit_store_can_use_sqlite_without_postgres() -> None:
    store = AuditStore("sqlite+pysqlite:///:memory:")
    event = make_event()

    store.append(event)

    events = store.list(trace_id="trace-1")
    assert len(events) == 1
    assert events[0].event_id == event.event_id
    assert events[0].payload["retrain_required"] is True
    assert store.count() == 1


def test_audit_store_returns_trace_events_in_chronological_order() -> None:
    store = AuditStore("sqlite+pysqlite:///:memory:")
    now = datetime.now(timezone.utc)
    first = make_event("trace-order", now)
    second = make_event("trace-order", now + timedelta(seconds=1))

    store.append(first)
    store.append(second)

    events = store.list(trace_id="trace-order")

    assert [event.event_id for event in events] == [first.event_id, second.event_id]


def test_audit_store_filters_event_type_and_limit() -> None:
    store = AuditStore("sqlite+pysqlite:///:memory:")
    store.append(make_event("trace-1"))
    store.append(
        AuditEvent(
            event_type=AuditEventType.EXECUTION_FAILED,
            occurred_at=datetime.now(timezone.utc),
            trace_id="trace-1",
            status="failed",
            error="test",
        )
    )

    events = store.list(event_type=AuditEventType.EXECUTION_FAILED, limit=1)

    assert len(events) == 1
    assert events[0].event_type == AuditEventType.EXECUTION_FAILED


def test_audit_event_row_round_trip() -> None:
    event = make_event()
    row = AuditEventRow(
        event_id=event.event_id,
        event_type=event.event_type.value,
        occurred_at=event.occurred_at,
        trace_id=event.trace_id,
        actor=event.actor,
        action=event.action,
        tool_name=event.tool_name,
        status=event.status,
        payload=event.payload,
        error=event.error,
    )

    restored = row.to_schema()
    assert restored.event_id == event.event_id
    assert restored.event_type == event.event_type
    assert restored.payload == event.payload
