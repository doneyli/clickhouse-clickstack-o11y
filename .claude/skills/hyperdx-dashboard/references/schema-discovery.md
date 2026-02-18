# Schema Discovery Reference

ClickStack uses OTel-native ClickHouse tables. Always discover the schema dynamically — run queries to find available tables, columns, services, and attributes.

## ClickHouse Access

From outside the container, use the `api` user:
```bash
curl -s "http://localhost:8123/?user=api&password=api" --data "SHOW TABLES FROM default"
```

From inside the container:
```bash
docker exec clickstack-local clickhouse-client --query "SHOW TABLES FROM default"
```

## Tables

| Table | Contents |
|-------|----------|
| `otel_traces` | Distributed traces (spans) |
| `otel_logs` | Log events |
| `otel_metrics_gauge` | Gauge metrics |
| `otel_metrics_sum` | Sum/counter metrics |
| `otel_metrics_histogram` | Histogram metrics |
| `otel_metrics_summary` | Summary metrics |
| `otel_metrics_exponential_histogram` | Exponential histogram metrics |
| `hyperdx_sessions` | Session data |

## `otel_traces` Table

| Column | Type | Description |
|--------|------|-------------|
| `Timestamp` | DateTime64(9) | Span timestamp (nanosecond precision) |
| `TraceId` | String | Trace ID |
| `SpanId` | String | Span ID |
| `ParentSpanId` | String | Parent span ID |
| `SpanName` | LowCardinality(String) | Operation/span name |
| `SpanKind` | LowCardinality(String) | Span kind (SPAN_KIND_SERVER, etc.) |
| `ServiceName` | LowCardinality(String) | Service name |
| `Duration` | UInt64 | Span duration in **nanoseconds** |
| `StatusCode` | LowCardinality(String) | Status (STATUS_CODE_OK, STATUS_CODE_ERROR, STATUS_CODE_UNSET) |
| `StatusMessage` | String | Status message |
| `SpanAttributes` | Map(LowCardinality(String), String) | Span-level attributes |
| `ResourceAttributes` | Map(LowCardinality(String), String) | Resource-level attributes |
| `ScopeName` | String | Instrumentation scope |
| `Events.Timestamp` | Array(DateTime64(9)) | Span event timestamps |
| `Events.Name` | Array(LowCardinality(String)) | Span event names |
| `Events.Attributes` | Array(Map(LowCardinality(String), String)) | Span event attributes |

## `otel_logs` Table

| Column | Type | Description |
|--------|------|-------------|
| `Timestamp` | DateTime64(9) | Log timestamp (nanosecond precision) |
| `TimestampTime` | DateTime | Materialized second-precision timestamp |
| `TraceId` | String | Correlated trace ID |
| `SpanId` | String | Correlated span ID |
| `SeverityText` | LowCardinality(String) | Log level (INFO, WARN, ERROR, etc.) |
| `SeverityNumber` | UInt8 | Numeric severity |
| `ServiceName` | LowCardinality(String) | Service name |
| `Body` | String | Log message body |
| `LogAttributes` | Map(LowCardinality(String), String) | Log-level attributes |
| `ResourceAttributes` | Map(LowCardinality(String), String) | Resource-level attributes |
| `ScopeName` | String | Instrumentation scope |

## `otel_metrics_gauge` / `otel_metrics_sum` Tables

| Column | Type | Description |
|--------|------|-------------|
| `TimeUnix` | DateTime64(9) | Metric timestamp |
| `MetricName` | String | Metric name (e.g., `system.cpu.utilization`) |
| `MetricDescription` | String | Metric description |
| `MetricUnit` | String | Unit (e.g., `By`, `1`, `{cpu}`) |
| `ServiceName` | LowCardinality(String) | Source service |
| `Value` | Float64 | Metric value |
| `Attributes` | Map(LowCardinality(String), String) | Metric-level attributes |
| `ResourceAttributes` | Map(LowCardinality(String), String) | Resource-level attributes |

## Discovery Queries

### List all services (traces)
```sql
SELECT ServiceName, count() AS cnt
FROM otel_traces
GROUP BY ServiceName
ORDER BY cnt DESC
```

