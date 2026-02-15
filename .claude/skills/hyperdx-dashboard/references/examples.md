# Working Dashboard Examples

All examples use the HyperDX Internal API format (`charts`/`series`), deployed via `POST http://localhost:8000/dashboards`.

## Chart Patterns

### 1. KPI Count Chart

```json
{
  "id": "total-llm-requests",
  "name": "Total LLM Requests",
  "x": 0, "y": 0, "w": 3, "h": 2,
  "series": [{
    "type": "number",
    "table": "logs",
    "aggFn": "count",
    "where": "gen_ai.request.model:*",
    "numberFormat": {
      "output": "number",
      "mantissa": 0,
      "factor": 1,
      "thousandSeparated": true,
      "average": false,
      "decimalBytes": false
    }
  }],
  "seriesReturnType": "column"
}
```

Note: No `field` for `count` aggFn.

### 2. KPI Sum Chart

```json
{
  "id": "total-input-tokens",
  "name": "Total Input Tokens",
  "x": 3, "y": 0, "w": 3, "h": 2,
  "series": [{
    "type": "number",
    "table": "logs",
    "aggFn": "sum",
    "field": "gen_ai.usage.input_tokens",
    "where": "gen_ai.request.model:*",
    "numberFormat": {
      "output": "number",
      "mantissa": 0,
      "factor": 1,
      "thousandSeparated": true,
      "average": false,
      "decimalBytes": false
    }
  }],
  "seriesReturnType": "column"
}
```

### 3. KPI Avg Chart (Latency)

```json
{
  "id": "avg-latency-ms",
  "name": "Avg Latency (ms)",
  "x": 9, "y": 0, "w": 3, "h": 2,
  "series": [{
    "type": "number",
    "table": "logs",
    "aggFn": "avg",
    "field": "duration",
    "where": "gen_ai.request.model:*",
    "numberFormat": {
      "output": "number",
      "mantissa": 2,
      "factor": 1,
      "thousandSeparated": true,
      "average": false,
      "decimalBytes": false
    }
  }],
  "seriesReturnType": "column"
}
```

Note: Use `duration` (HyperDX field name), NOT `_duration`.

### 4. Time-Series Chart (Count Over Time)

```json
{
  "id": "requests-over-time",
  "name": "LLM Requests Over Time",
  "x": 0, "y": 2, "w": 6, "h": 3,
  "series": [{
    "type": "time",
    "table": "logs",
    "aggFn": "count",
    "where": "gen_ai.request.model:*",
    "groupBy": []
  }],
  "seriesReturnType": "column"
}
```

### 5. Multi-Series Time Chart (Two Lines)

```json
{
  "id": "token-usage-over-time",
  "name": "Token Usage Over Time",
  "x": 6, "y": 2, "w": 6, "h": 3,
  "series": [
    {
      "type": "time",
      "table": "logs",
      "aggFn": "sum",
      "field": "gen_ai.usage.input_tokens",
      "where": "gen_ai.request.model:*",
      "groupBy": []
    },
    {
      "type": "time",
      "table": "logs",
      "aggFn": "sum",
      "field": "gen_ai.usage.output_tokens",
      "where": "gen_ai.request.model:*",
      "groupBy": []
    }
  ],
  "seriesReturnType": "column"
}
```

Multiple items in `series` array = multiple lines on the same chart.

### 6. Time Chart with groupBy

```json
{
  "id": "cpu-by-status",
  "name": "CPU % by Health Status",
  "x": 0, "y": 5, "w": 6, "h": 3,
  "series": [{
    "type": "time",
    "table": "logs",
    "aggFn": "avg",
    "field": "system.cpu.percent",
    "where": "span_name:cpu-load-sample service:macos-system-monitor",
    "groupBy": ["health.status"]
  }],
  "seriesReturnType": "column"
}
```

### 7. System Metrics KPI (Custom Attributes)

```json
{
  "id": "avg-cpu-pct",
  "name": "Avg CPU %",
  "x": 0, "y": 0, "w": 3, "h": 2,
  "series": [{
    "type": "number",
    "table": "logs",
    "aggFn": "avg",
    "field": "system.cpu.percent",
    "where": "span_name:cpu-load-sample service:macos-system-monitor",
    "numberFormat": {
      "output": "percent",
      "mantissa": 1,
      "factor": 1,
      "thousandSeparated": true,
      "average": false,
      "decimalBytes": false
    }
  }],
  "seriesReturnType": "column"
}
```

## Full Dashboard Example — LLM Observability

