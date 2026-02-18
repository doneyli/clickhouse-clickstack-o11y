# Tile Format — Complete Reference

## API Endpoint

```
POST http://localhost:8000/dashboards
Content-Type: application/json
```

No auth required for ClickStack local mode.

## Dashboard JSON Schema

```json
{
  "name": "Dashboard Name",
  "tags": ["tag1", "tag2"],
  "tiles": [ /* tile objects */ ]
}
```

Required fields: `name`, `tags` (array, can be empty), `tiles` (array).

## Tile JSON Schema

```json
{
  "id": "unique-kebab-case-id",
  "x": 0,
  "y": 0,
  "w": 12,
  "h": 3,
  "config": {
    "name": "Human Readable Name",
    "source": "traces",
    "select": [
      {
        "aggFn": "avg",
        "valueExpression": "Duration",
        "aggCondition": ""
      }
    ],
    "where": "service:my-service",
    "whereLanguage": "lucene",
    "groupBy": [],
    "displayType": "line"
  }
}
```

## Tile-Level Fields

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `id` | string | Yes | Unique kebab-case identifier, max 36 chars |
| `x` | number | Yes | Column position, 0–23 (24-col grid) |
| `y` | number | Yes | Row position (0-based) |
| `w` | number | Yes | Width in grid units, 1–24 |
| `h` | number | Yes | Height in grid units, typically 2 (KPI) or 3 (chart) |
| `config` | object | Yes | Tile configuration (see below) |

## Config Fields

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `name` | string | Yes | Displayed as tile title |
| `source` | string | Yes | `"traces"`, `"logs"`, or `"metrics"` |
| `select` | array | Yes | 1+ select item objects (see below) |
| `where` | string | Yes | Lucene query filter (empty string = match all) |
| `whereLanguage` | string | Yes | Always `"lucene"` |
| `groupBy` | array | Yes | Array of `{"valueExpression": "Col"}` objects, or `[]` |
| `displayType` | string | Yes | `"line"`, `"stacked_bar"`, `"number"`, `"table"`, `"markdown"` |
| `numberFormat` | object | No | Required for `displayType: "number"` |
| `metricName` | string | No | Required for metrics tiles — the metric name |
| `metricDataType` | string | No | Required for metrics tiles — `"Gauge"`, `"Sum"`, `"Histogram"`, `"Summary"` |

## Select Item Fields

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `aggFn` | string | Yes | Aggregation function (see below) |
| `valueExpression` | string | Yes | ClickHouse column expression to aggregate. Empty `""` for count. |
| `aggCondition` | string | Yes | Per-item SQL filter condition. Empty `""` for no per-item filter. |
| `level` | number | For quantile | 0–1 quantile level (e.g., 0.95 for P95). Required when `aggFn: "quantile"`. |

## Valid `aggFn` Values

**Standard:** `count`, `sum`, `avg`, `min`, `max`, `count_distinct`, `last_value`

**Quantile:** `quantile` (requires `level` field, e.g., 0.5, 0.9, 0.95, 0.99)

**Merge variants:** `quantileMerge`, `histogram`, `histogramMerge`

## Mandatory Config by displayType

### `line` / `stacked_bar` (time series)
```json
{
  "name": "Chart Title",
  "source": "traces",
  "select": [{"aggFn": "avg", "valueExpression": "Duration", "aggCondition": ""}],
  "where": "service:my-service",
  "whereLanguage": "lucene",
  "groupBy": [],
  "displayType": "line"
}
```
**Required:** `name`, `source`, `select`, `where`, `whereLanguage`, `groupBy`, `displayType`.

### `number` (KPI)
```json
{
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
```
**Required:** All standard fields plus `numberFormat`.

### `table`
```json
{
  "name": "Top Operations",
  "source": "traces",
  "select": [{"aggFn": "count", "valueExpression": "", "aggCondition": ""}],
  "where": "service:my-service",
  "whereLanguage": "lucene",
  "groupBy": [{"valueExpression": "SpanName"}],
  "displayType": "table"
}
```
**Required:** All standard fields. `groupBy` typically non-empty for useful tables.

### Metrics time series
```json
{
  "name": "CPU Utilization",
  "source": "metrics",
  "select": [{"aggFn": "avg", "valueExpression": "Value", "aggCondition": ""}],
  "where": "",
  "whereLanguage": "lucene",
  "groupBy": [],
  "displayType": "line",
  "metricName": "system.cpu.utilization",
  "metricDataType": "Gauge"
}
```
**Required:** All standard fields plus `metricName` and `metricDataType`.

