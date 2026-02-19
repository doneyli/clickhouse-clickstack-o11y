#!/usr/bin/env python3
"""Create System Metrics Overview dashboard on ClickStack via v2 API."""
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
    "name": "System Metrics Overview",
    "tags": ["metrics", "system"],
    "tiles": [
        # Top row: 4 KPI tiles (w:6, h:3 each in 24-col grid)
        {
            "name": "CPU Utilization",
            "x": 0, "y": 0, "w": 6, "h": 3,
            "series": [{
                "type": "number",
                "sourceId": SRC["metric"],
                "aggFn": "avg",
                "field": "Value",
                "where": "",
                "whereLanguage": "lucene",
                "metricName": "system.cpu.utilization",
                "metricDataType": "gauge",
                "numberFormat": {
                    "output": "percent", "mantissa": 1, "thousandSeparated": True
                }
            }]
        },
        {
            "name": "Memory Utilization",
            "x": 6, "y": 0, "w": 6, "h": 3,
            "series": [{
                "type": "number",
                "sourceId": SRC["metric"],
                "aggFn": "avg",
                "field": "Value",
                "where": "",
                "whereLanguage": "lucene",
                "metricName": "system.memory.utilization",
                "metricDataType": "gauge",
                "numberFormat": {
                    "output": "percent", "mantissa": 1, "thousandSeparated": True
                }
            }]
        },
        {
            "name": "Container CPU",
            "x": 12, "y": 0, "w": 6, "h": 3,
            "series": [{
                "type": "number",
                "sourceId": SRC["metric"],
                "aggFn": "avg",
                "field": "Value",
                "where": "",
                "whereLanguage": "lucene",
                "metricName": "container.cpu.utilization",
                "metricDataType": "gauge",
                "numberFormat": {
                    "output": "percent", "mantissa": 1, "thousandSeparated": True
                }
            }]
        },
        {
            "name": "Container Memory %",
            "x": 18, "y": 0, "w": 6, "h": 3,
            "series": [{
                "type": "number",
                "sourceId": SRC["metric"],
                "aggFn": "avg",
                "field": "Value",
                "where": "",
                "whereLanguage": "lucene",
                "metricName": "container.memory.percent",
                "metricDataType": "gauge",
                "numberFormat": {
                    "output": "percent", "mantissa": 1, "thousandSeparated": True
                }
            }]
        },

        # Second row: 2 time series (w:12, h:6)
        {
            "name": "CPU Utilization Over Time",
            "x": 0, "y": 3, "w": 12, "h": 6,
            "series": [{
                "type": "time",
                "sourceId": SRC["metric"],
                "aggFn": "avg",
                "field": "Value",
                "where": "",
                "whereLanguage": "lucene",
                "groupBy": [],
                "displayType": "line",
                "metricName": "system.cpu.utilization",
                "metricDataType": "gauge"
            }]
        },
        {
            "name": "Memory Utilization Over Time",
            "x": 12, "y": 3, "w": 12, "h": 6,
            "series": [{
                "type": "time",
                "sourceId": SRC["metric"],
                "aggFn": "avg",
                "field": "Value",
                "where": "",
                "whereLanguage": "lucene",
                "groupBy": [],
                "displayType": "line",
                "metricName": "system.memory.utilization",
                "metricDataType": "gauge"
            }]
        },

        # Third row: 2 time series (w:12, h:6)
        {
            "name": "Container CPU Usage Over Time",
            "x": 0, "y": 9, "w": 12, "h": 6,
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
            "name": "Network I/O (bytes/s)",
            "x": 12, "y": 9, "w": 12, "h": 6,
            "series": [{
                "type": "time",
                "sourceId": SRC["metric"],
                "aggFn": "sum",
                "field": "Value",
                "where": "",
                "whereLanguage": "lucene",
                "groupBy": [],
                "displayType": "line",
                "metricName": "system.network.io",
                "metricDataType": "sum"
            }]
        }
    ]
}

resp = requests.post(f'{API}/api/v2/dashboards', json=dashboard, headers=HEADERS)

if resp.status_code != 200:
    print(f"Deploy failed ({resp.status_code}): {resp.text}")
    exit(1)

data = resp.json()['data']
dashboard_id = data['id']
print(f"Dashboard created successfully!")
print(f"URL: http://localhost:8080/dashboards/{dashboard_id}")
print(f"ID: {dashboard_id}")
