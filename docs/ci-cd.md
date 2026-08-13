# CI/CD

This project uses GitHub Actions for CI/CD.

## Workflow

Workflow file:

```text
.github/workflows/ci-cd.yml
```

The pipeline runs on:

- Pull requests
- Pushes to `main` or `master`
- Manual `workflow_dispatch`

## CI

The `quality` job runs:

- Python compile checks for `dags`, `services`, `src`, and `tests`
- JSON validation for app configs and Grafana dashboards
- Docker Compose config validation
- Unit tests with `pytest`

The CI job uses `requirements-ci.txt` so unit tests stay fast and do not install the full ML runtime.

## Container Delivery

The `docker` job builds these images:

- `ghcr.io/<owner>/<repo>/api:<sha>`
- `ghcr.io/<owner>/<repo>/airflow:<sha>`
- `ghcr.io/<owner>/<repo>/kafka:<sha>`

On pull requests the images are built but not pushed. On pushes to `main` or `master`, the images are pushed to GitHub Container Registry with both `<sha>` and `latest` tags.

## Deployment

The `deploy` job deploys to a remote Docker host over SSH. It uploads:

- `docker-compose.yml`
- `docker-compose.prod.yml`
- Runtime source and config directories used by mounted services

Then it pulls the published GHCR images and runs:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --no-build
```

## Required GitHub Secrets

Set these repository or environment secrets:

```text
DEPLOY_HOST      Remote Docker host/IP
DEPLOY_USER      SSH user
DEPLOY_SSH_KEY   Private SSH key
```

Optional:

```text
DEPLOY_PORT      SSH port, defaults to 22
DEPLOY_PATH      Remote project path, defaults to ~/credit-scoring-mlops
GHCR_USERNAME    GHCR username, defaults to the GitHub actor
GHCR_TOKEN       GHCR token, defaults to the workflow GitHub token
```

Use `GHCR_TOKEN` if the remote host cannot pull private GHCR images with the workflow token.
