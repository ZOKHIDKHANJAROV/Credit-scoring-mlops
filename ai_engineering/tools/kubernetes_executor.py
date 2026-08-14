"""Approval-gated Kubernetes execution for training jobs."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any


class KubernetesExecutor:
    """Execute only the allowlisted training Job manifest after approval."""

    def __init__(
        self,
        manifest_path: str | Path = "k8s/jobs/model-training-job.yaml",
        namespace: str = "ai-engineering",
    ) -> None:
        self.manifest_path = Path(manifest_path)
        self.namespace = namespace

    def apply_training_job(self, approved: bool) -> dict[str, Any]:
        """Create the training Job only when an approval has been granted."""
        if not approved:
            return {
                "executed": False,
                "action": "create_training_job",
                "reason": "Human approval is required",
            }

        if not self.manifest_path.exists():
            raise FileNotFoundError(f"Training manifest not found: {self.manifest_path}")

        command = [
            "kubectl",
            "apply",
            "-f",
            str(self.manifest_path),
            "--namespace",
            self.namespace,
        ]

        try:
            completed = subprocess.run(
                command,
                check=True,
                capture_output=True,
                text=True,
                timeout=120,
            )
        except FileNotFoundError as exc:
            return {
                "executed": False,
                "action": "create_training_job",
                "reason": "kubectl is not installed or not available on PATH",
                "error": str(exc),
            }
        except subprocess.CalledProcessError as exc:
            return {
                "executed": False,
                "action": "create_training_job",
                "reason": "kubectl command failed",
                "stdout": exc.stdout,
                "stderr": exc.stderr,
            }

        return {
            "executed": True,
            "action": "create_training_job",
            "namespace": self.namespace,
            "manifest_path": str(self.manifest_path),
            "stdout": completed.stdout.strip(),
        }
