from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from evidently import Report
from evidently.presets import DataDriftPreset
from sqlalchemy import create_engine
from sqlalchemy.engine import URL

import os


load_dotenv()

TRAIN_PATH = Path("data/processed/train.csv")
REPORTS_DIR = Path("reports")
REPORT_PATH = REPORTS_DIR / "data_drift_report.html"

DATABASE_URL = URL.create(
    drivername="postgresql+psycopg2",
    username="mlflow",
    password="mlflow",
    host="127.0.0.1",
    port=5432,
    database="mlflow",
)



FEATURE_COLUMNS = [
    "age",
    "duration_months",
    "credit_amount",
]


def load_reference_data() -> pd.DataFrame:
    if not TRAIN_PATH.exists():
        raise FileNotFoundError(f"Train file not found: {TRAIN_PATH}")

    train_df = pd.read_csv(TRAIN_PATH)

    return train_df[FEATURE_COLUMNS].copy()


def load_current_data() -> pd.DataFrame:
    engine = create_engine(DATABASE_URL)

    query = """
        SELECT age, duration_months, credit_amount
        FROM scoring_logs
        ORDER BY created_at DESC
        LIMIT 1000
    """

    current_df = pd.read_sql(query, engine)

    if current_df.empty:
        raise ValueError("No production scoring logs found in database")

    return current_df[FEATURE_COLUMNS].copy()


def main() -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    reference_data = load_reference_data()
    current_data = load_current_data()

    report = Report([
        DataDriftPreset(),
    ])

    snapshot = report.run(
        reference_data=reference_data,
        current_data=current_data,
    )

    snapshot.save_html(REPORT_PATH)

    print("Data drift report generated")
    print(f"Reference shape: {reference_data.shape}")
    print(f"Current shape: {current_data.shape}")
    print(f"Report path: {REPORT_PATH}")


if __name__ == "__main__":
    main()