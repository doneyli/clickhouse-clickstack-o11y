#!/usr/bin/env python3
"""
Utility to query ClickHouse directly for inspecting ingested data.

Usage:
    python query_clickhouse.py --query "SELECT count(*) FROM log_stream"
    python query_clickhouse.py --summary      # Data overview
    python query_clickhouse.py --attributes   # All attribute keys
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

    # Row counts by type
    print("\n--- Row Counts by Type ---")
    try:
        result = client.query("""
            SELECT
                type,
                count(*) as cnt
            FROM log_stream
            GROUP BY type
            ORDER BY cnt DESC
        """)
        if result.result_rows:
            for row in result.result_rows:
                print(f"  {row[0]:<15} {row[1]:>10,}")
        else:
            print("  (no data)")
    except Exception as e:
        print(f"  (No data yet: {e})")

    # Data distribution
    print("\n--- Data Overview ---")
    try:
        result = client.query("""
            SELECT
                count(*) as total_rows,
                count(DISTINCT _service) as services,
                count(DISTINCT span_name) as span_names,
                min(timestamp) as earliest,
                max(timestamp) as latest
            FROM log_stream
        """)
        if result.result_rows:
            row = result.result_rows[0]
            print(f"  Total rows:    {row[0]:,}")
            print(f"  Services:      {row[1]}")
            print(f"  Span names:    {row[2]}")
            print(f"  Earliest:      {row[3]}")
            print(f"  Latest:        {row[4]}")
    except Exception as e:
        print(f"  (No data yet: {e})")

    # Per-service breakdown
    print("\n--- Per-Service Breakdown ---")
    try:
        result = client.query("""
            SELECT
                _service as service,
                count(*) as cnt,
                round(avg(_duration), 0) as avg_latency_ms
            FROM log_stream
            WHERE type = 'span'
            GROUP BY service
            ORDER BY cnt DESC
            LIMIT 20
        """)
        if result.result_rows:
            print(f"  {'Service':<40} {'Count':>10} {'Avg ms':>10}")
            print(f"  {'-'*40} {'-'*10} {'-'*10}")
            for row in result.result_rows:
                print(f"  {row[0]:<40} {row[1]:>10,} {row[2]:>10,.0f}")
    except Exception as e:
        print(f"  (No span data yet: {e})")


def show_attributes():
    """Show all attribute keys found in the data."""
    client = get_client()

    print("String attribute keys in log_stream:")
    print("-" * 50)
    try:
        result = client.query("""
            SELECT DISTINCT arrayJoin(mapKeys(_string_attributes)) as attr_key
            FROM log_stream
            ORDER BY attr_key
            LIMIT 100
        """)
        for row in result.result_rows:
            print(f"  {row[0]}")
        if not result.result_rows:
            print("  (none found)")
    except Exception as e:
        print(f"  Error: {e}")

    print("\nNumber attribute keys in log_stream:")
    print("-" * 50)
    try:
        result = client.query("""
            SELECT DISTINCT arrayJoin(mapKeys(_number_attributes)) as attr_key
            FROM log_stream
            ORDER BY attr_key
            LIMIT 100
        """)
        for row in result.result_rows:
            print(f"  {row[0]}")
        if not result.result_rows:
            print("  (none found)")
    except Exception as e:
        print(f"  Error: {e}")


def show_services():
    """Show all services in the data."""
    client = get_client()
    print("Services in log_stream:")
    print("-" * 40)
    try:
        result = client.query("""
            SELECT DISTINCT _service
            FROM log_stream
            ORDER BY _service
        """)
        for row in result.result_rows:
            print(f"  {row[0]}")
        if not result.result_rows:
            print("  (none found)")
    except Exception as e:
        print(f"  Error: {e}")


def main():
    parser = argparse.ArgumentParser(description="Query ClickHouse for data inspection")
    parser.add_argument("--query", type=str, help="Run a custom SQL query")
    parser.add_argument("--summary", action="store_true", help="Show data overview")
    parser.add_argument("--attributes", action="store_true", help="Show all attribute keys")
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
        show_summary()


if __name__ == "__main__":
    main()
