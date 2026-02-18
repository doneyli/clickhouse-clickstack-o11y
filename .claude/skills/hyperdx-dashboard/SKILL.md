---
name: hyperdx-dashboard
description: Generates, validates, and deploys ClickStack dashboard definitions via the internal REST API. Covers tile layout, aggregation, Lucene filters, and OTel-native schema discovery. Use when creating, modifying, or fixing dashboards.
---

# ClickStack Dashboard Builder

## Workflow

1. **Discover data** — Query ClickHouse to see available tables, services, and attributes:
   ```bash
   # List tables
   curl -s "http://localhost:8123/?user=api&password=api" --data "SHOW TABLES FROM default"

   # Discover traces schema and services
   curl -s "http://localhost:8123/?user=api&password=api" --data "SELECT ServiceName, count() AS cnt FROM otel_traces GROUP BY ServiceName ORDER BY cnt DESC"

   # Discover trace attributes
   curl -s "http://localhost:8123/?user=api&password=api" --data "SELECT DISTINCT arrayJoin(SpanAttributes.keys) AS attr FROM otel_traces ORDER BY attr LIMIT 100"

   # Discover log attributes
   curl -s "http://localhost:8123/?user=api&password=api" --data "SELECT DISTINCT arrayJoin(LogAttributes.keys) AS attr FROM otel_logs ORDER BY attr LIMIT 100"

   # Discover metrics
   curl -s "http://localhost:8123/?user=api&password=api" --data "SELECT DISTINCT MetricName FROM otel_metrics_gauge UNION ALL SELECT DISTINCT MetricName FROM otel_metrics_sum ORDER BY MetricName"

   # Discover data sources
   curl -s http://localhost:8000/sources | python3 -m json.tool
   ```
2. **Generate JSON** — Build the dashboard definition following the Tile Format below.
3. **Validate** — For every tile, print the Post-Generation Validation Checklist from `references/rules.md` with `[ok]` or `[FAIL]` for each item. Fix all `[FAIL]` items before proceeding. Do NOT skip this step.
4. **Deploy** — Use Python `requests` to POST to the ClickStack internal API (`/dashboards`) on port 8000. No auth required for local mode.
5. **Verify** — Open ClickStack UI at `http://localhost:8080/dashboards` and confirm tiles render.

## CRITICAL: Always Use the API

**NEVER insert dashboards directly into the database.** Always use the ClickStack REST API.

```
# Internal API (no auth required for local mode)
POST   http://localhost:8000/dashboards          # Create dashboard
GET    http://localhost:8000/dashboards          # List all dashboards
DELETE http://localhost:8000/dashboards/{id}     # Delete dashboard
```

**No auth needed** — ClickStack local mode handles team/user automatically.

## Tile Format

```json
{
  "name": "Dashboard Name",
  "tags": ["tag1", "tag2"],
  "tiles": [
    {
      "id": "unique-kebab-id",
      "x": 0, "y": 0, "w": 12, "h": 3,
      "config": {
        "name": "Chart Title",
        "source": "traces",
        "select": [{
          "aggFn": "avg",
          "valueExpression": "Duration",
          "aggCondition": ""
        }],
        "where": "service:my-service",
        "whereLanguage": "lucene",
        "groupBy": [],
        "displayType": "line"
      }
    }
  ]
}
```

Key points:
- **`tiles`** array (NOT `charts`) with **`config`** containing **`select`** (NOT `series`)
- **`source`**: `"traces"`, `"logs"`, or `"metrics"` — determines which ClickHouse table to query
- **`select`** items: `aggFn` + `valueExpression` (ClickHouse column expression) + `aggCondition`
- **`where`** uses Lucene syntax with `whereLanguage: "lucene"` required
- **`groupBy`** is an array of objects: `[{"valueExpression": "ServiceName"}]`
- **`displayType`**: `"line"`, `"stacked_bar"`, `"number"`, `"table"`, `"markdown"`
- **Grid is 24 columns wide** — `x + w <= 24`

## Critical Rules

| # | Rule | What breaks |
|---|------|-------------|
| 1 | `where` uses **Lucene syntax** with `whereLanguage: "lucene"` | SQL syntax silently fails |
| 2 | `valueExpression` uses ClickHouse column names (e.g., `Duration`, `ServiceName`) | HyperDX abstracted names (e.g., `duration`, `service`) don't work in valueExpression |
| 3 | Top-level array is `tiles`, not `charts` | API validation error |
| 4 | `displayType` must be valid | `"line"`, `"stacked_bar"`, `"number"`, `"table"`, `"markdown"` |
| 5 | `aggFn` must be valid | **Standard:** `count`, `sum`, `avg`, `min`, `max`, `count_distinct`, `last_value`. **Quantile:** `quantile` with `level` field (0-1). Invalid values fail. |
| 6 | `valueExpression: ""` for `count` aggFn | Including a column with count may error |
| 7 | `numberFormat` on `displayType: "number"` tiles | KPI tiles display raw without formatting |
| 8 | Grid is 24 columns wide; `x + w <= 24` | Tiles overlap or overflow |
| 9 | `groupBy` is array of objects `[{"valueExpression": "Col"}]` or empty `[]` | Strings fail validation |
| 10 | Deploy via API only — `POST http://localhost:8000/dashboards` | Direct DB inserts may cause issues |
| 11 | `Duration` in `otel_traces` is **nanoseconds** (UInt64) | Not milliseconds — HyperDX UI handles display formatting |
| 12 | `tags: []` required at dashboard level | API validation error |
| 13 | All select items in a tile share the same `where`, `groupBy`, `displayType` | Per-item filtering uses `aggCondition` |
| 14 | `whereLanguage: "lucene"` required on every tile config | Omitting may default to wrong language |
| 15 | `h: 2` for KPI (`displayType: "number"`), `h: 3` for all others | Inconsistent heights break row alignment |
| 16 | Tile `id`: descriptive kebab-case, max 36 chars | Omitting generates UUIDs — unreadable |
| 17 | Metrics tiles need `metricName` and `metricDataType` in config | Missing fields → no data or API error |
| 18 | **NEVER use `type:span` or `type:log`** in `where` clauses | Internal field — not searchable via Lucene |

