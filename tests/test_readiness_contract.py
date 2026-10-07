from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_readiness_endpoint_is_migration_aware():
    service = (ROOT / "ai_engineering" / "api" / "agent_service.py").read_text()

    assert 'def database_is_ready()' in service
    assert 'SELECT 1' in service
    assert 'SELECT version_num FROM alembic_version' in service
    assert 'def ready()' in service
    assert 'if not database_is_ready()' in service
    assert 'raise HTTPException(status_code=503' in service


def test_kubernetes_uses_readiness_for_routing_and_health_for_liveness():
    deployment = (ROOT / "k8s" / "agents" / "ai-agent-deployment.yaml").read_text()

    readiness_block = deployment.split("readinessProbe:", 1)[1].split("livenessProbe:", 1)[0]
    liveness_block = deployment.split("livenessProbe:", 1)[1].split("resources:", 1)[0]

    assert 'path: /ready' in readiness_block
    assert 'path: /health' in liveness_block


def test_readiness_does_not_run_migrations():
    service = (ROOT / "ai_engineering" / "api" / "agent_service.py").read_text()
    ready_block = service.split('@app.get("/ready")', 1)[1].split('@app.get("/metrics")', 1)[0]

    assert 'alembic upgrade' not in ready_block
    assert 'CREATE TABLE' not in ready_block
