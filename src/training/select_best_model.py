import mlflow
import pandas as pd
from mlflow.tracking import MlflowClient


EXPERIMENT_NAME = "credit-scoring"
METRIC_NAME = "roc_auc"


def main() -> None:
    client = MlflowClient()

    experiment = client.get_experiment_by_name(EXPERIMENT_NAME)

    if experiment is None:
        raise ValueError(f"Experiment not found: {EXPERIMENT_NAME}")

    runs = client.search_runs(
        experiment_ids=[experiment.experiment_id],
        filter_string=f"attributes.status = 'FINISHED' and metrics.{METRIC_NAME} > 0",
        order_by=[f"metrics.{METRIC_NAME} DESC"],
    )

    if not runs:
        raise ValueError("No finished runs found")

    rows = []

    for run in runs:
        metrics = run.data.metrics
        params = run.data.params

        rows.append(
            {
                "run_id": run.info.run_id,
                "run_name": run.data.tags.get("mlflow.runName"),
                "model": run.data.tags.get("mlflow.log-model.history", "")[:60],
                "roc_auc": metrics.get("roc_auc"),
                "gini": metrics.get("gini"),
                "accuracy": metrics.get("accuracy"),
                "precision": metrics.get("precision"),
                "recall": metrics.get("recall"),
                "f1": metrics.get("f1"),
            }
        )

    results_df = pd.DataFrame(rows)
    results_df = results_df.sort_values(by=METRIC_NAME, ascending=False)

    print("\nModel comparison:")
    print(
        results_df[
            [
                "run_name",
                "roc_auc",
                "gini",
                "accuracy",
                "precision",
                "recall",
                "f1",
            ]
        ].to_string(index=False)
    )

    best_run = runs[0]

    print("\nBest model:")
    print(f"Run name: {best_run.data.tags.get('mlflow.runName')}")
    print(f"Run ID: {best_run.info.run_id}")
    print(f"ROC-AUC: {best_run.data.metrics.get(METRIC_NAME):.4f}")

    mlflow.set_experiment(EXPERIMENT_NAME)

    with mlflow.start_run(run_name="best_model_selection"):
        mlflow.log_param("selection_metric", METRIC_NAME)
        mlflow.log_param("best_run_id", best_run.info.run_id)
        mlflow.log_param(
            "best_run_name",
            best_run.data.tags.get("mlflow.runName"),
        )
        mlflow.log_metric(
            f"best_{METRIC_NAME}",
            best_run.data.metrics.get(METRIC_NAME),
        )

    print("\nBest model selection logged to MLflow")


if __name__ == "__main__":
    main()