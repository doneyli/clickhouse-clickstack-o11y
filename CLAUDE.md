# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ClickStack Sample Data Demo — loads the [ClickStack e-commerce sample data](https://clickhouse.com/docs/use-cases/observability/clickstack/getting-started/sample-data) into a local HyperDX instance for exploration and dashboard building. Uses a single HyperDX Local container (ClickHouse + MongoDB + OTel Collector + UI) with Python tooling for data querying and AI-powered dashboard creation via Claude.

## Setup & Common Commands

```bash
./setup.sh                                    # Full idempotent setup (6 steps)
source .venv/bin/activate                     # Activate Python venv (created by setup.sh)
docker compose up -d                          # Start HyperDX container
```

### Query ClickHouse
```bash
python query_clickhouse.py --summary       # Data overview (counts, services, time range)
python query_clickhouse.py --attributes    # All string and number attribute keys
python query_clickhouse.py --services      # All services
python query_clickhouse.py --query "SELECT count(*) FROM log_stream WHERE type='span'"
```

## Architecture

All services run inside a single Docker container (`hyperdx-local`):
- **OTel Collector** — receives OTLP on ports 4317 (gRPC) / 4318 (HTTP)
- **ClickHouse** — stores all data in `log_stream` table (port 8123)
- **MongoDB** — stores dashboards, teams, users, sources
- **HyperDX UI** — port 8080
- **HyperDX Internal API** — port 8000

Data flow: `sample.tar.gz` → OTLP HTTP (4318) → OTel Collector → ClickHouse `log_stream` → HyperDX UI

### Sample Data

The data comes from the [OpenTelemetry Demo](https://opentelemetry.io/docs/demo/) — a simulated e-commerce store with microservices. It includes traces, logs, and metrics. Run `python query_clickhouse.py --services` and `--attributes` to discover available services and attributes.

## Dashboard Creation

### Use the `/hyperdx-dashboard` skill

When creating, modifying, or fixing dashboards, **always invoke the `/hyperdx-dashboard` skill**. It encapsulates the complete workflow: discover data via ClickHouse, generate the dashboard JSON, validate against all rules, deploy via the API, and verify in the UI. The skill's reference docs live in `.claude/skills/hyperdx-dashboard/references/`.

### HyperDX Dashboard API

Official API docs: https://www.hyperdx.io/docs/api/dashboards

Both endpoints work locally and read/write the same dashboards:

| Endpoint | Format differences |
|---|---|
| `POST http://localhost:8000/dashboards` (internal, recommended) | Uses `table: "logs"`, `seriesReturnType: "column"` |
| `POST http://localhost:8000/api/v1/dashboards` (public, matches official docs) | Uses `dataSource: "events"`, `asRatio: false` |

**Auth:** `Authorization: Bearer {ACCESS_KEY}` — get token:
```bash
docker exec hyperdx-local mongo --quiet --eval \
  'db=db.getSiblingDB("hyperdx"); print(db.users.findOne({}).accessKey)'
```

**NEVER insert dashboards directly into MongoDB** — direct inserts assign the wrong team ID and dashboards silently won't appear in the UI.

### Dashboard JSON format (internal API)

```json
{
  "name": "Dashboard Name",
  "charts": [
    {
      "id": "unique-kebab-id",
      "name": "Chart Title",
      "x": 0, "y": 0, "w": 6, "h": 3,
      "series": [{
        "type": "time",
        "table": "logs",
        "aggFn": "avg",
        "field": "duration",
        "where": "service:my-service",
        "groupBy": []
      }],
      "seriesReturnType": "column"
    }
  ]
}
```

Key rules:
- **`charts` array** (NOT `tiles`) with **`series`** (NOT `config`/`select`)
- **`where` uses Lucene syntax** — `span_name:value service:name` (NOT SQL)
- **`field` uses HyperDX names** — `duration`, `service`, `span_name` and custom attributes by name (NOT ClickHouse columns like `_duration`, `_service`, `_number_attributes[...]`)
- **No** `source`, `displayType`, `whereLanguage`, `granularity` fields
- **`numberFormat` required** on `type: "number"` KPI tiles
- **Omit `field`** for `count` aggFn
- **Grid is 12 columns wide** — `x + w <= 12`
- Valid `aggFn`: count, sum, avg, min, max, p50, p90, p95, p99, count_distinct, last_value, count_per_sec, count_per_min, count_per_hour, plus `_rate` variants
- Valid series `type`: time, number, table, histogram, search, markdown

## Critical Gotchas

- **`log_stream` is the only table** — spans, logs, and events all go here.
- **`_duration` is already milliseconds** — Float64, no conversion needed.
- **MongoDB shell is `mongo` not `mongosh`** — HyperDX Local uses legacy shell.

## ClickHouse `log_stream` Schema (Key Columns)

These column names are for **direct ClickHouse SQL queries** (`query_clickhouse.py`). Dashboard `field` values use HyperDX names instead (see mapping below).

| Column | Type | HyperDX field name |
|---|---|---|
| `_service` | String | `service` |
| `span_name` | String | `span_name` |
| `_duration` | Float64 (ms) | `duration` |
| `severity_text` | String | `level` |
| `_hdx_body` | String | `body` |
| `type` | String | `hyperdx_event_type` |
| `_string_attributes` | Map(String, String) | attribute name directly |
| `_number_attributes` | Map(String, Float64) | attribute name directly |
| `_timestamp_sort_key` | DateTime | — |

Run `python query_clickhouse.py --attributes` to discover available attribute keys in the loaded sample data.
