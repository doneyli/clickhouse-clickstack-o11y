---
name: hyperdx-dashboard
description: Generates, validates, and deploys HyperDX dashboard definitions via the internal REST API. Covers chart layout, aggregation, Lucene filters, and the HyperDX log_stream schema. Use when creating, modifying, or fixing HyperDX dashboards.
---

# HyperDX Dashboard Builder

## Workflow

1. **Discover data** — Run `.venv/bin/python query_clickhouse.py --summary --attributes` to see available services, span names, and attributes in ClickHouse.
2. **Generate JSON** — Build the dashboard definition following the Chart Format below.
3. **Validate** — Check every chart against the Critical Rules section.
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
| **Series source** | `table: "logs"` | `dataSource: "events"` |
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
| 5 | `aggFn` supports: count, sum, avg, min, max, p50, p90, p95, p99, count_distinct, last_value | Invalid values fail silently |
| 6 | `numberFormat` required on `type: "number"` series | KPI tiles display raw |
| 7 | Grid is 12 columns wide; `x + w <= 12` | Tiles overlap or overflow |
| 8 | `field` is omitted (or absent) for `count` aggFn | Including a field with count may error |
| 9 | `groupBy` is an array (e.g., `["span_name"]`) | Works for time charts to split by field |
| 10 | Deploy via API only, never MongoDB direct insert | Wrong team ID → dashboard invisible |
| 11 | `duration` is the field name for span duration (ms) | Not `_duration` |

## Lucene Where Syntax

```
service:macos-system-monitor                    # Filter by service
span_name:cpu-load-sample                       # Filter by span name
gen_ai.request.model:*                          # Field exists (any value)
level:error                                     # Filter by level
span_name:cpu-load-sample service:my-service    # AND (space-separated)
```

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

## Series Types

| type | Use | Extra fields |
|------|-----|-------------|
| `time` | Line/bar charts over time | `groupBy` array |
| `number` | KPI number tiles | `numberFormat` object |
| `table` | Table display | `sortOrder` ("asc"/"desc") |
| `histogram` | Histogram | |
| `search` | Search results | `fields` array |
| `markdown` | Markdown text | `content` string |

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

## Common Chart Patterns

**KPI row (4 across):** `w:3, h:2` at `x: 0, 3, 6, 9` on `y:0`

**Half-width charts:** `w:6, h:3` at `x: 0, 6`

**Full-width chart:** `w:12, h:3`

## Project Tools

| Command | Purpose |
|---------|---------|
| `.venv/bin/python query_clickhouse.py --summary` | Data overview (counts, services) |
| `.venv/bin/python query_clickhouse.py --attributes` | List all attributes |
| `.venv/bin/python query_clickhouse.py --query "SQL"` | Run arbitrary ClickHouse SQL |
| `.venv/bin/python generate_demo_data.py --count 100` | Generate synthetic LLM trace data |
| `.venv/bin/python system-telemetry/generate_system_traces.py --count 10 --interval 5` | Generate system telemetry |

## References

For detailed documentation, see:
- [Chart format reference](references/chart-format.md) — Full field reference and schema
- [ClickHouse schema](references/clickhouse-schema.md) — Complete log_stream schema and discovery queries
- [Rules & validation checklist](references/rules.md) — All rules with post-generation checklist
- [Working examples](references/examples.md) — Verified chart patterns and full dashboard examples
