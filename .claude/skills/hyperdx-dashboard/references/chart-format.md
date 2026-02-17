# Chart Format — Complete Reference

## API Endpoint

Use the **public** endpoint (matches official docs, accepts `table` for convenience):

```
POST http://localhost:8000/api/v1/dashboards
Authorization: Bearer {ACCESS_KEY}
Content-Type: application/json
```

## Dashboard JSON Schema

```json
{
  "name": "Dashboard Name",
  "query": "",
  "tags": ["tag1", "tag2"],
  "charts": [ /* chart objects */ ]
}
```

## Chart JSON Schema

```json
{
  "id": "unique-kebab-case-id",
  "name": "Human Readable Name",
  "x": 0,
  "y": 0,
  "w": 6,
  "h": 3,
  "series": [
    {
      "type": "time",
      "table": "logs",
      "aggFn": "avg",
      "field": "system.cpu.percent",
      "where": "span_name:cpu-load-sample service:macos-system-monitor",
      "groupBy": [],
      "numberFormat": {}
    }
  ],
  "asRatio": false
}
```

## Chart-Level Fields

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `id` | string | Yes | Unique kebab-case identifier, max 36 chars |
| `name` | string | Yes | Displayed as chart title |
| `x` | number | Yes | Column position, 0–11 |
| `y` | number | Yes | Row position (0-based) |
| `w` | number | Yes | Width in grid units, 1–12 |
| `h` | number | Yes | Height in grid units, typically 2 (KPI) or 3 (chart) |
| `series` | array | Yes | 1+ series objects (see below) |
| `asRatio` | boolean | Yes | Always `false`. Required by this skill for determinism. |

## Series Fields

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `type` | string | Yes | `time`, `number`, `table`, `histogram`, `search`, `markdown` |
| `table` | string | Yes* | `"logs"` for traces/spans/logs, `"metrics"` for metrics. Not needed for markdown. When using `"metrics"`, `metricDataType` is also required and `field` must use `"name - DataType"` format. |
| `aggFn` | string | Yes* | Aggregation function (see below). Not needed for search/markdown. |
| `field` | string | No | HyperDX field name to aggregate. Omit for `count`. |
| `where` | string | No | Lucene query filter (default: empty = match all) |
| `groupBy` | array | No | Array of field names to group by (time charts only) |
| `numberFormat` | object | No | Required for `type: "number"` KPI tiles |
| `sortOrder` | string | No | `"desc"` or `"asc"` (table type only) |
| `fields` | array | No | Column list (search type only) |
| `content` | string | No | Markdown text (markdown type only) |
| `metricDataType` | string | No* | Required for metrics series (`table: "metrics"`). Valid values: `"Gauge"`, `"Sum"`, `"Histogram"`, `"Summary"`. |

## Mandatory Fields by Series Type

For each series type, emit **exactly** these fields — no more, no less (except `field` which is omitted for `count` aggFn).

### `time` series
```json
{
  "type": "time",
  "table": "logs",
  "aggFn": "avg",
  "field": "duration",
  "where": "span_name:my-span",
  "groupBy": []
}
```
**Required:** `type`, `table`, `aggFn`, `where`, `groupBy`. Also `field` unless aggFn is `count`.

### `number` series (KPI)
```json
{
  "type": "number",
  "table": "logs",
  "aggFn": "avg",
  "field": "duration",
  "where": "span_name:my-span",
  "numberFormat": {
    "output": "number",
    "mantissa": 2,
    "factor": 1,
    "thousandSeparated": true,
    "average": false,
    "decimalBytes": false
  }
}
```
**Required:** `type`, `table`, `aggFn`, `where`, `numberFormat`. Also `field` unless aggFn is `count`. No `groupBy`.

### `table` series
```json
{
  "type": "table",
  "table": "logs",
  "aggFn": "count",
  "where": "service:my-service",
  "groupBy": ["span_name"],
  "sortOrder": "desc"
}
```
**Required:** `type`, `table`, `aggFn`, `where`, `groupBy`, `sortOrder`. Also `field` unless aggFn is `count`.

### `histogram` series
```json
{
  "type": "histogram",
  "table": "logs",
  "field": "duration",
  "where": "service:my-service"
}
```
**Required:** `type`, `table`, `field`, `where`. No `aggFn`, no `groupBy`.

### `search` series
```json
{
  "type": "search",
  "table": "logs",
  "where": "level:error",
  "fields": ["service", "span_name", "body", "duration"]
}
```
**Required:** `type`, `table`, `where`, `fields`. No `aggFn`, no `groupBy`.

### `markdown` series
```json
{
  "type": "markdown",
  "content": "## Section Title\nDescription text here."
}
```
**Required:** `type`, `content` only. No `table`, `aggFn`, `field`, `where`, or `groupBy`.

### Metrics `time` series
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
**Required:** `type`, `table` (`"metrics"`), `aggFn`, `field` (in `"name - DataType"` format), `metricDataType`, `where`, `groupBy`. Also `field` is always required for metrics (no bare `count`).

