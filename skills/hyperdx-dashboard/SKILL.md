---
name: hyperdx-dashboard
description: Generates, validates, and deploys ClickStack dashboard definitions via the v2 API. Covers tile layout, series types, Lucene filters, and OTel-native schema discovery. Use when creating, modifying, or fixing dashboards.
license: Apache-2.0
compatibility: Requires a running ClickStack instance (Docker) with API access on port 8000 and ClickHouse on port 8123.
metadata:
  author: doneyli
  version: "1.0.0"
---

# ClickStack Dashboard Builder (v2 API)

## Workflow

1. **Discover data** — Query ClickHouse to see available tables, services, and attributes:
   ```bash
   # List tables
   curl -s "http://localhost:8123/?user=api&password=api" --data "SHOW TABLES FROM default"

   # Discover traces schema and services
   curl -s "http://localhost:8123/?user=api&password=api" --data "SELECT ServiceName, count() AS cnt FROM otel_traces GROUP BY ServiceName ORDER BY cnt DESC"

   # Discover trace attributes
   curl -s "http://localhost:8123/?user=api&password=api" --data "SELECT DISTINCT arrayJoin(SpanAttributes.keys) AS attr FROM otel_traces ORDER BY attr LIMIT 100"

   # Discover log services (includes nginx-demo)
   curl -s "http://localhost:8123/?user=api&password=api" --data "SELECT ServiceName, count() AS cnt FROM otel_logs GROUP BY ServiceName ORDER BY cnt DESC"

   # Discover log attributes
   curl -s "http://localhost:8123/?user=api&password=api" --data "SELECT DISTINCT arrayJoin(LogAttributes.keys) AS attr FROM otel_logs ORDER BY attr LIMIT 100"

   # Discover NGINX log attributes (if working with nginx-demo data)
   curl -s "http://localhost:8123/?user=api&password=api" --data "SELECT DISTINCT arrayJoin(LogAttributes.keys) AS attr FROM otel_logs WHERE ServiceName = 'nginx-demo' ORDER BY attr"

   # Discover metrics
   curl -s "http://localhost:8123/?user=api&password=api" --data "SELECT DISTINCT MetricName FROM otel_metrics_gauge UNION ALL SELECT DISTINCT MetricName FROM otel_metrics_sum ORDER BY MetricName"
   ```
2. **Resolve source IDs** — Fetch source IDs from `GET /sources` (mandatory — the API needs MongoDB source IDs, not kind strings like `"traces"`):
   ```python
   sources = requests.get(f'{API}/sources').json()
   SRC = {s['kind']: s['id'] for s in sources}
   # SRC = {"trace": "<id>", "log": "<id>", "metric": "<id>", "session": "<id>"}
   ```
   Use `SRC["trace"]`, `SRC["log"]`, `SRC["metric"]` as the `sourceId` in each series.
3. **Generate JSON** — Build the dashboard definition following the Tile Format below.
4. **Validate** — For every tile, print the Post-Generation Validation Checklist from `references/rules.md` with `[ok]` or `[FAIL]` for each item. Fix all `[FAIL]` items before proceeding. Do NOT skip this step.
5. **Deploy** — Use Python `requests` to POST to the ClickStack v2 API (`/api/v2/dashboards`) on port 8000 with Bearer auth.
6. **Verify** — Open ClickStack UI at `http://localhost:8080/dashboards` and confirm tiles render.

## CRITICAL: Always Use the API

**NEVER insert dashboards directly into the database.** Always use the ClickStack v2 REST API.

```
# v2 API (Bearer auth required)
POST   http://localhost:8000/api/v2/dashboards          # Create dashboard
GET    http://localhost:8000/api/v2/dashboards          # List all dashboards
GET    http://localhost:8000/api/v2/dashboards/{id}     # Get dashboard
DELETE http://localhost:8000/api/v2/dashboards/{id}     # Delete dashboard

# Source discovery (internal API, no auth)
GET    http://localhost:8000/sources                     # List data sources
```

### Auth

The v2 API requires a Bearer token (user access key). In local mode, `setup.sh` creates a default user with access key `clickstack-local-v2-api-key`.

```bash
curl -H "Authorization: Bearer clickstack-local-v2-api-key" http://localhost:8000/api/v2/dashboards
```

## Tile Format (v2 API)

```json
{
  "name": "Dashboard Name",
  "tags": ["tag1", "tag2"],
  "tiles": [
    {
      "name": "Chart Title",
      "x": 0, "y": 0, "w": 12, "h": 6,
      "series": [{
        "type": "time",
        "sourceId": "<source-id-from-GET-/sources>",
        "aggFn": "avg",
        "field": "Duration",
        "where": "ServiceName:my-service",
        "whereLanguage": "lucene",
        "groupBy": ["SpanName"],
        "displayType": "line"
      }]
    }
  ]
}
```

Key points:
- **`tiles`** array with **`series`** (NOT `config.select`)
- **`sourceId`** in each series: Must be a **source ID** from `GET /sources` (NOT a kind string like `"traces"`)
  - Fetch sources: `requests.get('http://localhost:8000/sources').json()`
  - Map by kind: `SRC = {s['kind']: s['id'] for s in sources}`
  - Use: `SRC["trace"]`, `SRC["log"]`, `SRC["metric"]`
