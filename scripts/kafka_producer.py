import json
import random
import time
from uuid import uuid4

from confluent_kafka import Producer

KAFKA_BOOTSTRAP_SERVERS = "127.0.0.1:19092"
TOPIC_NAME = "credit_applications"


def delivery_report(error, message) -> None:
    if error is not None:
        print(f"Delivery failed: {error}")
    else:
        print(
            f"Message delivered | topic={message.topic()} "
            f"partition={message.partition()} offset={message.offset()}"
        )


def generate_credit_application() -> dict:
    return {
        "application_id": str(uuid4()),
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
    producer = Producer(
        {
            "bootstrap.servers": KAFKA_BOOTSTRAP_SERVERS,
        }
    )

    number_of_messages = 10

    print(f"Sending {number_of_messages} messages to topic: {TOPIC_NAME}")

    for index in range(number_of_messages):
        application = generate_credit_application()
        message_value = json.dumps(application)

        producer.produce(
            topic=TOPIC_NAME,
            key=application["application_id"],
            value=message_value,
            callback=delivery_report,
        )

        producer.poll(0)

        print(
            f"[{index + 1}/{number_of_messages}] Sent application_id="
            f"{application['application_id']}"
        )

        time.sleep(0.5)

    producer.flush()
    print("Finished sending messages")


if __name__ == "__main__":
    main()