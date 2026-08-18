"""Approval-gated Kubernetes execution and status inspection."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any


class KubernetesExecutor:
    """Execute only approved training jobs and inspect their Kubernetes status."""

    def __init__(
        self,
        manifest_path: str | Path = "k8s/jobs/model-training-job.yaml",
        namespace: str = "ai-engineering",
    ) -> None:
        self.manifest_path = Path(manifest_path)
        self.namespace = namespace

    def apply_training_job(self, approved: bool) -> dict[str, Any]:
        if not approved:
            return {
                "executed": False,
                "action": "create_training_job",
                "reason": "Human approval is required",
            }

        if not self.manifest_path.exists():
            raise FileNotFoundError(f"Training manifest not found: {self.manifest_path}")

        command = [
            "kubectl", "apply", "-f", str(self.manifest_path),
            "--namespace", self.namespace,
        ]
        try:
            completed = subprocess.run(
                command, check=True, capture_output=True, text=True, timeout=120
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

    def get_training_job_status(self, job_name: str) -> dict[str, Any]:
        """Read a Job status without modifying Kubernetes state."""
        command = [
            "kubectl", "get", "job", job_name,
            "--namespace", self.namespace,
            "-o", "json",
        ]
        try:
            completed = subprocess.run(
                command, check=True, capture_output=True, text=True, timeout=30
            )
        except FileNotFoundError as exc:
            return {
                "lifecycle": "failed",
                "reason": "kubectl is not installed or not available on PATH",
                "error": str(exc),
            }
        except subprocess.CalledProcessError as exc:
            return {
                "lifecycle": "failed",
                "reason": "Unable to read Kubernetes Job status",
                "stdout": exc.stdout,
                "stderr": exc.stderr,
            }

        import json

        payload = json.loads(completed.stdout)
        status = payload.get("status", {})
        succeeded = int(status.get("succeeded", 0) or 0)
        failed = int(status.get("failed", 0) or 0)
        active = int(status.get("active", 0) or 0)

        if succeeded > 0:
            lifecycle = "completed"
        elif failed > 0:
            lifecycle = "failed"
        elif active > 0:
            lifecycle = "running"
        else:
            lifecycle = "pending"

        return {
            "lifecycle": lifecycle,
            "job_name": job_name,
            "namespace": self.namespace,
            "active": active,
            "succeeded": succeeded,
            "failed": failed,
            "conditions": status.get("conditions", []),
        }
