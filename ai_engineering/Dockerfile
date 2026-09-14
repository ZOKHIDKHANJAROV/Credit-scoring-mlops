FROM python:3.11-slim

ARG KUBECTL_VERSION=v1.34.1

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates \
    && curl -fsSL -o /usr/local/bin/kubectl "https://dl.k8s.io/release/${KUBECTL_VERSION}/bin/linux/amd64/kubectl" \
    && chmod +x /usr/local/bin/kubectl \
    && kubectl version --client=true \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./requirements.txt
RUN pip install --upgrade pip \
    && pip install -r requirements.txt

COPY ai_engineering ./ai_engineering
COPY src ./src
COPY k8s ./k8s

EXPOSE 8010

CMD ["uvicorn", "ai_engineering.api.agent_service:app", "--host", "0.0.0.0", "--port", "8010"]
