#!/usr/bin/env python3
"""Replay HDFS log lines into the LogSense ingestion API at a configurable rate.

This script reads a real HDFS log dataset and emits each line as a log ingestion
request to POST /api/v1/logs/ingest. It intentionally keeps block IDs repeated in
sequence so the anomaly detector can observe block-level aggregation under load.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import threading
import time
from pathlib import Path
from typing import Iterable

import requests


DEFAULT_URL = "http://localhost:8000/api/v1/logs/ingest"
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FILE = PROJECT_ROOT / "backend" / "ai_pipeline" / "data" / "HDFS.log"
BLOCK_RE = re.compile(r"(blk_-?\d+)")


def resolve_default_data_file(path: Path | None = None) -> Path:
    candidate = path or DEFAULT_FILE
    if candidate.exists():
        return candidate

    search_dir = candidate.parent if candidate.parent.exists() else PROJECT_ROOT / "backend" / "ai_pipeline" / "data"
    for name in ("HDFS.log", "hdfs.log", "HDFS.LOG", "hdfs.LOG"):
        resolved = search_dir / name
        if resolved.exists():
            return resolved
    return candidate


def normalize_log_level(raw_message: str) -> str:
    message = raw_message.upper()
    if "ERROR" in message or "FATAL" in message:
        return "ERROR"
    if "WARN" in message:
        return "WARN"
    return "INFO"


def iter_log_lines(path: Path) -> Iterable[str]:
    if not path.exists():
        raise FileNotFoundError(f"HDFS log file not found: {path}")

    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            line = line.strip()
            if line:
                yield line


def chunked(iterable: Iterable[str], size: int) -> Iterable[list[str]]:
    batch: list[str] = []
    for item in iterable:
        batch.append(item)
        if len(batch) >= size:
            yield batch
            batch = []
    if batch:
        yield batch


def post_log(url: str, raw_message: str, source_host: str) -> tuple[bool, str | None]:
    payload = {
        "source_host": source_host,
        "log_level": normalize_log_level(raw_message),
        "raw_message": raw_message,
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
        return response.ok, response.text
    except requests.RequestException as exc:  # pragma: no cover - runtime networking
        return False, str(exc)


def rate_limited_stream(
    lines: Iterable[str],
    url: str,
    source_host: str,
    rate_per_second: float,
    batch_size: int = 1,
    max_messages: int | None = None,
) -> tuple[int, int]:
    interval = 1.0 / rate_per_second
    sent = 0
    failed = 0

    for batch in chunked(lines, batch_size):
        if max_messages is not None and sent >= max_messages:
            break

        started_at = time.perf_counter()
        for raw_message in batch:
            if max_messages is not None and sent >= max_messages:
                break

            ok, reason = post_log(url, raw_message, source_host)
            if not ok:
                failed += 1
                print(f"[FAIL] {raw_message[:120]} -> {reason}", file=sys.stderr)

            sent += 1
            next_tick = started_at + ((sent / max(1, batch_size)) * interval)
            sleep_for = max(0.0, next_tick - time.perf_counter())
            if sleep_for > 0:
                time.sleep(sleep_for)

    return sent, failed


def stream_forever(file_path: Path, url: str, source_host: str, rate_per_second: float, replay_limit: int | None) -> None:
    if replay_limit is not None:
        print(f"Streaming {replay_limit} logs from {file_path} at {rate_per_second:.1f} logs/sec")
    else:
        print(f"Streaming HDFS logs from {file_path} continuously at {rate_per_second:.1f} logs/sec")

    while True:
        lines = list(iter_log_lines(file_path))
        if not lines:
            raise RuntimeError(f"No log lines found in {file_path}")

        if replay_limit is not None:
            lines = lines[:replay_limit]

        sent, failed = rate_limited_stream(
            lines=lines,
            url=url,
            source_host=source_host,
            rate_per_second=rate_per_second,
            batch_size=1,
            max_messages=replay_limit,
        )
        print(f"Sent {sent} logs; failed={failed}")

        if replay_limit is not None:
            break
        time.sleep(1.0)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Replay HDFS logs into the LogSense ingest API.")
    parser.add_argument("--file", type=Path, default=DEFAULT_FILE, help="Path to the HDFS log dataset")
    parser.add_argument("--url", default=DEFAULT_URL, help="Log ingest endpoint URL")
    parser.add_argument("--source-host", default="hdfs-datanode-01", help="source_host value sent with each ingested log")
    parser.add_argument("--rate", type=float, default=25.0, help="Target logs/sec (for example 20-50)")
    parser.add_argument("--limit", type=int, default=None, help="Optional max number of lines to send before exiting")
    parser.add_argument("--loop", action="store_true", help="Keep replaying the file continuously after the first pass")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    file_path = resolve_default_data_file(args.file)
    file_path = file_path.resolve() if file_path.is_absolute() else (Path.cwd() / file_path).resolve()

    if not file_path.exists():
        print(f"HDFS log file not found: {file_path}", file=sys.stderr)
        print("Tip: place HDFS.log or hdfs.log under backend/ai_pipeline/data/ or pass --file /path/to/HDFS.log", file=sys.stderr)
        return 1

    try:
        if args.loop:
            stream_forever(file_path, args.url, args.source_host, args.rate, None)
        else:
            lines = list(iter_log_lines(file_path))
            if args.limit is not None:
                lines = lines[: args.limit]
            sent, failed = rate_limited_stream(lines, args.url, args.source_host, args.rate, batch_size=1, max_messages=args.limit)
            print(f"Completed replay: sent={sent}, failed={failed}")
    except KeyboardInterrupt:
        print("\nStopping HDFS log replay.", file=sys.stderr)
        return 0
    except Exception as exc:  # pragma: no cover - runtime safeguard
        print(f"Replay failed: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
