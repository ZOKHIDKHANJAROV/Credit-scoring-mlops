FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt ./requirements.txt
RUN pip install --upgrade pip \
    && pip install -r requirements.txt

COPY ai_engineering ./ai_engineering
COPY src ./src
COPY reports ./reports

EXPOSE 8010

CMD ["uvicorn", "ai_engineering.api.agent_service:app", "--host", "0.0.0.0", "--port", "8010"]
