from types import SimpleNamespace

import pytest

from ai_engineering.workers.reconciliation_worker import ReconciliationWorker


class FakeStore:
    def __init__(self, approvals):
        self.approvals = approvals

    def list_reconcilable(self, limit=100):
        return self.approvals[:limit]


class FakeService:
    def __init__(self, failures=None):
        self.failures = set(failures or [])
        self.calls = []

    def reconcile(self, approval_id):
        self.calls.append(approval_id)
        if approval_id in self.failures:
            raise RuntimeError("boom")


class FakeLock:
    def __init__(self, acquired=True):
        self.acquired = acquired
        self.calls = 0

    def try_acquire(self):
        self.calls += 1
        return self.acquired


def approval(approval_id):
    return SimpleNamespace(approval_id=approval_id)


def test_run_once_reconciles_bounded_batch():
    store = FakeStore([approval("a"), approval("b"), approval("c")])
    service = FakeService()
    lock = FakeLock()
    worker = ReconciliationWorker(store, service, lock, batch_size=2)

    processed = worker.run_once()

    assert processed == 2
    assert service.calls == ["a", "b"]
    assert lock.calls == 1


def test_run_once_skips_when_another_worker_holds_lease():
    store = FakeStore([approval("a")])
    service = FakeService()
    lock = FakeLock(acquired=False)
    worker = ReconciliationWorker(store, service, lock)

    assert worker.run_once() == 0
    assert service.calls == []
    assert lock.calls == 1


def test_run_once_continues_after_item_failure():
    store = FakeStore([approval("a"), approval("b")])
    service = FakeService(failures={"a"})
    worker = ReconciliationWorker(store, service, FakeLock())

    assert worker.run_once() == 1
    assert service.calls == ["a", "b"]


def test_worker_rejects_invalid_configuration():
    with pytest.raises(ValueError):
        ReconciliationWorker(FakeStore([]), FakeService(), FakeLock(), interval_seconds=0)
    with pytest.raises(ValueError):
        ReconciliationWorker(FakeStore([]), FakeService(), FakeLock(), batch_size=0)
