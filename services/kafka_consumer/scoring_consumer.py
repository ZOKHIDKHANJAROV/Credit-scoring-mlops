import json
import os
from datetime import datetime

from confluent_kafka import Consumer, Producer
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

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "127.0.0.1:19092")
INPUT_TOPIC = os.getenv("KAFKA_INPUT_TOPIC", "credit_applications")
OUTPUT_TOPIC = os.getenv("KAFKA_OUTPUT_TOPIC", "scoring_results")
CONSUMER_GROUP = os.getenv("KAFKA_CONSUMER_GROUP", "credit-scoring-consumer")


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
        }
    )


def delivery_report(error, message) -> None:
    if error is not None:
        print(f"Failed to deliver scoring result: {error}")
    else:
        print(
            f"Scoring result delivered | topic={message.topic()} "
            f"partition={message.partition()} offset={message.offset()}"
        )


def score_application(application_payload: dict) -> dict:
    application_id = application_payload.get("application_id")

    clean_payload = {
        key: value
        for key, value in application_payload.items()
        if key != "application_id"
    }

    application = CreditApplication(**clean_payload)

    features = build_features(application)
    default_probability = float(model.predict_proba(features)[:, 1][0])

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
        "scored_at": datetime.utcnow().isoformat(),
    }


def main() -> None:
    consumer = create_consumer()
    producer = create_producer()

    consumer.subscribe([INPUT_TOPIC])

    print("Kafka scoring consumer started")
    print(f"Input topic: {INPUT_TOPIC}")
    print(f"Output topic: {OUTPUT_TOPIC}")
    print(f"Bootstrap servers: {KAFKA_BOOTSTRAP_SERVERS}")
    print("Waiting for messages...")

    try:
        while True:
            message = consumer.poll(timeout=1.0)

            if message is None:
                continue

            if message.error():
                print(f"Consumer error: {message.error()}")
                continue

            try:
                raw_value = message.value().decode("utf-8")
                application_payload = json.loads(raw_value)

                result = score_application(application_payload)

                producer.produce(
                    topic=OUTPUT_TOPIC,
                    key=result["application_id"],
                    value=json.dumps(result),
                    callback=delivery_report,
                )
                producer.poll(0)

                consumer.commit(message)

                print(
                    f"Scored application_id={result['application_id']} | "
                    f"probability={result['default_probability']} | "
                    f"score={result['score']} | "
                    f"decision={result['decision']}"
                )

            except ValidationError as error:
                print(f"Invalid application payload: {error}")
                consumer.commit(message)

            except Exception as error:
                print(f"Failed to process message: {error}")

    except KeyboardInterrupt:
        print("Stopping consumer...")

    finally:
        producer.flush()
        consumer.close()


if __name__ == "__main__":
    main()