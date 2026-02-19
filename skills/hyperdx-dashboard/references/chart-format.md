# Tile Format — Complete Reference (v2 API)

## API Endpoint

```
POST http://localhost:8000/api/v2/dashboards
Authorization: Bearer clickstack-local-v2-api-key
Content-Type: application/json
```

Bearer auth required. In local mode, `setup.sh` creates a user with access key `clickstack-local-v2-api-key`.

## Dashboard JSON Schema

```json
{
  "name": "Dashboard Name",
  "tags": ["tag1", "tag2"],
  "tiles": [ /* tile objects */ ]
}
```

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| `name` | string | Yes | Max 1024 chars |
| `tags` | string[] | No | Max 50 tags, max 32 chars each |
| `tiles` | Tile[] | Yes | Array of tile objects |

## Tile JSON Schema

```json
{
  "name": "Chart Title",
  "x": 0,
  "y": 0,
  "w": 12,
  "h": 6,
  "series": [
    {
      "type": "time",
      "sourceId": "<source-id-from-GET-/sources>",
      "aggFn": "avg",
      "field": "Duration",
      "where": "ServiceName:my-service",
      "whereLanguage": "lucene",
      "groupBy": ["SpanName"],
      "displayType": "line"
    }
  ]
}
```

## Tile-Level Fields

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `name` | string | Yes | Displayed as tile title |
| `x` | number | Yes | Column position, 0–23 (24-col grid) |
| `y` | number | Yes | Row position (0-based) |
| `w` | number | Yes | Width in grid units, 1–24 |
| `h` | number | Yes | Height: 3 (number/KPI), 6 (time), 5 (table) |
| `series` | Series[] | Yes | 1–5 series objects. All must have the same `type`. |
| `asRatio` | boolean | No | Show as ratio (optional) |

No `id` field on create — the API generates one. On GET, tiles include an `id`.

## Series Types

Series are discriminated by the `type` field. All series in a tile must have the same `type`.

### TimeChartSeries (`type: "time"`)

Line charts and stacked bar charts over time.

```json
{
  "type": "time",
  "sourceId": "<trace-source-id>",
  "aggFn": "avg",
  "field": "Duration",
  "where": "ServiceName:my-service",
  "whereLanguage": "lucene",
  "groupBy": ["SpanName"],
  "displayType": "line"
}
```

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `type` | `"time"` | Yes | Discriminator |
| `sourceId` | string | Yes | Source ID from `GET /sources` (ObjectId format) |
| `aggFn` | string | Yes | Aggregation function (see below) |
| `field` | string | No | ClickHouse column to aggregate. Omit or `""` for count. |
| `where` | string | Yes | Lucene filter (empty string = match all) |
| `whereLanguage` | string | No | `"lucene"` or `"sql"`. Always use `"lucene"`. |
| `groupBy` | string[] | Yes | Column names to group by. Max 10. `[]` for no grouping. |
| `displayType` | string | No | `"line"` (default) or `"stacked_bar"` |
| `level` | number | No | 0–1 quantile level. Required when `aggFn: "quantile"`. |
| `numberFormat` | object | No | Number formatting (see below) |
| `metricDataType` | string | No | Required for metrics: `"gauge"`, `"sum"`, `"histogram"`, `"summary"` |
| `metricName` | string | No | Required for metrics: e.g., `"system.cpu.utilization"` |
| `alias` | string | No | Display alias for the series |

### NumberChartSeries (`type: "number"`)

KPI number tiles showing a single aggregated value.

```json
{
  "type": "number",
  "sourceId": "<trace-source-id>",
  "aggFn": "count",
  "field": "",
  "where": "",
  "whereLanguage": "lucene",
  "numberFormat": {
    "output": "number", "mantissa": 0, "thousandSeparated": true
  }
}
```

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `type` | `"number"` | Yes | Discriminator |
| `sourceId` | string | Yes | Source ID from `GET /sources` |
| `aggFn` | string | Yes | Aggregation function |
| `field` | string | No | ClickHouse column. Omit or `""` for count. |
| `where` | string | Yes | Lucene filter |
| `whereLanguage` | string | No | Always `"lucene"` |
| `numberFormat` | object | No | Recommended for readable display |
| `level` | number | No | For quantile aggFn |
| `metricDataType` | string | No | For metrics |
| `metricName` | string | No | For metrics |
| `alias` | string | No | Display alias |

No `groupBy`. No `displayType`.

### TableChartSeries (`type: "table"`)

Table display with aggregation and grouping.

