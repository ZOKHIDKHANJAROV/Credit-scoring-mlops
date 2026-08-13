import json
import os
import random
import signal
import time
from datetime import datetime, timezone
from uuid import uuid4

from confluent_kafka import Producer


KAFKA_BOOTSTRAP_SERVERS = os.getenv(
    "KAFKA_BOOTSTRAP_SERVERS",
    "redpanda:9092",
)
TOPIC_NAME = os.getenv(
    "KAFKA_INPUT_TOPIC",
    "credit_applications",
)
APPLICATION_INTERVAL_SECONDS = float(
    os.getenv("APPLICATION_INTERVAL_SECONDS", "30")
)

running = True


def stop_producer(signum, frame) -> None:
    global running
    print(f"Stopping producer. Signal received: {signum}", flush=True)
    running = False


def delivery_report(error, message) -> None:
    if error is not None:
        print(f"Delivery failed: {error}", flush=True)
        return

    print(
        "Application delivered | "
        f"topic={message.topic()} | "
        f"partition={message.partition()} | "
        f"offset={message.offset()}",
        flush=True,
    )


def generate_credit_application() -> dict:
    return {
        "application_id": str(uuid4()),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "checking_account_status": random.randint(1, 4),
        "duration_months": random.choice([6, 12, 18, 24, 36, 48, 60]),
        "credit_history": random.randint(0, 4),
        "purpose": random.randint(0, 10),
        "credit_amount": random.randint(500, 15000),
        "savings_account": random.randint(1, 5),
        "employment_since": random.randint(1, 5),
        "installment_rate": random.randint(1, 4),
        "personal_status_sex": random.randint(1, 4),
        "other_debtors": random.randint(1, 3),
        "residence_since": random.randint(1, 4),
        "property": random.randint(1, 4),
        "age": random.randint(18, 75),
        "other_installment_plans": random.randint(1, 3),
        "housing": random.randint(1, 3),
        "existing_credits": random.randint(1, 4),
        "job": random.randint(1, 4),
        "people_liable": random.randint(1, 2),
        "telephone": random.randint(1, 2),
        "foreign_worker": random.randint(1, 2),
    }


def main() -> None:
    signal.signal(signal.SIGTERM, stop_producer)
    signal.signal(signal.SIGINT, stop_producer)

    producer = Producer(
        {
            "bootstrap.servers": KAFKA_BOOTSTRAP_SERVERS,
            "client.id": "automatic-credit-application-producer",
            "retries": 10,
        }
    )

    print("Automatic Kafka producer started", flush=True)
    print(f"Kafka: {KAFKA_BOOTSTRAP_SERVERS}", flush=True)
    print(f"Topic: {TOPIC_NAME}", flush=True)
    print(
        f"Application interval: {APPLICATION_INTERVAL_SECONDS} seconds",
        flush=True,
    )

    try:
        while running:
            application = generate_credit_application()

            producer.produce(
                topic=TOPIC_NAME,
                key=application["application_id"],
                value=json.dumps(application),
                callback=delivery_report,
            )

            producer.poll(0)

            print(
                "Application generated | "
                f"id={application['application_id']} | "
                f"amount={application['credit_amount']} | "
                f"duration={application['duration_months']} | "
                f"age={application['age']}",
                flush=True,
            )

            time.sleep(APPLICATION_INTERVAL_SECONDS)

    finally:
        print("Flushing remaining messages...", flush=True)
        producer.flush(timeout=10)
        print("Automatic producer stopped", flush=True)


if __name__ == "__main__":
    main()