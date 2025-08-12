import json
import uuid
import random
import boto3
import argparse

def main(queue_url: str, n: int):
    sqs = boto3.client("sqs")
    entries = []
    for i in range(n):
        amount = round(random.uniform(10, 1200), 2)
        payload = {
            "order_id": str(uuid.uuid4()),
            "user_id": f"user-{random.randint(1,999)}",
            "amount": amount,
            "currency": "USD",
            "items": [
                {"sku": f"SKU-{random.randint(100,999)}", "qty": random.randint(1,5)}
            ]
        }
        entries.append({"Id": str(i), "MessageBody": json.dumps(payload)})

        if len(entries) == 10 or i == n - 1:
            sqs.send_message_batch(QueueUrl=queue_url, Entries=entries)
            entries = []

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--queue-url", required=True)
    parser.add_argument("--count", type=int, default=25)
    args = parser.parse_args()
    main(args.queue_url, args.count)
