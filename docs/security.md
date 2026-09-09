# AI Engineering Security

The AI Engineering Command Center treats the LLM as an untrusted planner. Infrastructure mutation is performed only by a bounded executor after human approval.

## Execution boundary

```text
LLM plan
   |
   v
allowlisted action
   |
   v
human approval
   |
   v
stable execution_id
   |
   v
KubernetesExecutor
   |
   +--> fixed namespace: ai-engineering
   +--> fixed training manifest
   +--> stable Job name: credit-training-{execution_id}
   +--> fixed kubectl invocation
```

The executor does not accept arbitrary `kubectl` commands, namespaces, Job names, or manifests from the LLM execution plan.

## API authentication secret

Production deployments should provide `AI_ENGINEERING_API_TOKEN` through a Kubernetes Secret. Never commit a real token to Git.

Generate a token locally and create the Secret:

```bash
kubectl -n ai-engineering create secret generic ai-engineering-api \
  --from-literal=AI_ENGINEERING_API_TOKEN="$(openssl rand -hex 32)"
```

Verify that the Secret exists without printing its value:

```bash
kubectl -n ai-engineering get secret ai-engineering-api
```

The deployment reads the token from the Secret as an environment variable. Rotate it by creating a new value and restarting the agent deployment.

## Kubernetes permissions

The agent ServiceAccount is restricted to the `ai-engineering` namespace and receives only the Kubernetes verbs required by the controlled workflow. The application layer additionally validates the namespace, execution identity and Job name before invoking `kubectl`.

Kubernetes RBAC `create` permissions cannot be narrowed to a single resource name, so application-level validation is an intentional second security boundary. A future production deployment can add an admission policy such as Kyverno or Gatekeeper for cluster-side enforcement.

## Network policy

The agent egress policy allows only the platform dependencies required by the control plane plus DNS. DNS is allowed to `kube-system` so standard CoreDNS deployments remain reachable when the namespace is isolated by NetworkPolicy.
