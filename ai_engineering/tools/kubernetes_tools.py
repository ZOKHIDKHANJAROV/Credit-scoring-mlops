"""Controlled Kubernetes planning tools for the AI Engineering Command Center."""

from __future__ import annotations

from pathlib import Path
from typing import Any


class KubernetesTools:
    """Generate safe, approval-gated training-job plans without executing Kubernetes."""

    def __init__(
        self,
        manifest_path: str | Path = "k8s/jobs/model-training-job.yaml",
        namespace: str = "ai-engineering",
        job_name: str = "credit-model-training",
    ) -> None:
        self.manifest_path = Path(manifest_path)
        self.namespace = namespace
        self.job_name = job_name

    def build_training_job_plan(
        self,
        reason: str = "Retraining requested by the monitoring workflow",
        drifted_features: list[str] | None = None,
    ) -> dict[str, Any]:
        """Return a training-job plan; never execute ``kubectl`` from this tool."""
        if not self.manifest_path.exists():
            return {
                "available": False,
                "action": "manual_review",
                "reason": f"Training manifest not found: {self.manifest_path}",
                "requires_human_approval": True,
            }

        return {
            "available": True,
            "action": "create_training_job",
            "namespace": self.namespace,
            "job_name": self.job_name,
            "manifest_path": str(self.manifest_path),
            "reason": reason,
            "drifted_features": list(drifted_features or []),
            "requires_human_approval": True,
            "execution": "approval_gated",
        }

    def get_training_job_plan(self) -> dict[str, Any]:
        """Backward-compatible wrapper for callers that only need a basic plan."""
        return self.build_training_job_plan()
