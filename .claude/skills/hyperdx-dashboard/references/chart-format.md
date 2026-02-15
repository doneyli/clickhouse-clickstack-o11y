# Chart Format — Complete Reference

## API Endpoint

Use the **internal** endpoint (NOT `/api/v1/dashboards` — see SKILL.md for why):

```
POST http://localhost:8000/dashboards
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
  "seriesReturnType": "column"
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
| `seriesReturnType` | string | No | `"column"` (default) or `"ratio"` |

## Series Fields

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `type` | string | Yes | `time`, `number`, `table`, `histogram`, `search`, `markdown` |
| `table` | string | Yes* | `"logs"` for traces/spans/logs, `"metrics"` for metrics. Not needed for markdown. |
| `aggFn` | string | Yes* | Aggregation function (see below). Not needed for search/markdown. |
| `field` | string | No | HyperDX field name to aggregate. Omit for `count`. |
| `where` | string | No | Lucene query filter (default: empty = match all) |
| `groupBy` | array | No | Array of field names to group by (time charts only) |
| `numberFormat` | object | No | Required for `type: "number"` KPI tiles |
| `sortOrder` | string | No | `"desc"` or `"asc"` (table type only) |
| `fields` | array | No | Column list (search type only) |
| `content` | string | No | Markdown text (markdown type only) |

## Valid `aggFn` Values

`count`, `sum`, `avg`, `min`, `max`, `p50`, `p90`, `p95`, `p99`, `count_distinct`, `last_value`, `count_per_sec`, `count_per_min`, `count_per_hour`, `avg_rate`, `min_rate`, `max_rate`, `p50_rate`, `p90_rate`, `p95_rate`, `p99_rate`

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

## Lucene Where Syntax

```
service:macos-system-monitor                    # Exact match
span_name:cpu-load-sample                       # Exact match
gen_ai.request.model:*                          # Field exists
level:error                                     # Exact match
span_name:cpu-load-sample service:my-service    # AND (space-separated)
```

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
