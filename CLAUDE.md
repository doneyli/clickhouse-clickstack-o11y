# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

HyperDX AI Dashboard Builder — an observability platform for monitoring LLM workloads. Uses a single HyperDX Local container (ClickHouse + MongoDB + OTel Collector + UI) with Python tooling for synthetic trace generation, data querying, and AI-powered dashboard creation via Claude.

## Setup & Common Commands

```bash
./setup.sh                                    # Full idempotent setup (8 steps)
source .venv/bin/activate                     # Activate Python venv (created by setup.sh)
docker compose up -d                          # Start HyperDX container
```

### Generate Data
```bash
python generate_demo_data.py                          # 100 traces (default)
python generate_demo_data.py --count 500              # Custom count
python generate_demo_data.py --services text-to-sql   # Single service
python generate_demo_data.py --error-rate 0.1         # 10% errors
```

### Query ClickHouse
```bash
python query_clickhouse.py --summary
python query_clickhouse.py --attributes
python query_clickhouse.py --services
python query_clickhouse.py --query "SELECT count(*) FROM log_stream WHERE type='span'"
```

### System Telemetry (macOS)
```bash
cd system-telemetry && python generate_system_traces.py          # Continuous (30s interval)
cd system-telemetry && python generate_system_traces.py --once   # Single collection
```

## Architecture

All services run inside a single Docker container (`hyperdx-local`):
- **OTel Collector** — receives OTLP on ports 4317 (gRPC) / 4318 (HTTP)
- **ClickHouse** — stores all data in `log_stream` table (port 8123)
- **MongoDB** — stores dashboards, teams, users, sources
- **HyperDX UI** — port 8080
- **HyperDX Internal API** — port 8000

Data flow: Python scripts → OTLP (4318) → OTel Collector → ClickHouse `log_stream` → HyperDX UI

### Services Generating Traces
- `text-to-sql-service` — spans: parse-question, generate-sql, execute-sql, format-response, text-to-sql-query
- `vector-rag-service` — spans: embed-query, vector-search, generate-answer, rag-pipeline
- `chatbot-service` — spans: chat-completion
- `macos-system-monitor` — spans: cpu-load-sample, memory-pressure-check, disk-io-sample, battery-status-check, network-connections-scan, top-processes-snapshot, system-health-check

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
        "field": "system.cpu.percent",
        "where": "span_name:cpu-load-sample service:macos-system-monitor",
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
- **`field` uses HyperDX names** — `duration`, `system.cpu.percent`, `gen_ai.usage.input_tokens` (NOT ClickHouse columns like `_duration`, `_number_attributes[...]`)
- **No** `source`, `displayType`, `whereLanguage`, `granularity` fields
- **`numberFormat` required** on `type: "number"` KPI tiles
- **Omit `field`** for `count` aggFn
- **Grid is 12 columns wide** — `x + w <= 12`
- Valid `aggFn`: count, sum, avg, min, max, p50, p90, p95, p99, count_distinct, last_value, count_per_sec, count_per_min, count_per_hour, plus `_rate` variants
- Valid series `type`: time, number, table, histogram, search, markdown

### Legacy: MongoDB direct insert (`create_dashboard_mongo.sh`)

The `create_dashboard_mongo.sh` script uses an older tiles/config/SQL format that predates the API approach. It exists for reference but **new dashboards should always use the REST API** via the `/hyperdx-dashboard` skill.

## Critical Gotchas

- **`log_stream` is the only table** — spans, logs, and events all go here.
- **`_duration` is already milliseconds** — Float64, no conversion needed.
- **MongoDB shell is `mongo` not `mongosh`** — HyperDX Local uses legacy shell.
- **`psutil.net_connections()` requires sudo on macOS** — always wrap in try/except for AccessDenied.

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
| `_string_attributes` | Map(String, String) | attribute name directly (e.g. `gen_ai.request.model`) |
| `_number_attributes` | Map(String, Float64) | attribute name directly (e.g. `gen_ai.usage.input_tokens`) |
| `_timestamp_sort_key` | DateTime | — |
