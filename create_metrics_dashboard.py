#!/usr/bin/env python3
"""Create System Metrics Overview dashboard"""

import requests
import json

API = 'http://localhost:8000'
TOKEN = '6990e12abb8303cd5571903f0000000000000000'
HEADERS = {'Authorization': f'Bearer {TOKEN}', 'Content-Type': 'application/json'}

dashboard = {
    "name": "System Metrics Overview",
    "query": "",
    "tags": ["metrics", "system"],
    "charts": [
        # Top row: 4 KPI tiles (w:3, h:2)
        {
            "id": "cpu-utilization-kpi",
            "name": "CPU Utilization",
            "x": 0, "y": 0, "w": 3, "h": 2,
            "series": [{
                "type": "number",
                "table": "metrics",
                "aggFn": "avg",
                "field": "system.cpu.utilization - Gauge",
                "metricDataType": "Gauge",
                "where": "",
                "numberFormat": {
                    "output": "percent",
                    "mantissa": 1,
                    "factor": 1,
                    "thousandSeparated": True,
                    "average": False
                }
            }],
            "seriesReturnType": "column"
        },
        {
            "id": "memory-utilization-kpi",
            "name": "Memory Utilization",
            "x": 3, "y": 0, "w": 3, "h": 2,
            "series": [{
                "type": "number",
                "table": "metrics",
                "aggFn": "avg",
                "field": "system.memory.utilization - Gauge",
                "metricDataType": "Gauge",
                "where": "",
                "numberFormat": {
                    "output": "percent",
                    "mantissa": 1,
                    "factor": 1,
                    "thousandSeparated": True,
                    "average": False
                }
            }],
            "seriesReturnType": "column"
        },
        {
            "id": "container-cpu-kpi",
            "name": "Container CPU",
            "x": 6, "y": 0, "w": 3, "h": 2,
            "series": [{
                "type": "number",
                "table": "metrics",
                "aggFn": "avg",
                "field": "container.cpu.utilization - Gauge",
                "metricDataType": "Gauge",
                "where": "",
                "numberFormat": {
                    "output": "percent",
                    "mantissa": 1,
                    "factor": 1,
                    "thousandSeparated": True,
                    "average": False
                }
            }],
            "seriesReturnType": "column"
        },
        {
            "id": "container-memory-kpi",
            "name": "Container Memory %",
            "x": 9, "y": 0, "w": 3, "h": 2,
            "series": [{
                "type": "number",
                "table": "metrics",
                "aggFn": "avg",
                "field": "container.memory.percent - Gauge",
                "metricDataType": "Gauge",
                "where": "",
                "numberFormat": {
                    "output": "percent",
                    "mantissa": 1,
                    "factor": 1,
                    "thousandSeparated": True,
                    "average": False
                }
            }],
            "seriesReturnType": "column"
        },

        # Second row: 2 time series (w:6, h:4)
        {
            "id": "cpu-utilization-over-time",
            "name": "CPU Utilization Over Time",
            "x": 0, "y": 2, "w": 6, "h": 4,
            "series": [{
                "type": "time",
                "table": "metrics",
                "aggFn": "avg",
                "field": "system.cpu.utilization - Gauge",
                "metricDataType": "Gauge",
                "where": "",
                "groupBy": []
            }],
            "seriesReturnType": "column"
        },
        {
            "id": "memory-utilization-over-time",
            "name": "Memory Utilization Over Time",
            "x": 6, "y": 2, "w": 6, "h": 4,
            "series": [{
                "type": "time",
                "table": "metrics",
                "aggFn": "avg",
                "field": "system.memory.utilization - Gauge",
                "metricDataType": "Gauge",
                "where": "",
                "groupBy": []
            }],
            "seriesReturnType": "column"
        },

        # Bottom row: 2 time series (w:6, h:4)
        {
            "id": "container-cpu-over-time",
            "name": "Container CPU Usage Over Time",
            "x": 0, "y": 6, "w": 6, "h": 4,
            "series": [{
                "type": "time",
                "table": "metrics",
                "aggFn": "avg",
                "field": "container.cpu.utilization - Gauge",
                "metricDataType": "Gauge",
                "where": "",
                "groupBy": []
            }],
            "seriesReturnType": "column"
        },
        {
            "id": "network-io-over-time",
            "name": "Network I/O (bytes/s)",
            "x": 6, "y": 6, "w": 6, "h": 4,
            "series": [{
                "type": "time",
                "table": "metrics",
                "aggFn": "sum_rate",
                "field": "system.network.io - Sum",
                "metricDataType": "Sum",
                "where": "",
                "groupBy": []
            }],
            "seriesReturnType": "column"
        }
    ]
}

print("=== VALIDATION CHECKLIST ===\n")

for i, chart in enumerate(dashboard['charts'], 1):
    print(f"Chart {i}: {chart['name']}")
    series = chart['series'][0]

    # Rule checks
    checks = [
        ("where uses Lucene syntax", series.get('where') == ""),
        ("field uses HyperDX names", not series['field'].startswith('_')),
        ("table is 'metrics'", series['table'] == 'metrics'),
        ("metricDataType present", 'metricDataType' in series),
        ("field format 'name - DataType'", ' - ' in series['field']),
        ("aggFn is valid", series['aggFn'] in ['avg', 'sum_rate', 'count']),
        ("type is valid", series['type'] in ['time', 'number']),
        ("numberFormat present (if type=number)", series['type'] != 'number' or 'numberFormat' in series),
        ("x + w <= 12", chart['x'] + chart['w'] <= 12),
        ("seriesReturnType is 'column'", chart['seriesReturnType'] == 'column'),
        ("groupBy is array", isinstance(series.get('groupBy', []), list)),
        ("h is 2 for KPI, >=3 for others", (series['type'] == 'number' and chart['h'] == 2) or (series['type'] != 'number' and chart['h'] >= 3)),
        ("chart id is kebab-case", '-' in chart['id']),
        ("no forbidden fields", not any(k in series for k in ['source', 'displayType', 'whereLanguage', 'granularity', 'config', 'select'])),
        ("no type:span in where", 'type:span' not in series.get('where', '') and 'type:log' not in series.get('where', ''))
    ]

    for check_name, passed in checks:
        status = "[ok]" if passed else "[FAIL]"
        print(f"  {status} {check_name}")

    print()

print("\n=== DEPLOYING DASHBOARD ===\n")

resp = requests.post(f'{API}/dashboards', headers=HEADERS, json=dashboard)

if resp.status_code != 200:
    print(f"❌ Deploy failed ({resp.status_code}): {resp.text}")
    exit(1)

data = resp.json()['data']
dashboard_id = data['_id']
print(f"✅ Dashboard created successfully!")
print(f"📊 URL: http://localhost:8080/dashboards/{dashboard_id}")
print(f"🆔 ID: {dashboard_id}")
