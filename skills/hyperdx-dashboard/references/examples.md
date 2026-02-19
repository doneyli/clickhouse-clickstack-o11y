# Working Dashboard Examples (v2 API)

All examples use the ClickStack v2 API format, deployed via `POST http://localhost:8000/api/v2/dashboards` with Bearer auth.

## Tile Patterns

### 1. KPI Count Tile

```json
{
  "name": "Total Requests",
  "x": 0, "y": 0, "w": 6, "h": 3,
  "series": [{
    "type": "number",
    "sourceId": "<trace-source-id>",
    "aggFn": "count",
    "field": "",
    "where": "",
    "whereLanguage": "lucene",
    "numberFormat": {
      "output": "number", "mantissa": 0, "thousandSeparated": true
    }
  }]
}
```

Note: `field: ""` for `count` aggFn. `sourceId` must be a source ID from `GET /sources`.

### 2. KPI Avg Latency Tile

```json
{
  "name": "Avg Latency",
  "x": 6, "y": 0, "w": 6, "h": 3,
  "series": [{
    "type": "number",
    "sourceId": "<trace-source-id>",
    "aggFn": "avg",
    "field": "Duration",
    "where": "ServiceName:my-service",
    "whereLanguage": "lucene",
    "numberFormat": {
      "output": "number", "mantissa": 2, "thousandSeparated": true
    }
  }]
}
```

Note: `Duration` is nanoseconds (UInt64). HyperDX UI handles display formatting.

### 3. Time-Series Line Chart

```json
{
  "name": "Requests Over Time",
  "x": 0, "y": 3, "w": 12, "h": 6,
  "series": [{
    "type": "time",
    "sourceId": "<trace-source-id>",
    "aggFn": "count",
    "field": "",
    "where": "ServiceName:my-service",
    "whereLanguage": "lucene",
    "groupBy": [],
    "displayType": "line"
  }]
}
```

### 4. Time-Series with groupBy

```json
{
  "name": "Latency by Service",
  "x": 0, "y": 9, "w": 12, "h": 6,
  "series": [{
    "type": "time",
    "sourceId": "<trace-source-id>",
    "aggFn": "avg",
    "field": "Duration",
    "where": "",
    "whereLanguage": "lucene",
    "groupBy": ["ServiceName"],
    "displayType": "line"
  }]
}
```

Note: `groupBy` uses plain strings `["ServiceName"]`, not objects.

### 5. Stacked Bar Chart

```json
{
  "name": "Errors by Service",
  "x": 12, "y": 3, "w": 12, "h": 6,
  "series": [{
    "type": "time",
    "sourceId": "<log-source-id>",
    "aggFn": "count",
    "field": "",
    "where": "SeverityText:error",
    "whereLanguage": "lucene",
    "groupBy": ["ServiceName"],
    "displayType": "stacked_bar"
  }]
}
```

### 6. Multi-Series Chart (Percentile Lines)

```json
{
  "name": "Latency Percentiles",
  "x": 0, "y": 15, "w": 12, "h": 6,
  "series": [
    {
      "type": "time",
      "sourceId": "<trace-source-id>",
      "aggFn": "quantile", "level": 0.5,
      "field": "Duration",
      "where": "ServiceName:checkout",
      "whereLanguage": "lucene",
      "groupBy": [],
      "displayType": "line"
    },
    {
      "type": "time",
      "sourceId": "<trace-source-id>",
      "aggFn": "quantile", "level": 0.95,
      "field": "Duration",
      "where": "ServiceName:checkout",
      "whereLanguage": "lucene",
      "groupBy": [],
      "displayType": "line"
    },
    {
      "type": "time",
      "sourceId": "<trace-source-id>",
      "aggFn": "quantile", "level": 0.99,
      "field": "Duration",
      "where": "ServiceName:checkout",
      "whereLanguage": "lucene",
      "groupBy": [],
      "displayType": "line"
    }
  ]
}
```

Note: Use `quantile` + `level` instead of `p50`/`p95`/`p99`. Each series has its own `where`.

### 7. Multi-Series with Different Filters

