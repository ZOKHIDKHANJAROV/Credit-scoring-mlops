from services.api.db.models import ScoringLog
from services.api.schemas import CreditApplication


def save_scoring_log(
    db,
    application: CreditApplication,
    default_probability: float,
    score: int,
    risk_level: str,
    decision: str,
    model_name: str,
) -> ScoringLog:
    scoring_log = ScoringLog(
        age=application.age,
        duration_months=application.duration_months,
        credit_amount=application.credit_amount,
        default_probability=default_probability,
        score=score,
        risk_level=risk_level,
        decision=decision,
        model_name=model_name,
    )

    db.add(scoring_log)
    db.commit()
    db.refresh(scoring_log)

    return scoring_log

def get_latest_scoring_logs(db, limit: int = 10):
    return (
        db.query(ScoringLog)
        .order_by(ScoringLog.created_at.desc())
        .limit(limit)
        .all()
    )