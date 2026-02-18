# Working Dashboard Examples

All examples use the ClickStack tiles format, deployed via `POST http://localhost:8000/dashboards`. No auth required for local mode.

## Tile Patterns

### 1. KPI Count Tile

```json
{
  "id": "total-requests",
  "x": 0, "y": 0, "w": 6, "h": 2,
  "config": {
    "name": "Total Requests",
    "source": "traces",
    "select": [{"aggFn": "count", "valueExpression": "", "aggCondition": ""}],
    "where": "",
    "whereLanguage": "lucene",
    "groupBy": [],
    "displayType": "number",
    "numberFormat": {
      "output": "number", "mantissa": 0, "factor": 1,
      "thousandSeparated": true, "average": false, "decimalBytes": false
    }
  }
}
```

Note: `valueExpression: ""` for `count` aggFn. Uses the **Integer Count** numberFormat template.

### 2. KPI Avg Latency Tile

```json
{
  "id": "avg-latency",
  "x": 6, "y": 0, "w": 6, "h": 2,
  "config": {
    "name": "Avg Latency",
    "source": "traces",
    "select": [{"aggFn": "avg", "valueExpression": "Duration", "aggCondition": ""}],
    "where": "service:my-service",
    "whereLanguage": "lucene",
    "groupBy": [],
    "displayType": "number",
    "numberFormat": {
      "output": "number", "mantissa": 2, "factor": 1,
      "thousandSeparated": true, "average": false, "decimalBytes": false
    }
  }
}
```

Note: `Duration` is nanoseconds (UInt64). HyperDX UI handles display formatting.

### 3. Time-Series Line Chart

```json
{
  "id": "requests-over-time",
  "x": 0, "y": 2, "w": 12, "h": 3,
  "config": {
    "name": "Requests Over Time",
    "source": "traces",
    "select": [{"aggFn": "count", "valueExpression": "", "aggCondition": ""}],
    "where": "service:my-service",
    "whereLanguage": "lucene",
    "groupBy": [],
    "displayType": "line"
  }
}
```

### 4. Time-Series with groupBy

```json
{
  "id": "latency-by-service",
  "x": 0, "y": 5, "w": 12, "h": 3,
  "config": {
    "name": "Latency by Service",
    "source": "traces",
    "select": [{"aggFn": "avg", "valueExpression": "Duration", "aggCondition": ""}],
    "where": "",
    "whereLanguage": "lucene",
    "groupBy": [{"valueExpression": "ServiceName"}],
    "displayType": "line"
  }
}
```

Note: `groupBy` uses objects `{"valueExpression": "ColumnName"}`, not strings.

### 5. Stacked Bar Chart

```json
{
  "id": "errors-by-service",
  "x": 12, "y": 2, "w": 12, "h": 3,
  "config": {
    "name": "Errors by Service",
    "source": "logs",
    "select": [{"aggFn": "count", "valueExpression": "", "aggCondition": ""}],
    "where": "level:error",
    "whereLanguage": "lucene",
    "groupBy": [{"valueExpression": "ServiceName"}],
    "displayType": "stacked_bar"
  }
}
```

### 6. Multi-Select Chart (Percentile Lines)

```json
{
  "id": "latency-percentiles",
  "x": 0, "y": 8, "w": 12, "h": 3,
  "config": {
    "name": "Latency Percentiles",
    "source": "traces",
    "select": [
      {"aggFn": "quantile", "level": 0.5, "valueExpression": "Duration", "aggCondition": ""},
      {"aggFn": "quantile", "level": 0.95, "valueExpression": "Duration", "aggCondition": ""},
      {"aggFn": "quantile", "level": 0.99, "valueExpression": "Duration", "aggCondition": ""}
    ],
    "where": "service:checkout",
    "whereLanguage": "lucene",
    "groupBy": [],
    "displayType": "line"
  }
}
```

Note: Use `quantile` + `level` instead of `p50`/`p95`/`p99`.

### 7. Multi-Select with aggCondition

