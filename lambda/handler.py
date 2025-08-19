import os
import json
import time
import decimal
import boto3
import logging
from typing import List, Dict, Any

# --- AWS clients ---
dynamodb = boto3.resource("dynamodb")
sns = boto3.client("sns")

# --- Environment variables ---
DDB_TABLE = os.environ["DDB_TABLE"]
SNS_TOPIC_ARN = os.environ["SNS_TOPIC_ARN"]
ALERT_AMOUNT = float(os.environ.get("ALERT_AMOUNT", "1500"))
SKIP_VALIDATION = os.environ.get("SKIP_VALIDATION", "false").lower() == "true"

# --- DynamoDB table reference ---
table = dynamodb.Table(DDB_TABLE)

# --- Logging setup ---
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# --- Helpers ---
def _to_decimal(obj: Any) -> Any:
    """
    Recursively convert all floats/ints in obj to Decimal for DynamoDB,
    leaving strings/bytes/None/booleans unchanged.
    """
    if isinstance(obj, dict):
        return {k: _to_decimal(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_to_decimal(v) for v in obj]
    if isinstance(obj, float) or isinstance(obj, int):
        return decimal.Decimal(str(obj))
    return obj

def _sum_items(items: list) -> float:
    total = 0.0
    for it in items:
        qty = float(it.get("qty", 0))
        price = float(it.get("unitPrice", 0) or it.get("price", 0))
        total += qty * price
    return total

# --- Validation (lightweight) ---
def validate(payload: dict) -> None:
    required = ["order_id", "user_id", "amount", "items"]
    for k in required:
        if k not in payload:
            raise ValueError(f"Missing field: {k}")
    if not isinstance(payload["items"], list) or len(payload["items"]) == 0:
        raise ValueError("items must be a non-empty list")
    if float(payload["amount"]) < 0:
        raise ValueError("amount must be non-negative")

    # Optional: basic line total check if fields exist (won't fail if unitPrice missing)
    try:
        computed = _sum_items(payload["items"])
        if computed > 0 and abs(computed - float(payload["amount"])) > 0.01:
            logger.warning(
                f"Amount mismatch: body={payload['amount']} computed={computed}"
            )
    except Exception:
        pass
def persist(payload: dict) -> None:
    item_full = {
        **payload,  # includes 'padding' if present
        "ts": int(time.time()),
        "status": "OK",
    }

    # Convert all numbers to Decimal recursively for DynamoDB
    item_full = _to_decimal(item_full)
    try:
        resp = table.put_item(
            Item=item_full,
            ConditionExpression="attribute_not_exists(order_id)",
            ReturnConsumedCapacity="TOTAL",
        )
        logger.info(f"DynamoDB put_item OK; consumed: {resp.get('ConsumedCapacity')}")
    except dynamodb.meta.client.exceptions.ConditionalCheckFailedException:
        # Duplicate order_id — treat as success (no reprocess)
        logger.info("Duplicate order_id; skipping put (idempotent).")

# --- SNS alert if needed ---
def maybe_alert(payload: dict) -> None:
    try:
        amt = float(payload["amount"])
    except Exception:
        amt = -1.0

    if amt >= ALERT_AMOUNT:
        message = {
            "event": "LARGE_ORDER",
            "order_id": payload.get("order_id"),
            "user_id": payload.get("user_id"),
            "amount": amt,
            "currency": payload.get("currency", "USD"),
            "ts": int(time.time()),
        }
        resp = sns.publish(TopicArn=SNS_TOPIC_ARN, Message=json.dumps(message))
        logger.info(f"SNS publish response: {resp}")

# --- Lambda handler (partial-batch failure for SQS) ---
def lambda_handler(event, context):
    records = event.get("Records", [])
    failures: List[Dict[str, str]] = []
    logger.info(f"Received event with {len(records)} records")

    for record in records:
        msg_id = record["messageId"]
        try:
            # Parse with Decimal to preserve numeric precision on 'amount' etc.
            payload = json.loads(record.get("body", ""), parse_float=decimal.Decimal)
            logger.info(f"Processing message ID={msg_id} order_id={payload.get('order_id')}")

            if not SKIP_VALIDATION:
                validate(payload)
            else:
                logger.warning("Skipping validation for testing")

            persist(payload)
            maybe_alert(payload)

            logger.info(f"Processed order_id={payload.get('order_id')}")
        except dynamodb.meta.client.exceptions.ConditionalCheckFailedException:
            # Already handled in persist(), but catch here just in case
            logger.info("Duplicate order_id at top level; treating as success.")
        except Exception as e:
            logger.error(f"Failed processing message {msg_id}: {e}", exc_info=True)
            # tell SQS to retry this specific record (or DLQ after maxReceiveCount)
            failures.append({"itemIdentifier": msg_id})

    return {"batchItemFailures": failures}
