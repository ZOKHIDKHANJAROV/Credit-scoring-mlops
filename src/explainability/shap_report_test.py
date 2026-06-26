from pathlib import Path

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


def load_champion_model():
    mlflow.set_tracking_uri("http://127.0.0.1:5000")
    model_uri = f"models:/{MODEL_NAME}@{MODEL_ALIAS}"
    return mlflow.catboost.load_model(model_uri)


def load_test_data() -> pd.DataFrame:
    if not TEST_DATA_PATH.exists():
        raise FileNotFoundError(f"Test file not found: {TEST_DATA_PATH}")

    df = pd.read_csv(TEST_DATA_PATH)

    if "target" in df.columns:
        df = df.drop(columns=["target"])

    return df


def main() -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    model = load_champion_model()
    data = load_test_data()

    sample = data.head(100)

    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(sample)

    shap.summary_plot(shap_values, sample, show=False)

    import matplotlib.pyplot as plt

    plt.tight_layout()
    plt.savefig(SHAP_IMAGE_PATH, bbox_inches="tight")
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
    print(f"Rows explained: {len(sample)}")
    print(f"Image path: {SHAP_IMAGE_PATH}")
    print(f"Report path: {SHAP_REPORT_PATH}")


if __name__ == "__main__":
    main()