- **`series`**: Each has a `type` discriminator (`time`, `number`, `table`, `search`, `markdown`)
- **`field`**: ClickHouse column name (`Duration`, `ServiceName`). Empty string for `count`.
- **`where`**: Lucene syntax per-series, with `whereLanguage: "lucene"`
- **`groupBy`**: Array of strings `["ServiceName"]` (NOT objects). Only on `time` and `table` types.
- **`displayType`**: Only on `time` series (`"line"` or `"stacked_bar"`)
- **Grid is 24 columns wide** — `x + w <= 24`
- **Tile `name`**: Required, top-level on tile (NOT nested in config)

## Series Types

### Time Series (`type: "time"`)
Line charts and stacked bar charts over time.
- Required: `type`, `sourceId`, `aggFn`, `where`, `groupBy`
- Optional: `field`, `whereLanguage`, `displayType` ("line"/"stacked_bar"), `level`, `numberFormat`, `metricDataType`, `metricName`, `alias`

### Number Series (`type: "number"`)
KPI number tiles.
- Required: `type`, `sourceId`, `aggFn`, `where`
- Optional: `field`, `whereLanguage`, `numberFormat`, `level`, `metricDataType`, `metricName`, `alias`
- No `groupBy`, no `displayType`

### Table Series (`type: "table"`)
Table display with grouping.
- Required: `type`, `sourceId`, `aggFn`, `where`, `groupBy`
- Optional: `field`, `whereLanguage`, `sortOrder` ("desc"/"asc"), `level`, `numberFormat`, `metricDataType`, `metricName`, `alias`
- No `displayType`

### Search Series (`type: "search"`)
Raw event search/log viewer.
- Required: `type`, `sourceId`, `fields` (string[]), `where`
- Optional: `whereLanguage`

### Markdown Series (`type: "markdown"`)
Static markdown text tile.
- Required: `type`, `content` (string, max 100k chars)
- No `sourceId`, no `field`, no `where`

## Critical Rules

| # | Rule | What breaks |
|---|------|-------------|
| 1 | `where` uses **Lucene syntax** with `whereLanguage: "lucene"` on each series | SQL syntax silently fails |
| 2 | `field` uses ClickHouse column names (e.g., `Duration`, `ServiceName`) | HyperDX names don't work |
| 3 | Top-level is `tiles` with `series` array. NOT `charts`, NOT `config.select[]` | API validation error |
| 4 | Series `type` must be valid: `time`, `number`, `table`, `search`, `markdown` | Zod validation error |
| 5 | `displayType` only on `time` series: `line` or `stacked_bar` | Other types have no displayType |
| 6 | `aggFn` must be valid: `avg`, `count`, `count_distinct`, `last_value`, `max`, `min`, `quantile`, `sum`, `any`, `none` | Zod validation error |
| 7 | `field: ""` (or omit) for `count` aggFn | Including a column with count may error |
| 8 | `numberFormat` recommended on `type: "number"` series | KPI tiles display raw without formatting |
| 9 | Grid is 24 columns wide; `x + w <= 24` | Tiles overlap or overflow |
| 10 | `groupBy` is array of **strings** `["Col"]` or `[]`. Max 10. Only on `time`/`table`. | Objects fail validation |
| 11 | Deploy via `POST /api/v2/dashboards` with Bearer auth | Unauthenticated requests get 401 |
| 12 | `tags: []` required at dashboard level (max 50 tags, max 32 chars each) | API validation error |
| 13 | Each series has its own `where` — no shared filter | Different from internal API |
| 14 | `h: 3` for number (KPI), `h: 6` for time (line/stacked_bar), `h: 5` for table | Inconsistent heights break alignment |
| 15 | Tile `name` is required, top-level on tile | API validation error |
| 16 | Metrics series need `metricName` and `metricDataType` (lowercase: `gauge`, `sum`, `histogram`, `summary`) | No data or API error |
| 17 | **NEVER use `type:span` or `type:log`** in `where` | Not searchable via Lucene |
| 18 | `sourceId` must be from `GET /sources`, NOT kind strings | Missing sources rejected by API |
| 19 | `Duration` is nanoseconds (UInt64) in `otel_traces` | HyperDX UI handles display formatting |
| 20 | Quantile uses `aggFn: "quantile"` + `level: 0.95` | Not `p95` — old aggFn values don't exist |
| 21 | All series in a tile must have the same `type` | Zod validation error |
| 22 | **Histogram metrics: do NOT use `ServiceName` in `groupBy`** — use `Attributes['key']` instead (e.g., `Attributes['rpc.service']`) *(discovered, not in API docs)* | HyperDX histogram query builder doesn't propagate `ServiceName` to inner subqueries |

Rules marked *(discovered, not in API docs)* were learned empirically — the API accepts the payload but the tile fails at render time. See `references/rules.md` > "Discovered Limitations" for full details, root cause analysis, and the template for documenting future findings.

## Lucene Where Syntax