```json
{
  "name": "LLM Observability (Pre-built)",
  "query": "",
  "tags": ["llm", "observability", "pre-built"],
  "charts": [
    {
      "id": "total-llm-requests",
      "name": "Total LLM Requests",
      "x": 0, "y": 0, "w": 3, "h": 2,
      "series": [{"type": "number", "table": "logs", "aggFn": "count", "where": "gen_ai.request.model:*", "numberFormat": {"output": "number", "mantissa": 0, "factor": 1, "thousandSeparated": true, "average": false, "decimalBytes": false}}],
      "seriesReturnType": "column"
    },
    {
      "id": "total-input-tokens",
      "name": "Total Input Tokens",
      "x": 3, "y": 0, "w": 3, "h": 2,
      "series": [{"type": "number", "table": "logs", "aggFn": "sum", "field": "gen_ai.usage.input_tokens", "where": "gen_ai.request.model:*", "numberFormat": {"output": "number", "mantissa": 0, "factor": 1, "thousandSeparated": true, "average": false, "decimalBytes": false}}],
      "seriesReturnType": "column"
    },
    {
      "id": "total-output-tokens",
      "name": "Total Output Tokens",
      "x": 6, "y": 0, "w": 3, "h": 2,
      "series": [{"type": "number", "table": "logs", "aggFn": "sum", "field": "gen_ai.usage.output_tokens", "where": "gen_ai.request.model:*", "numberFormat": {"output": "number", "mantissa": 0, "factor": 1, "thousandSeparated": true, "average": false, "decimalBytes": false}}],
      "seriesReturnType": "column"
    },
    {
      "id": "avg-latency-ms",
      "name": "Avg Latency (ms)",
      "x": 9, "y": 0, "w": 3, "h": 2,
      "series": [{"type": "number", "table": "logs", "aggFn": "avg", "field": "duration", "where": "gen_ai.request.model:*", "numberFormat": {"output": "number", "mantissa": 2, "factor": 1, "thousandSeparated": true, "average": false, "decimalBytes": false}}],
      "seriesReturnType": "column"
    },
    {
      "id": "requests-over-time",
      "name": "LLM Requests Over Time",
      "x": 0, "y": 2, "w": 6, "h": 3,
      "series": [{"type": "time", "table": "logs", "aggFn": "count", "where": "gen_ai.request.model:*", "groupBy": []}],
      "seriesReturnType": "column"
    },
    {
      "id": "token-usage-over-time",
      "name": "Token Usage Over Time",
      "x": 6, "y": 2, "w": 6, "h": 3,
      "series": [
        {"type": "time", "table": "logs", "aggFn": "sum", "field": "gen_ai.usage.input_tokens", "where": "gen_ai.request.model:*", "groupBy": []},
        {"type": "time", "table": "logs", "aggFn": "sum", "field": "gen_ai.usage.output_tokens", "where": "gen_ai.request.model:*", "groupBy": []}
      ],
      "seriesReturnType": "column"
    },
    {
      "id": "avg-latency-over-time",
      "name": "Avg Latency Over Time (ms)",
      "x": 0, "y": 5, "w": 6, "h": 3,
      "series": [{"type": "time", "table": "logs", "aggFn": "avg", "field": "duration", "where": "gen_ai.request.model:*", "groupBy": []}],
      "seriesReturnType": "column"
    },
    {
      "id": "max-latency-over-time",
      "name": "Max Latency Over Time (ms)",
      "x": 6, "y": 5, "w": 6, "h": 3,
      "series": [{"type": "time", "table": "logs", "aggFn": "max", "field": "duration", "where": "gen_ai.request.model:*", "groupBy": []}],
      "seriesReturnType": "column"
    }
  ]
}
```

## Deploy Pattern

```python
import requests

API = 'http://localhost:8000'
TOKEN = '<access_key>'  # Get via: docker exec hyperdx-local mongo --quiet --eval 'db=db.getSiblingDB("hyperdx"); print(db.users.findOne({}).accessKey)'
HEADERS = {'Authorization': f'Bearer {TOKEN}', 'Content-Type': 'application/json'}

dashboard = {
    'name': 'My Dashboard',
    'query': '',
    'tags': ['my-tag'],
    'charts': [ ... ]
}

resp = requests.post(f'{API}/dashboards', headers=HEADERS, json=dashboard)
data = resp.json()['data']
print(f"URL: http://localhost:8080/dashboards/{data['_id']}")
```

## Key Differences from Old MongoDB Format

| Old (MongoDB) | New (API) |
|---------------|-----------|
| `tiles` array | `charts` array |
| `config.name` | `name` (top-level on chart) |
| `config.select[].aggFn` | `series[].aggFn` |
| `config.select[].valueExpression` | `series[].field` (HyperDX name) |
| `config.where` (SQL) | `series[].where` (Lucene) |
| `config.whereLanguage: "sql"` | Not needed — always Lucene |
| `config.displayType: "line"` | `series[].type: "time"` |
| `config.displayType: "number"` | `series[].type: "number"` |
| `config.source: "{{ID}}"` | Not needed — API handles routing |
| `_number_attributes['x']` in valueExpression | `x` in field (plain name) |
| `_duration` | `duration` |
| `_service` | `service` |
