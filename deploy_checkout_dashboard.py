#!/usr/bin/env python3
"""Deploy Checkout Service Overview dashboard to ClickStack via v2 API."""
import requests
import sys

API = 'http://localhost:8000'
TOKEN = 'clickstack-local-v2-api-key'
HEADERS = {'Authorization': f'Bearer {TOKEN}'}

# Resolve source IDs (required — v2 API needs IDs, not kind strings)
sources = requests.get(f'{API}/sources').json()
SRC = {s['kind']: s['id'] for s in sources}
# SRC = {"trace": "<id>", "log": "<id>", "metric": "<id>", "session": "<id>"}

dashboard = {
    "name": "Checkout Service Overview",
    "tags": ["checkout", "e-commerce"],
    "tiles": [
        # ── Row 0 (y=0, h=3): KPI tiles ─────────────────────────────
        {
            "name": "Total Checkouts",
            "x": 0, "y": 0, "w": 6, "h": 3,
            "series": [{
                "type": "number",
                "sourceId": SRC["trace"],
                "aggFn": "count",
                "field": "",
                "where": "ServiceName:checkout SpanName:\"oteldemo.CheckoutService/PlaceOrder\"",
                "whereLanguage": "lucene",
                "numberFormat": {
                    "output": "number", "mantissa": 0,
                    "thousandSeparated": True
                }
            }]
        },
        {
            "name": "Avg Checkout Latency",
            "x": 6, "y": 0, "w": 6, "h": 3,
            "series": [{
                "type": "number",
                "sourceId": SRC["trace"],
                "aggFn": "avg",
                "field": "Duration",
                "where": "ServiceName:checkout SpanName:\"oteldemo.CheckoutService/PlaceOrder\"",
                "whereLanguage": "lucene",
                "numberFormat": {
                    "output": "number", "mantissa": 2,
                    "thousandSeparated": True
                }
            }]
        },
        {
            "name": "P95 Checkout Latency",
            "x": 12, "y": 0, "w": 6, "h": 3,
            "series": [{
                "type": "number",
                "sourceId": SRC["trace"],
                "aggFn": "quantile",
                "level": 0.95,
                "field": "Duration",
                "where": "ServiceName:checkout SpanName:\"oteldemo.CheckoutService/PlaceOrder\"",
                "whereLanguage": "lucene",
                "numberFormat": {
                    "output": "number", "mantissa": 2,
                    "thousandSeparated": True
                }
            }]
        },
        {
            "name": "Errors",
            "x": 18, "y": 0, "w": 6, "h": 3,
            "series": [{
                "type": "number",
                "sourceId": SRC["log"],
                "aggFn": "count",
                "field": "",
                "where": "ServiceName:checkout SeverityText:error",
                "whereLanguage": "lucene",
                "numberFormat": {
                    "output": "number", "mantissa": 0,
                    "thousandSeparated": True
                }
            }]
        },

        # ── Row 1 (y=3, h=6): Latency percentiles + Request throughput
        {
            "name": "Checkout Latency Percentiles",
            "x": 0, "y": 3, "w": 12, "h": 6,
            "series": [
                {
                    "type": "time",
                    "sourceId": SRC["trace"],
                    "aggFn": "quantile", "level": 0.5,
                    "field": "Duration",
                    "where": "ServiceName:checkout SpanName:\"oteldemo.CheckoutService/PlaceOrder\"",
                    "whereLanguage": "lucene",
                    "groupBy": [],
                    "displayType": "line"
                },
                {
                    "type": "time",
                    "sourceId": SRC["trace"],
                    "aggFn": "quantile", "level": 0.95,
                    "field": "Duration",
                    "where": "ServiceName:checkout SpanName:\"oteldemo.CheckoutService/PlaceOrder\"",
                    "whereLanguage": "lucene",
                    "groupBy": [],
                    "displayType": "line"
                },
                {
                    "type": "time",
                    "sourceId": SRC["trace"],
                    "aggFn": "quantile", "level": 0.99,
                    "field": "Duration",
                    "where": "ServiceName:checkout SpanName:\"oteldemo.CheckoutService/PlaceOrder\"",
                    "whereLanguage": "lucene",
                    "groupBy": [],
                    "displayType": "line"
                }
            ]
        },
        {
            "name": "Request Throughput",
            "x": 12, "y": 3, "w": 12, "h": 6,
            "series": [{
                "type": "time",
                "sourceId": SRC["trace"],
                "aggFn": "count",
                "field": "",
                "where": "ServiceName:checkout",
                "whereLanguage": "lucene",
                "groupBy": ["SpanName"],
                "displayType": "stacked_bar"
            }]
        },

        # ── Row 2 (y=9, h=6): Downstream latency + Errors over time ─
        {
            "name": "Downstream Service Latency",
            "x": 0, "y": 9, "w": 12, "h": 6,
            "series": [{
                "type": "time",
                "sourceId": SRC["trace"],
                "aggFn": "avg",
                "field": "Duration",
                "where": "ServiceName:checkout",
                "whereLanguage": "lucene",
                "groupBy": ["SpanName"],
                "displayType": "line"
            }]
        },
        {
            "name": "Errors Over Time",
            "x": 12, "y": 9, "w": 12, "h": 6,
            "series": [{
                "type": "time",
                "sourceId": SRC["log"],
                "aggFn": "count",
                "field": "",
                "where": "ServiceName:checkout SeverityText:error",
                "whereLanguage": "lucene",
                "groupBy": ["ServiceName"],
                "displayType": "stacked_bar"
            }]
        },

        # ── Row 3 (y=15, h=6): Backend service latency + errors ─────
        {
            "name": "Backend Service Latency",
            "x": 0, "y": 15, "w": 12, "h": 6,
            "series": [{
                "type": "time",
                "sourceId": SRC["trace"],
                "aggFn": "avg",
                "field": "Duration",
                "where": "ServiceName:payment OR ServiceName:cart OR ServiceName:shipping OR ServiceName:currency",
                "whereLanguage": "lucene",
                "groupBy": ["ServiceName"],
                "displayType": "line"
            }]
        },
        {
            "name": "Backend Errors by Service",
            "x": 12, "y": 15, "w": 12, "h": 6,
            "series": [{
                "type": "time",
                "sourceId": SRC["log"],
                "aggFn": "count",
                "field": "",
                "where": "SeverityText:error (ServiceName:payment OR ServiceName:cart OR ServiceName:shipping OR ServiceName:currency)",
                "whereLanguage": "lucene",
                "groupBy": ["ServiceName"],
                "displayType": "stacked_bar"
            }]
        },

        # ── Row 4 (y=21, h=6): Metrics ──────────────────────────────
        {
            "name": "Container CPU Utilization",
            "x": 0, "y": 21, "w": 12, "h": 6,
            "series": [{
                "type": "time",
                "sourceId": SRC["metric"],
                "aggFn": "avg",
                "field": "Value",
                "where": "",
                "whereLanguage": "lucene",
                "groupBy": [],
                "displayType": "line",
                "metricName": "container.cpu.utilization",
                "metricDataType": "gauge"
            }]
        },
        {
            "name": "Redis Memory Used",
            "x": 12, "y": 21, "w": 12, "h": 6,
            "series": [{
                "type": "time",
                "sourceId": SRC["metric"],
                "aggFn": "avg",
                "field": "Value",
                "where": "",
                "whereLanguage": "lucene",
                "groupBy": [],
                "displayType": "line",
                "metricName": "redis.memory.used",
                "metricDataType": "gauge"
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
