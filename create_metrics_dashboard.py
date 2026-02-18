#!/usr/bin/env python3
"""Create System Metrics Overview dashboard on ClickStack."""
import requests
import sys

API = 'http://localhost:8000'

dashboard = {
    "name": "System Metrics Overview",
    "tags": ["metrics", "system"],
    "tiles": [
        # Top row: 4 KPI tiles (w:6, h:2 each in 24-col grid)
        {
            "id": "cpu-utilization-kpi",
            "x": 0, "y": 0, "w": 6, "h": 2,
            "config": {
                "name": "CPU Utilization",
                "source": "metrics",
                "select": [{"aggFn": "avg", "valueExpression": "Value", "aggCondition": ""}],
                "where": "",
                "whereLanguage": "lucene",
                "groupBy": [],
                "displayType": "number",
                "metricName": "system.cpu.utilization",
                "metricDataType": "Gauge",
                "numberFormat": {
                    "output": "percent", "mantissa": 1, "factor": 1,
                    "thousandSeparated": True, "average": False
                }
            }
        },
        {
            "id": "memory-utilization-kpi",
            "x": 6, "y": 0, "w": 6, "h": 2,
            "config": {
                "name": "Memory Utilization",
                "source": "metrics",
                "select": [{"aggFn": "avg", "valueExpression": "Value", "aggCondition": ""}],
                "where": "",
                "whereLanguage": "lucene",
                "groupBy": [],
                "displayType": "number",
                "metricName": "system.memory.utilization",
                "metricDataType": "Gauge",
                "numberFormat": {
                    "output": "percent", "mantissa": 1, "factor": 1,
                    "thousandSeparated": True, "average": False
                }
            }
        },
        {
            "id": "container-cpu-kpi",
            "x": 12, "y": 0, "w": 6, "h": 2,
            "config": {
                "name": "Container CPU",
                "source": "metrics",
                "select": [{"aggFn": "avg", "valueExpression": "Value", "aggCondition": ""}],
                "where": "",
                "whereLanguage": "lucene",
                "groupBy": [],
                "displayType": "number",
                "metricName": "container.cpu.utilization",
                "metricDataType": "Gauge",
                "numberFormat": {
                    "output": "percent", "mantissa": 1, "factor": 1,
                    "thousandSeparated": True, "average": False
                }
            }
        },
        {
            "id": "container-memory-kpi",
            "x": 18, "y": 0, "w": 6, "h": 2,
            "config": {
                "name": "Container Memory %",
                "source": "metrics",
                "select": [{"aggFn": "avg", "valueExpression": "Value", "aggCondition": ""}],
                "where": "",
                "whereLanguage": "lucene",
                "groupBy": [],
                "displayType": "number",
                "metricName": "container.memory.percent",
                "metricDataType": "Gauge",
                "numberFormat": {
                    "output": "percent", "mantissa": 1, "factor": 1,
                    "thousandSeparated": True, "average": False
                }
            }
        },

        # Second row: 2 time series (w:12, h:4)
        {
            "id": "cpu-utilization-over-time",
            "x": 0, "y": 2, "w": 12, "h": 4,
            "config": {
                "name": "CPU Utilization Over Time",
                "source": "metrics",
                "select": [{"aggFn": "avg", "valueExpression": "Value", "aggCondition": ""}],
                "where": "",
                "whereLanguage": "lucene",
                "groupBy": [],
                "displayType": "line",
                "metricName": "system.cpu.utilization",
                "metricDataType": "Gauge"
            }
        },
        {
            "id": "memory-utilization-over-time",
            "x": 12, "y": 2, "w": 12, "h": 4,
            "config": {
                "name": "Memory Utilization Over Time",
                "source": "metrics",
                "select": [{"aggFn": "avg", "valueExpression": "Value", "aggCondition": ""}],
                "where": "",
                "whereLanguage": "lucene",
                "groupBy": [],
                "displayType": "line",
                "metricName": "system.memory.utilization",
                "metricDataType": "Gauge"
            }
        },

        # Third row: 2 time series (w:12, h:4)
        {
            "id": "container-cpu-over-time",
            "x": 0, "y": 6, "w": 12, "h": 4,
            "config": {
                "name": "Container CPU Usage Over Time",
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
            "id": "network-io-over-time",
            "x": 12, "y": 6, "w": 12, "h": 4,
            "config": {
                "name": "Network I/O (bytes/s)",
                "source": "metrics",
                "select": [{"aggFn": "sum", "valueExpression": "Value", "aggCondition": ""}],
                "where": "",
                "whereLanguage": "lucene",
                "groupBy": [],
                "displayType": "line",
                "metricName": "system.network.io",
                "metricDataType": "Sum"
            }
        }
    ]
}

resp = requests.post(f'{API}/dashboards', json=dashboard)

if resp.status_code != 200:
    print(f"Deploy failed ({resp.status_code}): {resp.text}")
    exit(1)

data = resp.json()
dashboard_id = data['id']
print(f"Dashboard created successfully!")
print(f"URL: http://localhost:8080/dashboards/{dashboard_id}")
print(f"ID: {dashboard_id}")