```json
{
  "id": "svc-latency-comparison",
  "x": 12, "y": 8, "w": 12, "h": 3,
  "config": {
    "name": "Service Latency Comparison",
    "source": "traces",
    "select": [
      {"aggFn": "avg", "valueExpression": "Duration", "aggCondition": "ServiceName = 'payment'"},
      {"aggFn": "avg", "valueExpression": "Duration", "aggCondition": "ServiceName = 'cart'"},
      {"aggFn": "avg", "valueExpression": "Duration", "aggCondition": "ServiceName = 'shipping'"}
    ],
    "where": "",
    "whereLanguage": "lucene",
    "groupBy": [],
    "displayType": "line"
  }
}
```

Note: `aggCondition` provides per-select-item SQL filtering. `where` is shared across all select items.

### 8. Table Tile

```json
{
  "id": "top-operations",
  "x": 0, "y": 11, "w": 12, "h": 3,
  "config": {
    "name": "Top Operations by Count",
    "source": "traces",
    "select": [{"aggFn": "count", "valueExpression": "", "aggCondition": ""}],
    "where": "service:checkout",
    "whereLanguage": "lucene",
    "groupBy": [{"valueExpression": "SpanName"}],
    "displayType": "table"
  }
}
```

### 9. Metrics Time Chart

```json
{
  "id": "cpu-utilization",
  "x": 0, "y": 14, "w": 12, "h": 3,
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
}
```

Note: Metrics tiles require `metricName` and `metricDataType` in config. `valueExpression` is always `"Value"` for metric aggregation.

### 10. Metrics KPI Tile

```json
{
  "id": "avg-memory-usage",
  "x": 12, "y": 14, "w": 6, "h": 2,
  "config": {
    "name": "Avg Memory Usage",
    "source": "metrics",
    "select": [{"aggFn": "avg", "valueExpression": "Value", "aggCondition": ""}],
    "where": "",
    "whereLanguage": "lucene",
    "groupBy": [],
    "displayType": "number",
    "metricName": "system.memory.usage",
    "metricDataType": "Sum",
    "numberFormat": {
      "output": "byte", "mantissa": 0, "factor": 1,
      "thousandSeparated": true, "average": false, "decimalBytes": true
    }
  }
}
```

## Deploy Pattern

```python
import requests

API = 'http://localhost:8000'

dashboard = {
    'name': 'My Dashboard',
    'tags': ['my-tag'],
    'tiles': [ ... ]
}

resp = requests.post(f'{API}/dashboards', json=dashboard)
data = resp.json()
print(f"URL: http://localhost:8080/dashboards/{data['id']}")
```

## Key Differences from v1 Format

| v1 (charts/series) | v2 (tiles/config/select) |
|--------------------|--------------------------|
| `charts` array | `tiles` array |
| `chart.name` | `tile.config.name` |
| `series[].aggFn` | `select[].aggFn` |
| `series[].field` (HyperDX name) | `select[].valueExpression` (ClickHouse column) |
| `series[].where` (per-series) | `config.where` (shared) + `select[].aggCondition` (per-item) |
| `series[].type: "time"` | `config.displayType: "line"` |
| `series[].type: "number"` | `config.displayType: "number"` |
| `series[].type: "table"` | `config.displayType: "table"` |
| `series[].groupBy: ["field"]` | `config.groupBy: [{"valueExpression": "Col"}]` |
| `series[].table: "logs"` | `config.source: "traces"` / `"logs"` |
| `chart.asRatio: false` | Not needed |
| `dashboard.query: ""` | Not needed |
| 12-col grid | 24-col grid |
| `p50`/`p95`/`p99` aggFn | `quantile` + `level` |
| `field: "duration"` | `valueExpression: "Duration"` |
| `field: "service"` → groupBy | `groupBy: [{"valueExpression": "ServiceName"}]` |
| Bearer token auth | No auth (local mode) |
| `POST /api/v1/dashboards` | `POST /dashboards` |
