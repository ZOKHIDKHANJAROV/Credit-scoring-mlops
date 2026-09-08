"""Approval-gated Kubernetes execution for training jobs."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any


class KubernetesExecutionUnknown(TimeoutError):
    """Raised when kubectl outcome cannot be established safely."""


class KubernetesExecutor:
    """Execute only the allowlisted training Job manifest after approval."""

    def __init__(self, manifest_path: str | Path = "k8s/jobs/model-training-job.yaml", namespace: str = "ai-engineering") -> None:
        self.manifest_path = Path(manifest_path)
        self.namespace = namespace

    def apply_training_job(self, approved: bool, execution_id: str | None = None) -> dict[str, Any]:
        if not approved:
            return {"executed": False, "action": "create_training_job", "reason": "Human approval is required"}
        if self.namespace != "ai-engineering":
            raise PermissionError("Training execution is restricted to ai-engineering namespace")
        if not self.manifest_path.exists():
            raise FileNotFoundError(f"Training manifest not found: {self.manifest_path}")

        command = ["kubectl", "apply", "-f", str(self.manifest_path), "--namespace", self.namespace]
        try:
            completed = subprocess.run(command, check=True, capture_output=True, text=True, timeout=120)
        except subprocess.TimeoutExpired as exc:
            raise KubernetesExecutionUnknown("kubectl timed out; execution outcome is unknown") from exc
        except FileNotFoundError as exc:
            return {"executed": False, "action": "create_training_job", "reason": "kubectl is not installed or not available on PATH", "error": str(exc)}
        except subprocess.CalledProcessError as exc:
            return {"executed": False, "action": "create_training_job", "reason": "kubectl command failed", "stdout": exc.stdout, "stderr": exc.stderr}

        return {"executed": True, "action": "create_training_job", "namespace": self.namespace, "manifest_path": str(self.manifest_path), "execution_id": execution_id, "stdout": completed.stdout.strip()}

    def get_training_job_status(self, job_name: str) -> dict[str, Any]:
        """Read-only reconciliation check for an existing Job."""
        if self.namespace != "ai-engineering":
            raise PermissionError("Training reconciliation is restricted to ai-engineering namespace")
        try:
            completed = subprocess.run(
                ["kubectl", "get", "job", job_name, "--namespace", self.namespace, "-o", "json"],
                check=False, capture_output=True, text=True, timeout=30,
            )
        except subprocess.TimeoutExpired as exc:
            raise KubernetesExecutionUnknown("kubectl status check timed out") from exc
        except FileNotFoundError as exc:
            return {"exists": False, "status": "unknown", "error": str(exc)}

        if completed.returncode != 0:
            return {"exists": False, "status": "absent", "stderr": completed.stderr.strip()}

        import json
        data = json.loads(completed.stdout)
        status = data.get("status", {})
        if status.get("completionTime"):
            state = "completed"
        elif status.get("failed", 0) > 0:
            state = "failed"
        else:
            state = "running"
        return {"exists": True, "status": state, "job": data}
