from datetime import datetime

from airflow import DAG
from airflow.operators.bash import BashOperator


PROJECT_DIR = "/opt/airflow/project"


with DAG(
    dag_id="credit_scoring_batch_pipeline",
    description="Batch pipeline for credit scoring project",
    start_date=datetime(2026, 1, 1),
    schedule="@daily",
    catchup=False,
    tags=["credit-scoring", "mlops"],
) as dag:

    validate_data = BashOperator(
        task_id="validate_data",
        bash_command=f"cd {PROJECT_DIR} && python -m src.data.validate_data",
    )

    build_features = BashOperator(
        task_id="build_features",
        bash_command=f"cd {PROJECT_DIR} && python -m src.features.build_features",
    )

    drift_report = BashOperator(
        task_id="drift_report",
        bash_command=(
            f"cd {PROJECT_DIR} && "
            "MONITORING_DATABASE_URL='postgresql+pg8000://mlflow:mlflow@postgres:5432/mlflow' "
            "python -m src.monitoring.drift_report"
        ),
    )

    shap_report = BashOperator(
        task_id="shap_report",
        bash_command=(
            f"cd {PROJECT_DIR} && "
            "MLFLOW_TRACKING_URI='http://mlflow:5000' "
            "MLFLOW_S3_ENDPOINT_URL='http://minio:9000' "
            "AWS_ACCESS_KEY_ID='minio' "
            "AWS_SECRET_ACCESS_KEY='minio123' "
            "python -m src.explainability.shap_report"
        ),
    )

    validate_data >> build_features >> drift_report >> shap_report