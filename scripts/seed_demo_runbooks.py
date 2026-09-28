#!/usr/bin/env python3
"""Seed demo runbooks into the LogSense API for presentation and QA."""

from __future__ import annotations

import argparse
import sys
from typing import Any

import requests

DEMO_RUNBOOKS: list[dict[str, str]] = [
    {
        "title": "Database Connection Pool Exhaustion",
        "category": "database",
        "content": """# Database Connection Pool Exhaustion

## Symptoms
- Rising `ERROR` logs for connection timeout or pool exhaustion
- Application latency spikes
- DB server CPU remains high while app threads wait for a connection

## Immediate triage
1. Check total active database sessions and pool usage.
2. Confirm whether a query is holding connections longer than expected.
3. Inspect recent application deploys or batch jobs for connection leaks.

## Likely root cause
A long-running transaction or leaked session is consuming the pool. This often appears during increased batch load or an application retry storm.

## Remediation
- Restart the affected application worker if a leak is confirmed.
- Tune the pool size or reduce lock contention for heavy queries.
- Kill stale transactions and review slow-query logs.
""",
    },
    {
        "title": "HDFS Block Replication Timeout",
        "category": "application_server",
        "content": """# HDFS Block Replication Timeout

## Symptoms
- `ERROR` messages about block transfer or replication timeout
- Datanodes fail to register or reconnect
- A cluster may show reduced storage health and data imbalance

## Immediate triage
1. Confirm the affected block ID and target datanode.
2. Check network connectivity and disk utilization on the datanode.
3. Review recent metadata or heartbeat failures.

## Likely root cause
The datanode is either overloaded, disconnected, or unable to write because of storage pressure or network instability.

## Remediation
- Move the workload away from the unhealthy node.
- Clear stale temporary blocks and verify disk free space.
- Rebalance replicas and restart the failing datanode when stable.
""",
    },
    {
        "title": "Application Thread Pool Starvation",
        "category": "application_server",
        "content": """# Application Thread Pool Starvation

## Symptoms
- HTTP requests pile up and time out
- Queue depth increases across workers
- Logs show repeated slow response or blocked execution messages

## Immediate triage
1. Inspect saturation of the application worker pool.
2. Review slow DB queries or external dependency latency.
3. Confirm if there is a retry loop or large batch job creating pressure.

## Likely root cause
The app is processing too many requests or waiting on a dependency that is under stress.

## Remediation
- Limit concurrent background jobs during peak periods.
- Increase worker capacity if the bottleneck is bounded by CPU or I/O.
- Add circuit breaking or queue backpressure to prevent cascading failures.
""",
    },
    {
        "title": "Disk Full on DataNode",
        "category": "storage",
        "content": """# Disk Full on DataNode

## Symptoms
- `ERROR` logs mention disk full or checksum mismatch
- Write operations fail for replicas or block transfers
- Storage metrics show near-zero free capacity

## Immediate triage
1. Check free disk space and inode usage.
2. Identify which application or service is filling the disk.
3. Confirm whether recent log rotation or backup jobs contributed to the issue.

## Likely root cause
The datanode or host has insufficient free space for block writes and replication.

## Remediation
- Free space by cleaning temp files and rotated logs.
- Reduce spool or cache size for adjacent services.
- Add storage capacity before the next high-throughput event.
""",
    },
]


def seed_runbooks(base_url: str) -> list[dict[str, Any]]:
    url = f"{base_url.rstrip('/')}/api/v1/runbooks"
    created: list[dict[str, Any]] = []

    for runbook in DEMO_RUNBOOKS:
        response = requests.post(url, json=runbook, timeout=10)
        payload = response.json() if response.content else {}

        if response.status_code in (200, 201):
            created.append({"title": runbook["title"], "status": "created", "payload": payload})
            print(f"[OK] {runbook['title']} -> {payload}")
        else:
            print(f"[FAIL] {runbook['title']} -> HTTP {response.status_code}: {payload}")

    return created


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Populate demo runbooks into LogSense.")
    parser.add_argument(
        "--base-url",
        default="http://localhost:8000",
        help="Base URL for the LogSense API (default: http://localhost:8000)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        seed_runbooks(args.base_url)
    except Exception as exc:  # pragma: no cover - operational script
        print(f"Runbook seeding failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
