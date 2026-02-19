#!/usr/bin/env python3
"""Deploy NGINX Access Log Overview dashboard to ClickStack via v2 API."""
import requests
import sys

API = 'http://localhost:8000'
TOKEN = 'clickstack-local-v2-api-key'
HEADERS = {'Authorization': f'Bearer {TOKEN}'}

# Resolve source IDs (required — v2 API needs IDs, not kind strings)
sources = requests.get(f'{API}/sources').json()
SRC = {s['kind']: s['id'] for s in sources}

dashboard = {
    "name": "NGINX Access Log Overview",
    "tags": ["nginx", "access-log"],
    "tiles": [
        # ── Row 0 (y=0, h=3): KPI tiles ─────────────────────────────
        {
            "name": "Total Requests",
            "x": 0, "y": 0, "w": 6, "h": 3,
            "series": [{
                "type": "number",
                "sourceId": SRC["log"],
                "aggFn": "count",
                "field": "",
                "where": "ServiceName:nginx-demo",
                "whereLanguage": "lucene",
                "numberFormat": {
                    "output": "number", "mantissa": 0,
                    "thousandSeparated": True
                }
            }]
        },
        {
            "name": "Error Count (4xx + 5xx)",
            "x": 6, "y": 0, "w": 6, "h": 3,
            "series": [{
                "type": "number",
                "sourceId": SRC["log"],
                "aggFn": "count",
                "field": "",
                "where": "ServiceName:nginx-demo AND (LogAttributes.status:4* OR LogAttributes.status:5*)",
                "whereLanguage": "lucene",
                "numberFormat": {
                    "output": "number", "mantissa": 0,
                    "thousandSeparated": True
                }
            }]
        },
        {
            "name": "Avg Response Time (s)",
            "x": 12, "y": 0, "w": 6, "h": 3,
            "series": [{
                "type": "number",
                "sourceId": SRC["log"],
                "aggFn": "avg",
                "field": "LogAttributes['upstream_response_time']",
                "where": "ServiceName:nginx-demo",
                "whereLanguage": "lucene",
                "numberFormat": {
                    "output": "number", "mantissa": 3,
                    "thousandSeparated": True
                }
            }]
        },
        {
            "name": "Unique Client IPs",
            "x": 18, "y": 0, "w": 6, "h": 3,
            "series": [{
                "type": "number",
                "sourceId": SRC["log"],
                "aggFn": "count_distinct",
                "field": "LogAttributes['remote_addr']",
                "where": "ServiceName:nginx-demo",
                "whereLanguage": "lucene",
                "numberFormat": {
                    "output": "number", "mantissa": 0,
                    "thousandSeparated": True
                }
            }]
        },

        # ── Row 1 (y=3, h=6): Requests over time + Errors over time ─
        {
            "name": "Requests Over Time",
            "x": 0, "y": 3, "w": 12, "h": 6,
            "series": [{
                "type": "time",
                "sourceId": SRC["log"],
                "aggFn": "count",
                "field": "",
                "where": "ServiceName:nginx-demo",
                "whereLanguage": "lucene",
                "groupBy": [],
                "displayType": "line"
            }]
        },
        {
            "name": "Errors Over Time (4xx + 5xx)",
            "x": 12, "y": 3, "w": 12, "h": 6,
            "series": [{
                "type": "time",
                "sourceId": SRC["log"],
                "aggFn": "count",
                "field": "",
                "where": "ServiceName:nginx-demo AND (LogAttributes.status:4* OR LogAttributes.status:5*)",
                "whereLanguage": "lucene",
                "groupBy": [],
                "displayType": "stacked_bar"
            }]
        },

        # ── Row 2 (y=9, h=6): Status codes over time + Avg upstream response time
        {
            "name": "Requests by Status Code",
            "x": 0, "y": 9, "w": 12, "h": 6,
            "series": [{
                "type": "time",
                "sourceId": SRC["log"],
                "aggFn": "count",
                "field": "",
                "where": "ServiceName:nginx-demo",
                "whereLanguage": "lucene",
                "groupBy": ["LogAttributes['status']"],
                "displayType": "stacked_bar"
            }]
        },
        {
            "name": "Avg Upstream Response Time",
            "x": 12, "y": 9, "w": 12, "h": 6,
            "series": [{
                "type": "time",
                "sourceId": SRC["log"],
                "aggFn": "avg",
                "field": "LogAttributes['upstream_response_time']",
                "where": "ServiceName:nginx-demo",
                "whereLanguage": "lucene",
                "groupBy": [],
                "displayType": "line"
            }]
        },

        # ── Row 3 (y=15, h=5): Status code counts table ─────────────
        {
            "name": "Status Code Breakdown",
            "x": 0, "y": 15, "w": 24, "h": 5,
            "series": [{
                "type": "table",
                "sourceId": SRC["log"],
                "aggFn": "count",
                "field": "",
                "where": "ServiceName:nginx-demo",
                "whereLanguage": "lucene",
                "groupBy": ["LogAttributes['status']"]
            }]
        }
    ]
}

resp = requests.post(f'{API}/api/v2/dashboards', json=dashboard, headers=HEADERS)
if resp.status_code != 200:
    print(f"Deploy FAILED ({resp.status_code}): {resp.text}")
    sys.exit(1)

data = resp.json()['data']
dashboard_id = data['id']
print(f"Dashboard deployed successfully!")
print(f"URL: http://localhost:8080/dashboards/{dashboard_id}")
print(f"Tiles: {len(data['tiles'])}")
print()
print("NOTE: NGINX sample data has historical timestamps (2025-10-20 to 2025-10-21).")
print("Set the UI time range to that period to see data in charts.")
