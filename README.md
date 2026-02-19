# ClickStack Observability Demo

AI-powered dashboard creation for ClickHouse observability using [ClickStack](https://clickhouse.com/docs/use-cases/observability/clickstack) and any AI coding agent via the [Agent Skills](https://agentskills.io/) standard.

## The Problem

Creating observability dashboards is slow. You dig through schemas, write queries, manually configure chart after chart. Migrating dashboards between vendors is worse — months of painstakingly recreating what you already had.

What if an AI could discover your data, generate dashboards, and validate them automatically — in under 60 seconds?

## What This Demo Shows

### Scenario A: Zero-to-Dashboard

Paste a vague prompt into Claude Code:

```
Create a dashboard for the checkout service. Show me everything important about it.
```

The AI discovers what data exists in ClickHouse (services, attributes, span names), generates a validated dashboard definition, deploys it via the ClickStack API, and opens it in the UI. The entire cycle takes roughly 60 seconds.

### Scenario B: Screenshot-to-Dashboard

Upload a screenshot of an existing dashboard from any observability vendor. Claude's vision reads the layout, chart types, and metrics, then reproduces the dashboard using the actual telemetry data available in your ClickHouse instance — and extends it with additional charts you request. This turns months of vendor migration into an afternoon.

## Architecture

### Data Pipeline

Everything runs inside a single Docker container (`clickstack-local`):

```
sample.tar.gz ──> OTLP HTTP (:4318) ──> OTel Collector ──> ClickHouse ──> HyperDX UI (:8080)
                                              ^                |
access.log ──> filelog receiver ──────────────┘           otel_traces (spans)
  (NGINX)                                                 otel_logs (logs + nginx)
                                                          otel_metrics_* (metrics)
```

Two data sources:
- **E-commerce sample data** — from the [OpenTelemetry Demo](https://opentelemetry.io/docs/demo/), ~15 microservices generating traces, logs, and metrics via OTLP.
- **NGINX access logs** — ~14,742 JSON log lines from the [ClickStack NGINX integration](https://clickhouse.com/docs/use-cases/observability/clickstack/integrations/nginx), ingested via the OTel Collector's `filelog` receiver. Appears as `ServiceName: nginx-demo` in ClickHouse.

### How the AI Skill Works

The `hyperdx-dashboard` [agent skill](https://agentskills.io/) codifies the entire dashboard creation workflow into a repeatable, validated process:

```
Natural language prompt
        |
        v
  1. DISCOVER ──> Query ClickHouse for services, attributes, metrics
        |
        v
  2. GENERATE ──> Build dashboard JSON (tiles, series, Lucene filters)
        |
        v
  3. VALIDATE ──> Check against 24-rule checklist
        |          (catches hallucinated fields, wrong syntax, grid overflow)
        |
        v
  4. DEPLOY  ──> POST to ClickStack API (/dashboards)
        |
        v
  5. VERIFY  ──> Confirm tiles render in the UI
```

The key insight: the skill queries the database *first* to ground the LLM in real data, then validates *after* generation against a strict checklist. This is **deterministic and validated**, not guess-and-pray. Hallucinated field names, invalid aggregation functions, and SQL-in-Lucene-fields are all caught before deployment.

The skill follows the [Agent Skills specification](https://agentskills.io/specification) and lives in `skills/hyperdx-dashboard/` with reference docs for the tile format, ClickHouse schema, validation rules, and working examples. It works with any supported AI coding agent — see [Install the skill](#install-the-skill) below.

## Quick Start

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) (must be running)
- Python 3.9+
- An AI coding agent ([Claude Code](https://code.claude.com/docs/en/overview), [Cursor](https://www.cursor.com/), [Windsurf](https://codeium.com/windsurf), [GitHub Copilot](https://github.com/features/copilot), or [any supported agent](https://agentskills.io/))

Verify prerequisites before starting:

```bash
docker info > /dev/null 2>&1 && echo "Docker: OK" || echo "Docker: NOT RUNNING — start Docker Desktop first"
python3 --version 2>&1 | grep -q "3\.\([9-9]\|[1-9][0-9]\)" && echo "Python: OK" || echo "Python: 3.9+ required"
```

### Setup

```bash
git clone https://github.com/doneyli/clickhouse-clickstack-o11y.git
cd clickhouse-clickstack-o11y
./setup.sh
```

`setup.sh` is idempotent and handles everything:

1. Creates `.env` from `.env.example`
2. Sets up a Python virtualenv and installs dependencies
3. Downloads the NGINX access log sample data
4. Starts the ClickStack container via Docker Compose (with custom OTel Collector config for NGINX)
5. Waits for ClickStack UI (port 8080) and ClickHouse (port 8123) to be ready
6. Creates the v2 API access key
7. Downloads and loads the e-commerce sample data via OTLP

### Verify setup

After `setup.sh` completes, confirm everything is working:

```bash
curl -s "http://localhost:8123/?user=api&password=api" \
  --data "SELECT ServiceName, count() AS cnt FROM otel_traces GROUP BY ServiceName ORDER BY cnt DESC"
```

If you see services and counts > 0, setup succeeded. If you get a connection error, check that Docker is running and the container is up (`docker compose ps`).

### Install the skill

The `hyperdx-dashboard` skill teaches your AI coding agent how to create, validate, and deploy ClickStack dashboards. Install it with the [Agent Skills CLI](https://github.com/vercel-labs/skills):

```bash
npx skills add doneyli/clickhouse-clickstack-o11y
```

The CLI auto-detects which AI agents you have installed (Claude Code, Cursor, Windsurf, GitHub Copilot, Cline, etc.) and installs the skill into each one.

> **Claude Code users:** If you cloned this repo, the skill is already auto-discovered via the symlink at `.claude/skills/hyperdx-dashboard` — no extra installation needed.

### Try it

Deploy a pre-built dashboard and optionally start streaming live data:

```bash
source .venv/bin/activate
python deploy_checkout_dashboard.py                # Deploy e-commerce checkout dashboard
python deploy_nginx_dashboard.py                   # Deploy NGINX access log dashboard
python stream_data.py --cycle 60 &                 # Optional: replay data with live timestamps
```

> **Note:** `stream_data.py` is optional. The sample data loaded by `setup.sh` is already in ClickHouse — streaming just adds continuously updating timestamps for Live Tail and time-range charts.
>
> **Note:** The NGINX access log data has historical timestamps (2025-10-20 to 2025-10-21). Set the UI time range to that period to see NGINX data in charts.

Open **http://localhost:8080** and go to the Dashboards tab. To create a dashboard with AI instead, open Claude Code in this directory and try:

```
Create a dashboard for the checkout service. Show me everything important about it.
```

## Guided Demo

The demo progresses through levels of increasing complexity, showing how the AI skill handles each:

**Level 1 — Auto-Discovery**: A vague prompt. The AI discovers services and attributes on its own.

```
Create a dashboard for the checkout service. Show me everything important about it.
```

**Level 2 — Syntax Trap**: A prompt that deliberately uses ClickHouse column names instead of tile format names. The skill's validation catches and corrects this automatically.

**Level 3 — Pixel-Perfect Spec**: A detailed layout specification with exact grid coordinates, KPI tiles, and number formatting. Tests that the AI follows precise instructions.

**Level 4 — Screenshot Migration**: Upload a screenshot of a dashboard from another tool. The AI reproduces it with the data available in ClickHouse.

Run `./cleanup_dashboards.sh` between each level to start fresh.

See [`demo-script.md`](demo-script.md) for the full scripted walkthrough with exact prompts for each level.

## Already Set Up?

If you've already run `setup.sh` and want to jump straight in:

```bash
# Start services and stream live data
docker compose up -d
source .venv/bin/activate
python stream_data.py --cycle 60 &     # Replay data with live timestamps (1-min cycles)

# Deploy pre-built dashboards
python deploy_checkout_dashboard.py
python deploy_nginx_dashboard.py

# Clean up between demo runs
./cleanup_dashboards.sh --force
```

### Example prompts for Claude Code

Start simple and ramp up:

```
Create a dashboard for the checkout service. Show me everything important about it.
```

```
Create a dashboard with:
- P95 latency for the frontend service, grouped by span_name
- Error count over time, grouped by service
- A KPI tile showing total request count
```

```
Create a "Frontend Performance" dashboard with 4 KPI tiles in the first row,
two half-width time charts in the second row, and a full-width operations table.
```

```
[paste a screenshot of an existing dashboard]
Recreate this dashboard using the data in my ClickHouse instance.
Add a P99 latency chart and an error rate breakdown.
```

```
Create a dashboard for the NGINX access logs (ServiceName: nginx-demo).
Show total requests, error rates, response times, status code breakdown, and top request paths.
```

> **Tip:** NGINX data has historical timestamps (2025-10-20 to 2025-10-21) — set the UI time range accordingly.

## Why ClickHouse for Observability

Observability data — logs, traces, metrics — is append-heavy, high-volume, and queried analytically (aggregations, percentiles, GROUP BY). ClickHouse was built for exactly this workload:

- **Columnar storage** — Observability queries scan specific fields across billions of rows. A columnar engine reads only the columns you need, not entire events. Aggregations over `Duration` or `ServiceName` are orders of magnitude faster than row-oriented stores.
- **Compression** — Typical telemetry data compresses 10:1 to 100:1. Storage costs drop dramatically compared to Elasticsearch or SaaS vendors.
- **High-cardinality friendly** — Sparse indexing (not dense inverted indexes) means adding new tag dimensions doesn't bloat index size. `Map(String, String)` columns store unbounded attributes without schema migrations.
- **Standard SQL** — No proprietary query language. Joins, CTEs, window functions all work out of the box. Any BI tool can connect via JDBC or HTTP.
- **Proven at scale** — Petabyte-scale production deployments at companies like Uber, Cloudflare, and Microsoft. Not an unproven choice.

**Honest tradeoff:** Full-text search is weaker than Elasticsearch. ClickHouse is optimized for analytics, not grep. For most observability workflows — dashboards, alerting, top-N queries — that's the right tradeoff.

## Why ClickStack

[ClickStack](https://clickhouse.com/docs/use-cases/observability/clickstack) is ClickHouse's open-source observability stack, born from ClickHouse's [acquisition of HyperDX](https://www.hyperdx.io/blog/clickhouse-acquires-hyperdx-to-accelerate-the-future-of-open-source-observability) in March 2025. It bundles three components: ClickHouse (database) + [HyperDX](https://www.hyperdx.io/) (UI and API) + OTel Collector (ingestion).

- **What HyperDX adds** — Turns raw ClickHouse into a complete observability platform: correlated logs/traces/metrics in one UI, Lucene-style search, dashboards, alerts, and session replay. No SQL required for day-to-day use.
- **Unified signals** — Logs, traces, metrics, and session replays stored in the same ClickHouse instance. Correlate across signal types without switching tools or contexts.
- **OTel-native schema** — Uses standard OpenTelemetry column names (`ServiceName`, `SpanName`, `Duration`) in separate tables (`otel_traces`, `otel_logs`, `otel_metrics_*`). No proprietary schema.
- **Cost structure** — Open-source core, no per-seat or per-host fees. You pay for compute and storage only.
- **Single-container local mode** — The `clickstack-local` image bundles everything (ClickHouse, OTel Collector, HyperDX UI) into one container for instant sandbox environments. That's what this demo uses.
- **Programmatic dashboard API** — ClickStack exposes a REST API for dashboard CRUD, which is what makes AI-powered dashboard creation possible. Without a programmatic API, LLM-generated dashboards would require brittle UI automation.

## Why AI-Powered Dashboards

**Time-to-Value** — An hour of manual dashboard work becomes 60 seconds of prompting. Discover, generate, validate, deploy — all in one shot.

**Lowered Barrier** — No ClickHouse SQL expertise needed. PMs, junior devs, and support engineers can create production-quality dashboards from plain English.

**Frictionless Migration** — Screenshot-to-dashboard turns months of vendor migration into an afternoon. Take a screenshot of your Datadog/Grafana dashboard, paste it, and get a working replica on ClickHouse.

**Deterministic Validation vs. Hallucination** — The AI queries the database first to discover what actually exists, then validates its output against a 24-rule checklist. Hallucinated fields, wrong syntax, and invalid layouts are caught before deployment — not after.

---

## Reference

### Project Structure

```
.
├── setup.sh                      # One-command setup (idempotent)
├── docker-compose.yaml           # ClickStack Local container
├── nginx-demo.yaml               # Custom OTel Collector config for NGINX logs
├── .env.example                  # Environment template
├── requirements.txt              # Python dependencies
├── sample.tar.gz                 # E-commerce sample data (downloaded by setup.sh)
├── access.log                    # NGINX access log sample (downloaded by setup.sh)
├── stream_data.py                # Live data streamer (timestamp rewriting)
├── deploy_checkout_dashboard.py  # Pre-built checkout dashboard
├── deploy_nginx_dashboard.py     # Pre-built NGINX access log dashboard
├── create_metrics_dashboard.py   # Pre-built metrics dashboard
├── cleanup_dashboards.sh         # Delete all dashboards
├── demo-script.md                # Step-by-step demo walkthrough
├── skills/                       # Agent skills (agentskills.io spec)
│   └── hyperdx-dashboard/        #   Dashboard builder skill + references
├── CLAUDE.md                     # Instructions for Claude Code
├── .claude/                      # Claude Code config (symlinks to skills/)
└── tests/                        # Dashboard skill test cases
```

### Ports

| Port | Service |
|------|---------|
| 8080 | ClickStack UI (HyperDX) |
| 8000 | ClickStack Internal API |
| 8123 | ClickHouse HTTP |
| 4317 | OTLP gRPC |
| 4318 | OTLP HTTP |

Data is persisted in Docker volumes (`clickstack-data`, `clickstack-db`), so it survives container restarts.

### Querying ClickHouse

```bash
# From outside the container
curl -s "http://localhost:8123/?user=api&password=api" --data "SELECT count() FROM otel_traces"

# From inside the container
docker exec clickstack-local clickhouse-client --query "SELECT count() FROM otel_traces"

# Discover services (traces)
curl -s "http://localhost:8123/?user=api&password=api" \
  --data "SELECT ServiceName, count() AS cnt FROM otel_traces GROUP BY ServiceName ORDER BY cnt DESC"

# Discover services (logs — includes nginx-demo)
curl -s "http://localhost:8123/?user=api&password=api" \
  --data "SELECT ServiceName, count() AS cnt FROM otel_logs GROUP BY ServiceName ORDER BY cnt DESC"

# Discover NGINX log attributes
curl -s "http://localhost:8123/?user=api&password=api" \
  --data "SELECT DISTINCT arrayJoin(LogAttributes.keys) FROM otel_logs WHERE ServiceName = 'nginx-demo' ORDER BY 1"
```

### Streaming Options

`stream_data.py` replays `sample.tar.gz` in a loop, rewriting all timestamps to "now" so ClickStack shows continuously updating data.

```bash
python stream_data.py                  # Default: 10-min cycles, all signals
python stream_data.py --cycle 60       # Compress into 1-min cycles (good for demos)
python stream_data.py --rate 2.0       # 2x speed multiplier
python stream_data.py --traces         # Only stream traces
python stream_data.py --logs --metrics # Logs + metrics only
```

### Direct API Usage

Dashboards are created via the ClickStack v2 REST API. Bearer auth required — use `clickstack-local-v2-api-key` (created by `setup.sh`).

```bash
# List dashboards
curl -H "Authorization: Bearer clickstack-local-v2-api-key" \
  http://localhost:8000/api/v2/dashboards

# Create a dashboard
curl -X POST http://localhost:8000/api/v2/dashboards \
  -H "Authorization: Bearer clickstack-local-v2-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Dashboard",
    "tags": [],
    "tiles": [{
      "name": "Request Rate",
      "x": 0, "y": 0, "w": 12, "h": 6,
      "series": [{
        "type": "time",
        "sourceId": "<source-id-from-GET-/sources>",
        "aggFn": "count",
        "field": "",
        "where": "",
        "whereLanguage": "lucene",
        "groupBy": ["ServiceName"],
        "displayType": "line"
      }]
    }]
  }'

# Discover source IDs (needed for sourceId field)
curl -s http://localhost:8000/sources | python3 -c "
import sys, json
for s in json.load(sys.stdin):
    print(f'{s[\"kind\"]}: {s[\"id\"]}')
"
```

### Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `setup.sh` fails immediately | Docker not running | Start Docker Desktop, verify with `docker info` |
| Port 8080 already in use | Another service on that port | Stop the conflicting service or change the port in `docker-compose.yaml` |
| ClickHouse query shows 0 counts | Data didn't load | Re-run `./setup.sh` (it's idempotent) |
| `deploy_checkout_dashboard.py` returns error | Container not running | Start it: `docker compose up -d` |
| Container exits immediately | Not enough memory | Allocate at least 4 GB RAM to Docker |

### Stopping

```bash
docker compose down        # Stop container (data persisted in volume)
docker compose down -v     # Stop and delete all data
```
