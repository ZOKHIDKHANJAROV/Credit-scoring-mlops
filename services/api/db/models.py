from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Integer, String
from sqlalchemy.orm import declarative_base


Base = declarative_base()


class ScoringLog(Base):
    __tablename__ = "scoring_logs"

    id = Column(Integer, primary_key=True, index=True)

    age = Column(Integer, nullable=False)
    duration_months = Column(Integer, nullable=False)
    credit_amount = Column(Float, nullable=False)

    default_probability = Column(Float, nullable=False)
    score = Column(Integer, nullable=False)
    risk_level = Column(String, nullable=False)
    decision = Column(String, nullable=False)
    model_name = Column(String, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)