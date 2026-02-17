# ClickHouse v1 Schema Reference

## `log_stream` Table

HyperDX v1 stores all observability data (logs, traces, metrics) in a single `log_stream` table.

### Core Columns

| Column | Type | Description |
|--------|------|-------------|
| `timestamp` | DateTime64 | Event timestamp |
| `type` | String | Record type: `'span'`, `'log'` — always filter with `type = 'span'` for traces |
| `_service` | String | Service name |
| `_duration` | Float64 | Span duration in **milliseconds** (materialized, no division needed) |
| `span_name` | String | Operation/span name |
| `trace_id` | String | Trace ID |
| `span_id` | String | Span ID |
| `parent_span_id` | String | Parent span ID |
| `_string_attributes` | Map(String, String) | All string-valued attributes |
| `_number_attributes` | Map(String, Float64) | All numeric-valued attributes |

### Attribute Maps

Attributes are stored in two typed maps. Using the wrong map returns empty/zero silently.

- **`_string_attributes`** — Map(String, String): string-valued custom attributes
- **`_number_attributes`** — Map(String, Float64): numeric-valued custom attributes

Run the discovery queries below to find what attributes are available in your data.

### Common Mistake: Wrong Map

```sql
-- WRONG: numeric values are in _number_attributes, not _string_attributes
_string_attributes['some.numeric.attr']   -- returns ''

-- CORRECT
_number_attributes['some.numeric.attr']    -- returns the number

-- WRONG: string values are in _string_attributes, not _number_attributes
_number_attributes['some.string.attr']     -- returns 0

-- CORRECT
_string_attributes['some.string.attr']     -- returns the string
```

## Discovery Queries

### Find all string attribute keys
```sql
SELECT DISTINCT arrayJoin(_string_attributes.keys) AS attr_key
FROM log_stream
ORDER BY attr_key
LIMIT 100
```

### Find all numeric attribute keys
```sql
SELECT DISTINCT arrayJoin(_number_attributes.keys) AS attr_key
FROM log_stream
ORDER BY attr_key
LIMIT 100
```

### Data distribution overview
```sql
SELECT
    count(*) AS total_rows,
    count(DISTINCT _service) AS services,
    count(DISTINCT span_name) AS span_names,
    min(timestamp) AS earliest,
    max(timestamp) AS latest
FROM log_stream
```

### Row counts by type
```sql
SELECT type, count(*) AS cnt
FROM log_stream
GROUP BY type
ORDER BY cnt DESC
```

### Per-service breakdown
```sql
SELECT
    _service AS service,
    count(*) AS cnt,
    round(avg(_duration), 0) AS avg_latency_ms
FROM log_stream
WHERE type = 'span'
GROUP BY service
ORDER BY cnt DESC
```

## `metric_stream` Table

HyperDX stores metrics in a separate `metric_stream` table. Dashboard charts targeting metrics use `table: "metrics"` (not queried via `log_stream`).

### Core Columns

| Column | Type | Description |
|--------|------|-------------|
| `timestamp` | DateTime64 | Metric timestamp |
| `name` | String | Metric name (e.g., `system.cpu.utilization`) |
| `data_type` | String | Metric type: `Gauge`, `Sum`, `Histogram`, `Summary` |
| `value` | Float64 | Metric value |
| `unit` | String | Unit of measurement (e.g., `By`, `1`, `{cpu}`) |
| `is_delta` | UInt8 | Whether metric is delta (1) or cumulative (0) |
| `is_monotonic` | UInt8 | Whether metric is monotonic (1) or not (0) |
| `_string_attributes` | Map(String, String) | String-valued resource/metric attributes |

### Discovery Queries

#### List all metric names with data types
```sql
SELECT DISTINCT name, data_type
FROM metric_stream
ORDER BY name
```

#### Metric value ranges
```sql
SELECT
    name,
    data_type,
    count(*) AS samples,
    min(value) AS min_val,
    avg(value) AS avg_val,
    max(value) AS max_val
FROM metric_stream
GROUP BY name, data_type
ORDER BY samples DESC
```

#### Per-metric sample counts and time range
```sql
SELECT
    name,
    data_type,
    count(*) AS cnt,
    min(timestamp) AS earliest,
    max(timestamp) AS latest
FROM metric_stream
GROUP BY name, data_type
ORDER BY cnt DESC
```

### Dashboard Field Format

When using metrics in dashboard `field`, combine the name and data type: `"name - DataType"`.

Example: metric name `system.cpu.utilization` with data_type `Gauge` → field value `"system.cpu.utilization - Gauge"`.

## Common WHERE Patterns (ClickHouse SQL Only)

**IMPORTANT:** These SQL patterns are for ClickHouse discovery queries (`query_clickhouse.py --query "..."`) only. Dashboard `where` clauses use **Lucene syntax** instead (e.g., `service:my-service span_name:my-span`). See [rules.md](rules.md) for dashboard rules.

```sql
-- All spans
type = 'span'

-- Specific service
type = 'span' AND _service = 'my-service'

-- Specific span name
type = 'span' AND span_name = 'my-span'

-- Error spans only
type = 'span' AND _string_attributes['otel.status_code'] = 'ERROR'

-- Spans with a specific string attribute
type = 'span' AND _string_attributes['my.attr'] != ''

-- Spans with a specific numeric attribute
type = 'span' AND _number_attributes['my.metric'] > 0
```
