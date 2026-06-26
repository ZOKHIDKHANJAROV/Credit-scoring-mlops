from pathlib import Path
import os

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import mlflow
import mlflow.catboost
import pandas as pd
import shap
from dotenv import load_dotenv


load_dotenv()

MODEL_NAME = "CreditScoringCatBoost"
MODEL_ALIAS = "champion"

TEST_DATA_PATH = Path("data/processed/test.csv")
REPORTS_DIR = Path("reports")
SHAP_REPORT_PATH = REPORTS_DIR / "shap_summary.html"
SHAP_IMAGE_PATH = REPORTS_DIR / "shap_summary.png"


def configure_mlflow() -> None:
    tracking_uri = os.getenv("MLFLOW_TRACKING_URI", "http://127.0.0.1:5000")
    print(f"MLflow tracking URI: {tracking_uri}")
    mlflow.set_tracking_uri(tracking_uri)


def load_champion_model():
    print("Loading champion model from MLflow Registry...")
    configure_mlflow()

    model_uri = f"models:/{MODEL_NAME}@{MODEL_ALIAS}"
    print(f"Model URI: {model_uri}")

    model = mlflow.catboost.load_model(model_uri)

    print("Model loaded successfully")
    return model


def load_test_data() -> pd.DataFrame:
    print(f"Loading test data from: {TEST_DATA_PATH}")

    if not TEST_DATA_PATH.exists():
        raise FileNotFoundError(f"Test file not found: {TEST_DATA_PATH}")

    df = pd.read_csv(TEST_DATA_PATH)

    if "target" in df.columns:
        df = df.drop(columns=["target"])

    print(f"Test data shape: {df.shape}")
    return df


def main() -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    model = load_champion_model()
    data = load_test_data()

    sample = data.head(30)
    print(f"SHAP sample shape: {sample.shape}")

    print("Creating SHAP explainer...")
    explainer = shap.TreeExplainer(model)

    print("Calculating SHAP values...")
    shap_values = explainer.shap_values(sample)

    print("Building SHAP summary plot...")
    shap.summary_plot(shap_values, sample, show=False, max_display=15)

    plt.tight_layout()
    plt.savefig(SHAP_IMAGE_PATH, bbox_inches="tight", dpi=120)
    plt.close()

    html = f"""
    <html>
        <head>
            <title>SHAP Summary Report</title>
        </head>
        <body>
            <h1>SHAP Summary Report</h1>
            <p>Model: {MODEL_NAME}@{MODEL_ALIAS}</p>
            <p>Rows explained: {len(sample)}</p>
            <img src="shap_summary.png" width="1000">
        </body>
    </html>
    """

    with open(SHAP_REPORT_PATH, "w", encoding="utf-8") as file:
        file.write(html)

    print("SHAP report generated")
    print(f"Image path: {SHAP_IMAGE_PATH}")
    print(f"Report path: {SHAP_REPORT_PATH}")


if __name__ == "__main__":
    main()