```json
{
  "type": "table",
  "sourceId": "<trace-source-id>",
  "aggFn": "count",
  "field": "",
  "where": "ServiceName:checkout",
  "whereLanguage": "lucene",
  "groupBy": ["SpanName"],
  "sortOrder": "desc"
}
```

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `type` | `"table"` | Yes | Discriminator |
| `sourceId` | string | Yes | Source ID from `GET /sources` |
| `aggFn` | string | Yes | Aggregation function |
| `field` | string | No | ClickHouse column. Omit or `""` for count. |
| `where` | string | Yes | Lucene filter |
| `whereLanguage` | string | No | Always `"lucene"` |
| `groupBy` | string[] | Yes | Column names to group by. Max 10. |
| `sortOrder` | string | No | `"desc"` (default) or `"asc"` |
| `numberFormat` | object | No | Number formatting |
| `level` | number | No | For quantile aggFn |
| `metricDataType` | string | No | For metrics |
| `metricName` | string | No | For metrics |

No `displayType`.

### SearchChartSeries (`type: "search"`)

Raw event search / log viewer.

```json
{
  "type": "search",
  "sourceId": "<log-source-id>",
  "fields": ["Timestamp", "ServiceName", "SeverityText", "Body"],
  "where": "SeverityText:error",
  "whereLanguage": "lucene"
}
```

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `type` | `"search"` | Yes | Discriminator |
| `sourceId` | string | Yes | Source ID from `GET /sources` |
| `fields` | string[] | Yes | Column names to display |
| `where` | string | Yes | Lucene filter |
| `whereLanguage` | string | No | Always `"lucene"` |

### MarkdownChartSeries (`type: "markdown"`)

Static markdown text tile for documentation or headers.

```json
{
  "type": "markdown",
  "content": "## Service Health\nThis section shows key metrics."
}
```

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `type` | `"markdown"` | Yes | Discriminator |
| `content` | string | Yes | Markdown text, max 100k chars |

No `sourceId`, no `field`, no `where`.

## Valid `aggFn` Values

| aggFn | Description | Requires `field` | Requires `level` |
|-------|-------------|-------------------|-------------------|
| `count` | Count of events | No (use `""`) | No |
| `sum` | Sum of values | Yes | No |
| `avg` | Average of values | Yes | No |
| `min` | Minimum value | Yes | No |
| `max` | Maximum value | Yes | No |
| `count_distinct` | Count distinct values | Yes | No |
| `last_value` | Most recent value | Yes | No |
| `quantile` | Quantile (percentile) | Yes | Yes (0–1) |
| `any` | Any value | Yes | No |
| `none` | No aggregation | No | No |

**Quantile examples:** `level: 0.5` (P50), `level: 0.9` (P90), `level: 0.95` (P95), `level: 0.99` (P99).

## `metricDataType` Values (lowercase)

| Value | ClickHouse Table |
|-------|------------------|
| `"gauge"` | `otel_metrics_gauge` |
| `"sum"` | `otel_metrics_sum` |
| `"histogram"` | `otel_metrics_histogram` |
| `"summary"` | `otel_metrics_summary` |
| `"exponential histogram"` | `otel_metrics_exponential_histogram` |

**Histogram `groupBy` limitation (discovered, not in API docs):** HyperDX's histogram query builder does NOT propagate `ServiceName` into its inner subqueries. Using `groupBy: ["ServiceName"]` on histogram metrics causes `Unknown expression identifier 'ServiceName'` at render time (the API accepts the payload fine). Instead, use `Attributes['key']` for groupBy on histograms (e.g., `Attributes['rpc.service']`, `Attributes['http.method']`), since `Attributes` IS included in the inner query. Alternatively, remove `groupBy` entirely. Gauge and sum metrics work fine with `ServiceName` in `groupBy`. See `references/rules.md` Rule 24 for full details.

## numberFormat Object

Recommended for `type: "number"` KPI tiles. Optional on other series types.

| Field | Type | Notes |
|-------|------|-------|
| `output` | string | `"number"`, `"percent"`, `"byte"`, `"time"`, `"currency"` |
| `mantissa` | number | Decimal places: `0` (integers), `1` (percent), `2` (latency) |
| `thousandSeparated` | boolean | `true` for readability |
| `factor` | number | Multiplier, usually `1` |
| `average` | boolean | Usually `false` |
| `decimalBytes` | boolean | Usually `false` |
| `currencySymbol` | string | For `output: "currency"` |
| `unit` | string | Custom unit label (e.g., `"ms"`) |

## numberFormat Templates

### Integer Count
```json
"numberFormat": {"output": "number", "mantissa": 0, "thousandSeparated": true}
```

