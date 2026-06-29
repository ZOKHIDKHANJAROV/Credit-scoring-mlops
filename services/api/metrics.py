from prometheus_client import Counter, Gauge, Histogram


SCORING_REQUESTS_TOTAL = Counter(
    "credit_scoring_requests_total",
    "Total number of credit scoring requests",
)

SCORING_DECISION_TOTAL = Counter(
    "credit_scoring_decision_total",
    "Total number of scoring decisions by decision type",
    ["decision"],
)

SCORING_RISK_LEVEL_TOTAL = Counter(
    "credit_scoring_risk_level_total",
    "Total number of scoring results by risk level",
    ["risk_level"],
)

SCORING_ERRORS_TOTAL = Counter(
    "credit_scoring_errors_total",
    "Total number of scoring errors",
)

DEFAULT_PROBABILITY = Gauge(
    "credit_scoring_default_probability",
    "Last predicted default probability",
)

CREDIT_SCORE = Gauge(
    "credit_scoring_score",
    "Last calculated credit score",
)

SCORING_REQUEST_LATENCY_SECONDS = Histogram(
    "credit_scoring_request_latency_seconds",
    "Credit scoring request latency in seconds",
)