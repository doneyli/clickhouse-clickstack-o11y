#!/usr/bin/env python3
"""Deploy Checkout Service Overview dashboard to ClickStack."""
import requests
import sys

API = 'http://localhost:8000'

dashboard = {
    "name": "Checkout Service Overview",
    "tags": ["checkout", "e-commerce"],
    "tiles": [
        # ── Row 0 (y=0): KPI tiles ──────────────────────────────────
        {
            "id": "total-checkouts",
            "x": 0, "y": 0, "w": 6, "h": 2,
            "config": {
                "name": "Total Checkouts",
                "source": "traces",
                "select": [{"aggFn": "count", "valueExpression": "", "aggCondition": ""}],
                "where": "service:checkout span_name:\"oteldemo.CheckoutService/PlaceOrder\"",
                "whereLanguage": "lucene",
                "groupBy": [],
                "displayType": "number",
                "numberFormat": {
                    "output": "number", "mantissa": 0, "factor": 1,
                    "thousandSeparated": True, "average": False, "decimalBytes": False
                }
            }
        },
        {
            "id": "avg-checkout-latency",
            "x": 6, "y": 0, "w": 6, "h": 2,
            "config": {
                "name": "Avg Checkout Latency",
                "source": "traces",
                "select": [{"aggFn": "avg", "valueExpression": "Duration", "aggCondition": ""}],
                "where": "service:checkout span_name:\"oteldemo.CheckoutService/PlaceOrder\"",
                "whereLanguage": "lucene",
                "groupBy": [],
                "displayType": "number",
                "numberFormat": {
                    "output": "number", "mantissa": 2, "factor": 1,
                    "thousandSeparated": True, "average": False, "decimalBytes": False
                }
            }
        },
        {
            "id": "p95-checkout-latency",
            "x": 12, "y": 0, "w": 6, "h": 2,
            "config": {
                "name": "P95 Checkout Latency",
                "source": "traces",
                "select": [{"aggFn": "quantile", "level": 0.95, "valueExpression": "Duration", "aggCondition": ""}],
                "where": "service:checkout span_name:\"oteldemo.CheckoutService/PlaceOrder\"",
                "whereLanguage": "lucene",
                "groupBy": [],
                "displayType": "number",
                "numberFormat": {
                    "output": "number", "mantissa": 2, "factor": 1,
                    "thousandSeparated": True, "average": False, "decimalBytes": False
                }
            }
        },
        {
            "id": "checkout-errors",
            "x": 18, "y": 0, "w": 6, "h": 2,
            "config": {
                "name": "Errors",
                "source": "logs",
                "select": [{"aggFn": "count", "valueExpression": "", "aggCondition": ""}],
                "where": "service:checkout level:error",
                "whereLanguage": "lucene",
                "groupBy": [],
                "displayType": "number",
                "numberFormat": {
                    "output": "number", "mantissa": 0, "factor": 1,
                    "thousandSeparated": True, "average": False, "decimalBytes": False
                }
            }
        },

        # ── Row 1 (y=2): Latency percentiles + Request throughput ───
        {
            "id": "checkout-latency-pctls",
            "x": 0, "y": 2, "w": 12, "h": 3,
            "config": {
                "name": "Checkout Latency Percentiles",
                "source": "traces",
                "select": [
                    {"aggFn": "quantile", "level": 0.5, "valueExpression": "Duration", "aggCondition": ""},
                    {"aggFn": "quantile", "level": 0.95, "valueExpression": "Duration", "aggCondition": ""},
                    {"aggFn": "quantile", "level": 0.99, "valueExpression": "Duration", "aggCondition": ""}
                ],
                "where": "service:checkout span_name:\"oteldemo.CheckoutService/PlaceOrder\"",
                "whereLanguage": "lucene",
                "groupBy": [],
                "displayType": "line"
            }
        },
        {
            "id": "request-throughput",
            "x": 12, "y": 2, "w": 12, "h": 3,
            "config": {
                "name": "Request Throughput",
                "source": "traces",
                "select": [{"aggFn": "count", "valueExpression": "", "aggCondition": ""}],
                "where": "service:checkout",
                "whereLanguage": "lucene",
                "groupBy": [{"valueExpression": "SpanName"}],
                "displayType": "stacked_bar"
            }
        },

        # ── Row 2 (y=5): Downstream latency + Errors over time ──────
        {
            "id": "downstream-svc-latency",
            "x": 0, "y": 5, "w": 12, "h": 3,
            "config": {
                "name": "Downstream Service Latency",
                "source": "traces",
                "select": [{"aggFn": "avg", "valueExpression": "Duration", "aggCondition": ""}],
                "where": "service:checkout",
                "whereLanguage": "lucene",
                "groupBy": [{"valueExpression": "SpanName"}],
                "displayType": "line"
            }
        },
        {
            "id": "errors-over-time",
            "x": 12, "y": 5, "w": 12, "h": 3,
            "config": {
                "name": "Errors Over Time",
                "source": "logs",
                "select": [{"aggFn": "count", "valueExpression": "", "aggCondition": ""}],
                "where": "service:checkout level:error",
                "whereLanguage": "lucene",
                "groupBy": [{"valueExpression": "ServiceName"}],
                "displayType": "stacked_bar"
            }
        },

        # ── Row 3 (y=8): Backend service latency + errors ───────────
        {
            "id": "backend-svc-latency",
            "x": 0, "y": 8, "w": 12, "h": 3,
            "config": {
                "name": "Backend Service Latency",
                "source": "traces",
                "select": [{"aggFn": "avg", "valueExpression": "Duration", "aggCondition": ""}],
                "where": "service:payment OR service:cart OR service:shipping OR service:currency",
                "whereLanguage": "lucene",
                "groupBy": [{"valueExpression": "ServiceName"}],
                "displayType": "line"
            }
        },
        {
            "id": "backend-errors-by-svc",
            "x": 12, "y": 8, "w": 12, "h": 3,
            "config": {
                "name": "Backend Errors by Service",
                "source": "logs",
                "select": [{"aggFn": "count", "valueExpression": "", "aggCondition": ""}],
                "where": "level:error (service:payment OR service:cart OR service:shipping OR service:currency)",
                "whereLanguage": "lucene",
                "groupBy": [{"valueExpression": "ServiceName"}],
                "displayType": "stacked_bar"
            }
        },

        # ── Row 4 (y=11): Metrics ───────────────────────────────────
        {
            "id": "container-cpu-util",
            "x": 0, "y": 11, "w": 12, "h": 3,
            "config": {
                "name": "Container CPU Utilization",
                "source": "metrics",
                "select": [{"aggFn": "avg", "valueExpression": "Value", "aggCondition": ""}],
                "where": "",
                "whereLanguage": "lucene",
                "groupBy": [],
                "displayType": "line",
                "metricName": "container.cpu.utilization",
                "metricDataType": "Gauge"
            }
        },
        {
            "id": "redis-memory-used",
            "x": 12, "y": 11, "w": 12, "h": 3,
            "config": {
                "name": "Redis Memory Used",
                "source": "metrics",
                "select": [{"aggFn": "avg", "valueExpression": "Value", "aggCondition": ""}],
                "where": "",
                "whereLanguage": "lucene",
                "groupBy": [],
                "displayType": "line",
                "metricName": "redis.memory.used",
                "metricDataType": "Gauge"
            }
        }
    ]
}

resp = requests.post(f'{API}/dashboards', json=dashboard)
if resp.status_code != 200:
    print(f"Deploy FAILED ({resp.status_code}): {resp.text}")
    sys.exit(1)

data = resp.json()
dashboard_id = data['id']
print(f"Dashboard deployed successfully!")
print(f"URL: http://localhost:8080/dashboards/{dashboard_id}")
print(f"Tiles: {len(data['tiles'])}")
