from fastapi import FastAPI

from services.api.model_loader import MODEL_NAME, model
from services.api.schemas import CreditApplication, ScoringResponse
from services.api.scoring import (
    build_features,
    get_decision,
    get_risk_level,
    probability_to_score,
)


app = FastAPI(
    title="Credit Scoring API",
    description="Production-style API for credit default prediction",
    version="0.1.0",
)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {
        "status": "ok",
        "model_name": MODEL_NAME,
    }


@app.post("/score", response_model=ScoringResponse)
def score_application(application: CreditApplication) -> ScoringResponse:
    features = build_features(application)

    default_probability = float(model.predict_proba(features)[:, 1][0])

    score = probability_to_score(default_probability)
    risk_level = get_risk_level(default_probability)
    decision = get_decision(default_probability)

    return ScoringResponse(
        default_probability=round(default_probability, 4),
        score=score,
        risk_level=risk_level,
        decision=decision,
        model_name=MODEL_NAME,
    )