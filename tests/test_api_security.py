from fastapi.testclient import TestClient

from ai_engineering.api import agent_service


def test_readiness_is_public():\n    client = TestClient(agent_service.app)\n    response = client.get("/ready")\n    assert response.status_code == 200\n    assert response.json()["status"] == "ready"\n\n\ndef test_health_is_public(monkeypatch):
    monkeypatch.setenv("AI_ENGINEERING_API_TOKEN", "secret-token")
    client = TestClient(agent_service.app)
    response = client.get("/health")
    assert response.status_code == 200


def test_protected_endpoint_rejects_missing_token(monkeypatch):
    monkeypatch.setenv("AI_ENGINEERING_API_TOKEN", "secret-token")
    client = TestClient(agent_service.app)
    response = client.get("/api/v1/agent/tools")
    assert response.status_code == 401


def test_protected_endpoint_accepts_valid_bearer_token(monkeypatch):
    monkeypatch.setenv("AI_ENGINEERING_API_TOKEN", "secret-token")
    client = TestClient(agent_service.app)
    response = client.get("/api/v1/agent/tools", headers={"Authorization": "Bearer secret-token"})
    assert response.status_code == 200


def test_invalid_token_is_rejected(monkeypatch):
    monkeypatch.setenv("AI_ENGINEERING_API_TOKEN", "secret-token")
    client = TestClient(agent_service.app)
    response = client.get("/api/v1/agent/tools", headers={"Authorization": "Bearer wrong-token"})
    assert response.status_code == 401
