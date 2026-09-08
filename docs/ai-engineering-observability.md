# AI Engineering Observability

The AI Engineering Command Center exposes Prometheus-compatible metrics at `GET /metrics`.

## Metrics

| Metric | Meaning |
|---|---|
| `agent_runs_total` | Agent runs grouped by final status |
| `agent_run_failures_total` | Agent failures grouped by reason |
| `agent_run_duration_seconds` | End-to-end agent run latency |
| `agent_tool_calls_total` | Tool calls grouped by tool and status |
| `agent_tool_duration_seconds` | Tool execution latency |
| `approval_requests_total` | Human approval requests grouped by action |
| `execution_total` | Approved executions grouped by action and status |
| `execution_duration_seconds` | Approved execution latency grouped by action |
| `execution_unknown_total` | Executions whose outcome is unknown |
| `execution_retry_total` | Retries started after reconciliation confirmed Job absence |

## Kubernetes scraping

The AI agent Deployment contains Prometheus scrape annotations:

- `prometheus.io/scrape: "true"`
- `prometheus.io/path: /metrics`
- `prometheus.io/port: "8010"`

This works with Prometheus installations that support annotation-based discovery. A `ServiceMonitor` is intentionally not included because that CRD is not guaranteed to exist in the project's base Kubernetes cluster.

## Operational rule

Metrics are observability signals, not an authorization boundary. `/metrics` should be reachable only from the monitoring plane or trusted cluster network. The AI agent's mutating API endpoints remain protected by bearer authentication.
