"""Periodic reconciliation worker for uncertain AI execution state."""

from __future__ import annotations

import logging
import os
import time
from typing import Callable

from sqlalchemy import text

from ai_engineering.observability import RECONCILIATION_RUNS_TOTAL
from ai_engineering.services.reconciliation_service import ReconciliationService
from ai_engineering.storage.approval_store import ApprovalStore
from ai_engineering.tools.kubernetes_executor import KubernetesExecutor

LOGGER = logging.getLogger(__name__)

DEFAULT_INTERVAL_SECONDS = 30
DEFAULT_BATCH_SIZE = 100
ADVISORY_LOCK_KEY = 918273645


class PostgresAdvisoryLock:
    """Session-level PostgreSQL advisory lock used for single-cycle ownership."""

    def __init__(self, engine, key: int = ADVISORY_LOCK_KEY) -> None:
        self.engine = engine
        self.key = key
        self._connection = None

    def try_acquire(self) -> bool:
        if self._connection is not None:
            return True
        connection = self.engine.connect()
        acquired = bool(
            connection.execute(
                text("SELECT pg_try_advisory_lock(:key)"), {"key": self.key}
            ).scalar()
        )
        if acquired:
            self._connection = connection
            return True
        connection.close()
        return False

    def release(self) -> None:
        if self._connection is None:
            return
        try:
            self._connection.execute(
                text("SELECT pg_advisory_unlock(:key)"), {"key": self.key}
            )
        finally:
            self._connection.close()
            self._connection = None


class ReconciliationWorker:
    """Run reconciliation periodically while ensuring only one worker is active."""

    def __init__(
        self,
        store: ApprovalStore,
        service: ReconciliationService,
        lock: PostgresAdvisoryLock,
        interval_seconds: int = DEFAULT_INTERVAL_SECONDS,
        batch_size: int = DEFAULT_BATCH_SIZE,
        sleep_fn: Callable[[float], None] = time.sleep,
    ) -> None:
        if interval_seconds < 1:
            raise ValueError("interval_seconds must be positive")
        if batch_size < 1:
            raise ValueError("batch_size must be positive")
        self.store = store
        self.service = service
        self.lock = lock
        self.interval_seconds = interval_seconds
        self.batch_size = batch_size
        self.sleep_fn = sleep_fn

    def run_once(self) -> int:
        """Reconcile one bounded batch if this instance owns the control-loop lease."""
        if not self.lock.try_acquire():
            LOGGER.info("reconciliation lease is owned by another worker")
            return 0

        processed = 0
        RECONCILIATION_RUNS_TOTAL.labels(status="started").inc()
        try:
            approvals = self.store.list_reconcilable(limit=self.batch_size)
            for approval in approvals:
                try:
                    self.service.reconcile(approval.approval_id)
                    processed += 1
                except Exception:
                    LOGGER.exception(
                        "reconciliation failed for approval %s", approval.approval_id
                    )
                    RECONCILIATION_RUNS_TOTAL.labels(status="item_failed").inc()
            RECONCILIATION_RUNS_TOTAL.labels(status="completed").inc()
            return processed
        except Exception:
            RECONCILIATION_RUNS_TOTAL.labels(status="failed").inc()
            raise
        finally:
            self.lock.release()

    def run_forever(self) -> None:
        """Run the reconciliation loop until the process receives a shutdown signal."""
        while True:
            try:
                self.run_once()
            except Exception:
                LOGGER.exception("reconciliation cycle failed")
            self.sleep_fn(self.interval_seconds)


def build_worker() -> ReconciliationWorker:
    interval_seconds = int(
        os.getenv("AI_RECONCILIATION_INTERVAL_SECONDS", str(DEFAULT_INTERVAL_SECONDS))
    )
    batch_size = int(os.getenv("AI_RECONCILIATION_BATCH_SIZE", str(DEFAULT_BATCH_SIZE)))
    store = ApprovalStore()
    service = ReconciliationService(store, KubernetesExecutor(), _build_audit_service())
    return ReconciliationWorker(
        store=store,
        service=service,
        lock=PostgresAdvisoryLock(store.engine),
        interval_seconds=interval_seconds,
        batch_size=batch_size,
    )


def _build_audit_service():
    """Build the same PostgreSQL audit backend used by the API."""
    from ai_engineering.services.audit_service import AuditService
    from ai_engineering.storage.audit_store import AuditStore

    return AuditService(AuditStore())


if __name__ == "__main__":
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
    build_worker().run_forever()
