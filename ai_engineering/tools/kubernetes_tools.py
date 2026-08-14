"""Controlled Kubernetes actions for the AI Engineering Command Center."""

from __future__ import annotations

from pathlib import Path
from typing import Any


class KubernetesTools:
    """Generate controlled training-job actions without executing them directly."""

    def __init__(self, manifest_path: str | Path = "k8s/jobs/model-training-job.yaml") -> None:
        self.manifest_path = Path(manifest_path)

    def get_training_job_plan(self) -> dict[str, Any]:
        """Return the training job plan that can be submitted after approval."""
        if not self.manifest_path.exists():
            return {
                "available": False,
                "action": "manual_review",
                "reason": f"Training manifest not found: {self.manifest_path}",
            }

        return {
            "available": True,
            "action": "create_training_job",
            "namespace": "ai-engineering",
            "job_name": "credit-model-training",
            "manifest_path": str(self.manifest_path),
            "requires_human_approval": True,
        }
