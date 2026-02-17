# Working Dashboard Examples

All examples use the HyperDX Internal API format (`charts`/`series`), deployed via `POST http://localhost:8000/dashboards`.

## Chart Patterns

### 1. KPI Count Chart

```json
{
  "id": "total-requests",
  "name": "Total Requests",
  "x": 0, "y": 0, "w": 3, "h": 2,
  "series": [{
    "type": "number",
    "table": "logs",
    "aggFn": "count",
    "where": "",
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

Note: No `field` for `count` aggFn. Uses the **Integer Count** numberFormat template.

### 2. KPI Sum Chart

```json
{
  "id": "total-metric-value",
  "name": "Total Metric Value",
  "x": 3, "y": 0, "w": 3, "h": 2,
  "series": [{
    "type": "number",
    "table": "logs",
    "aggFn": "sum",
    "field": "my.numeric.attribute",
    "where": "service:my-service",
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
    "where": "service:my-service",
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

Note: Use `duration` (HyperDX field name), NOT `_duration`. Uses the **Latency ms** numberFormat template.

### 4. Time-Series Chart (Count Over Time)

```json
{
  "id": "requests-over-time",
  "name": "Requests Over Time",
  "x": 0, "y": 2, "w": 6, "h": 3,
  "series": [{
    "type": "time",
    "table": "logs",
    "aggFn": "count",
    "where": "service:my-service",
    "groupBy": []
  }],
  "seriesReturnType": "column"
}
```

### 5. Multi-Series Time Chart (Two Lines)

```json
{
  "id": "two-metrics-over-time",
  "name": "Two Metrics Over Time",
  "x": 6, "y": 2, "w": 6, "h": 3,
  "series": [
    {
      "type": "time",
      "table": "logs",
      "aggFn": "avg",
      "field": "metric.one",
      "where": "service:my-service",
      "groupBy": []
    },
    {
      "type": "time",
      "table": "logs",
      "aggFn": "avg",
      "field": "metric.two",
      "where": "service:my-service",
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
  "id": "latency-by-service",
  "name": "Latency by Service",
  "x": 0, "y": 5, "w": 6, "h": 3,
  "series": [{
    "type": "time",
    "table": "logs",
    "aggFn": "avg",
    "field": "duration",
    "where": "",
    "groupBy": ["service"]
  }],
  "seriesReturnType": "column"
}
```

### 7. KPI with Custom Numeric Attribute

```json
{
  "id": "avg-custom-metric",
  "name": "Avg Custom Metric",
  "x": 0, "y": 0, "w": 3, "h": 2,
  "series": [{
    "type": "number",
    "table": "logs",
    "aggFn": "avg",
    "field": "my.custom.metric",
    "where": "span_name:my-operation service:my-service",
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

### 8. Table Chart (Top Spans by Count)

```json
{
  "id": "top-spans-by-count",
  "name": "Top Spans by Count",
  "x": 0, "y": 8, "w": 6, "h": 3,
  "series": [{
    "type": "table",
    "table": "logs",
    "aggFn": "count",
    "where": "service:my-service",
    "groupBy": ["span_name"],
    "sortOrder": "desc"
  }],
  "seriesReturnType": "column"
}
```

Note: `table` type requires `groupBy` and `sortOrder`. No `field` needed for `count` aggFn.

### 9. Search Chart (Recent Error Events)

```json
{
  "id": "recent-errors",
  "name": "Recent Errors",
  "x": 6, "y": 8, "w": 6, "h": 3,
  "series": [{
    "type": "search",
    "table": "logs",
    "where": "level:error",
    "fields": ["service", "span_name", "body", "duration"]
  }],
  "seriesReturnType": "column"
}
```

Note: `search` type requires `fields` array. No `aggFn` or `groupBy`.

### 10. Markdown Chart (Section Divider)

```json
{
  "id": "section-header",
  "name": "Section Header",
  "x": 0, "y": 11, "w": 12, "h": 3,
  "series": [{
    "type": "markdown",
    "content": "## Section Title\nDescription text here."
  }],
  "seriesReturnType": "column"
}
```

Note: `markdown` type requires only `type` and `content`. No `table`, `aggFn`, `field`, or `where`.

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
