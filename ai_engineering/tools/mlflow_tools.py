"""Read-only MLflow tools for the AI Engineering Command Center."""

from __future__ import annotations

import os
from typing import Any

import mlflow
from mlflow.tracking import MlflowClient


class MLflowTools:
    """Provide safe inspection of the credit-scoring MLflow state."""

    def __init__(
        self,
        tracking_uri: str | None = None,
        experiment_name: str = "credit-scoring",
        model_name: str = "CreditScoringCatBoost",
        model_alias: str = "champion",
    ) -> None:
        self.tracking_uri = tracking_uri or os.getenv(
            "MLFLOW_TRACKING_URI", "http://127.0.0.1:5000"
        )
        self.experiment_name = experiment_name
        self.model_name = model_name
        self.model_alias = model_alias
        mlflow.set_tracking_uri(self.tracking_uri)
        self.client = MlflowClient(tracking_uri=self.tracking_uri)

    def get_champion_model(self) -> dict[str, Any]:
        """Return metadata for the configured champion model alias."""
        try:
            model_version = self.client.get_model_version_by_alias(
                self.model_name, self.model_alias
            )
        except Exception as exc:
            return {
                "available": False,
                "model_name": self.model_name,
                "alias": self.model_alias,
                "error": str(exc),
            }

        return {
            "available": True,
            "model_name": self.model_name,
            "alias": self.model_alias,
            "version": model_version.version,
            "run_id": model_version.run_id,
            "status": model_version.status,
        }

    def get_run_metrics(self, run_id: str) -> dict[str, Any]:
        """Return metrics for a specific MLflow run without loading its model artifact."""
        if not run_id or not run_id.strip():
            raise ValueError("run_id must not be empty")

        try:
            run = self.client.get_run(run_id)
        except Exception as exc:
            return {
                "available": False,
                "run_id": run_id,
                "error": str(exc),
            }

        return {
            "available": True,
            "run_id": run.info.run_id,
            "run_name": run.data.tags.get("mlflow.runName"),
            "metrics": dict(run.data.metrics),
            "params": dict(run.data.params),
        }

    def get_latest_model_runs(self, limit: int = 10) -> list[dict[str, Any]]:
        """Return recent finished runs from the credit-scoring experiment."""
        if limit < 1 or limit > 100:
            raise ValueError("limit must be between 1 and 100")

        experiment = self.client.get_experiment_by_name(self.experiment_name)
        if experiment is None:
            return []

        runs = self.client.search_runs(
            experiment_ids=[experiment.experiment_id],
            filter_string="attributes.status = 'FINISHED'",
            order_by=["attributes.start_time DESC"],
            max_results=limit,
        )

        result: list[dict[str, Any]] = []
        for run in runs:
            result.append(
                {
                    "run_id": run.info.run_id,
                    "run_name": run.data.tags.get("mlflow.runName"),
                    "start_time": run.info.start_time,
                    "metrics": dict(run.data.metrics),
                    "params": dict(run.data.params),
                }
            )
        return result

    def compare_latest_models(self) -> list[dict[str, Any]]:
        """Compare the latest run for each supported model family."""
        runs = self.get_latest_model_runs(limit=100)
        supported = {"catboost_baseline", "lightgbm_baseline", "xgboost_baseline"}

        latest: dict[str, dict[str, Any]] = {}
        for run in runs:
            name = run.get("run_name")
            if name not in supported or name in latest:
                continue
            latest[name] = {
                "run_name": name,
                "run_id": run["run_id"],
                "roc_auc": run["metrics"].get("roc_auc"),
                "gini": run["metrics"].get("gini"),
                "accuracy": run["metrics"].get("accuracy"),
                "precision": run["metrics"].get("precision"),
                "recall": run["metrics"].get("recall"),
                "f1": run["metrics"].get("f1"),
            }

        return sorted(
            latest.values(),
            key=lambda row: row["roc_auc"] if row["roc_auc"] is not None else float("-inf"),
            reverse=True,
        )
