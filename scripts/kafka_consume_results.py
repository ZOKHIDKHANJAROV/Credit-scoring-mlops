import json
import os

from confluent_kafka import Consumer


KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "127.0.0.1:19092")
TOPIC_NAME = os.getenv("KAFKA_OUTPUT_TOPIC", "scoring_results")
CONSUMER_GROUP = os.getenv("KAFKA_RESULTS_CONSUMER_GROUP", "credit-scoring-results-reader")


def create_consumer() -> Consumer:
    return Consumer(
        {
            "bootstrap.servers": KAFKA_BOOTSTRAP_SERVERS,
            "group.id": CONSUMER_GROUP,
            "auto.offset.reset": "earliest",
            "enable.auto.commit": True,
        }
    )


def main() -> None:
    consumer = create_consumer()
    consumer.subscribe([TOPIC_NAME])

    print("Kafka results consumer started")
    print(f"Topic: {TOPIC_NAME}")
    print(f"Bootstrap servers: {KAFKA_BOOTSTRAP_SERVERS}")
    print("Reading scoring results. Press Ctrl+C to stop.")
    print()

    try:
        while True:
            message = consumer.poll(timeout=1.0)

            if message is None:
                continue

            if message.error():
                print(f"Consumer error: {message.error()}")
                continue

            raw_value = message.value().decode("utf-8")
            result = json.loads(raw_value)

            print(
                "Scoring result | "
                f"application_id={result.get('application_id')} | "
                f"probability={result.get('default_probability')} | "
                f"score={result.get('score')} | "
                f"risk={result.get('risk_level')} | "
                f"decision={result.get('decision')} | "
                f"model={result.get('model_name')}"
            )

    except KeyboardInterrupt:
        print("Stopping results consumer...")

    finally:
        consumer.close()


if __name__ == "__main__":
    main()