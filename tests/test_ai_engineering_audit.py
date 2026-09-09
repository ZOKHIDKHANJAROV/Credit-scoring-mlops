from ai_engineering.schemas.audit import AuditEventType
from ai_engineering.services.audit_service import AuditService
from ai_engineering.services.execution_trace import ExecutionTrace
from ai_engineering.storage.audit_store import AuditStore


def test_audit_store_filters_events_by_trace() -> None:
    store = AuditStore()
    audit = AuditService(store)
    trace_a = audit.new_trace_id()
    trace_b = audit.new_trace_id()

    audit.record(AuditEventType.AGENT_REQUESTED, trace_a, payload={"task": "a"})
    audit.record(AuditEventType.TOOL_CALLED, trace_b, tool_name="tool")

    events = store.list(trace_id=trace_a)
    assert len(events) == 1
    assert events[0].trace_id == trace_a
    assert events[0].event_type == AuditEventType.AGENT_REQUESTED


def test_execution_trace_records_tool_and_completion() -> None:
    audit = AuditService()
    trace = ExecutionTrace(audit=audit)

    trace.request("inspect model drift")
    trace.tool_call("monitoring_get_retrain_signal", {})
    trace.tool_result("monitoring_get_retrain_signal", {"retrain_required": True})
    trace.execution_started("create_training_job")
    trace.execution_completed("create_training_job", {"executed": True})

    events = trace.events()
    assert [event.event_type for event in events] == [
        AuditEventType.AGENT_REQUESTED,
        AuditEventType.TOOL_CALLED,
        AuditEventType.TOOL_RESULT,
        AuditEventType.EXECUTION_STARTED,
        AuditEventType.EXECUTION_COMPLETED,
    ]
    assert events[-1].status == "completed"


def test_closed_trace_rejects_new_events() -> None:
    trace = ExecutionTrace()
    trace.execution_completed("create_training_job", {"executed": True})

    try:
        trace.request("should fail")
    except RuntimeError as exc:
        assert "already closed" in str(exc)
    else:
        raise AssertionError("Closed execution trace accepted a new event")


def test_execution_failure_is_terminal() -> None:
    trace = ExecutionTrace()
    trace.execution_failed("create_training_job", "kubectl failed")

    event = trace.events()[0]
    assert event.event_type == AuditEventType.EXECUTION_FAILED
    assert event.status == "failed"
    assert event.error == "kubectl failed"
