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
- **ClickStack Internal API** — port 8000

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

### ClickStack Dashboard API

No auth required for local mode.

```
POST   http://localhost:8000/dashboards          # Create dashboard
GET    http://localhost:8000/dashboards          # List all dashboards
DELETE http://localhost:8000/dashboards/{id}     # Delete dashboard
```

### Dashboard JSON format (tiles)

```json
{
  "name": "Dashboard Name",
  "tags": [],
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
        "groupBy": [{"valueExpression": "ServiceName"}],
        "displayType": "line"
      }
    }
  ]
}
```

Key rules:
- **`tiles` array** with **`config`** containing **`select`** (NOT `charts`/`series`)
- **`source`**: `"traces"`, `"logs"`, or `"metrics"`
- **`select`** items: `aggFn` + `valueExpression` (ClickHouse column) + `aggCondition`
- **`where` uses Lucene syntax** with `whereLanguage: "lucene"` required
- **`groupBy`** is objects: `[{"valueExpression": "ColumnName"}]` (NOT strings)
- **Grid is 24 columns wide** — `x + w <= 24`
- **`tags: []`** required at dashboard level
- Valid `aggFn`: count, sum, avg, min, max, count_distinct, last_value, quantile (with level)
- Valid `displayType`: line, stacked_bar, number, table, markdown
- **For metrics:** add `metricName` and `metricDataType` to config
- **Quantile** replaces p50/p90/p95/p99: use `aggFn: "quantile"` with `level: 0.95`

## Critical Gotchas

- **`otel_traces`** stores spans. **`otel_logs`** stores logs. **`otel_metrics_*`** stores metrics.
- **`Duration` is nanoseconds** — UInt64 in `otel_traces`. HyperDX UI handles display formatting.
- **`valueExpression` uses ClickHouse column names** — `Duration`, `ServiceName`, `SpanName` (NOT HyperDX names like `duration`, `service`).
- **Lucene `where` still uses HyperDX field names** — `service:X`, `span_name:X`, `level:error` (HyperDX maps these to column expressions).
- **NEVER use `type:span` or `type:log` in Lucene `where` clauses** — not searchable, silently returns 0 rows.
- **ClickHouse access from outside** uses `user=api&password=api` — the `default` user is restricted to localhost inside the container.

## ClickHouse Schema (Key Columns)

### `otel_traces`

| Column | Type | Lucene field |
|--------|------|-------------|
| `ServiceName` | LowCardinality(String) | `service` |
| `SpanName` | LowCardinality(String) | `span_name` |
| `Duration` | UInt64 (nanoseconds) | `duration` |
| `StatusCode` | LowCardinality(String) | — |
| `SpanAttributes` | Map(String, String) | attribute name directly |
| `ResourceAttributes` | Map(String, String) | — |

### `otel_logs`

| Column | Type | Lucene field |
|--------|------|-------------|
| `ServiceName` | LowCardinality(String) | `service` |
| `SeverityText` | LowCardinality(String) | `level` |
| `Body` | String | `body` |
| `LogAttributes` | Map(String, String) | attribute name directly |
