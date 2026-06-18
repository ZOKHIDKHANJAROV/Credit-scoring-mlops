import mlflow.catboost


MODEL_NAME = "CreditScoringCatBoost"
MODEL_STAGE_OR_VERSION = "latest"


def load_model():
    model_uri = f"models:/{MODEL_NAME}/{MODEL_STAGE_OR_VERSION}"
    return mlflow.catboost.load_model(model_uri)


model = load_model()