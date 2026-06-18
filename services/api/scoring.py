import pandas as pd

from services.api.schemas import CreditApplication
from src.utils.config import load_feature_config

def build_features(application: CreditApplication) -> pd.DataFrame:
    data = application.model_dump()
    config = load_feature_config()

    df = pd.DataFrame([data])

    df["credit_amount_per_month"] = (
        df["credit_amount"] / df["duration_months"]
    )

    df["credit_amount_per_age"] = (
        df["credit_amount"] / df["age"]
    )

    df["is_long_term_loan"] = (
        df["duration_months"] >= config["long_term_threshold"]
    ).astype(int)

    df["is_high_amount_loan"] = (
        df["credit_amount"] >= config["high_amount_threshold"]
    ).astype(int)

    return df


def probability_to_score(default_probability: float) -> int:
    min_score = 300
    max_score = 850

    score = max_score - int(default_probability * (max_score - min_score))

    return max(min_score, min(max_score, score))


def get_risk_level(default_probability: float) -> str:
    if default_probability < 0.25:
        return "low"
    if default_probability < 0.50:
        return "medium"
    if default_probability < 0.75:
        return "high"

    return "very_high"


def get_decision(default_probability: float) -> str:
    if default_probability < 0.30:
        return "approved"
    if default_probability < 0.60:
        return "manual_review"

    return "rejected"