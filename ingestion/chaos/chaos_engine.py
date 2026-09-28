#!/usr/bin/env python3
import argparse
import random
import time
from typing import Iterable

import requests

API_URL = "http://localhost:8000/api/v1/logs/ingest"

NORMAL_MESSAGES = [
    "INFO: Block {blk} received successfully from {src}",
    "INFO: Client {client} connected to datanode {host}",
    "INFO: Replication successful for block {blk} to {host}",
    "INFO: Cache hit for block {blk}",
    "WARN: Temporary slow response from {host} for block {blk}",
    "INFO: Heartbeat received from {host}",
    "INFO: Lease renewed for block {blk}",
]

FAILURE_MESSAGES = [
    "ERROR: Receiving block {blk} src: /10.0.0.2:50010 dest: /10.0.0.3:50010: DataXceiver error: Network is unreachable",
    "ERROR: DatanodeRegistrationException: DataNode {host} failed to register with namenode",
    "WARN: Slow read from {host} for block {blk}: expected 1000ms, got 42000ms",
    "ERROR: Block {blk} is invalid: checksum mismatch while writing to local disk",
    "ERROR: Unable to replicate block {blk} to datanode {host}: connection reset by peer",
    "ERROR: Disk full on {host} while writing block {blk}",
    "ERROR: Failed to transfer block {blk} due to timeout from {host}",
]

HOSTS = [
    "app-server-01",
    "app-server-02",
    "db-server-01",
    "hdfs-datanode-01",
    "hdfs-datanode-02",
    "hdfs-namenode-01",
]

CLIENTS = ["spark-client", "etl-job", "api-gateway", "batch-worker"]


def make_block_id() -> str:
    return f"blk_{random.randint(10_000_000_000_000, 99_999_999_999_999)}"


def choose_log_level(message: str) -> str:
    upper_message = message.upper()
    if "ERROR" in upper_message or "FAIL" in upper_message or "EXCEPTION" in upper_message:
        return "ERROR"
    if "WARN" in upper_message or "SLOW" in upper_message:
        return "WARN"
    return "INFO"


def build_normal_message() -> str:
    host = random.choice(HOSTS)
    block = make_block_id()
    src = random.choice(HOSTS)
    client = random.choice(CLIENTS)
    template = random.choice(NORMAL_MESSAGES)
    return template.format(blk=block, host=host, src=src, client=client)


def build_failure_message() -> str:
    host = random.choice(HOSTS)
    block = make_block_id()
    template = random.choice(FAILURE_MESSAGES)
    return template.format(blk=block, host=host)


def send_event(raw_message: str, source_host: str) -> None:
    payload = {
        "source_host": source_host,
        "log_level": choose_log_level(raw_message),
        "raw_message": raw_message,
    }

    try:
        response = requests.post(API_URL, json=payload, timeout=10)
        status = "OK" if response.ok else f"ERROR({response.status_code})"
        print(f"[{status}] {source_host} :: {raw_message[:120]}")
    except Exception as exc:
        print(f"[FAIL] {source_host} :: {exc}")


def generate_cycle(crash_mode: bool = False) -> None:
    if crash_mode:
        for _ in range(random.randint(8, 15)):
            message = build_failure_message()
            source_host = random.choice(HOSTS)
            send_event(message, source_host)
            time.sleep(0.2)

        for _ in range(3):
            message = build_normal_message()
            send_event(message, random.choice(HOSTS))
    else:
        for _ in range(random.randint(5, 12)):
            if random.random() < 0.18:
                message = build_failure_message()
            else:
                message = build_normal_message()
            source_host = random.choice(HOSTS)
            send_event(message, source_host)
            time.sleep(0.5)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate normal + failure log traffic for LogSense.")
    parser.add_argument("--crash", action="store_true", help="Generate a concentrated failure burst")
    parser.add_argument("--loops", type=int, default=1, help="Number of cycles to emit")
    parser.add_argument("--sleep", type=float, default=1.0, help="Seconds between cycles")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    print(f"Sending logs to {API_URL}")
    for i in range(args.loops):
        print(f"\n=== cycle {i + 1}/{args.loops} ===")
        generate_cycle(crash_mode=args.crash)
        if i < args.loops - 1:
            time.sleep(args.sleep)


if __name__ == "__main__":
    main()
