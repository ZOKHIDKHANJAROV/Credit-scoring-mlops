from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_ai_image_contains_migration_artifacts():
    dockerfile = (ROOT / "ai_engineering" / "Dockerfile").read_text()
    assert "COPY alembic.ini ./alembic.ini" in dockerfile
    assert "COPY migrations ./migrations" in dockerfile


def test_kubernetes_workloads_gate_startup_on_migrations():
    deployment = (ROOT / "k8s" / "agents" / "ai-agent-deployment.yaml").read_text()
    worker = (ROOT / "k8s" / "agents" / "ai-reconciliation-worker.yaml").read_text()

    for manifest in (deployment, worker):
        assert "initContainers:" in manifest
        assert "name: database-migration" in manifest
        assert "alembic" in manifest
        assert "upgrade" in manifest
        assert "head" in manifest
        assert "AI_AUDIT_DATABASE_URL" in manifest


def test_ai_image_workflow_rebuilds_for_migrations():
    workflow = (ROOT / ".github" / "workflows" / "ai-agent-image.yml").read_text()
    assert '"migrations/**"' in workflow
    assert '"alembic.ini"' in workflow
    assert "python -m compileall -q ai_engineering migrations" in workflow


def test_alembic_serializes_online_migrations():
    env = (ROOT / "migrations" / "env.py").read_text()
    assert "pg_advisory_lock" in env
    assert "pg_advisory_unlock" in env
    assert "MIGRATION_LOCK_KEY" in env
