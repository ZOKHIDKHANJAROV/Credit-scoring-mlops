import json
import os
import time
from datetime import datetime, timezone
from typing import Any

from confluent_kafka import Consumer, KafkaError, Message, Producer
from prometheus_client import Counter, Gauge, Histogram, start_http_server
from pydantic import ValidationError

from services.api.db.database import SessionLocal
from services.api.db.repository import save_scoring_log
from services.api.model_loader import MODEL_NAME, model
from services.api.schemas import CreditApplication
from services.api.scoring import (
    build_features,
    get_decision,
    get_risk_level,
    probability_to_score,
)


# -------------------------------------------------------------------
# Prometheus metrics
# -------------------------------------------------------------------

KAFKA_SCORING_REQUESTS_TOTAL = Counter(
    "credit_scoring_kafka_requests_total",
    "Total number of credit applications successfully processed from Kafka",
)

KAFKA_SCORING_ERRORS_TOTAL = Counter(
    "credit_scoring_kafka_errors_total",
    "Total number of Kafka scoring errors",
)

KAFKA_DEFAULT_PROBABILITY = Gauge(
    "credit_scoring_kafka_default_probability",
    "Last default probability produced by Kafka scoring",
)

KAFKA_CREDIT_SCORE = Gauge(
    "credit_scoring_kafka_credit_score",
    "Last credit score produced by Kafka scoring",
)

KAFKA_DECISION_TOTAL = Counter(
    "credit_scoring_kafka_decision_total",
    "Total Kafka scoring decisions by decision type",
    ["decision"],
)

KAFKA_RISK_LEVEL_TOTAL = Counter(
    "credit_scoring_kafka_risk_level_total",
    "Total Kafka scoring results by risk level",
    ["risk_level"],
)

KAFKA_SCORING_LATENCY_SECONDS = Histogram(
    "credit_scoring_kafka_latency_seconds",
    "Kafka scoring processing latency in seconds",
)

KAFKA_MESSAGES_RECEIVED_TOTAL = Counter(
    "credit_scoring_kafka_messages_received_total",
    "Total number of messages received from Kafka",
)

KAFKA_INVALID_MESSAGES_TOTAL = Counter(
    "credit_scoring_kafka_invalid_messages_total",
    "Total number of invalid Kafka messages",
)


# -------------------------------------------------------------------
# Configuration
# -------------------------------------------------------------------

KAFKA_BOOTSTRAP_SERVERS = os.getenv(
    "KAFKA_BOOTSTRAP_SERVERS",
    "127.0.0.1:19092",
)

INPUT_TOPIC = os.getenv(
    "KAFKA_INPUT_TOPIC",
    "credit_applications",
)

OUTPUT_TOPIC = os.getenv(
    "KAFKA_OUTPUT_TOPIC",
    "scoring_results",
)

CONSUMER_GROUP = os.getenv(
    "KAFKA_CONSUMER_GROUP",
    "credit-scoring-consumer",
)

METRICS_PORT = int(
    os.getenv(
        "KAFKA_METRICS_PORT",
        "8001",
    )
)


# -------------------------------------------------------------------
# Kafka clients
# -------------------------------------------------------------------

def create_consumer() -> Consumer:
    return Consumer(
        {
            "bootstrap.servers": KAFKA_BOOTSTRAP_SERVERS,
            "group.id": CONSUMER_GROUP,
            "auto.offset.reset": "earliest",
            "enable.auto.commit": False,
        }
    )


def create_producer() -> Producer:
    return Producer(
        {
            "bootstrap.servers": KAFKA_BOOTSTRAP_SERVERS,
            "client.id": "credit-scoring-result-producer",
            "retries": 10,
        }
    )


def delivery_report(error: Any, message: Message) -> None:
    if error is not None:
        KAFKA_SCORING_ERRORS_TOTAL.inc()

        print(
            f"Failed to deliver scoring result: {error}",
            flush=True,
        )
        return

    print(
        "Scoring result delivered | "
        f"topic={message.topic()} | "
        f"partition={message.partition()} | "
        f"offset={message.offset()}",
        flush=True,
    )


# -------------------------------------------------------------------
# Scoring
# -------------------------------------------------------------------

def score_application(application_payload: dict[str, Any]) -> dict[str, Any]:
    application_id = application_payload.get("application_id")

    metadata_fields = {
        "application_id",
        "created_at",
    }

    clean_payload = {
        key: value
        for key, value in application_payload.items()
        if key not in metadata_fields
    }

    application = CreditApplication(**clean_payload)

    features = build_features(application)

    default_probability = float(
        model.predict_proba(features)[:, 1][0]
    )

    score = probability_to_score(default_probability)
    risk_level = get_risk_level(default_probability)
    decision = get_decision(default_probability)

    db = SessionLocal()

    try:
        save_scoring_log(
            db=db,
            application=application,
            default_probability=default_probability,
            score=score,
            risk_level=risk_level,
            decision=decision,
            model_name=MODEL_NAME,
        )
    finally:
        db.close()

    return {
        "application_id": application_id,
        "default_probability": round(default_probability, 4),
        "score": score,
        "risk_level": risk_level,
        "decision": decision,
        "model_name": MODEL_NAME,
        "scored_at": datetime.now(timezone.utc).isoformat(),
    }


