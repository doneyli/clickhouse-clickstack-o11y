#!/usr/bin/env python3
"""
Continuously stream sample data into HyperDX with current timestamps.

Replays sample.tar.gz in a loop, rewriting timestamps to "now" so that
HyperDX Live Tail shows a continuous flow of data.

Usage:
    python stream_data.py                  # Default: 10-min cycles, all signals
    python stream_data.py --cycle 60       # Compress into 1-min cycles
    python stream_data.py --rate 2.0       # 2x speed multiplier
    python stream_data.py --traces         # Only stream traces
    python stream_data.py --logs --metrics # Logs + metrics only
    python stream_data.py -v               # Verbose (every batch)
    python stream_data.py -q               # Quiet (summary every 30s)
"""

from __future__ import annotations

import argparse
import io
import os
import re
import signal
import sys
import tarfile
import time

import requests
from dotenv import load_dotenv

load_dotenv()

# Regex to match all OTLP nanosecond timestamp fields (quoted string values)
TIMESTAMP_RE = re.compile(
    r'"(startTimeUnixNano|endTimeUnixNano|timeUnixNano|observedTimeUnixNano)"\s*:\s*"(\d+)"'
)

SIGNAL_TYPES = ("traces", "logs", "metrics")


def load_batches(tar_path: str, signals: set[str]) -> list[tuple[str, int, int, str]]:
    """Load batches from sample.tar.gz.

    Returns (signal_type, sort_ts_ns, original_ts_ns, payload).
    sort_ts_ns is clamped to p5–p95 for pacing; original_ts_ns is the real
    min timestamp for correct payload offset computation.
    """
    raw = []
    with tarfile.open(tar_path, "r:gz") as tf:
        for member in tf.getmembers():
            if not member.isfile():
                continue
            signal_type = member.name.replace(".json", "")
            if signal_type not in signals:
                continue
            f = tf.extractfile(member)
            if f is None:
                continue
            for line in io.TextIOWrapper(f, encoding="utf-8"):
                line = line.strip()
                if not line:
                    continue
                ts = extract_min_timestamp(line)
                if ts is not None:
                    raw.append((signal_type, ts, line))

    if not raw:
        return []

    # Compute p5/p95 bounds and clamp outliers for pacing
    timestamps = sorted(t[1] for t in raw)
    lo = timestamps[len(timestamps) // 20]
    hi = timestamps[19 * len(timestamps) // 20]

    batches = []
    for sig, ts, payload in raw:
        sort_ts = max(lo, min(hi, ts))
        batches.append((sig, sort_ts, ts, payload))

    batches.sort(key=lambda b: b[1])
    return batches


def extract_min_timestamp(payload: str) -> int | None:
    """Extract the smallest nanosecond timestamp from an OTLP JSON line."""
    matches = TIMESTAMP_RE.findall(payload)
    if not matches:
        return None
    return min(int(m[1]) for m in matches)


def rewrite_timestamps(payload: str, offset_ns: int) -> str:
    """Shift all nanosecond timestamps by offset_ns."""
    def replace_ts(m):
        field_name = m.group(1)
        old_ts = int(m.group(2))
        new_ts = old_ts + offset_ns
        return f'"{field_name}":"{new_ts}"'
    return TIMESTAMP_RE.sub(replace_ts, payload)


def preflight(tar_path: str, otlp_endpoint: str, api_key: str):
    """Verify prerequisites before streaming."""
    errors = []

    if not os.path.exists(tar_path):
        errors.append(f"{tar_path} not found. Run ./setup.sh first.")

    if not api_key:
        errors.append(
            "HYPERDX_API_KEY not set in .env. Run ./setup.sh or set it manually."
        )

    try:
        r = requests.get(f"{otlp_endpoint.rstrip('/')}/", timeout=3)
        # OTel collector returns various codes; any response means it's up
    except requests.ConnectionError:
        errors.append(
            f"Cannot reach OTLP endpoint at {otlp_endpoint}. "
            "Is the HyperDX container running? (docker compose up -d)"
        )

    if errors:
        for e in errors:
            print(f"  ERROR: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Stream sample data into HyperDX with live timestamps"
    )
    parser.add_argument(
        "--cycle", type=float, default=600,
        help="Cycle duration in seconds (default: 600 = 10 min)",
    )
    parser.add_argument(
        "--rate", type=float, default=1.0,
        help="Speed multiplier (2.0 = twice as fast)",
    )
    parser.add_argument("--traces", action="store_true", help="Stream traces only")
    parser.add_argument("--logs", action="store_true", help="Stream logs only")
    parser.add_argument("--metrics", action="store_true", help="Stream metrics only")
    parser.add_argument("-v", "--verbose", action="store_true", help="Print every batch")
    parser.add_argument("-q", "--quiet", action="store_true", help="Summary every 30s only")
    args = parser.parse_args()

    # Determine which signals to stream
    selected = set()
    if args.traces:
        selected.add("traces")
    if args.logs:
        selected.add("logs")
    if args.metrics:
        selected.add("metrics")
    if not selected:
        selected = set(SIGNAL_TYPES)

    tar_path = "sample.tar.gz"
    otlp_endpoint = os.getenv("OTLP_ENDPOINT", "http://localhost:4318")
    api_key = os.getenv("HYPERDX_API_KEY", "")

    # Preflight checks
    preflight(tar_path, otlp_endpoint, api_key)

    # Load and sort batches
    print(f"Loading batches from {tar_path}...")
    batches = load_batches(tar_path, selected)
    if not batches:
        print("No batches found. Check sample.tar.gz contents.", file=sys.stderr)
        sys.exit(1)

    # Compute original timeline
    original_start_ns = batches[0][1]
    original_end_ns = batches[-1][1]
    original_duration_ns = original_end_ns - original_start_ns
    if original_duration_ns <= 0:
        original_duration_ns = 1  # avoid division by zero

    original_duration_s = original_duration_ns / 1e9
    cycle_s = args.cycle
    compression_ratio = cycle_s / original_duration_s

    # Count by signal type
    counts = {}
    for sig, _, _, _ in batches:
        counts[sig] = counts.get(sig, 0) + 1
    count_str = " + ".join(f"{counts.get(s, 0)} {s}" for s in SIGNAL_TYPES if s in counts)

    print(
        f"Streaming {len(batches)} batches ({count_str}) in {cycle_s:.0f}s cycles "
        f"(original span: {original_duration_s / 3600:.1f}h, rate: {args.rate}x)"
    )
    print("Ctrl+C to stop\n")

    # Setup HTTP session
    session = requests.Session()
    session.headers.update({
        "Content-Type": "application/json",
        "authorization": api_key,
    })

    # Graceful shutdown
    shutdown = False

    def handle_signal(signum, frame):
        nonlocal shutdown
        shutdown = True

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    # Streaming loop
    cycle_num = 0
    total_sent = 0
    total_errors = 0
    stream_start = time.time()

    report_interval = 30.0 if args.quiet else 10.0

    try:
        while not shutdown:
            cycle_num += 1
            cycle_start = time.time()
            cycle_start_ns = int(cycle_start * 1e9)

            cycle_sent = 0
            cycle_errors = 0
            cycle_counts = {s: 0 for s in SIGNAL_TYPES}
            last_report = cycle_start

            for i, (signal_type, sort_ts, orig_ts, payload) in enumerate(batches):
                if shutdown:
                    break

                # Compute target send time within this cycle (using clamped sort_ts)
                batch_offset_ns = sort_ts - original_start_ns
                target_time = cycle_start + (batch_offset_ns / 1e9) * compression_ratio

                # Apply rate multiplier to sleep
                now = time.time()
                sleep_time = (target_time - now) / args.rate
                if sleep_time > 0:
                    # Sleep in small increments to check shutdown flag
                    end_sleep = now + sleep_time
                    while time.time() < end_sleep and not shutdown:
                        time.sleep(min(0.1, end_sleep - time.time()))

                if shutdown:
                    break

                # Compress timestamps to fit within the cycle duration,
                # and use clamped sort_ts as baseline to avoid outlier blowup
                compressed_offset_ns = int(batch_offset_ns * compression_ratio)
                desired_ts_ns = cycle_start_ns + compressed_offset_ns
                ts_offset_ns = desired_ts_ns - sort_ts

                # Rewrite timestamps and send
                rewritten = rewrite_timestamps(payload, ts_offset_ns)
                endpoint = f"{otlp_endpoint}/v1/{signal_type}"

                try:
                    r = session.post(endpoint, data=rewritten, timeout=5)
                    if r.status_code >= 400:
                        cycle_errors += 1
                        if args.verbose:
                            print(f"  WARN: {signal_type} HTTP {r.status_code}")
                except requests.RequestException as e:
                    cycle_errors += 1
                    if args.verbose:
                        print(f"  WARN: {signal_type} {e}")

                cycle_sent += 1
                cycle_counts[signal_type] = cycle_counts.get(signal_type, 0) + 1

                # Periodic reporting
                now = time.time()
                if args.verbose:
                    print(
                        f"  [{time.strftime('%H:%M:%S')}] {signal_type} batch {i + 1}/{len(batches)}"
                    )
                elif now - last_report >= report_interval:
                    elapsed = now - cycle_start
                    rate = cycle_sent / elapsed if elapsed > 0 else 0
                    parts = " ".join(
                        f"{s}: {cycle_counts.get(s, 0)}" for s in SIGNAL_TYPES if s in selected
                    )
                    err_str = f" errors: {cycle_errors}" if cycle_errors else ""
                    print(
                        f"[{time.strftime('%H:%M:%S')}] {cycle_sent} batches | "
                        f"{parts} | {rate:.1f}/s{err_str}"
                    )
                    last_report = now

            # Cycle complete
            total_sent += cycle_sent
            total_errors += cycle_errors
            cycle_elapsed = time.time() - cycle_start

            if not shutdown:
                print(
                    f"\n--- Cycle {cycle_num} complete "
                    f"({cycle_elapsed:.1f}s, {cycle_sent} batches"
                    f"{f', {cycle_errors} errors' if cycle_errors else ''}). "
                    f"Restarting ---\n"
                )

    finally:
        elapsed = time.time() - stream_start
        print(
            f"\nStopped after {cycle_num} cycle(s), {elapsed:.0f}s total. "
            f"Sent {total_sent} batches ({total_errors} errors)."
        )


if __name__ == "__main__":
    main()