### Metrics `number` series (KPI)
```json
{
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
    "thousandSeparated": true,
    "average": false,
    "decimalBytes": false
  }
}
```
**Required:** `type`, `table` (`"metrics"`), `aggFn`, `field` (in `"name - DataType"` format), `metricDataType`, `where`, `numberFormat`. No `groupBy`.

## Valid `aggFn` Values

**Valid values:** `count`, `count_rate`, `sum`, `avg`, `min`, `max`, `p50`, `p90`, `p95`, `p99`, `count_distinct`, `avg_rate`, `sum_rate`, `min_rate`, `max_rate`, `p50_rate`, `p90_rate`, `p95_rate`, `p99_rate`

## numberFormat Object

Required for `type: "number"` (KPI tiles).

| Field | Type | Notes |
|-------|------|-------|
| `output` | string | `"number"`, `"percent"`, `"byte"`, `"time"`, `"currency"` |
| `mantissa` | number | Decimal places: `0` (integers), `1` (percent), `2` (latency) |
| `thousandSeparated` | boolean | `true` for readability |
| `factor` | number | Multiplier, usually `1` |
| `average` | boolean | Usually `false` |
| `decimalBytes` | boolean | Usually `false` |

## numberFormat Templates

Use these canonical templates verbatim for KPI (`type: "number"`) charts. Always include all 6 fields.

### Integer Count
```json
"numberFormat": {"output": "number", "mantissa": 0, "factor": 1, "thousandSeparated": true, "average": false, "decimalBytes": false}
```
Use for: request counts, token totals, event counts.

### Latency ms
```json
"numberFormat": {"output": "number", "mantissa": 2, "factor": 1, "thousandSeparated": true, "average": false, "decimalBytes": false}
```
Use for: avg/p50/p90/p95/p99 latency, duration metrics.

### Percentage
```json
"numberFormat": {"output": "percent", "mantissa": 1, "factor": 1, "thousandSeparated": true, "average": false, "decimalBytes": false}
```
Use for: CPU %, memory %, error rates (when pre-computed as 0–1 ratio).

### Bytes
```json
"numberFormat": {"output": "byte", "mantissa": 0, "factor": 1, "thousandSeparated": true, "average": false, "decimalBytes": true}
```
Use for: memory usage, disk I/O, network bytes.

### Decimal
```json
"numberFormat": {"output": "number", "mantissa": 2, "factor": 1, "thousandSeparated": true, "average": false, "decimalBytes": false}
```
Use for: load averages, scores, ratios, any decimal metric.

## Lucene Where Syntax

```
service:macos-system-monitor                    # Exact match
span_name:cpu-load-sample                       # Exact match
gen_ai.request.model:*                          # Field exists (any value)
level:error                                     # Exact match
span_name:cpu-load-sample service:my-service    # AND (space-separated)
span_name:cpu-load-sample OR span_name:memory   # OR (explicit keyword)
NOT level:error                                 # NOT (negation prefix)
-level:error                                    # Negation (shorthand for NOT)
body:"connection refused"                       # Quoted string (exact phrase)
duration:>1000                                  # Greater than
duration:>=500                                  # Greater than or equal
duration:<100                                   # Less than
service:macos-*                                 # Wildcard (partial match)
```

**Precedence:** `NOT` binds tightest, then `AND` (space), then `OR`. Use parentheses for clarity: `(service:a OR service:b) NOT level:error`.

## HyperDX Field Names

Use these names in `field` and `where`, NOT ClickHouse column expressions:

| HyperDX Name | Maps To | Type |
|--------------|---------|------|
| `duration` | `_duration` | number |
| `service` | `_service` | string |
| `span_name` | `span_name` | string |
| `level` | `severity_text` | string |
| `body` | `_hdx_body` | string |
| `host` | `_host` | string |
| `hyperdx_event_type` | `type` | string |
| Custom (e.g., `system.cpu.percent`) | `_number_attributes['system.cpu.percent']` | auto |
| Custom (e.g., `health.status`) | `_string_attributes['health.status']` | auto |

## Multi-Series Charts

Multiple items in the `series` array create multi-series charts (e.g., two lines on one chart):

```json
"series": [
  {"type": "time", "table": "logs", "aggFn": "avg", "field": "system.load.1m", "where": "...", "groupBy": []},
  {"type": "time", "table": "logs", "aggFn": "avg", "field": "system.load.5m", "where": "...", "groupBy": []},
  {"type": "time", "table": "logs", "aggFn": "avg", "field": "system.load.15m", "where": "...", "groupBy": []}
]
```

> **Constraint:** All series within a single chart MUST share identical `type` and identical `groupBy` arrays. Mixed types or mismatched `groupBy` silently drops data.

## Grid Layout Patterns

Grid is 12 columns wide.

**4 KPIs across:** `w:3, h:2` at `x: 0, 3, 6, 9`

**Half-width charts:** `w:6, h:3` at `x: 0, 6`

**Full-width chart:** `w:12, h:3`

**Typical dashboard:**
```
y:0  h:2  — KPI row (4x w:3)
y:2  h:3  — Chart row (2x w:6)
y:5  h:3  — Chart row (2x w:6)
y:8  h:3  — Chart row (2x w:6)
```
