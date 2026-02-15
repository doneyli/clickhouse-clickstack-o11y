#!/usr/bin/env python3
"""
Utility to query ClickHouse directly for inspecting ingested trace data.

Usage:
    python query_clickhouse.py --query "SELECT count(*) FROM log_stream"
    python query_clickhouse.py --summary      # Data summary
    python query_clickhouse.py --attributes   # All gen_ai.* attributes
    python query_clickhouse.py --services     # All services
"""

import argparse
import os
import sys

from dotenv import load_dotenv

load_dotenv()


def get_client():
    """Create a ClickHouse client, trying default user first then api/api."""
    import clickhouse_connect

    ch_url = os.getenv("CLICKHOUSE_URL", "http://localhost:8123")
    host = ch_url.replace("http://", "").replace("https://", "").split(":")[0]
    port = int(ch_url.split(":")[-1]) if ":" in ch_url.split("//")[-1] else 8123

    # Try default user with no password first
    try:
        client = clickhouse_connect.get_client(host=host, port=port, username="default", password="")
        client.query("SELECT 1")
        return client
    except Exception:
        pass

    # Fallback to api/api
    try:
        client = clickhouse_connect.get_client(host=host, port=port, username="api", password="api")
        client.query("SELECT 1")
        return client
    except Exception as e:
        print(f"ERROR: Could not connect to ClickHouse at {ch_url}")
        print(f"  Tried users: default (no password), api/api")
        print(f"  Error: {e}")
        sys.exit(1)


def run_query(query: str):
    """Execute a query and print results."""
    client = get_client()
    result = client.query(query)
    if result.column_names:
        # Print header
        header = " | ".join(str(c) for c in result.column_names)
        print(header)
        print("-" * len(header))
    for row in result.result_rows:
        print(" | ".join(str(v) for v in row))


def show_summary():
    """Show a summary of ingested data."""
    client = get_client()

    print("=" * 60)
    print("CLICKHOUSE DATA SUMMARY")
    print("=" * 60)

    # Tables
    print("\n--- Tables ---")
    result = client.query("SHOW TABLES")
    for row in result.result_rows:
        print(f"  {row[0]}")

    # Data distribution
    print("\n--- Trace Data Distribution ---")
    try:
        result = client.query("""
            SELECT
                count(*) as total_traces,
                countIf(_string_attributes['gen_ai.request.model'] != '') as llm_traces,
                min(timestamp) as earliest,
                max(timestamp) as latest,
                count(DISTINCT _service) as services,
                count(DISTINCT _string_attributes['gen_ai.request.model']) - 1 as models
            FROM log_stream
            WHERE type = 'span'
        """)
        if result.result_rows:
            row = result.result_rows[0]
            print(f"  Total traces:  {row[0]:,}")
            print(f"  LLM traces:    {row[1]:,}")
            print(f"  Earliest:      {row[2]}")
            print(f"  Latest:        {row[3]}")
            print(f"  Services:      {row[4]}")
            print(f"  Models:        {row[5]}")
    except Exception as e:
        print(f"  (No trace data yet: {e})")

    # Per-model stats
    print("\n--- Per-Model Stats ---")
    try:
        result = client.query("""
            SELECT
                _string_attributes['gen_ai.request.model'] as model,
                count(*) as cnt,
                round(avg(_number_attributes['gen_ai.usage.input_tokens']), 0) as avg_input,
                round(avg(_number_attributes['gen_ai.usage.output_tokens']), 0) as avg_output,
                round(avg(_duration), 0) as avg_latency_ms
            FROM log_stream
            WHERE type = 'span'
              AND _string_attributes['gen_ai.request.model'] != ''
            GROUP BY model
            ORDER BY cnt DESC
        """)
        if result.result_rows:
            print(f"  {'Model':<35} {'Count':>8} {'Avg In':>8} {'Avg Out':>8} {'Avg ms':>8}")
            print(f"  {'-'*35} {'-'*8} {'-'*8} {'-'*8} {'-'*8}")
            for row in result.result_rows:
                print(f"  {row[0]:<35} {row[1]:>8,} {row[2]:>8,.0f} {row[3]:>8,.0f} {row[4]:>8,.0f}")
    except Exception as e:
        print(f"  (No LLM data yet: {e})")


def show_attributes():
    """Show all gen_ai.* attributes found in traces."""
    client = get_client()
    print("gen_ai.* attributes found in log_stream:")
    print("-" * 40)
    try:
        result = client.query("""
            SELECT DISTINCT arrayJoin(mapKeys(_string_attributes)) as attr_key
            FROM log_stream
            WHERE type = 'span'
              AND attr_key LIKE 'gen_ai.%'
            ORDER BY attr_key
        """)
        for row in result.result_rows:
            print(f"  {row[0]}")
        if not result.result_rows:
            print("  (none found)")
    except Exception as e:
        print(f"  Error: {e}")


def show_services():
    """Show all services in traces."""
    client = get_client()
    print("Services in log_stream:")
    print("-" * 40)
    try:
        result = client.query("""
            SELECT DISTINCT _service
            FROM log_stream
            WHERE type = 'span'
            ORDER BY _service
        """)
        for row in result.result_rows:
            print(f"  {row[0]}")
        if not result.result_rows:
            print("  (none found)")
    except Exception as e:
        print(f"  Error: {e}")


def main():
    parser = argparse.ArgumentParser(description="Query ClickHouse for trace data inspection")
    parser.add_argument("--query", type=str, help="Run a custom SQL query")
    parser.add_argument("--summary", action="store_true", help="Show data summary")
    parser.add_argument("--attributes", action="store_true", help="Show gen_ai.* attributes")
    parser.add_argument("--services", action="store_true", help="Show all services")
    args = parser.parse_args()

    if args.query:
        run_query(args.query)
    elif args.summary:
        show_summary()
    elif args.attributes:
        show_attributes()
    elif args.services:
        show_services()
    else:
        # Default: show summary
        show_summary()


if __name__ == "__main__":
    main()
