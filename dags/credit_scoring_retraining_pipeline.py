from datetime import datetime

from airflow import DAG
from airflow.operators.bash import BashOperator

PROJECT_DIR = "/opt/airflow/project"

COMMON_ENV = (
    "MLFLOW_TRACKING_URI='http://mlflow:5000' "
    "MLFLOW_S3_ENDPOINT_URL='http://minio:9000' "
    "AWS_ACCESS_KEY_ID='minio' "
    "AWS_SECRET_ACCESS_KEY='minio123' "
    "DATABASE_URL='postgresql+psycopg2://mlflow:mlflow@postgres:5432/mlflow' "
    "MONITORING_DATABASE_URL='postgresql+pg8000://mlflow:mlflow@postgres:5432/mlflow' "
)

with DAG(
    dag_id="credit_scoring_retraining_pipeline",
    description="Full model retraining pipeline for credit scoring project",
    start_date=datetime(2026, 1, 1),
    schedule=None,
    catchup=False,
    tags=["credit-scoring", "mlops", "retraining"],
) as dag:

    validate_data = BashOperator(
        task_id="validate_data",
        bash_command=f"cd {PROJECT_DIR} && python -m src.data.validate_data",
    )

    build_features = BashOperator(
        task_id="build_features",
        bash_command=f"cd {PROJECT_DIR} && python -m src.features.build_features",
    )

    train_catboost = BashOperator(
        task_id="train_catboost",
        bash_command=(
            f"cd {PROJECT_DIR} && "
            f"{COMMON_ENV}"
            "python -m src.training.train_catboost"
        ),
    )

    train_lightgbm = BashOperator(
        task_id="train_lightgbm",
        bash_command=(
            f"cd {PROJECT_DIR} && "
            f"{COMMON_ENV}"
            "python -m src.training.train_lightgbm"
        ),
    )

    train_xgboost = BashOperator(
        task_id="train_xgboost",
        bash_command=(
            f"cd {PROJECT_DIR} && "
            f"{COMMON_ENV}"
            "python -m src.training.train_xgboost"
        ),
    )

    select_best_model = BashOperator(
        task_id="select_best_model",
        bash_command=(
            f"cd {PROJECT_DIR} && "
            f"{COMMON_ENV}"
            "python -m src.training.select_best_model"
        ),
    )

    promote_model = BashOperator(
        task_id="promote_model",
        bash_command=(
            f"cd {PROJECT_DIR} && "
            f"{COMMON_ENV}"
            "python -m src.training.promote_model"
        ),
    )

    shap_report = BashOperator(
        task_id="shap_report",
        bash_command=(
            f"cd {PROJECT_DIR} && "
            f"{COMMON_ENV}"
            "python -m src.explainability.shap_report"
        ),
    )

    validate_data >> build_features

    build_features >> [train_catboost, train_lightgbm, train_xgboost]

    [train_catboost, train_lightgbm, train_xgboost] >> select_best_model

    select_best_model >> promote_model >> shap_report