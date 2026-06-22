from pathlib import Path

import pandas as pd
from evidently import Report
from evidently.presets import DataDriftPreset
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy import create_engine
from sqlalchemy.engine import URL

TRAIN_PATH = Path("data/processed/train.csv")
REPORTS_DIR = Path("reports")
REPORT_PATH = REPORTS_DIR / "data_drift_report.html"


FEATURE_COLUMNS = [
    "age",
    "duration_months",
    "credit_amount",
]


def build_database_url() -> URL:
    return URL.create(
        drivername="postgresql+pg8000",
        username="mlflow",
        password="mlflow",
        host="127.0.0.1",
        port=55432,
        database="mlflow",
    )


def print_database_diagnostics() -> None:
    database_url = build_database_url()
    print("Database connection diagnostics:")
    print(f"  driver: {database_url.drivername}")
    print(f"  host: {database_url.host}")
    print(f"  port: {database_url.port}")
    print(f"  database: {database_url.database}")
    print(f"  username: {database_url.username}")


def load_reference_data() -> pd.DataFrame:
    if not TRAIN_PATH.exists():
        raise FileNotFoundError(f"Train file not found: {TRAIN_PATH}")

    train_df = pd.read_csv(TRAIN_PATH)

    return train_df[FEATURE_COLUMNS].copy()


def load_current_data() -> pd.DataFrame:
    engine = create_engine(build_database_url())

    query = """
        SELECT age, duration_months, credit_amount
        FROM scoring_logs
        ORDER BY created_at DESC
        LIMIT 1000
    """

    try:
        current_df = pd.read_sql(query, engine)
    except (ProgrammingError, OperationalError) as exc:
        raise RuntimeError(
            "Failed to authenticate to PostgreSQL. If the container password was changed or the "
            "volume preserved an older value, reset it with:\n"
            'docker exec -it credit_scoring_postgres psql -U mlflow -d mlflow -c "ALTER USER mlflow WITH PASSWORD \'mlflow\';"'
            "\n\nThe monitoring script expects Docker PostgreSQL on 127.0.0.1:55432. "
            "Run `docker compose up -d postgres` after changing docker-compose.yml."
        ) from exc

    if current_df.empty:
        raise ValueError("No production scoring logs found in database")

    return current_df[FEATURE_COLUMNS].copy()


def main() -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    print_database_diagnostics()

    reference_data = load_reference_data()
    current_data = load_current_data()

    report = Report([DataDriftPreset()])

    snapshot = report.run(
        reference_data=reference_data,
        current_data=current_data,
    )

    snapshot.save_html(str(REPORT_PATH))

    print("Data drift report generated")
    print(f"Reference shape: {reference_data.shape}")
    print(f"Current shape: {current_data.shape}")
    print(f"Report path: {REPORT_PATH}")


if __name__ == "__main__":
    main()
