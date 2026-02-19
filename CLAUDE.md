# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ClickStack Sample Data Demo — loads the [ClickStack e-commerce sample data](https://clickhouse.com/docs/use-cases/observability/clickstack/getting-started/sample-data) into a local ClickStack instance for exploration and dashboard building. Uses a single ClickStack Local container (ClickHouse + OTel Collector + HyperDX UI) with Python tooling for AI-powered dashboard creation via Claude.

## Setup & Common Commands

```bash
./setup.sh                                    # Full idempotent setup (5 steps)
source .venv/bin/activate                     # Activate Python venv (created by setup.sh)
docker compose up -d                          # Start ClickStack container
```

### Query ClickHouse

```bash
# From outside the container (use api user)
curl -s "http://localhost:8123/?user=api&password=api" --data "SHOW TABLES FROM default"
curl -s "http://localhost:8123/?user=api&password=api" --data "SELECT ServiceName, count() FROM otel_traces GROUP BY ServiceName ORDER BY count() DESC"

# From inside the container
docker exec clickstack-local clickhouse-client --query "SELECT count() FROM otel_traces"
```

## Architecture

All services run inside a single Docker container (`clickstack-local`):
- **OTel Collector** — receives OTLP on ports 4317 (gRPC) / 4318 (HTTP)
- **ClickHouse** — stores data in OTel-native tables (port 8123)
- **HyperDX UI** — port 8080
- **ClickStack API** — port 8000 (internal API + v2 API at `/api/v2/`)

Data flow: `sample.tar.gz` → OTLP HTTP (4318) → OTel Collector → ClickHouse → HyperDX UI

### ClickHouse Tables

| Table | Contents |
|-------|----------|
| `otel_traces` | Distributed traces (spans) |
| `otel_logs` | Log events |
| `otel_metrics_gauge` | Gauge metrics |
| `otel_metrics_sum` | Sum/counter metrics |
| `otel_metrics_histogram` | Histogram metrics |
| `otel_metrics_summary` | Summary metrics |

### Sample Data

The data comes from the [OpenTelemetry Demo](https://opentelemetry.io/docs/demo/) — a simulated e-commerce store with microservices. It includes traces, logs, and metrics. Query ClickHouse directly to discover available services and attributes.

## Dashboard Creation

### Use the `/hyperdx-dashboard` skill

When creating, modifying, or fixing dashboards, **always invoke the `/hyperdx-dashboard` skill**. It encapsulates the complete workflow: discover data via ClickHouse, generate the dashboard JSON, validate against all rules, deploy via the API, and verify in the UI. The skill's reference docs live in `.claude/skills/hyperdx-dashboard/references/`.

### ClickStack v2 Dashboard API

Bearer auth required. In local mode, use access key `clickstack-local-v2-api-key` (created by `setup.sh`).

```
# v2 API (Bearer auth)
POST   http://localhost:8000/api/v2/dashboards          # Create dashboard
GET    http://localhost:8000/api/v2/dashboards          # List all dashboards
GET    http://localhost:8000/api/v2/dashboards/{id}     # Get dashboard
DELETE http://localhost:8000/api/v2/dashboards/{id}     # Delete dashboard

# Source discovery (internal API, no auth)
GET    http://localhost:8000/sources                     # List data sources
```

### Dashboard JSON format (v2 API)

```json
{
  "name": "Dashboard Name",
  "tags": [],
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
        "groupBy": ["ServiceName"],
        "displayType": "line"
      }]
    }
  ]
}
```

Key rules:
- **`tiles`** array with **`series`** (NOT `config.select[]`)
- **`sourceId`** per-series: Must be a **source ID** from `GET http://localhost:8000/sources` (NOT a kind string like `"traces"`)
  - Resolve: `SRC = {s['kind']: s['id'] for s in requests.get(f'{API}/sources').json()}`
  - Use: `SRC["trace"]`, `SRC["log"]`, `SRC["metric"]`
- **Series `type`**: `time`, `number`, `table`, `search`, `markdown` — discriminated union
- **`field`**: ClickHouse column name (`Duration`, `ServiceName`). Empty or omit for `count`.
- **`where`** per-series: Lucene syntax with `whereLanguage: "lucene"`
- **`groupBy`** is **string array**: `["ServiceName"]` (NOT objects). Only on `time`/`table`.
- **`displayType`**: Only on `time` series (`"line"` or `"stacked_bar"`)
- **Grid is 24 columns wide** — `x + w <= 24`
- **Heights:** `h: 3` for number (KPI), `h: 6` for time, `h: 5` for table
- Valid `aggFn`: count, sum, avg, min, max, count_distinct, last_value, quantile (with level), any, none
- **For metrics:** add `metricName` and `metricDataType` (lowercase: `gauge`, `sum`, `histogram`, `summary`)
- **Quantile** replaces p50/p90/p95/p99: use `aggFn: "quantile"` with `level: 0.95`

## Critical Gotchas

- **`otel_traces`** stores spans. **`otel_logs`** stores logs. **`otel_metrics_*`** stores metrics.
- **`Duration` is nanoseconds** — UInt64 in `otel_traces`. HyperDX UI handles display formatting.
- **`field` uses ClickHouse column names** — `Duration`, `ServiceName`, `SpanName` (NOT HyperDX names like `duration`, `service`).
- **Lucene `where` uses ClickHouse column names directly** — `ServiceName:X`, `SpanName:X`, `SeverityText:error`, `Body:"text"`. HyperDX-mapped names like `service`, `level`, `span_name` do NOT work (fails with "Unknown identifier").
- **Map properties use dot notation in Lucene** — `LogAttributes.key:value`, `SpanAttributes.key:value`.
- **NEVER use `type:span` or `type:log` in Lucene `where` clauses** — not searchable, silently returns 0 rows.
- **ClickHouse access from outside** uses `user=api&password=api` — the `default` user is restricted to localhost inside the container.

## ClickHouse Schema (Key Columns)

### `otel_traces`

Lucene `where` uses ClickHouse column names directly (NOT HyperDX-mapped names).

| Column | Type | Lucene `where` usage |
|--------|------|---------------------|
| `ServiceName` | LowCardinality(String) | `ServiceName:value` |
| `SpanName` | LowCardinality(String) | `SpanName:value` |
| `Duration` | UInt64 (nanoseconds) | `Duration:>1000000` |
| `StatusCode` | LowCardinality(String) | `StatusCode:value` |
| `SpanAttributes` | Map(String, String) | `SpanAttributes.key:value` (dot notation) |
| `ResourceAttributes` | Map(String, String) | — |

### `otel_logs`

| Column | Type | Lucene `where` usage |
|--------|------|---------------------|
| `ServiceName` | LowCardinality(String) | `ServiceName:value` |
| `SeverityText` | LowCardinality(String) | `SeverityText:error` |
| `Body` | String | `Body:"search text"` |
| `LogAttributes` | Map(String, String) | `LogAttributes.key:value` (dot notation) |
