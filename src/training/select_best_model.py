import mlflow
import pandas as pd
from mlflow.tracking import MlflowClient
from dotenv import load_dotenv

load_dotenv()

EXPERIMENT_NAME = "credit-scoring"
METRIC_NAME = "roc_auc"

MODEL_RUN_NAMES = [
    "catboost_baseline",
    "lightgbm_baseline",
    "xgboost_baseline",
]


def main() -> None:
    client = MlflowClient()

    experiment = client.get_experiment_by_name(EXPERIMENT_NAME)

    if experiment is None:
        raise ValueError(f"Experiment not found: {EXPERIMENT_NAME}")

    runs = client.search_runs(
        experiment_ids=[experiment.experiment_id],
        filter_string=f"attributes.status = 'FINISHED' and metrics.{METRIC_NAME} > 0",
        order_by=["attributes.start_time DESC"],
    )

    if not runs:
        raise ValueError("No finished model runs found")

    rows = []

    for run in runs:
        run_name = run.data.tags.get("mlflow.runName")

        if run_name not in MODEL_RUN_NAMES:
            continue

        metrics = run.data.metrics

        rows.append(
            {
                "run_id": run.info.run_id,
                "run_name": run_name,
                "start_time": run.info.start_time,
                "roc_auc": metrics.get("roc_auc"),
                "gini": metrics.get("gini"),
                "accuracy": metrics.get("accuracy"),
                "precision": metrics.get("precision"),
                "recall": metrics.get("recall"),
                "f1": metrics.get("f1"),
            }
        )

    if not rows:
        raise ValueError("No model runs found for comparison")

    results_df = pd.DataFrame(rows)

    # Берём только последний запуск каждой модели
    latest_results_df = (
        results_df
        .sort_values(by="start_time", ascending=False)
        .drop_duplicates(subset=["run_name"], keep="first")
        .sort_values(by=METRIC_NAME, ascending=False)
    )

    print("\nLatest model comparison:")
    print(
        latest_results_df[
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

    best_row = latest_results_df.iloc[0]

    print("\nBest latest model:")
    print(f"Run name: {best_row['run_name']}")
    print(f"Run ID: {best_row['run_id']}")
    print(f"ROC-AUC: {best_row[METRIC_NAME]:.4f}")
    mlflow.set_tracking_uri("http://127.0.0.1:5000")
    mlflow.set_experiment(EXPERIMENT_NAME)

    with mlflow.start_run(run_name="best_model_selection"):
        mlflow.log_param("selection_metric", METRIC_NAME)
        mlflow.log_param("selection_strategy", "latest_run_per_model")
        mlflow.log_param("best_run_id", best_row["run_id"])
        mlflow.log_param("best_run_name", best_row["run_name"])
        mlflow.log_metric(f"best_{METRIC_NAME}", best_row[METRIC_NAME])

    print("\nBest model selection logged to MLflow")


if __name__ == "__main__":
    main()