import os
import json
import time
import decimal
import boto3
from typing import List, Dict

dynamodb = boto3.resource("dynamodb")
sns = boto3.client("sns")

DDB_TABLE = os.environ["DDB_TABLE"]
SNS_TOPIC_ARN = os.environ["SNS_TOPIC_ARN"]
ALERT_AMOUNT = float(os.environ.get("ALERT_AMOUNT", "500"))

table = dynamodb.Table(DDB_TABLE)

class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, decimal.Decimal):
            return float(o)
        return super().default(o)

def validate(payload: dict) -> None:
    required = ["order_id", "user_id", "amount", "items"]
    for k in required:
        if k not in payload:
            raise ValueError(f"Missing field: {k}")
    if not isinstance(payload["items"], list) or len(payload["items"]) == 0:
        raise ValueError("items must be a non-empty list")
    if float(payload["amount"]) < 0:
        raise ValueError("amount must be non-negative")

def persist(payload: dict) -> None:
    item = {
        "order_id": str(payload["order_id"]),
        "user_id": str(payload["user_id"]),
        "amount": decimal.Decimal(str(payload["amount"])),
        "currency": payload.get("currency", "USD"),
        "items": payload["items"],
        "ts": int(time.time())
    }
    table.put_item(Item=item)

def maybe_alert(payload: dict) -> None:
    amt = float(payload["amount"])
    if amt >= ALERT_AMOUNT:
        message = {
            "event": "LARGE_ORDER",
            "order_id": payload["order_id"],
            "user_id": payload["user_id"],
            "amount": amt,
            "currency": payload.get("currency", "USD"),
            "ts": int(time.time()),
        }
        sns.publish(TopicArn=SNS_TOPIC_ARN, Message=json.dumps(message))

def lambda_handler(event, context):
    failures: List[Dict[str, str]] = []
    for record in event.get("Records", []):
        msg_id = record["messageId"]
        try:
            payload = json.loads(record.get("body", ""))
            validate(payload)
            persist(payload)
            maybe_alert(payload)
        except Exception:
            # Fail only this record
            failures.append({"itemIdentifier": msg_id})
    return {"batchItemFailures": failures}
