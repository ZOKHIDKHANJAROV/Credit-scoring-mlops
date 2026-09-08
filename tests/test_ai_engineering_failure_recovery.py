from pathlib import Path
from unittest.mock import Mock

import pytest

from ai_engineering.schemas.approvals import ApprovalDecision, ApprovalRequest, ApprovalStatus
from ai_engineering.schemas.audit import AuditEventType
from ai_engineering.services.reconciliation_service import ReconciliationService
from ai_engineering.storage.approval_store import ApprovalStore, InvalidApprovalTransition
from ai_engineering.tools.kubernetes_executor import KubernetesExecutionUnknown, KubernetesExecutor


def make_unknown(store: ApprovalStore) -> ApprovalRequest:
    request = store.create(ApprovalRequest(action="create_training_job", reason="test"))
    store.decide(ApprovalDecision(approval_id=request.approval_id, approved=True, decided_by="test"))
    store.mark_executing(request.approval_id)
    return store.mark_unknown(request.approval_id, {"unknown": True})


def test_unknown_is_not_reexecuted_implicitly() -> None:
    store = ApprovalStore()
    request = make_unknown(store)

    with pytest.raises(InvalidApprovalTransition):
        store.mark_executing(request.approval_id)


def test_unknown_can_be_reconciled_to_completed() -> None:
    store = ApprovalStore()
    request = make_unknown(store)
    executor = Mock()
    executor.get_training_job_status.return_value = {"exists": True, "status": "completed"}
    audit = Mock()

    result = ReconciliationService(store, executor, audit).reconcile(request.approval_id)

    assert result.status == ApprovalStatus.COMPLETED
    assert audit.record.call_args_list[0].args[0] == AuditEventType.EXECUTION_RECONCILIATION_STARTED
    assert audit.record.call_args_list[-1].args[0] == AuditEventType.EXECUTION_RECONCILIATION_COMPLETED


def test_unknown_job_absence_can_be_retried_once() -> None:
    store = ApprovalStore()
    request = make_unknown(store)
    executor = Mock()
    executor.get_training_job_status.return_value = {"exists": False, "status": "absent"}
    executor.apply_training_job.return_value = {"executed": True, "execution_id": request.approval_id}
    audit = Mock()

    result = ReconciliationService(store, executor, audit).retry_if_absent(request.approval_id)

    assert result.status == ApprovalStatus.COMPLETED
    executor.apply_training_job.assert_called_once_with(approved=True, execution_id=request.approval_id)
    assert any(call.args[0] == AuditEventType.EXECUTION_RETRY for call in audit.record.call_args_list)


def test_timeout_is_classified_as_unknown(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    manifest = tmp_path / "job.yaml"
    manifest.write_text("metadata:\n  name: credit-model-training\n", encoding="utf-8")

    def timeout(*args, **kwargs):
        raise __import__("subprocess").TimeoutExpired(cmd=args[0], timeout=120)

    monkeypatch.setattr("subprocess.run", timeout)
    executor = KubernetesExecutor(manifest_path=manifest)

    with pytest.raises(KubernetesExecutionUnknown):
        executor.apply_training_job(approved=True, execution_id="abc-123")


def test_execution_id_is_used_as_stable_job_name(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    manifest = tmp_path / "job.yaml"
    manifest.write_text("apiVersion: batch/v1\nmetadata:\n  name: credit-model-training\n", encoding="utf-8")
    completed = Mock(returncode=0, stdout="created", stderr="")
    captured = {}

    def run(command, **kwargs):
        captured["command"] = command
        captured["input"] = kwargs.get("input")
        return completed

    monkeypatch.setattr("subprocess.run", run)
    result = KubernetesExecutor(manifest_path=manifest).apply_training_job(True, "abc-123")

    assert result["executed"] is True
    assert "credit-training-abc-123" in captured["input"]
    assert captured["command"][:4] == ["kubectl", "apply", "-f", "-"]