## Lucene Where Syntax

```
service:my-service                                 # Exact match
span_name:my-span                                  # Exact match
level:error                                        # Exact match
service:my-service span_name:my-span               # AND (space-separated)
service:a OR service:b                             # OR (explicit keyword)
NOT level:error                                    # Negation
-level:error                                       # Negation (shorthand)
body:"connection refused"                          # Exact phrase
duration:>1000                                     # Comparison operators
service:frontend-*                                 # Wildcard
```

Precedence: `NOT` > `AND` (space) > `OR`. Use parentheses for clarity.

## Source Types & Column Names

### Traces (`source: "traces"` → `otel_traces` table)

| Column | Type | Use in Lucene `where` |
|--------|------|----------------------|
| `Timestamp` | DateTime64(9) | — |
| `TraceId` | String | — |
| `SpanId` | String | — |
| `SpanName` | LowCardinality(String) | `span_name:value` |
| `ServiceName` | LowCardinality(String) | `service:value` |
| `Duration` | UInt64 (nanoseconds) | `duration:>1000000` |
| `StatusCode` | LowCardinality(String) | — |
| `SpanAttributes` | Map(LowCardinality(String), String) | attribute name directly |
| `ResourceAttributes` | Map(LowCardinality(String), String) | — |

### Logs (`source: "logs"` → `otel_logs` table)

| Column | Type | Use in Lucene `where` |
|--------|------|----------------------|
| `Timestamp` | DateTime64(9) | — |
| `ServiceName` | LowCardinality(String) | `service:value` |
| `SeverityText` | LowCardinality(String) | `level:error` |
| `Body` | String | `body:"search term"` |
| `LogAttributes` | Map(LowCardinality(String), String) | attribute name directly |
| `ResourceAttributes` | Map(LowCardinality(String), String) | — |

### Metrics (`source: "metrics"`)

Metrics are split across tables by type: `otel_metrics_gauge`, `otel_metrics_sum`, `otel_metrics_histogram`, `otel_metrics_summary`.

| Column | Type | Notes |
|--------|------|-------|
| `MetricName` | String | Metric name (e.g., `system.cpu.utilization`) |
| `Value` | Float64 | The metric value |
| `ServiceName` | LowCardinality(String) | Source service |
| `Attributes` | Map(LowCardinality(String), String) | Metric attributes |
| `TimeUnix` | DateTime64(9) | Timestamp |

For metrics tiles, add to config: `"metricName": "metric.name"`, `"metricDataType": "Gauge"` (or `"Sum"`, `"Histogram"`, `"Summary"`).

## Select Item Types

### Standard aggregation
```json
{"aggFn": "avg", "valueExpression": "Duration", "aggCondition": ""}
```

### Count (no column)
```json
{"aggFn": "count", "valueExpression": "", "aggCondition": ""}
```

### Quantile (replaces p50/p90/p95/p99)
```json
{"aggFn": "quantile", "level": 0.95, "valueExpression": "Duration", "aggCondition": ""}
```

### Per-item filter (aggCondition)
```json
{"aggFn": "avg", "valueExpression": "Duration", "aggCondition": "ServiceName = 'checkout'"}
```

## Display Types

| displayType | Use | Extra config fields |
|-------------|-----|-------------------|
| `line` | Line charts over time | `groupBy` array |
| `stacked_bar` | Stacked bar charts | `groupBy` array |
| `number` | KPI number tiles | `numberFormat` object |
| `table` | Table display | `groupBy` array |
| `markdown` | Markdown text | `content` string in select |

## Deploy Pattern (Python)

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

### Deploy Error Handling

| Status | Cause | Fix |
|--------|-------|-----|
| `400` / validation error | Malformed JSON (missing required fields, invalid types) | Re-validate against the checklist in `references/rules.md` |
| `500` | Internal container error | Check container logs: `docker logs clickstack-local --tail 50` |
| Connection refused | Container not running | Start it: `docker compose up -d` |

## Common Tile Patterns

**4 KPIs across:** `w:6, h:2` at `x: 0, 6, 12, 18` on `y:0`

**Half-width charts:** `w:12, h:3` at `x: 0, 12`

**Full-width chart:** `w:24, h:3`

## References

For detailed documentation, see:
- [Chart format reference](references/chart-format.md) — Full field reference and schema
- [Schema discovery](references/schema-discovery.md) — OTel-native schema and discovery queries
- [Rules & validation checklist](references/rules.md) — All rules with post-generation checklist
- [Working examples](references/examples.md) — Verified tile patterns and full dashboard examples
