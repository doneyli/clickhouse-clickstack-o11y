---
name: hyperdx-dashboard
description: Generates, validates, and deploys HyperDX dashboard definitions via the internal REST API. Covers chart layout, aggregation, Lucene filters, and the HyperDX log_stream schema. Use when creating, modifying, or fixing HyperDX dashboards.
---

# HyperDX Dashboard Builder

## Workflow

1. **Discover data** — Run `.venv/bin/python query_clickhouse.py --summary --attributes` to see available services, span names, and attributes in ClickHouse.
   For metrics, also query: `.venv/bin/python query_clickhouse.py --query "SELECT DISTINCT name, data_type FROM metric_stream ORDER BY name"` or use the API: `curl -s http://localhost:8000/metrics/names -H "Authorization: Bearer {TOKEN}"`
2. **Generate JSON** — Build the dashboard definition following the Chart Format below.
3. **Validate** — For every chart, print the Post-Generation Validation Checklist from `references/rules.md` with `[ok]` or `[FAIL]` for each item. Fix all `[FAIL]` items before proceeding. Do NOT skip this step.
4. **Deploy** — Use Python `requests` to POST to the HyperDX internal API on port 8000.
5. **Verify** — Open HyperDX UI at `http://localhost:8080/dashboards` and confirm charts render.

## CRITICAL: Always Use the API

**NEVER insert dashboards directly into MongoDB.** Always use the HyperDX REST API.

