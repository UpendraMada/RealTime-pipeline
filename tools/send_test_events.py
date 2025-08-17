import json
import uuid
import random
import time
import argparse
from typing import Dict, Any, List
import boto3
from botocore.exceptions import ClientError

# ---------- Payload Creation ----------
def make_base_payload() -> Dict[str, Any]:
    amount = round(random.uniform(10, 1200), 2)
    return {
        "order_id": str(uuid.uuid4()),
        "user_id": f"user-{random.randint(1, 999_999)}",
        "amount": amount,
        "currency": "USD",
        "items": [
            {"sku": f"SKU-{random.randint(100, 999)}", "qty": random.randint(1, 5)}
            for _ in range(random.randint(1, 4))
        ],
    }

def make_padded_payload(target_kb: int) -> Dict[str, Any]:
    payload = make_base_payload()
    if target_kb <= 0:
        return payload
    # Estimate size and pad safely under 256KB
    body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    target_bytes = target_kb * 1024
    target_bytes = min(target_bytes, 240 * 1024)  # Leave headroom
    pad_len = max(0, target_bytes - len(body))
    if pad_len > 0:
        payload["padding"] = "x" * pad_len
    return payload

# ---------- Safe SQS Sending ----------
def _send_with_split_on_413(sqs, queue_url, sub):
    """Send SQS batch; on HTTP 413, split and retry."""
    try:
        return sqs.send_message_batch(QueueUrl=queue_url, Entries=sub)
    except ClientError as ex:
        error_code = ex.response.get("Error", {}).get("Code")
        if error_code in ("413", "RequestEntityTooLarge"):
            if len(sub) == 1:
                raise  # Can't split further
            mid = len(sub) // 2
            _send_with_split_on_413(sqs, queue_url, sub[:mid])
            return _send_with_split_on_413(sqs, queue_url, sub[mid:])
        raise

def send_batch(sqs, queue_url: str, entries: List[Dict[str, Any]], retry=3, backoff=0.5):
    """Send messages in safe chunks, retrying on failure."""
    for attempt in range(retry):
        resp = _send_with_split_on_413(sqs, queue_url, entries)
        failed = resp.get("Failed", [])
        if failed:
            for f in failed:
                print(f" Failed ID {f['Id']} - {f.get('Message')}")
        if not failed:
            return
        id_to_entry = {e["Id"]: e for e in entries}
        entries = [id_to_entry[f["Id"]] for f in failed if f.get("Id") in id_to_entry]
        time.sleep(backoff * (2 ** attempt))
    ids = [f.get("Id") for f in failed]
    raise RuntimeError(f"Failed to send entries after retries: {ids}")

# ---------- Main Sending Logic ----------
def main(queue_url: str, n: int, target_kb: int, batch_size: int, rate: float):
    sqs = boto3.client("sqs")
    delay_per_msg = 0 if rate <= 0 else 1.0 / rate
    next_tick = time.perf_counter()
    entries = []
    sent = 0
    for i in range(n):
        payload = make_padded_payload(target_kb)
        entry = {
            "Id": str(uuid.uuid4()),  # Always unique
            "MessageBody": json.dumps(payload, separators=(",", ":")),
        }
        entries.append(entry)

        if len(entries) == batch_size or i == n - 1:
            print(f"Sending batch of {len(entries)} messages (target size {target_kb} KB)")
            send_batch(sqs, queue_url, entries)
            sent += len(entries)
            entries = []

        if delay_per_msg > 0:
            next_tick += delay_per_msg
            sleep = next_tick - time.perf_counter()
            if sleep > 0:
                time.sleep(sleep)

        if sent and sent % 1000 == 0:
            print(f" Sent {sent}/{n} messages…")

    print(f" Done. Sent {sent} messages.")

# ---------- CLI Entry ----------
if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--queue-url", required=True)
    ap.add_argument("--count", type=int, default=1000)
    ap.add_argument("--target-kb", type=int, default=200, help="Target size per message (KB), <=240 recommended")
    ap.add_argument("--batch-size", type=int, default=10)
    ap.add_argument("--rate", type=float, default=0, help="msgs/sec, 0 = as fast as possible")
    args = ap.parse_args()

    if not (1 <= args.batch_size <= 10):
        raise SystemExit("--batch-size must be between 1 and 10")

    main(args.queue_url, args.count, args.target_kb, args.batch_size, args.rate)
