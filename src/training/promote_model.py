import mlflow
from mlflow.tracking import MlflowClient
from dotenv import load_dotenv

load_dotenv()

EXPERIMENT_NAME = "credit-scoring"
METRIC_NAME = "roc_auc"
MODEL_NAME = "CreditScoringCatBoost"
MODEL_ALIAS = "champion"

TARGET_RUN_NAME = "catboost_baseline"


def main() -> None:
    client = MlflowClient()

    experiment = client.get_experiment_by_name(EXPERIMENT_NAME)

    if experiment is None:
        raise ValueError(f"Experiment not found: {EXPERIMENT_NAME}")

    runs = client.search_runs(
        experiment_ids=[experiment.experiment_id],
        filter_string=(
            f"attributes.status = 'FINISHED' "
            f"and tags.mlflow.runName = '{TARGET_RUN_NAME}' "
            f"and metrics.{METRIC_NAME} > 0"
        ),
        order_by=["attributes.start_time DESC"],
    )

    if not runs:
        raise ValueError(f"No finished runs found for {TARGET_RUN_NAME}")

    latest_run = runs[0]
    latest_run_id = latest_run.info.run_id
    latest_roc_auc = latest_run.data.metrics[METRIC_NAME]

    model_versions = client.search_model_versions(f"name = '{MODEL_NAME}'")

    matched_version = None

    for version in model_versions:
        if version.run_id == latest_run_id:
            matched_version = version
            break

    if matched_version is None:
        raise ValueError(
            f"No registered model version found for run_id={latest_run_id}"
        )

    client.set_registered_model_alias(
        name=MODEL_NAME,
        alias=MODEL_ALIAS,
        version=matched_version.version,
    )

    print("Model promoted successfully")
    print(f"Model name: {MODEL_NAME}")
    print(f"Alias: {MODEL_ALIAS}")
    print(f"Version: {matched_version.version}")
    print(f"Run ID: {latest_run_id}")
    print(f"ROC-AUC: {latest_roc_auc:.4f}")


if __name__ == "__main__":
    main()