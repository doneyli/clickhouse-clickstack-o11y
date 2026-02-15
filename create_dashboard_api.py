#!/usr/bin/env python3
"""
Create HyperDX dashboards via the REST API v2.

IMPORTANT LIMITATION: The external API v2 uses `series` format tiles with
`dataSource: "events"` or `"metrics"`. It does NOT support traces (otel_traces).
LLM data lives in traces, so this API CANNOT build LLM observability dashboards.
This script is included for demonstration of the API pattern only.

Use create_dashboard_mongo.sh for trace-based dashboards instead.

Usage:
    python create_dashboard_api.py --create    # Create a sample log dashboard
    python create_dashboard_api.py --list      # List dashboards
    python create_dashboard_api.py --delete ID # Delete a dashboard
"""

import argparse
import json
import os
import sys

import requests
from dotenv import load_dotenv

load_dotenv()

API_URL = os.getenv("HYPERDX_API_URL", "http://localhost:8000")
API_KEY = os.getenv("HYPERDX_API_KEY", "")


def get_headers():
    if not API_KEY:
        print("WARNING: HYPERDX_API_KEY not set in .env")
        print("  Retrieve with: docker exec hyperdx-local mongo --quiet --eval \\")
        print("    'db=db.getSiblingDB(\"hyperdx\"); print(db.users.findOne({}).accessKey)'")
    return {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }


def list_dashboards():
    """List all dashboards via API."""
    resp = requests.get(f"{API_URL}/api/v2/dashboards", headers=get_headers())
    if resp.status_code != 200:
        print(f"Error {resp.status_code}: {resp.text}")
        return
    dashboards = resp.json()
    if not dashboards:
        print("No dashboards found.")
        return
    print(f"Found {len(dashboards)} dashboard(s):")
    for d in dashboards:
        tile_count = len(d.get("tiles", []))
        tags = ", ".join(d.get("tags", []))
        print(f"  [{d['_id']}] {d['name']} ({tile_count} tiles) [{tags}]")


def create_sample_dashboard():
    """Create a sample Log Activity Dashboard to demonstrate the API pattern.

    NOTE: This only works with logs/events data source, NOT traces.
    For LLM observability dashboards (which use traces), use create_dashboard_mongo.sh.
    """
    dashboard = {
        "name": "Log Activity Dashboard (API Demo)",
        "tiles": [
            {
                "name": "Total Log Events",
                "x": 0, "y": 0, "w": 4, "h": 3,
                "series": [{
                    "type": "number",
                    "dataSource": "events",
                    "aggFn": "count",
                    "where": "",
                }],
            },
            {
                "name": "Log Events Over Time",
                "x": 4, "y": 0, "w": 8, "h": 3,
                "series": [{
                    "type": "time",
                    "dataSource": "events",
                    "aggFn": "count",
                    "where": "",
                }],
            },
            {
                "name": "Error Logs",
                "x": 0, "y": 3, "w": 6, "h": 3,
                "series": [{
                    "type": "time",
                    "dataSource": "events",
                    "aggFn": "count",
                    "where": "level:error",
                }],
            },
            {
                "name": "Logs by Service",
                "x": 6, "y": 3, "w": 6, "h": 3,
                "series": [{
                    "type": "time",
                    "dataSource": "events",
                    "aggFn": "count",
                    "where": "",
                    "groupBy": ["service"],
                }],
            },
        ],
        "tags": ["demo", "api-v2"],
    }

    print("Creating 'Log Activity Dashboard (API Demo)' via REST API v2...")
    print()
    print("NOTE: This API only supports logs/events. For LLM trace dashboards,")
    print("      use: bash create_dashboard_mongo.sh --create")
    print()

    resp = requests.post(
        f"{API_URL}/api/v2/dashboards",
        headers=get_headers(),
        json=dashboard,
    )
    if resp.status_code in (200, 201):
        result = resp.json()
        dashboard_id = result.get("_id", "unknown")
        ui_url = os.getenv("HYPERDX_UI_URL", "http://localhost:8080")
        print(f"Dashboard created: {dashboard_id}")
        print(f"View at: {ui_url}/dashboards/{dashboard_id}")
    else:
        print(f"Error {resp.status_code}: {resp.text}")


def delete_dashboard(dashboard_id: str):
    """Delete a dashboard by ID."""
    resp = requests.delete(
        f"{API_URL}/api/v2/dashboards/{dashboard_id}",
        headers=get_headers(),
    )
    if resp.status_code in (200, 204):
        print(f"Dashboard {dashboard_id} deleted.")
    else:
        print(f"Error {resp.status_code}: {resp.text}")


def main():
    parser = argparse.ArgumentParser(
        description="Create HyperDX dashboards via REST API v2 (logs/events only)",
        epilog="NOTE: API v2 does NOT support traces. Use create_dashboard_mongo.sh for LLM dashboards.",
    )
    parser.add_argument("--list", action="store_true", help="List all dashboards")
    parser.add_argument("--create", action="store_true", help="Create sample log dashboard")
    parser.add_argument("--delete", type=str, metavar="ID", help="Delete dashboard by ID")
    args = parser.parse_args()

    if args.list:
        list_dashboards()
    elif args.create:
        create_sample_dashboard()
    elif args.delete:
        delete_dashboard(args.delete)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
