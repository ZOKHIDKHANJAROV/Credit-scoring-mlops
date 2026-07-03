import time
from typing import List

from fastapi import FastAPI
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from services.api.db.database import SessionLocal, engine
from services.api.db.models import Base
from services.api.db.repository import save_scoring_log, get_latest_scoring_logs
from services.api.metrics import (
    CREDIT_SCORE,
    DEFAULT_PROBABILITY,
    SCORING_DECISION_TOTAL,
    SCORING_ERRORS_TOTAL,
    SCORING_REQUEST_LATENCY_SECONDS,
    SCORING_REQUESTS_TOTAL,
    SCORING_RISK_LEVEL_TOTAL,
    RETRAIN_REQUIRED,
)
from services.api.model_loader import MODEL_NAME, model
from services.api.schemas import CreditApplication, ScoringResponse, ScoringLogResponse
from services.api.scoring import (
    build_features,
    get_decision,
    get_risk_level,
    probability_to_score,
)
from services.api.explainability import get_top_reasons
import json
from pathlib import Path

app = FastAPI(
    title="Credit Scoring API",
    description="Production-style API for credit default prediction",
    version="0.1.0",
)

RETRAIN_SIGNAL_PATH = Path("reports/retrain_signal.json")
Base.metadata.create_all(bind=engine)

def update_retrain_required_metric() -> None:
    if not RETRAIN_SIGNAL_PATH.exists():
        RETRAIN_REQUIRED.set(0)
        return

    try:
        with open(RETRAIN_SIGNAL_PATH, "r", encoding="utf-8") as file:
            signal = json.load(file)

        retrain_required = bool(signal.get("retrain_required", False))
        RETRAIN_REQUIRED.set(1 if retrain_required else 0)

    except Exception:
        RETRAIN_REQUIRED.set(0)

@app.get("/health")
def health_check() -> dict[str, str]:
    return {
        "status": "ok",
        "model_name": MODEL_NAME,
    }


@app.post("/score", response_model=ScoringResponse)
def score_application(application: CreditApplication) -> ScoringResponse:
    start_time = time.time()
    SCORING_REQUESTS_TOTAL.inc()

    db = SessionLocal()

    try:
        features = build_features(application)

        default_probability = float(model.predict_proba(features)[:, 1][0])
        top_reasons = get_top_reasons(model=model, features=features, top_n=3)

        score = probability_to_score(default_probability)
        risk_level = get_risk_level(default_probability)
        decision = get_decision(default_probability)

        save_scoring_log(
            db=db,
            application=application,
            default_probability=default_probability,
            score=score,
            risk_level=risk_level,
            decision=decision,
            model_name=MODEL_NAME,
        )

        DEFAULT_PROBABILITY.set(default_probability)
        CREDIT_SCORE.set(score)
        SCORING_DECISION_TOTAL.labels(decision=decision).inc()
        SCORING_RISK_LEVEL_TOTAL.labels(risk_level=risk_level).inc()

        return ScoringResponse(
            default_probability=round(default_probability, 4),
            score=score,
            risk_level=risk_level,
            decision=decision,
            model_name=MODEL_NAME,
            top_reasons=top_reasons,
        )

    except Exception:
        SCORING_ERRORS_TOTAL.inc()
        raise

    finally:
        db.close()
        latency = time.time() - start_time
        SCORING_REQUEST_LATENCY_SECONDS.observe(latency)


@app.get("/scoring-logs", response_model=List[ScoringLogResponse])
def scoring_logs(limit: int = 10):
    db = SessionLocal()

    try:
        return get_latest_scoring_logs(db=db, limit=limit)

    finally:
        db.close()


@app.get("/metrics")
def metrics():
    update_retrain_required_metric()
    
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )