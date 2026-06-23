import pandas as pd

from services.api.schemas import CreditApplication
from services.api.scoring import (
    build_features,
    get_decision,
    get_risk_level,
    probability_to_score,
)


def test_probability_to_score_low_probability():
    score = probability_to_score(0.0)
    assert score == 850


def test_probability_to_score_high_probability():
    score = probability_to_score(1.0)
    assert score == 300


def test_probability_to_score_middle_probability():
    score = probability_to_score(0.5)
    assert score == 575


def test_get_risk_level_low():
    assert get_risk_level(0.10) == "low"


def test_get_risk_level_medium():
    assert get_risk_level(0.30) == "medium"


def test_get_risk_level_high():
    assert get_risk_level(0.60) == "high"


def test_get_risk_level_very_high():
    assert get_risk_level(0.90) == "very_high"


def test_get_decision_approved():
    assert get_decision(0.20) == "approved"


def test_get_decision_manual_review():
    assert get_decision(0.40) == "manual_review"


def test_get_decision_rejected():
    assert get_decision(0.70) == "rejected"


def test_build_features_creates_expected_columns():
    application = CreditApplication(
        checking_account_status=1,
        duration_months=24,
        credit_history=2,
        purpose=3,
        credit_amount=3500,
        savings_account=1,
        employment_since=3,
        installment_rate=2,
        personal_status_sex=2,
        other_debtors=1,
        residence_since=2,
        property=2,
        age=32,
        other_installment_plans=1,
        housing=2,
        existing_credits=1,
        job=3,
        people_liable=1,
        telephone=1,
        foreign_worker=1,
    )

    features = build_features(application)

    assert isinstance(features, pd.DataFrame)
    assert features.shape[0] == 1

    expected_columns = [
        "credit_amount_per_month",
        "credit_amount_per_age",
        "is_long_term_loan",
        "is_high_amount_loan",
    ]

    for column in expected_columns:
        assert column in features.columns