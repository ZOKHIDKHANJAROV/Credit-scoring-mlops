import random
import time

import requests


API_URL = "http://127.0.0.1:8000/score"


def generate_application() -> dict:
    return {
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
    number_of_requests = 30

    print(f"Sending {number_of_requests} scoring requests to {API_URL}")

    success_count = 0
    error_count = 0

    for i in range(number_of_requests):
        application = generate_application()

        try:
            response = requests.post(API_URL, json=application, timeout=10)

            if response.status_code == 200:
                result = response.json()
                success_count += 1

                print(
                    f"[{i + 1}/{number_of_requests}] "
                    f"OK | probability={result['default_probability']} "
                    f"score={result['score']} "
                    f"risk={result['risk_level']} "
                    f"decision={result['decision']}"
                )
            else:
                error_count += 1
                print(
                    f"[{i + 1}/{number_of_requests}] "
                    f"ERROR {response.status_code}: {response.text}"
                )

        except requests.RequestException as error:
            error_count += 1
            print(f"[{i + 1}/{number_of_requests}] REQUEST FAILED: {error}")

        time.sleep(0.2)

    print()
    print("Finished")
    print(f"Success: {success_count}")
    print(f"Errors: {error_count}")


if __name__ == "__main__":
    main()