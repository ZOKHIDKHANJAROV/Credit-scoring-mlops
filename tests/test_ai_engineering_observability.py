from fastapi.testclient import TestClient

from ai_engineering.api import agent_service
from ai_engineering.observability import (
    AGENT_RUNS_TOTAL,
    EXECUTION_UNKNOWN_TOTAL,
    metrics_response,
)


def test_metrics_payload_contains_command_center_metrics():
    AGENT_RUNS_TOTAL.labels(status="completed").inc()
    EXECUTION_UNKNOWN_TOTAL.labels(action="create_training_job").inc()

    payload, content_type = metrics_response()
    text = payload.decode("utf-8")

    assert content_type.startswith("text/plain")
    assert "agent_runs_total" in text
    assert "agent_run_duration_seconds" in text
    assert "agent_tool_calls_total" in text
    assert "agent_tool_duration_seconds" in text
    assert "approval_requests_total" in text
    assert "execution_total" in text
    assert "execution_duration_seconds" in text
    assert "execution_unknown_total" in text
    assert "execution_retry_total" in text


def test_metrics_endpoint_is_available_for_scraping(monkeypatch):
    monkeypatch.setenv("AI_ENGINEERING_API_TOKEN", "secret-token")
    client = TestClient(agent_service.app)

    response = client.get("/metrics")

    assert response.status_code == 200
    assert "agent_runs_total" in response.text