### Latency
```json
"numberFormat": {"output": "number", "mantissa": 2, "thousandSeparated": true}
```

### Percentage
```json
"numberFormat": {"output": "percent", "mantissa": 1, "thousandSeparated": true}
```

### Bytes
```json
"numberFormat": {"output": "byte", "mantissa": 0, "thousandSeparated": true, "decimalBytes": true}
```

## Lucene Where Syntax

Lucene `where` uses **ClickHouse column names directly**. HyperDX-mapped names like `service`, `level`, `span_name` do NOT work.

```
ServiceName:my-service                             # Exact match
SpanName:my-operation                              # Exact match
SeverityText:error                                 # Exact match (logs)
ServiceName:my-service SpanName:my-op              # AND (space-separated)
ServiceName:a OR ServiceName:b                     # OR (explicit keyword)
NOT SeverityText:error                             # Negation
-SeverityText:error                                # Negation (shorthand)
Body:"connection refused"                          # Exact phrase
Duration:>1000000                                  # Greater than (nanoseconds for traces)
ServiceName:frontend-*                             # Wildcard
LogAttributes.key:value                            # Map property (dot notation)
```

**Precedence:** `NOT` > `AND` (space) > `OR`. Use parentheses for clarity.

## Lucene Field Names (for `where`)

| Lucene field | Table | ClickHouse Column |
|-------------|-------|-------------------|
| `ServiceName:X` | traces / logs | `ServiceName` |
| `SpanName:X` | traces | `SpanName` |
| `SeverityText:X` | logs | `SeverityText` |
| `Body:"text"` | logs | `Body` |
| `Duration:>N` | traces | `Duration` |
| `SpanAttributes.key:value` | traces | `SpanAttributes['key']` |
| `LogAttributes.key:value` | logs | `LogAttributes['key']` |

## Column Names (for `field` and `groupBy`)

Use actual ClickHouse column names in `field` and `groupBy`:

| field | Source | Column Type |
|-------|--------|-------------|
| `Duration` | traces | UInt64 (nanoseconds) |
| `ServiceName` | traces/logs | LowCardinality(String) |
| `SpanName` | traces | LowCardinality(String) |
| `StatusCode` | traces | LowCardinality(String) |
| `SeverityText` | logs | LowCardinality(String) |
| `Body` | logs | String |
| `SpanAttributes['key']` | traces | String (from Map) |
| `LogAttributes['key']` | logs | String (from Map) |
| `Value` | metrics | Float64 |

## Multi-Series Tiles

Multiple series in a tile create multi-line charts. All series must have the same `type`.

```json
"series": [
  {"type": "time", "sourceId": "<id>", "aggFn": "quantile", "level": 0.5, "field": "Duration", "where": "", "whereLanguage": "lucene", "groupBy": [], "displayType": "line"},
  {"type": "time", "sourceId": "<id>", "aggFn": "quantile", "level": 0.95, "field": "Duration", "where": "", "whereLanguage": "lucene", "groupBy": [], "displayType": "line"},
  {"type": "time", "sourceId": "<id>", "aggFn": "quantile", "level": 0.99, "field": "Duration", "where": "", "whereLanguage": "lucene", "groupBy": [], "displayType": "line"}
]
```

Each series has its own `where` filter (no shared `aggCondition`).

## Grid Layout Patterns

Grid is **24 columns wide**.

**4 KPIs across:** `w:6, h:3` at `x: 0, 6, 12, 18`

**Half-width charts:** `w:12, h:6` at `x: 0, 12`

**Full-width chart:** `w:24, h:6`

**Full-width table:** `w:24, h:5`

**Typical dashboard:**
```
y:0   h:3  — KPI row (4× w:6, type: "number")
y:3   h:6  — Chart row (2× w:12, type: "time")
y:9   h:6  — Chart row (2× w:12)
y:15  h:5  — Table row (1× w:24, type: "table")
```

## Source Resolution

The `sourceId` field requires a **MongoDB source ID** from `GET /sources`, not a kind string. Source IDs are dynamic and change per container restart.

```python
# Fetch and map source IDs (internal API, no auth required)
sources = requests.get('http://localhost:8000/sources').json()
SRC = {s['kind']: s['id'] for s in sources}
# SRC = {"trace": "<id>", "log": "<id>", "metric": "<id>", "session": "<id>"}

# Use in series
"sourceId": SRC["trace"]   # for traces
"sourceId": SRC["log"]     # for logs
"sourceId": SRC["metric"]  # for metrics
```

**Kind strings like `"traces"`, `"logs"`, `"metrics"` will be rejected by the API.** Always resolve IDs first.
