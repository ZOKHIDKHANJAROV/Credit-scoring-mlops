import os

import mlflow
import mlflow.catboost


MODEL_NAME = "CreditScoringCatBoost"
MODEL_ALIAS = "champion"


def load_model():
    tracking_uri = os.getenv("MLFLOW_TRACKING_URI", "http://127.0.0.1:5000")
    mlflow.set_tracking_uri(tracking_uri)

    model_uri = f"models:/{MODEL_NAME}@{MODEL_ALIAS}"
    return mlflow.catboost.load_model(model_uri)


model = load_model()