```json
{
  "name": "Service Latency Comparison",
  "x": 12, "y": 15, "w": 12, "h": 6,
  "series": [
    {
      "type": "time",
      "sourceId": "<trace-source-id>",
      "aggFn": "avg",
      "field": "Duration",
      "where": "ServiceName:payment",
      "whereLanguage": "lucene",
      "groupBy": [],
      "displayType": "line"
    },
    {
      "type": "time",
      "sourceId": "<trace-source-id>",
      "aggFn": "avg",
      "field": "Duration",
      "where": "ServiceName:cart",
      "whereLanguage": "lucene",
      "groupBy": [],
      "displayType": "line"
    },
    {
      "type": "time",
      "sourceId": "<trace-source-id>",
      "aggFn": "avg",
      "field": "Duration",
      "where": "ServiceName:shipping",
      "whereLanguage": "lucene",
      "groupBy": [],
      "displayType": "line"
    }
  ]
}
```

Note: In v2, each series has its own `where` — no shared filter or `aggCondition`.

### 8. Table Tile

```json
{
  "name": "Top Operations by Count",
  "x": 0, "y": 21, "w": 24, "h": 5,
  "series": [{
    "type": "table",
    "sourceId": "<trace-source-id>",
    "aggFn": "count",
    "field": "",
    "where": "ServiceName:checkout",
    "whereLanguage": "lucene",
    "groupBy": ["SpanName"],
    "sortOrder": "desc"
  }]
}
```

### 9. Metrics Time Chart

```json
{
  "name": "CPU Utilization Over Time",
  "x": 0, "y": 26, "w": 12, "h": 6,
  "series": [{
    "type": "time",
    "sourceId": "<metric-source-id>",
    "aggFn": "avg",
    "field": "Value",
    "where": "",
    "whereLanguage": "lucene",
    "groupBy": [],
    "displayType": "line",
    "metricName": "system.cpu.utilization",
    "metricDataType": "gauge"
  }]
}
```

Note: Metrics series require `metricName` and `metricDataType` (lowercase). `field` is always `"Value"` for metric aggregation.

### 10. Metrics KPI Tile

```json
{
  "name": "Avg Memory Usage",
  "x": 12, "y": 26, "w": 6, "h": 3,
  "series": [{
    "type": "number",
    "sourceId": "<metric-source-id>",
    "aggFn": "avg",
    "field": "Value",
    "where": "",
    "whereLanguage": "lucene",
    "metricName": "system.memory.usage",
    "metricDataType": "sum",
    "numberFormat": {
      "output": "byte", "mantissa": 0, "thousandSeparated": true, "decimalBytes": true
    }
  }]
}
```

### 11. Search / Log Viewer Tile

```json
{
  "name": "Recent Error Logs",
  "x": 0, "y": 32, "w": 24, "h": 6,
  "series": [{
    "type": "search",
    "sourceId": "<log-source-id>",
    "fields": ["Timestamp", "ServiceName", "SeverityText", "Body"],
    "where": "SeverityText:error",
    "whereLanguage": "lucene"
  }]
}
```

### 12. Markdown Tile

```json
{
  "name": "Section Header",
  "x": 0, "y": 38, "w": 24, "h": 2,
  "series": [{
    "type": "markdown",
    "content": "## Infrastructure Metrics\nCPU, memory, and network metrics from the container runtime."
  }]
}
```

## Deploy Pattern

```python
import requests

API = 'http://localhost:8000'
TOKEN = 'clickstack-local-v2-api-key'
HEADERS = {'Authorization': f'Bearer {TOKEN}'}

# Step 1: Resolve source IDs (mandatory — internal API, no auth)
sources = requests.get(f'{API}/sources').json()
SRC = {s['kind']: s['id'] for s in sources}
# SRC = {"trace": "<id>", "log": "<id>", "metric": "<id>", "session": "<id>"}

# Step 2: Build dashboard (use SRC[kind] for sourceId fields)
dashboard = {
    'name': 'My Dashboard',
    'tags': ['my-tag'],
    'tiles': [
        {
            'name': 'My Chart',
            'x': 0, 'y': 0, 'w': 12, 'h': 6,
            'series': [{
                'type': 'time',
                'sourceId': SRC['trace'],
                'aggFn': 'count',
                'field': '',
                'where': '',
                'whereLanguage': 'lucene',
                'groupBy': [],
                'displayType': 'line'
            }]
        }
    ]
}

# Step 3: Deploy via v2 API
resp = requests.post(f'{API}/api/v2/dashboards', json=dashboard, headers=HEADERS)
data = resp.json()['data']
print(f"URL: http://localhost:8080/dashboards/{data['id']}")
```
