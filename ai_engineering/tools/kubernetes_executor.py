"""Approval-gated Kubernetes execution for training jobs."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Any


class KubernetesExecutionUnknown(TimeoutError):
    """Raised when kubectl outcome cannot be established safely."""


class KubernetesExecutor:
    """Execute only the allowlisted training Job manifest after approval."""

    JOB_ID_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,38}[a-z0-9])?$")
    JOB_NAME_RE = re.compile(r"^credit-training-[a-z0-9](?:[a-z0-9-]{0,38}[a-z0-9])?$")

    def __init__(
        self,
        manifest_path: str | Path = "k8s/jobs/model-training-job.yaml",
        namespace: str = "ai-engineering",
    ) -> None:
        self.manifest_path = Path(manifest_path)
        self.namespace = namespace

    @classmethod
    def _job_name(cls, execution_id: str) -> str:
        safe_id = execution_id.lower().strip()
        if not cls.JOB_ID_RE.fullmatch(safe_id):
            raise ValueError(
                "execution_id must be a DNS-1123-safe identifier of 1-40 lowercase characters"
            )
        return f"credit-training-{safe_id}"

    @classmethod
    def _validate_job_name(cls, job_name: str) -> None:
        if not cls.JOB_NAME_RE.fullmatch(job_name):
            raise ValueError("job_name must refer to an ai-engineering credit-training Job")

    def _render_manifest(self, execution_id: str) -> str:
        manifest = self.manifest_path.read_text(encoding="utf-8")
        job_name = self._job_name(execution_id)
        rendered, replacements = re.subn(
            r"(^\s*name:\s*)credit-model-training(\s*$)",
            rf"\g<1>{job_name}\g<2>",
            manifest,
            count=1,
            flags=re.MULTILINE,
        )
        if replacements != 1:
            raise ValueError("Training manifest must contain metadata.name=credit-model-training")
        return rendered

    def apply_training_job(self, approved: bool, execution_id: str | None = None) -> dict[str, Any]:
        if not approved:
            return {
                "executed": False,
                "action": "create_training_job",
                "reason": "Human approval is required",
            }
        if self.namespace != "ai-engineering":
            raise PermissionError("Training execution is restricted to ai-engineering namespace")
        if not execution_id:
            raise ValueError("execution_id is required for approved training execution")
        if not self.manifest_path.exists():
            raise FileNotFoundError(f"Training manifest not found: {self.manifest_path}")

        job_name = self._job_name(execution_id)
        command = ["kubectl", "apply", "-f", "-", "--namespace", "ai-engineering"]
        try:
            completed = subprocess.run(
                command,
                input=self._render_manifest(execution_id),
                check=True,
                capture_output=True,
                text=True,
                timeout=120,
            )
        except subprocess.TimeoutExpired as exc:
            raise KubernetesExecutionUnknown("kubectl timed out; execution outcome is unknown") from exc
        except FileNotFoundError:
            return {
                "executed": False,
                "action": "create_training_job",
                "reason": "kubectl is not installed or not available on PATH",
            }
        except subprocess.CalledProcessError:
            return {
                "executed": False,
                "action": "create_training_job",
                "reason": "kubectl command failed",
            }

        return {
            "executed": True,
            "action": "create_training_job",
            "namespace": "ai-engineering",
            "job_name": job_name,
            "manifest_path": str(self.manifest_path),
            "execution_id": execution_id,
            "stdout": completed.stdout.strip(),
        }

    def get_training_job_status(self, job_name: str) -> dict[str, Any]:
        """Read-only reconciliation check for an existing training Job."""
        if self.namespace != "ai-engineering":
            raise PermissionError("Training reconciliation is restricted to ai-engineering namespace")
        self._validate_job_name(job_name)
        try:
            completed = subprocess.run(
                ["kubectl", "get", "job", job_name, "--namespace", "ai-engineering", "-o", "json"],
                check=False,
                capture_output=True,
                text=True,
                timeout=30,
            )
        except subprocess.TimeoutExpired as exc:
            raise KubernetesExecutionUnknown("kubectl status check timed out") from exc
        except FileNotFoundError:
            return {"exists": False, "status": "unknown", "error": "kubectl is not available"}

        if completed.returncode != 0:
            return {"exists": False, "status": "absent"}

        data = json.loads(completed.stdout)
        status = data.get("status", {})
        if status.get("completionTime"):
            state = "completed"
        elif status.get("failed", 0) > 0:
            state = "failed"
        else:
            state = "running"
        return {"exists": True, "status": state, "job": data}