## numberFormat Object

Required for `displayType: "number"` KPI tiles.

| Field | Type | Notes |
|-------|------|-------|
| `output` | string | `"number"`, `"percent"`, `"byte"`, `"time"`, `"currency"` |
| `mantissa` | number | Decimal places: `0` (integers), `1` (percent), `2` (latency) |
| `thousandSeparated` | boolean | `true` for readability |
| `factor` | number | Multiplier, usually `1` |
| `average` | boolean | Usually `false` |
| `decimalBytes` | boolean | Usually `false` |

## numberFormat Templates

### Integer Count
```json
"numberFormat": {"output": "number", "mantissa": 0, "factor": 1, "thousandSeparated": true, "average": false, "decimalBytes": false}
```

### Latency
```json
"numberFormat": {"output": "number", "mantissa": 2, "factor": 1, "thousandSeparated": true, "average": false, "decimalBytes": false}
```

### Percentage
```json
"numberFormat": {"output": "percent", "mantissa": 1, "factor": 1, "thousandSeparated": true, "average": false, "decimalBytes": false}
```

### Bytes
```json
"numberFormat": {"output": "byte", "mantissa": 0, "factor": 1, "thousandSeparated": true, "average": false, "decimalBytes": true}
```

## Lucene Where Syntax

```
service:my-service                                 # Exact match
span_name:my-operation                             # Exact match
level:error                                        # Exact match
service:my-service span_name:my-op                 # AND (space-separated)
service:a OR service:b                             # OR (explicit keyword)
NOT level:error                                    # Negation
-level:error                                       # Negation (shorthand)
body:"connection refused"                          # Exact phrase
duration:>1000000                                  # Greater than (nanoseconds for traces)
service:frontend-*                                 # Wildcard
```

**Precedence:** `NOT` > `AND` (space) > `OR`. Use parentheses for clarity.

## Lucene Field Names (for `where`)

Lucene field names are mapped by HyperDX from the source expression definitions:

| Lucene field | Traces column | Logs column |
|-------------|---------------|-------------|
| `service` | `ServiceName` | `ServiceName` |
| `span_name` | `SpanName` | — |
| `level` | — | `SeverityText` |
| `body` | `SpanName` | `Body` |
| `duration` | `Duration` | — |
| Custom attributes | `SpanAttributes['key']` | `LogAttributes['key']` |

## Column Names (for `valueExpression` and `groupBy`)

Use actual ClickHouse column names in `valueExpression` and `groupBy`:

| valueExpression | Source | Column Type |
|----------------|--------|-------------|
| `Duration` | traces | UInt64 (nanoseconds) |
| `ServiceName` | traces/logs | LowCardinality(String) |
| `SpanName` | traces | LowCardinality(String) |
| `StatusCode` | traces | LowCardinality(String) |
| `SeverityText` | logs | LowCardinality(String) |
| `Body` | logs | String |
| `SpanAttributes['key']` | traces | String (from Map) |
| `LogAttributes['key']` | logs | String (from Map) |
| `Value` | metrics | Float64 |

## Multi-Select Tiles

Multiple items in `select` create multi-series charts:

```json
"select": [
  {"aggFn": "quantile", "level": 0.5, "valueExpression": "Duration", "aggCondition": ""},
  {"aggFn": "quantile", "level": 0.95, "valueExpression": "Duration", "aggCondition": ""},
  {"aggFn": "quantile", "level": 0.99, "valueExpression": "Duration", "aggCondition": ""}
]
```

All select items share the same `where`, `groupBy`, and `displayType`.

For per-item filtering, use `aggCondition`:
```json
"select": [
  {"aggFn": "avg", "valueExpression": "Duration", "aggCondition": "ServiceName = 'payment'"},
  {"aggFn": "avg", "valueExpression": "Duration", "aggCondition": "ServiceName = 'cart'"}
]
```

## Grid Layout Patterns

Grid is **24 columns wide**.

**4 KPIs across:** `w:6, h:2` at `x: 0, 6, 12, 18`

**Half-width charts:** `w:12, h:3` at `x: 0, 12`

**Full-width chart:** `w:24, h:3`

**Typical dashboard:**
```
y:0  h:2  — KPI row (4x w:6)
y:2  h:3  — Chart row (2x w:12)
y:5  h:3  — Chart row (2x w:12)
y:8  h:3  — Chart row (2x w:12)
```