Both endpoints work (user's MongoDB team has been aligned with the local team):

```
# Internal API (recommended — uses same format as UI)
POST http://localhost:8000/dashboards
GET  http://localhost:8000/dashboards
PUT  http://localhost:8000/dashboards/{id}
DELETE http://localhost:8000/dashboards/{id}

# Public API v1 (official docs format — also works)
POST http://localhost:8000/api/v1/dashboards
GET  http://localhost:8000/api/v1/dashboards
PUT  http://localhost:8000/api/v1/dashboards/{id}
DELETE http://localhost:8000/api/v1/dashboards/{id}
```

**Auth:** `Authorization: Bearer {ACCESS_KEY}`

Get access key:
```bash
docker exec hyperdx-local mongo --quiet --eval \
  'db=db.getSiblingDB("hyperdx"); print(db.users.findOne({}).accessKey)'
```

### Two endpoints, two formats

Both endpoints read/write the same dashboards. The difference is the wire format:

| | Internal `/dashboards` | Public `/api/v1/dashboards` |
|---|---|---|
| **Series source (logs/traces)** | `table: "logs"` | `dataSource: "events"` |
| **Series source (metrics)** | `table: "metrics"` | `dataSource: "metrics"` |
| **Ratio mode** | `seriesReturnType: "column"` | `asRatio: false` |
| **Response ID** | `_id` | `id` |
| **Input accepts** | internal format only | accepts `table` (auto-converts to `dataSource` in response) |

**Use the internal `/dashboards` endpoint** — it matches the format used throughout this project's dashboard JSON files and the UI.

## Chart Format (Internal API)

```json
{
  "name": "Dashboard Name",
  "query": "",
  "tags": ["tag1", "tag2"],
  "charts": [
    {
      "id": "unique-kebab-id",
      "name": "Chart Title",
      "x": 0, "y": 0, "w": 6, "h": 3,
      "series": [{
        "type": "time",
        "table": "logs",
        "aggFn": "avg",
        "field": "system.cpu.percent",
        "where": "span_name:cpu-load-sample service:macos-system-monitor",
        "groupBy": []
      }],
      "seriesReturnType": "column"
    }
  ]
}
```

Key points:
- **`charts`** array (NOT `tiles`)
- Each chart has `id`, `name`, `x`, `y`, `w`, `h`, `series`, `seriesReturnType`
- **`where`** uses Lucene syntax (NOT SQL)
- **`field`** uses HyperDX field names (NOT ClickHouse column expressions)
- **No** `source`, `displayType`, `whereLanguage`, or `granularity` fields

## Critical Rules

| # | Rule | What breaks |
|---|------|-------------|
| 1 | `where` uses **Lucene syntax** | SQL syntax silently fails |
| 2 | `field` uses HyperDX names (e.g., `system.cpu.percent`) | ClickHouse expressions like `_number_attributes['...']` won't work |
| 3 | Top-level array is `charts`, not `tiles` | Dashboard shows empty |
| 4 | Series `type` must be: `time`, `number`, `table`, `histogram`, `search`, `markdown` | Chart renders blank |
| 5 | `aggFn` must be valid | **Standard:** `count`, `count_rate`, `sum`, `avg`, `min`, `max`, `p50`, `p90`, `p95`, `p99`, `count_distinct`, `avg_rate`, `sum_rate`, `min_rate`, `max_rate`, `p50_rate`, `p90_rate`, `p95_rate`, `p99_rate`. **Internal only:** `last_value`, `count_per_sec`, `count_per_min`, `count_per_hour`. Invalid values fail silently. |
| 6 | `numberFormat` required on `type: "number"` series | KPI tiles display raw |
| 7 | Grid is 12 columns wide; `x + w <= 12` | Tiles overlap or overflow |
| 8 | `field` is omitted (or absent) for `count` aggFn | Including a field with count may error |
| 9 | `groupBy` is an array (e.g., `["span_name"]`) | Works for time charts to split by field |
| 10 | Deploy via API only, never MongoDB direct insert | Wrong team ID → dashboard invisible |
| 11 | `duration` is the field name for span duration (ms) | Not `_duration` |
| 12 | No `source`, `displayType`, `whereLanguage`, `granularity`, `config`, `select` | Old MongoDB format fields — silently ignored or cause errors |
| 13 | All series in a chart share identical `type` and `groupBy` | Mixed types or mismatched groupBy silently drops data |
| 14 | Always emit: `seriesReturnType: "column"`, `table: "logs"` (or `"metrics"` for metric data), `groupBy: []` on time series, `query: ""` at dashboard level | Omitting creates non-deterministic API behavior |
| 15 | `h: 2` for KPI (`type: "number"`), `h: 3` for all others | Inconsistent heights break row alignment |
| 16 | Chart `id`: descriptive kebab-case, max 36 chars | Omitting generates UUIDs — unreadable in debugging |
| 17 | Metrics series require `metricDataType` and `field` in `"name - DataType"` format | Missing `metricDataType` → API error "Metric data type is required". Wrong field format → silently returns no data. |

## Lucene Where Syntax

```
service:macos-system-monitor                    # Exact match
span_name:cpu-load-sample                       # Exact match
gen_ai.request.model:*                          # Field exists (any value)
level:error                                     # Exact match
span_name:cpu-load-sample service:my-service    # AND (space-separated)
span_name:cpu-load-sample OR span_name:memory   # OR (explicit keyword)
NOT level:error                                 # Negation
-level:error                                    # Negation (shorthand)
body:"connection refused"                       # Exact phrase
duration:>1000                                  # Comparison operators
service:macos-*                                 # Wildcard
```

Precedence: `NOT` > `AND` (space) > `OR`. See `references/chart-format.md` for full syntax reference.

## HyperDX Field Names

Use these in `field` and `where`, NOT ClickHouse column names:

| HyperDX Name | Maps To | Type |
|--------------|---------|------|
| `duration` | `_duration` | number |
| `service` | `_service` | string |
| `span_name` | `span_name` | string |
| `level` | `severity_text` | string |
| `body` | `_hdx_body` | string |
| `host` | `_host` | string |
| Custom attributes (e.g., `system.cpu.percent`) | `_number_attributes['system.cpu.percent']` | auto-detected |
| Metric fields (e.g., `system.cpu.utilization - Gauge`) | From `/metrics/names` API or `metric_stream` table | metric |

## Series Types

| type | Use | Extra fields |
|------|-----|-------------|
| `time` | Line/bar charts over time | `groupBy` array |
| `number` | KPI number tiles | `numberFormat` object |
| `table` | Table display | `sortOrder` ("asc"/"desc") |
| `histogram` | Histogram | |
| `search` | Search results | `fields` array |
| `markdown` | Markdown text | `content` string |

## Metrics Charts

When charting **metric data** (from the `metric_stream` ClickHouse table), series require three additional fields compared to logs/traces:

1. **`table: "metrics"`** — NOT `"logs"`
2. **`metricDataType`** — required string: `"Gauge"`, `"Sum"`, `"Histogram"`, or `"Summary"`
3. **`field` format: `"metric.name - DataType"`** — e.g., `"system.cpu.utilization - Gauge"`, `"http.server.request.duration - Histogram"`

### Discovering metrics

```bash
# Via ClickHouse — list all metric names and their data types
.venv/bin/python query_clickhouse.py --query "SELECT DISTINCT name, data_type FROM metric_stream ORDER BY name"

# Via HyperDX API — returns metric names in the "name - DataType" format
curl -s http://localhost:8000/metrics/names -H "Authorization: Bearer {TOKEN}"
```

### Metrics `time` series example

```json
{
  "type": "time",
  "table": "metrics",
  "aggFn": "avg",
  "field": "system.cpu.utilization - Gauge",
  "metricDataType": "Gauge",
  "where": "",
  "groupBy": []
}
```

### Metrics `number` series (KPI) example

```json
{
  "type": "number",
  "table": "metrics",
  "aggFn": "avg",
  "field": "system.memory.usage - Sum",
  "metricDataType": "Sum",
  "where": "",
  "numberFormat": {
    "output": "byte",
    "mantissa": 0,
    "factor": 1,
    "thousandSeparated": true,
    "average": false,
    "decimalBytes": true
  }
}
```

### Notes

- **Sum-type metrics** support `_rate` aggFn variants (e.g., `sum_rate`, `avg_rate`, `count_rate`)
- The `metricDataType` value must match the suffix in the `field` name (e.g., field `"... - Gauge"` → `metricDataType: "Gauge"`)
- All other chart-level fields (`id`, `name`, `x`, `y`, `w`, `h`, `seriesReturnType`) remain the same as logs charts

## Deploy Pattern (Python)

```python
import requests

API = 'http://localhost:8000'
TOKEN = '<access_key>'  # from MongoDB users.accessKey
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

### Deploy Error Handling

Always check `resp.status_code` after the POST:

| Status | Cause | Fix |
|--------|-------|-----|
| `401` | Bad or expired access key | Re-fetch token: `docker exec hyperdx-local mongo --quiet --eval 'db=db.getSiblingDB("hyperdx"); print(db.users.findOne({}).accessKey)'` |
| `400` | Malformed JSON (missing required fields, invalid types) | Re-validate against the checklist in `references/rules.md` |
| `500` | Internal HyperDX/container error | Check container logs: `docker logs hyperdx-local --tail 50` |
| Connection refused | Container not running | Start it: `docker compose up -d` |

```python
resp = requests.post(f'{API}/dashboards', headers=HEADERS, json=dashboard)
if resp.status_code != 200:
    print(f"Deploy failed ({resp.status_code}): {resp.text}")
else:
    data = resp.json()['data']
    print(f"URL: http://localhost:8080/dashboards/{data['_id']}")
```

## Common Chart Patterns

**KPI row (4 across):** `w:3, h:2` at `x: 0, 3, 6, 9` on `y:0`

**Half-width charts:** `w:6, h:3` at `x: 0, 6`

**Full-width chart:** `w:12, h:3`

## Project Tools

| Command | Purpose |
|---------|---------|
| `.venv/bin/python query_clickhouse.py --summary` | Data overview (counts, services) |
| `.venv/bin/python query_clickhouse.py --attributes` | List all attribute keys |
| `.venv/bin/python query_clickhouse.py --services` | List all services |
| `.venv/bin/python query_clickhouse.py --query "SQL"` | Run arbitrary ClickHouse SQL |

## References

For detailed documentation, see:
- [Chart format reference](references/chart-format.md) — Full field reference and schema
- [ClickHouse schema](references/clickhouse-schema.md) — Complete log_stream schema and discovery queries
- [Rules & validation checklist](references/rules.md) — All rules with post-generation checklist
- [Working examples](references/examples.md) — Verified chart patterns and full dashboard examples
