#!/usr/bin/env python3
"""Deploy Checkout Service Overview dashboard with backend metrics."""
import requests
import subprocess
import sys

# Get access token
token = subprocess.check_output([
    'docker', 'exec', 'hyperdx-local', 'mongo', '--quiet', '--eval',
    'db=db.getSiblingDB("hyperdx"); print(db.users.findOne({}).accessKey)'
]).decode().strip()

API = 'http://localhost:8000'
HEADERS = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}

dashboard = {
    "name": "Checkout Service Overview",
    "query": "",
    "tags": ["checkout", "e-commerce"],
    "charts": [
        # ── Row 0 (y=0): KPI tiles ──────────────────────────────────
        {
            "id": "total-checkouts",
            "name": "Total Checkouts",
            "x": 0, "y": 0, "w": 3, "h": 2,
            "series": [{
                "type": "number",
                "table": "logs",
                "aggFn": "count",
                "where": "service:checkout span_name:\"oteldemo.CheckoutService/PlaceOrder\"",
                "numberFormat": {"output": "number", "mantissa": 0, "factor": 1,
                                 "thousandSeparated": True, "average": False, "decimalBytes": False}
            }],
            "asRatio": False
        },
        {
            "id": "avg-checkout-latency",
            "name": "Avg Checkout Latency (ms)",
            "x": 3, "y": 0, "w": 3, "h": 2,
            "series": [{
                "type": "number",
                "table": "logs",
                "aggFn": "avg",
                "field": "duration",
                "where": "service:checkout span_name:\"oteldemo.CheckoutService/PlaceOrder\"",
                "numberFormat": {"output": "number", "mantissa": 2, "factor": 1,
                                 "thousandSeparated": True, "average": False, "decimalBytes": False}
            }],
            "asRatio": False
        },
        {
            "id": "p95-checkout-latency",
            "name": "P95 Checkout Latency (ms)",
            "x": 6, "y": 0, "w": 3, "h": 2,
            "series": [{
                "type": "number",
                "table": "logs",
                "aggFn": "p95",
                "field": "duration",
                "where": "service:checkout span_name:\"oteldemo.CheckoutService/PlaceOrder\"",
                "numberFormat": {"output": "number", "mantissa": 2, "factor": 1,
                                 "thousandSeparated": True, "average": False, "decimalBytes": False}
            }],
            "asRatio": False
        },
        {
            "id": "checkout-errors",
            "name": "Errors",
            "x": 9, "y": 0, "w": 3, "h": 2,
            "series": [{
                "type": "number",
                "table": "logs",
                "aggFn": "count",
                "where": "service:checkout level:error",
                "numberFormat": {"output": "number", "mantissa": 0, "factor": 1,
                                 "thousandSeparated": True, "average": False, "decimalBytes": False}
            }],
            "asRatio": False
        },

        # ── Row 1 (y=2): Latency percentiles + Request throughput ───
        {
            "id": "checkout-latency-pctls",
            "name": "Checkout Latency Percentiles (ms)",
            "x": 0, "y": 2, "w": 6, "h": 3,
            "series": [
                {
                    "type": "time",
                    "table": "logs",
                    "aggFn": "p50",
                    "field": "duration",
                    "where": "service:checkout span_name:\"oteldemo.CheckoutService/PlaceOrder\"",
                    "groupBy": []
                },
                {
                    "type": "time",
                    "table": "logs",
                    "aggFn": "p95",
                    "field": "duration",
                    "where": "service:checkout span_name:\"oteldemo.CheckoutService/PlaceOrder\"",
                    "groupBy": []
                },
                {
                    "type": "time",
                    "table": "logs",
                    "aggFn": "p99",
                    "field": "duration",
                    "where": "service:checkout span_name:\"oteldemo.CheckoutService/PlaceOrder\"",
                    "groupBy": []
                }
            ],
            "asRatio": False
        },
        {
            "id": "request-throughput",
            "name": "Request Throughput",
            "x": 6, "y": 2, "w": 6, "h": 3,
            "series": [{
                "type": "time",
                "table": "logs",
                "aggFn": "count",
                "where": "service:checkout",
                "groupBy": ["span_name"]
            }],
            "asRatio": False
        },

        # ── Row 2 (y=5): Downstream latency + Errors over time ──────
        {
            "id": "downstream-svc-latency",
            "name": "Downstream Service Latency (ms)",
            "x": 0, "y": 5, "w": 6, "h": 3,
            "series": [{
                "type": "time",
                "table": "logs",
                "aggFn": "avg",
                "field": "duration",
                "where": "service:checkout",
                "groupBy": ["span_name"]
            }],
            "asRatio": False
        },
        {
            "id": "errors-over-time",
            "name": "Errors Over Time",
            "x": 6, "y": 5, "w": 6, "h": 3,
            "series": [{
                "type": "time",
                "table": "logs",
                "aggFn": "count",
                "where": "service:checkout level:error",
                "groupBy": ["span_name"]
            }],
            "asRatio": False
        },

        # ── Row 3 (y=8): Order amount + PlaceOrder histogram ────────
        {
            "id": "avg-order-amount",
            "name": "Avg Order Amount Over Time",
            "x": 0, "y": 8, "w": 6, "h": 3,
            "series": [{
                "type": "time",
                "table": "logs",
                "aggFn": "avg",
                "field": "app.order.amount",
                "where": "service:checkout span_name:\"oteldemo.CheckoutService/PlaceOrder\"",
                "groupBy": []
            }],
            "asRatio": False
        },
        {
            "id": "placeorder-latency-dist",
            "name": "PlaceOrder Latency Distribution",
            "x": 6, "y": 8, "w": 6, "h": 3,
            "series": [{
                "type": "histogram",
                "table": "logs",
                "field": "duration",
                "where": "service:checkout span_name:\"oteldemo.CheckoutService/PlaceOrder\""
            }],
            "asRatio": False
        },

        # ── Row 4 (y=11): Operations table + Recent errors ──────────
        {
            "id": "ops-by-request-count",
            "name": "Operations by Request Count",
            "x": 0, "y": 11, "w": 6, "h": 3,
            "series": [{
                "type": "table",
                "table": "logs",
                "aggFn": "count",
                "where": "service:checkout",
                "groupBy": ["span_name"],
                "sortOrder": "desc"
            }],
            "asRatio": False
        },
        {
            "id": "recent-errors",
            "name": "Recent Errors",
            "x": 6, "y": 11, "w": 6, "h": 3,
            "series": [{
                "type": "search",
                "table": "logs",
                "where": "service:checkout level:error",
                "fields": ["level", "service", "body"]
            }],
            "asRatio": False
        },

        # ══════════════════════════════════════════════════════════════
        # BACKEND SERVICE METRICS (new section)
        # ══════════════════════════════════════════════════════════════

        # ── Row 5 (y=14): Backend KPI tiles ──────────────────────────
        {
            "id": "avg-payment-latency",
            "name": "Avg Payment Latency (ms)",
            "x": 0, "y": 14, "w": 3, "h": 2,
            "series": [{
                "type": "number",
                "table": "logs",
                "aggFn": "avg",
                "field": "duration",
                "where": "service:payment",
                "numberFormat": {"output": "number", "mantissa": 2, "factor": 1,
                                 "thousandSeparated": True, "average": False, "decimalBytes": False}
            }],
            "asRatio": False
        },
        {
            "id": "avg-cart-latency",
            "name": "Avg Cart Latency (ms)",
            "x": 3, "y": 14, "w": 3, "h": 2,
            "series": [{
                "type": "number",
                "table": "logs",
                "aggFn": "avg",
                "field": "duration",
                "where": "service:cart",
                "numberFormat": {"output": "number", "mantissa": 2, "factor": 1,
                                 "thousandSeparated": True, "average": False, "decimalBytes": False}
            }],
            "asRatio": False
        },
        {
            "id": "avg-shipping-latency",
            "name": "Avg Shipping Latency (ms)",
            "x": 6, "y": 14, "w": 3, "h": 2,
            "series": [{
                "type": "number",
                "table": "logs",
                "aggFn": "avg",
                "field": "duration",
                "where": "service:shipping",
                "numberFormat": {"output": "number", "mantissa": 2, "factor": 1,
                                 "thousandSeparated": True, "average": False, "decimalBytes": False}
            }],
            "asRatio": False
        },
        {
            "id": "total-payment-txns",
            "name": "Payment Transactions",
            "x": 9, "y": 14, "w": 3, "h": 2,
            "series": [{
                "type": "number",
                "table": "logs",
                "aggFn": "count",
                "where": "service:payment span_name:\"grpc.oteldemo.PaymentService/Charge\"",
                "numberFormat": {"output": "number", "mantissa": 0, "factor": 1,
                                 "thousandSeparated": True, "average": False, "decimalBytes": False}
            }],
            "asRatio": False
        },

        # ── Row 6 (y=16): Backend latency + Backend errors ──────────
        {
            "id": "backend-svc-latency",
            "name": "Backend Service Latency (ms)",
            "x": 0, "y": 16, "w": 6, "h": 3,
            "series": [
                {
                    "type": "time",
                    "table": "logs",
                    "aggFn": "avg",
                    "field": "duration",
                    "where": "service:payment",
                    "groupBy": []
                },
                {
                    "type": "time",
                    "table": "logs",
                    "aggFn": "avg",
                    "field": "duration",
                    "where": "service:cart",
                    "groupBy": []
                },
                {
                    "type": "time",
                    "table": "logs",
                    "aggFn": "avg",
                    "field": "duration",
                    "where": "service:shipping",
                    "groupBy": []
                },
                {
                    "type": "time",
                    "table": "logs",
                    "aggFn": "avg",
                    "field": "duration",
                    "where": "service:currency",
                    "groupBy": []
                }
            ],
            "asRatio": False
        },
        {
            "id": "backend-errors-by-svc",
            "name": "Backend Errors by Service",
            "x": 6, "y": 16, "w": 6, "h": 3,
            "series": [{
                "type": "time",
                "table": "logs",
                "aggFn": "count",
                "where": "level:error (service:payment OR service:cart OR service:shipping OR service:currency)",
                "groupBy": ["service"]
            }],
            "asRatio": False
        },

        # ── Row 7 (y=19): Infra metrics ─────────────────────────────
        {
            "id": "container-cpu-util",
            "name": "Container CPU Utilization",
            "x": 0, "y": 19, "w": 6, "h": 3,
            "series": [{
                "type": "time",
                "table": "metrics",
                "aggFn": "avg",
                "field": "container.cpu.utilization - Gauge",
                "metricDataType": "Gauge",
                "where": "",
                "groupBy": []
            }],
            "asRatio": False
        },
        {
            "id": "redis-memory-used",
            "name": "Redis Memory Used",
            "x": 6, "y": 19, "w": 6, "h": 3,
            "series": [{
                "type": "time",
                "table": "metrics",
                "aggFn": "avg",
                "field": "redis.memory.used - Gauge",
                "metricDataType": "Gauge",
                "where": "",
                "groupBy": []
            }],
            "asRatio": False
        },

        # ── Row 8 (y=22): JVM + Kafka metrics ───────────────────────
        {
            "id": "jvm-memory-used",
            "name": "JVM Memory Used",
            "x": 0, "y": 22, "w": 6, "h": 3,
            "series": [{
                "type": "time",
                "table": "metrics",
                "aggFn": "avg",
                "field": "jvm.memory.used - Sum",
                "metricDataType": "Sum",
                "where": "",
                "groupBy": []
            }],
            "asRatio": False
        },
        {
            "id": "kafka-consumer-lag",
            "name": "Kafka Consumer Lag",
            "x": 6, "y": 22, "w": 6, "h": 3,
            "series": [{
                "type": "time",
                "table": "metrics",
                "aggFn": "max",
                "field": "kafka.consumer.records_lag - Gauge",
                "metricDataType": "Gauge",
                "where": "",
                "groupBy": []
            }],
            "asRatio": False
        }
    ]
}

resp = requests.post(f'{API}/api/v1/dashboards', headers=HEADERS, json=dashboard)
if resp.status_code != 200:
    print(f"Deploy FAILED ({resp.status_code}): {resp.text}")
    sys.exit(1)

data = resp.json()['data']
dashboard_id = data['id']
print(f"Dashboard deployed successfully!")
print(f"URL: http://localhost:8080/dashboards/{dashboard_id}")
print(f"Charts: {len(data['charts'])}")
