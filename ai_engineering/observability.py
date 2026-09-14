"""Prometheus metrics for the AI Engineering Command Center."""

from __future__ import annotations

from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest


AGENT_RUNS_TOTAL = Counter(
    "agent_runs_total",
    "Total AI agent runs by final status.",
    ("status",),
)
AGENT_RUN_FAILURES_TOTAL = Counter(
    "agent_run_failures_total",
    "Total AI agent run failures by reason.",
    ("reason",),
)
AGENT_RUN_DURATION_SECONDS = Histogram(
    "agent_run_duration_seconds",
    "AI agent run duration in seconds.",
    buckets=(0.1, 0.5, 1, 2, 5, 10, 30, 60, 120),
)
TOOL_CALLS_TOTAL = Counter(
    "agent_tool_calls_total",
    "Total tool calls by tool and final status.",
    ("tool", "status"),
)
TOOL_DURATION_SECONDS = Histogram(
    "agent_tool_duration_seconds",
    "Tool execution duration in seconds.",
    ("tool",),
    buckets=(0.01, 0.05, 0.1, 0.5, 1, 2, 5, 10, 30, 60),
)
APPROVAL_REQUESTS_TOTAL = Counter(
    "approval_requests_total",
    "Total human approval requests by action.",
    ("action",),
)
EXECUTIONS_TOTAL = Counter(
    "execution_total",
    "Total approved executions by action and final status.",
    ("action", "status"),
)
EXECUTION_UNKNOWN_TOTAL = Counter(
    "execution_unknown_total",
    "Total executions whose outcome is unknown.",
    ("action",),
)
EXECUTION_RETRIES_TOTAL = Counter(
    "execution_retry_total",
    "Total execution retries after reconciliation confirmed Job absence.",
    ("action",),
)
EXECUTION_DURATION_SECONDS = Histogram(
    "execution_duration_seconds",
    "Approved execution duration in seconds.",
    ("action",),
    buckets=(0.1, 0.5, 1, 2, 5, 10, 30, 60, 120),
)
RECONCILIATION_RUNS_TOTAL = Counter(
    "reconciliation_runs_total",
    "Total automatic reconciliation cycles and item failures.",
    ("status",),
)


def metrics_response() -> tuple[bytes, str]:
    """Return the current Prometheus exposition payload and content type."""
    return generate_latest(), CONTENT_TYPE_LATEST