def update_success_metrics(
    result: dict[str, Any],
    processing_time: float,
) -> None:
    KAFKA_SCORING_REQUESTS_TOTAL.inc()

    KAFKA_DEFAULT_PROBABILITY.set(
        float(result["default_probability"])
    )

    KAFKA_CREDIT_SCORE.set(
        int(result["score"])
    )

    KAFKA_DECISION_TOTAL.labels(
        decision=str(result["decision"])
    ).inc()

    KAFKA_RISK_LEVEL_TOTAL.labels(
        risk_level=str(result["risk_level"])
    ).inc()

    KAFKA_SCORING_LATENCY_SECONDS.observe(processing_time)


# -------------------------------------------------------------------
# Message processing
# -------------------------------------------------------------------

def process_message(
    message: Message,
    consumer: Consumer,
    producer: Producer,
) -> None:
    started_at = time.perf_counter()
    KAFKA_MESSAGES_RECEIVED_TOTAL.inc()

    try:
        raw_value = message.value().decode("utf-8")
        application_payload = json.loads(raw_value)

        if not isinstance(application_payload, dict):
            raise ValueError(
                "Kafka message payload must be a JSON object"
            )

        result = score_application(application_payload)

        processing_time = time.perf_counter() - started_at
        update_success_metrics(result, processing_time)

        application_id = result.get("application_id")

        producer.produce(
            topic=OUTPUT_TOPIC,
            key=str(application_id) if application_id else None,
            value=json.dumps(
                result,
                ensure_ascii=False,
            ),
            callback=delivery_report,
        )

        producer.poll(0)

        consumer.commit(
            message=message,
            asynchronous=False,
        )

        print(
            "Scored application | "
            f"application_id={application_id} | "
            f"probability={result['default_probability']} | "
            f"score={result['score']} | "
            f"risk_level={result['risk_level']} | "
            f"decision={result['decision']} | "
            f"latency={processing_time:.4f}s",
            flush=True,
        )

    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        KAFKA_SCORING_ERRORS_TOTAL.inc()
        KAFKA_INVALID_MESSAGES_TOTAL.inc()

        print(
            f"Invalid Kafka message: {error}",
            flush=True,
        )

        # Невалидное сообщение повторно обработать невозможно,
        # поэтому фиксируем offset и переходим к следующему.
        consumer.commit(
            message=message,
            asynchronous=False,
        )

    except ValidationError as error:
        KAFKA_SCORING_ERRORS_TOTAL.inc()
        KAFKA_INVALID_MESSAGES_TOTAL.inc()

        print(
            f"Invalid credit application payload: {error}",
            flush=True,
        )

        consumer.commit(
            message=message,
            asynchronous=False,
        )

    except Exception as error:
        KAFKA_SCORING_ERRORS_TOTAL.inc()

        print(
            "Failed to process Kafka message | "
            f"error_type={type(error).__name__} | "
            f"error={error}",
            flush=True,
        )

        # При временной ошибке БД, MLflow или MinIO offset не фиксируем.
        # После перезапуска consumer сможет обработать сообщение повторно.


# -------------------------------------------------------------------
# Main loop
# -------------------------------------------------------------------

def main() -> None:
    start_http_server(METRICS_PORT)

    print(
        f"Kafka consumer Prometheus metrics started on port {METRICS_PORT}",
        flush=True,
    )

    consumer = create_consumer()
    producer = create_producer()

    consumer.subscribe([INPUT_TOPIC])

    print("Kafka scoring consumer started", flush=True)
    print(f"Input topic: {INPUT_TOPIC}", flush=True)
    print(f"Output topic: {OUTPUT_TOPIC}", flush=True)
    print(
        f"Bootstrap servers: {KAFKA_BOOTSTRAP_SERVERS}",
        flush=True,
    )
    print(f"Consumer group: {CONSUMER_GROUP}", flush=True)
    print("Waiting for messages...", flush=True)

    try:
        while True:
            message = consumer.poll(timeout=1.0)

            if message is None:
                producer.poll(0)
                continue

            if message.error():
                if message.error().code() == KafkaError._PARTITION_EOF:
                    continue

                KAFKA_SCORING_ERRORS_TOTAL.inc()

                print(
                    f"Kafka consumer error: {message.error()}",
                    flush=True,
                )
                continue

            process_message(
                message=message,
                consumer=consumer,
                producer=producer,
            )

    except KeyboardInterrupt:
        print(
            "Stopping Kafka consumer...",
            flush=True,
        )

    finally:
        print(
            "Flushing Kafka producer...",
            flush=True,
        )

        producer.flush(timeout=10)
        consumer.close()

        print(
            "Kafka consumer stopped",
            flush=True,
        )


if __name__ == "__main__":
    main()