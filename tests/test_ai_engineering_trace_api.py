from fastapi.testclient import TestClient

from ai_engineering.api.agent_service import app, approval_store, audit_store


client = TestClient(app)


def test_audit_stats_starts_empty() -> None:
    audit_store.clear()
    response = client.get("/api/v1/audit/stats")
    assert response.status_code == 200
    payload = response.json()
    assert payload["event_count"] == 0
    assert payload["event_counts"]["approval_requested"] == 0


def test_create_approval_creates_traceable_audit_event() -> None:
    audit_store.clear()
    approval_store.clear()

    response = client.post(
        "/api/v1/approvals",
        json={
            "action": "create_training_job",
            "reason": "Retraining signal is active",
            "execution_plan": {"job_name": "credit-model-training"},
        },
    )

    assert response.status_code == 201
    approval = response.json()
    approval_id = approval["approval_id"]

    events = client.get(f"/api/v1/audit/traces/{approval_id}")
    assert events.status_code == 200
    payload = events.json()
    assert len(payload) == 1
    assert payload[0]["event_type"] == "approval_requested"
    assert payload[0]["trace_id"] == approval_id


def test_audit_event_filter_and_limit() -> None:
    audit_store.clear()
    approval_store.clear()

    client.post(
        "/api/v1/approvals",
        json={
            "action": "create_training_job",
            "reason": "test",
        },
    )
    client.post(
        "/api/v1/approvals",
        json={
            "action": "create_training_job",
            "reason": "test-2",
        },
    )

    response = client.get(
        "/api/v1/audit/events",
        params={"event_type": "approval_requested", "limit": 1},
    )
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_command_center_overview_returns_read_only_snapshot() -> None:
    audit_store.clear()
    approval_store.clear()

    create_response = client.post(
        "/api/v1/approvals",
        json={
            "action": "create_training_job",
            "reason": "retraining signal",
            "execution_plan": {"model": "CreditScoringCatBoost"},
        },
    )
    assert create_response.status_code == 201

    response = client.get(
        "/api/v1/command-center/overview",
        params={"approval_limit": 10, "audit_limit": 10},
    )
    assert response.status_code == 200
    payload = response.json()

    assert payload["approval_counts"]["pending"] == 1
    assert payload["approval_counts"]["completed"] == 0
    assert payload["audit_event_counts"]["approval_requested"] == 1
    assert len(payload["pending_approvals"]) == 1
    assert len(payload["recent_approvals"]) == 1
    assert len(payload["recent_audit_events"]) == 1
    assert payload["reconcilable_approvals"] == []
