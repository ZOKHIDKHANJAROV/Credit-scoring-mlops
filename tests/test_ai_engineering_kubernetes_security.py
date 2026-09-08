from pathlib import Path
from unittest.mock import Mock

import pytest

from ai_engineering.tools.kubernetes_executor import KubernetesExecutor


@pytest.fixture
def manifest(tmp_path: Path) -> Path:
    path = tmp_path / "job.yaml"
    path.write_text(
        "apiVersion: batch/v1\n"
        "kind: Job\n"
        "metadata:\n"
        "  name: credit-model-training\n",
        encoding="utf-8",
    )
    return path


def test_approved_execution_requires_stable_execution_id(manifest: Path) -> None:
    executor = KubernetesExecutor(manifest_path=manifest)

    with pytest.raises(ValueError, match="execution_id is required"):
        executor.apply_training_job(approved=True)


def test_malicious_execution_id_is_rejected_before_kubectl(manifest: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    called = Mock()
    monkeypatch.setattr("subprocess.run", called)
    executor = KubernetesExecutor(manifest_path=manifest)

    with pytest.raises(ValueError, match="DNS-1123-safe"):
        executor.apply_training_job(approved=True, execution_id="../../prod-job")

    called.assert_not_called()


def test_namespace_override_is_rejected(manifest: Path) -> None:
    executor = KubernetesExecutor(manifest_path=manifest, namespace="default")

    with pytest.raises(PermissionError, match="ai-engineering namespace"):
        executor.apply_training_job(approved=True, execution_id="abc-123")


def test_executor_uses_fixed_namespace_and_stable_job_name(manifest: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    completed = Mock(returncode=0, stdout="created", stderr="")
    captured = {}

    def run(command, **kwargs):
        captured["command"] = command
        captured["input"] = kwargs["input"]
        return completed

    monkeypatch.setattr("subprocess.run", run)
    result = KubernetesExecutor(manifest_path=manifest).apply_training_job(
        approved=True,
        execution_id="abc-123",
    )

    assert result["namespace"] == "ai-engineering"
    assert result["job_name"] == "credit-training-abc-123"
    assert captured["command"] == ["kubectl", "apply", "-f", "-", "--namespace", "ai-engineering"]
    assert "name: credit-training-abc-123" in captured["input"]


def test_execution_plan_cannot_change_executor_command(manifest: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    completed = Mock(returncode=0, stdout="created", stderr="")
    captured = {}

    def run(command, **kwargs):
        captured["command"] = command
        captured["input"] = kwargs["input"]
        return completed

    monkeypatch.setattr("subprocess.run", run)
    executor = KubernetesExecutor(manifest_path=manifest)
    untrusted_plan = {
        "namespace": "kube-system",
        "job_name": "arbitrary-job",
        "kubectl": "delete namespace ai-engineering",
        "manifest": "kind: Pod\nmetadata:\n  name: attacker",
    }

    executor.apply_training_job(approved=True, execution_id="abc-123")

    assert captured["command"] == ["kubectl", "apply", "-f", "-", "--namespace", "ai-engineering"]
    assert "kube-system" not in captured["input"]
    assert "arbitrary-job" not in captured["input"]
    assert untrusted_plan["kubectl"] not in " ".join(captured["command"])


def test_read_only_status_rejects_arbitrary_job_name(manifest: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    called = Mock()
    monkeypatch.setattr("subprocess.run", called)
    executor = KubernetesExecutor(manifest_path=manifest)

    with pytest.raises(ValueError, match="credit-training Job"):
        executor.get_training_job_status("kube-system-job")

    called.assert_not_called()