Lucene `where` uses **ClickHouse column names directly** — `ServiceName:X`, `SeverityText:error`, `SpanName:X`, `Body:"text"`. HyperDX-mapped names like `service`, `level`, `span_name` do NOT work.

```
ServiceName:my-service                             # Exact match
SpanName:my-span                                   # Exact match
SeverityText:error                                 # Exact match (logs)
ServiceName:my-service SpanName:my-span            # AND (space-separated)
ServiceName:a OR ServiceName:b                     # OR (explicit keyword)
NOT SeverityText:error                             # Negation
-SeverityText:error                                # Negation (shorthand)
Body:"connection refused"                          # Exact phrase
Duration:>1000                                     # Comparison operators
ServiceName:frontend-*                             # Wildcard
LogAttributes.key:value                            # Map property (dot notation)
```

Precedence: `NOT` > `AND` (space) > `OR`. Use parentheses for clarity.

## Source Types & Column Names

### Traces (`sourceId: SRC["trace"]` → `otel_traces` table)

| Column | Type | Use in Lucene `where` |
|--------|------|----------------------|
| `Timestamp` | DateTime64(9) | — |
| `TraceId` | String | — |
| `SpanId` | String | — |
| `SpanName` | LowCardinality(String) | `SpanName:value` |
| `ServiceName` | LowCardinality(String) | `ServiceName:value` |
| `Duration` | UInt64 (nanoseconds) | `Duration:>1000000` |
| `StatusCode` | LowCardinality(String) | — |
| `SpanAttributes` | Map(LowCardinality(String), String) | `SpanAttributes.key:value` (dot notation) |
| `ResourceAttributes` | Map(LowCardinality(String), String) | — |

### Logs (`sourceId: SRC["log"]` → `otel_logs` table)

| Column | Type | Use in Lucene `where` |
|--------|------|----------------------|
| `Timestamp` | DateTime64(9) | — |
| `ServiceName` | LowCardinality(String) | `ServiceName:value` |
| `SeverityText` | LowCardinality(String) | `SeverityText:error` |
| `Body` | String | `Body:"search term"` |
| `LogAttributes` | Map(LowCardinality(String), String) | `LogAttributes.key:value` (dot notation) |
| `ResourceAttributes` | Map(LowCardinality(String), String) | — |

### Metrics (`sourceId: SRC["metric"]`)

Metrics are split across tables by type: `otel_metrics_gauge`, `otel_metrics_sum`, `otel_metrics_histogram`, `otel_metrics_summary`.

| Column | Type | Notes |
|--------|------|-------|
| `MetricName` | String | Metric name (e.g., `system.cpu.utilization`) |
| `Value` | Float64 | The metric value |
| `ServiceName` | LowCardinality(String) | Source service |
| `Attributes` | Map(LowCardinality(String), String) | Metric attributes |
| `TimeUnix` | DateTime64(9) | Timestamp |

For metrics series, add: `"metricName": "metric.name"`, `"metricDataType": "gauge"` (lowercase: `gauge`, `sum`, `histogram`, `summary`, `exponential histogram`).

## Deploy Pattern (Python)

```python
import requests

API = 'http://localhost:8000'
TOKEN = 'clickstack-local-v2-api-key'
HEADERS = {'Authorization': f'Bearer {TOKEN}'}

# Step 1: Resolve source IDs (mandatory — use internal API, no auth)
sources = requests.get(f'{API}/sources').json()
SRC = {s['kind']: s['id'] for s in sources}

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

# Step 2: Deploy via v2 API
resp = requests.post(f'{API}/api/v2/dashboards', json=dashboard, headers=HEADERS)
data = resp.json()['data']
print(f"URL: http://localhost:8080/dashboards/{data['id']}")
```

### Deploy Error Handling

| Status | Cause | Fix |
|--------|-------|-----|
| `400` / validation error | Malformed JSON (missing fields, invalid types, missing sources) | Re-validate against checklist in `references/rules.md` |
| `401` | Missing or invalid Bearer token | Use `clickstack-local-v2-api-key` or check `setup.sh` ran |
| `500` | Internal container error | Check container logs: `docker logs clickstack-local --tail 50` |
| Connection refused | Container not running | Start it: `docker compose up -d` |

## Common Tile Patterns

**4 KPIs across:** `w:6, h:3` at `x: 0, 6, 12, 18` on `y:0`

**Half-width charts:** `w:12, h:6` at `x: 0, 12`

**Full-width chart:** `w:24, h:6`

**Full-width table:** `w:24, h:5`

**Typical layout:**
```
y:0   h:3  — KPI row (4× w:6, type: "number")
y:3   h:6  — Chart row (2× w:12, type: "time")
y:9   h:6  — Chart row (2× w:12)
y:15  h:5  — Table row (1× w:24, type: "table")
```

## References

For detailed documentation, see:
- [Chart format reference](references/chart-format.md) — Full field reference and schema
- [Schema discovery](references/schema-discovery.md) — OTel-native schema and discovery queries
- [Rules & validation checklist](references/rules.md) — All rules with post-generation checklist
- [Working examples](references/examples.md) — Verified tile patterns and full dashboard examples
