from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime

class CreditApplication(BaseModel):
    checking_account_status: int = Field(..., ge=1, le=4)
    duration_months: int = Field(..., ge=1, le=100)
    credit_history: int = Field(..., ge=0, le=4)
    purpose: int = Field(..., ge=0, le=10)
    credit_amount: float = Field(..., gt=0)
    savings_account: int = Field(..., ge=1, le=5)
    employment_since: int = Field(..., ge=1, le=5)
    installment_rate: int = Field(..., ge=1, le=4)
    personal_status_sex: int = Field(..., ge=1, le=4)
    other_debtors: int = Field(..., ge=1, le=3)
    residence_since: int = Field(..., ge=1, le=4)
    property: int = Field(..., ge=1, le=4)
    age: int = Field(..., ge=18, le=100)
    other_installment_plans: int = Field(..., ge=1, le=3)
    housing: int = Field(..., ge=1, le=3)
    existing_credits: int = Field(..., ge=1, le=4)
    job: int = Field(..., ge=1, le=4)
    people_liable: int = Field(..., ge=1, le=2)
    telephone: int = Field(..., ge=1, le=2)
    foreign_worker: int = Field(..., ge=1, le=2)


class ScoringResponse(BaseModel):
    default_probability: float
    score: int
    risk_level: str
    decision: str
    model_name: str

class ScoringLogResponse(BaseModel):
    id: int
    age: int
    duration_months: int
    credit_amount: float
    default_probability: float
    score: int
    risk_level: str
    decision: str
    model_name: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)