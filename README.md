# ClickStack Observability Demo

AI-powered dashboard creation for ClickHouse observability, using [Claude Code](https://code.claude.com/docs/en/overview) + [HyperDX](https://www.hyperdx.io/).

## The Problem

Creating observability dashboards is slow. You dig through schemas, write queries, manually configure chart after chart. Migrating dashboards between vendors is worse — months of painstakingly recreating what you already had.

What if an AI could discover your data, generate dashboards, and validate them automatically — in under 60 seconds?

## What This Demo Shows

### Scenario A: Zero-to-Dashboard

Paste a vague prompt into Claude Code:

```
Create a dashboard for the checkout service. Show me everything important about it.
```

The AI discovers what data exists in ClickHouse (services, attributes, span names), generates a validated dashboard definition, deploys it via the HyperDX API, and opens it in the UI. The entire cycle takes roughly 60 seconds.

### Scenario B: Screenshot-to-Dashboard

Upload a screenshot of an existing dashboard from any observability vendor. Claude's vision reads the layout, chart types, and metrics, then reproduces the dashboard using the actual telemetry data available in your ClickHouse instance — and extends it with additional charts you request. This turns months of vendor migration into an afternoon.

## Architecture

### Data Pipeline

Everything runs inside a single Docker container (`hyperdx-local`):

```
sample.tar.gz ──> OTLP HTTP (:4318) ──> OTel Collector ──> ClickHouse ──> HyperDX UI (:8080)
                                                              |
                                                         log_stream (traces + logs)
                                                         metric_stream (metrics)
```

The sample data comes from the [OpenTelemetry Demo](https://opentelemetry.io/docs/demo/) — a simulated e-commerce store with ~15 microservices generating traces, logs, and metrics.

### How the AI Skill Works

The `/hyperdx-dashboard` [Claude Code skill](https://code.claude.com/docs/en/skills) codifies the entire dashboard creation workflow into a repeatable, validated process:

```
Natural language prompt
        |
        v
  1. DISCOVER ──> Query ClickHouse for services, attributes, metrics
        |
        v
  2. GENERATE ──> Build dashboard JSON (charts, series, Lucene filters)
        |
        v
  3. VALIDATE ──> Check against 17-rule checklist
        |          (catches hallucinated fields, wrong syntax, grid overflow)
        |
        v
  4. DEPLOY  ──> POST to HyperDX public API (/api/v1/dashboards)
        |
        v
  5. VERIFY  ──> Confirm charts render in the UI
```

The key insight: the skill queries the database *first* to ground the LLM in real data, then validates *after* generation against a strict checklist. This is **deterministic and validated**, not guess-and-pray. Hallucinated field names, invalid aggregation functions, and SQL-in-Lucene-fields are all caught before deployment.

The skill definition lives in `.claude/skills/hyperdx-dashboard/` with reference docs for the chart format, ClickHouse schema, validation rules, and working examples.

## Quick Start

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) (must be running — `docker info` should succeed)
- Python 3.9+
- [Claude Code](https://code.claude.com/docs/en/overview) (for AI dashboard creation)

### Setup

```bash
git clone https://github.com/doneyli/clickhouse-clickstack-o11y.git
cd clickhouse-clickstack-o11y
./setup.sh
```

`setup.sh` is idempotent and handles everything:

1. Creates `.env` from `.env.example`
2. Sets up a Python virtualenv and installs dependencies
3. Starts the HyperDX container via Docker Compose
4. Waits for HyperDX UI (port 8080) and ClickHouse (port 8123) to be ready
5. Bootstraps MongoDB with a team, user, API key, and data sources
6. Downloads and loads the e-commerce sample data via OTLP

### Try it

Once `setup.sh` completes, start streaming live data and create your first dashboard:

```bash
source .venv/bin/activate
python stream_data.py --cycle 60 &     # Replay data with live timestamps
python deploy_checkout_dashboard.py    # Deploy a pre-built dashboard
```

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

**Level 2 — Syntax Trap**: A prompt that deliberately uses ClickHouse SQL column names instead of HyperDX field names. The skill's validation catches and corrects this automatically.

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

# Deploy a pre-built dashboard
python deploy_checkout_dashboard.py

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

## Why ClickHouse for Observability

Observability data — logs, traces, metrics — is append-heavy, high-volume, and queried analytically (aggregations, percentiles, GROUP BY). ClickHouse was built for exactly this workload:

- **Columnar storage** — Observability queries scan specific fields across billions of rows. A columnar engine reads only the columns you need, not entire events. Aggregations over `duration` or `service` are orders of magnitude faster than row-oriented stores.
- **Compression** — Typical telemetry data compresses 10:1 to 100:1. Storage costs drop dramatically compared to Elasticsearch or SaaS vendors.
- **High-cardinality friendly** — Sparse indexing (not dense inverted indexes) means adding new tag dimensions doesn't bloat index size. `Map(String, String)` columns store unbounded attributes without schema migrations.
- **Standard SQL** — No proprietary query language. Joins, CTEs, window functions all work out of the box. Any BI tool can connect via JDBC or HTTP.
- **Proven at scale** — Petabyte-scale production deployments at companies like Uber, Cloudflare, and Microsoft. Not an unproven choice.

**Honest tradeoff:** Full-text search is weaker than Elasticsearch. ClickHouse is optimized for analytics, not grep. For most observability workflows — dashboards, alerting, top-N queries — that's the right tradeoff.

## Why ClickStack

[ClickStack](https://clickhouse.com/docs/use-cases/observability/clickstack) is ClickHouse's open-source observability stack, born from ClickHouse's [acquisition of HyperDX](https://www.hyperdx.io/blog/clickhouse-acquires-hyperdx-to-accelerate-the-future-of-open-source-observability) in March 2025. It bundles three components: ClickHouse (database) + [HyperDX](https://www.hyperdx.io/) (UI and API) + OTel Collector (ingestion).

- **What HyperDX adds** — Turns raw ClickHouse into a complete observability platform: correlated logs/traces/metrics in one UI, Lucene-style search, dashboards, alerts, and session replay. No SQL required for day-to-day use.
- **Unified signals** — Logs, traces, metrics, and session replays stored in the same ClickHouse instance. Correlate across signal types without switching tools or contexts.
- **Cost structure** — Open-source core, no per-seat or per-host fees. You pay for compute and storage only.
- **Single-container local mode** — The `hyperdx-local` image bundles everything (ClickHouse, MongoDB, OTel Collector, UI) into one container for instant sandbox environments. That's what this demo uses.
- **Programmatic dashboard API** — HyperDX exposes a REST API for dashboard CRUD, which is what makes AI-powered dashboard creation possible. Without a programmatic API, LLM-generated dashboards would require brittle UI automation.

## Why AI-Powered Dashboards

**Time-to-Value** — An hour of manual dashboard work becomes 60 seconds of prompting. Discover, generate, validate, deploy — all in one shot.

**Lowered Barrier** — No ClickHouse SQL expertise needed. PMs, junior devs, and support engineers can create production-quality dashboards from plain English.

**Frictionless Migration** — Screenshot-to-dashboard turns months of vendor migration into an afternoon. Take a screenshot of your Datadog/Grafana dashboard, paste it, and get a working replica on ClickHouse.

**Deterministic Validation vs. Hallucination** — The AI queries the database first to discover what actually exists, then validates its output against a 17-rule checklist. Hallucinated fields, wrong syntax, and invalid layouts are caught before deployment — not after.

---

## Reference

### Project Structure

```
.
├── setup.sh                      # One-command setup (idempotent)
├── docker-compose.yaml           # HyperDX Local container
├── .env.example                  # Environment template
├── requirements.txt              # Python dependencies
├── sample.tar.gz                 # E-commerce sample data (downloaded by setup.sh)
├── query_clickhouse.py           # CLI for querying ClickHouse
├── stream_data.py                # Live data streamer (timestamp rewriting)
├── deploy_checkout_dashboard.py  # Pre-built checkout dashboard
├── create_metrics_dashboard.py   # Pre-built metrics dashboard
├── cleanup_dashboards.sh         # Delete all dashboards
├── demo-script.md                # Step-by-step demo walkthrough
├── CLAUDE.md                     # Instructions for Claude Code
├── .claude/                      # Claude Code skills and references
└── tests/                        # Dashboard skill test cases
```

### Ports

| Port | Service |
|------|---------|
| 8080 | HyperDX UI |
| 8000 | HyperDX API |
| 8123 | ClickHouse HTTP |
| 4317 | OTLP gRPC |
| 4318 | OTLP HTTP |

Data is persisted in a Docker volume (`hyperdx-data`), so it survives container restarts.

### Querying ClickHouse

```bash
source .venv/bin/activate

python query_clickhouse.py --summary       # Data overview (counts, services, time range)
python query_clickhouse.py --services      # List all services
python query_clickhouse.py --attributes    # All string and number attribute keys
python query_clickhouse.py --query "SELECT count(*) FROM log_stream"

# For queries with special characters, use stdin:
python query_clickhouse.py --query - <<'SQL'
SELECT _service, count() as cnt
FROM log_stream
WHERE type = 'span'
GROUP BY _service
ORDER BY cnt DESC
SQL
```

### Streaming Options

`stream_data.py` replays `sample.tar.gz` in a loop, rewriting all timestamps to "now" so HyperDX shows continuously updating data.

```bash
python stream_data.py                  # Default: 10-min cycles, all signals
python stream_data.py --cycle 60       # Compress into 1-min cycles (good for demos)
python stream_data.py --rate 2.0       # 2x speed multiplier
python stream_data.py --traces         # Only stream traces
python stream_data.py --logs --metrics # Logs + metrics only
```

### Direct API Usage

Dashboards must be created via the HyperDX REST API — **never insert directly into MongoDB** (direct inserts assign the wrong team ID and dashboards silently won't appear).

```bash
# Get your API key
ACCESS_KEY=$(docker exec hyperdx-local mongo --quiet --eval \
  'db=db.getSiblingDB("hyperdx"); print(db.users.findOne({}).accessKey)')

# Create a dashboard
curl -X POST http://localhost:8000/api/v1/dashboards \
  -H "Authorization: Bearer ${ACCESS_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Dashboard",
    "charts": [{
      "id": "request-rate",
      "name": "Request Rate",
      "x": 0, "y": 0, "w": 6, "h": 3,
      "series": [{
        "type": "time",
        "table": "logs",
        "aggFn": "count",
        "where": "",
        "groupBy": ["service"]
      }],
      "asRatio": false
    }]
  }'
```

### Stopping

```bash
docker compose down        # Stop container (data persisted in volume)
docker compose down -v     # Stop and delete all data
```
