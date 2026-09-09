# AI Engineering Agent Workflow

The command center separates LLM reasoning from infrastructure mutation.

```text
User / Event
    |
    v
POST /api/v1/agent/decision
    |
    v
OrchestratorAgent.reason()
    |
    v
AgentDecision
    |
    +--> read-only action -> return decision
    |
    +--> propose_retraining
             |
             v
       ApprovalRequest (pending)
             |
             v
       Human decision
        /          \
   rejected       approved
                     |
                     v
             KubernetesExecutor
                     |
                     v
              Kubernetes Job
                     |
                     v
          reconciliation / audit
```

## Mutation boundary

`OrchestratorAgent` is a reasoning layer. It is explicitly instructed not to execute infrastructure actions. The LLM output is parsed into an allowlisted `AgentDecision`.

Only `propose_retraining` is mapped automatically to the mutating approval action `create_training_job`. The Kubernetes executor receives a stable approval ID as its execution identity and renders the Job name from that ID. The executor also fixes the namespace and manifest path rather than accepting infrastructure parameters from the LLM.

The API's approval endpoints are the human-in-the-loop boundary:

1. create or request approval;
2. approve or reject it;
3. execute only an approved request;
4. reconcile an unknown outcome after an executor timeout.

## Traceability

The decision endpoint records `decision_created`. A generated training approval records `approval_requested` under the approval ID. Execution and reconciliation continue the same audit trace so an operator can inspect the complete lifecycle.

## Observability

Prometheus metrics cover agent runs, tool calls, approvals, executions, unknown outcomes, retries and latency. Grafana provisions the AI Engineering Command Center dashboard from `monitoring/grafana/dashboards`.

Metrics are operational telemetry, not an authorization mechanism. Authorization remains enforced by the API token, approval state machine, executor validation and Kubernetes RBAC.