### List all services (logs)
```sql
SELECT ServiceName, count() AS cnt
FROM otel_logs
GROUP BY ServiceName
ORDER BY cnt DESC
```

### List span names for a service
```sql
SELECT SpanName, count() AS cnt
FROM otel_traces
WHERE ServiceName = 'checkout'
GROUP BY SpanName
ORDER BY cnt DESC
```

### Data distribution overview (traces)
```sql
SELECT
    count(*) AS total_spans,
    count(DISTINCT ServiceName) AS services,
    count(DISTINCT SpanName) AS span_names,
    min(Timestamp) AS earliest,
    max(Timestamp) AS latest
FROM otel_traces
```

### Per-service latency (traces)
```sql
SELECT
    ServiceName,
    count() AS span_count,
    round(avg(Duration) / 1e6, 2) AS avg_latency_ms,
    round(quantile(0.95)(Duration) / 1e6, 2) AS p95_latency_ms
FROM otel_traces
GROUP BY ServiceName
ORDER BY span_count DESC
```

### Find all span attribute keys
```sql
SELECT DISTINCT arrayJoin(SpanAttributes.keys) AS attr_key
FROM otel_traces
ORDER BY attr_key
LIMIT 100
```

### Find all log attribute keys
```sql
SELECT DISTINCT arrayJoin(LogAttributes.keys) AS attr_key
FROM otel_logs
ORDER BY attr_key
LIMIT 100
```

### List all metric names
```sql
SELECT 'Gauge' AS type, DISTINCT MetricName FROM otel_metrics_gauge
UNION ALL
SELECT 'Sum' AS type, DISTINCT MetricName FROM otel_metrics_sum
ORDER BY MetricName
```

### Metric value ranges
```sql
SELECT
    MetricName,
    count() AS samples,
    min(Value) AS min_val,
    round(avg(Value), 4) AS avg_val,
    max(Value) AS max_val
FROM otel_metrics_gauge
GROUP BY MetricName
ORDER BY samples DESC
```

### Log severity distribution
```sql
SELECT SeverityText, count() AS cnt
FROM otel_logs
GROUP BY SeverityText
ORDER BY cnt DESC
```

## Source Discovery (API)

ClickStack auto-creates data sources at container startup. Discover them via the API:

```bash
curl -s http://localhost:8000/sources | python3 -c "
import sys, json
for s in json.load(sys.stdin):
    print(f'{s[\"kind\"]}: name={s[\"name\"]}, table={s[\"from\"][\"tableName\"]}, id={s[\"id\"]}')
"
```

Typical output:
```
log: name=Logs, table=otel_logs, id=<dynamic>
trace: name=Traces, table=otel_traces, id=<dynamic>
metric: name=Metrics, table=, id=<dynamic>
session: name=Sessions, table=hyperdx_sessions, id=<dynamic>
```

The `source` string in tile configs maps to these source kinds:
- `"traces"` → Traces source → `otel_traces`
- `"logs"` → Logs source → `otel_logs`
- `"metrics"` → Metrics source → `otel_metrics_*` (routed by `metricDataType`)

## Attribute Maps

Attributes are stored in typed Map columns. Use the right map:

```sql
-- Span attributes (traces)
SpanAttributes['http.method']
SpanAttributes['http.url']

-- Log attributes (logs)
LogAttributes['exception.message']

-- Resource attributes (both)
ResourceAttributes['service.version']

-- Metric attributes
Attributes['state']
Attributes['direction']
```

## Key Differences from v1 (`log_stream`)

| v1 (log_stream) | v2 (OTel-native) |
|-----------------|-------------------|
| `_service` | `ServiceName` |
| `span_name` | `SpanName` |
| `_duration` (Float64, ms) | `Duration` (UInt64, nanoseconds) |
| `severity_text` | `SeverityText` |
| `_hdx_body` | `Body` (logs) / `SpanName` (traces) |
| `_string_attributes['key']` | `SpanAttributes['key']` / `LogAttributes['key']` |
| `_number_attributes['key']` | `SpanAttributes['key']` (all strings in OTel) |
| `type = 'span'` | Separate `otel_traces` table |
| `type = 'log'` | Separate `otel_logs` table |
| `metric_stream` | `otel_metrics_gauge/sum/histogram/summary` |
