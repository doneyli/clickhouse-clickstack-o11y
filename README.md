# ClickStack Observability Demo

End-to-end observability demo using [ClickStack](https://clickhouse.com/docs/use-cases/observability/clickstack) (ClickHouse for o11y) with [HyperDX](https://www.hyperdx.io/) as the UI layer. Loads e-commerce sample data from the [OpenTelemetry Demo](https://opentelemetry.io/docs/demo/) — traces, logs, and metrics from ~15 microservices — into a single local container, then uses [Claude Code](https://claude.ai/code) to build dashboards via natural language.

## What's in the box

| Component | Description |
|---|---|
| **HyperDX Local** | Single Docker container running ClickHouse + MongoDB + OTel Collector + UI |
| **Sample data** | ~7 MB of traces, logs, and metrics from a simulated e-commerce store |
| **`stream_data.py`** | Replays sample data with live timestamps for continuous data flow |
| **`query_clickhouse.py`** | CLI tool for querying ClickHouse directly (summary, attributes, services, custom SQL) |
| **`deploy_checkout_dashboard.py`** | Deploys a pre-built Checkout Service dashboard via the HyperDX API |
| **`create_metrics_dashboard.py`** | Deploys a pre-built System Metrics dashboard |
| **`cleanup_dashboards.sh`** | Deletes all dashboards (useful between demo runs) |
| **Claude Code skill** | `/hyperdx-dashboard` — AI-powered dashboard creation from natural language prompts |

## Prerequisites

- Docker
- Python 3.9+
- [Claude Code](https://docs.anthropic.com/en/docs/claude-code/overview) (optional, for AI dashboard creation)

## Quick Start

```bash
git clone <repo-url> && cd clickstack-o11y
./setup.sh
```

`setup.sh` is idempotent and handles everything:

1. Creates `.env` from `.env.example`
2. Sets up a Python virtualenv and installs dependencies
3. Starts the HyperDX container via Docker Compose
4. Waits for HyperDX UI (port 8080) and ClickHouse (port 8123) to be ready
5. Bootstraps MongoDB with a team, user, API key, and data sources
6. Downloads and loads the e-commerce sample data via OTLP

Once complete, open **http://localhost:8080** to explore the data.

## Architecture

Everything runs inside a single Docker container (`hyperdx-local`):

```
sample.tar.gz ──► OTLP HTTP (:4318) ──► OTel Collector ──► ClickHouse ──► HyperDX UI (:8080)
                                                              │
                                                         log_stream (traces + logs)
                                                         metric_stream (metrics)
```

| Port | Service |
|---|---|
| 8080 | HyperDX UI |
| 8000 | HyperDX API |
| 8123 | ClickHouse HTTP |
| 4317 | OTLP gRPC |
| 4318 | OTLP HTTP |

Data is persisted in a Docker volume (`hyperdx-data`), so it survives container restarts.

## Querying Data

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

## Streaming Live Data

The sample data has static timestamps. To see data flow in HyperDX's Live Tail and make time-based charts work, run the streamer:

```bash
python stream_data.py                  # Default: 10-min cycles, all signals
python stream_data.py --cycle 60       # Compress into 1-min cycles (good for demos)
python stream_data.py --rate 2.0       # 2x speed multiplier
python stream_data.py --traces         # Only stream traces
python stream_data.py --logs --metrics # Logs + metrics only
```

This replays `sample.tar.gz` in a loop, rewriting all timestamps to "now" so HyperDX shows continuously updating data.

## Creating Dashboards

### Option 1: Pre-built dashboards

```bash
source .venv/bin/activate
python deploy_checkout_dashboard.py    # Checkout Service Overview (traces + metrics)
python create_metrics_dashboard.py     # System Metrics Overview
```

### Option 2: Claude Code (AI-powered)

With [Claude Code](https://docs.anthropic.com/en/docs/claude-code/overview) installed, use the built-in `/hyperdx-dashboard` skill:

```
> Create a dashboard for the checkout service. Show me everything important about it.
```

Claude discovers available services and attributes via ClickHouse, generates the dashboard JSON, validates it, and deploys via the API.

### Option 3: Direct API

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

### Cleanup

```bash
./cleanup_dashboards.sh          # Interactive: lists dashboards, asks for confirmation
./cleanup_dashboards.sh --force  # Non-interactive: deletes all
```

## Running a Demo

A typical demo flow:

```bash
# 1. Start services and stream live data
docker compose up -d
source .venv/bin/activate
python stream_data.py --cycle 60 &     # Background: stream data in 1-min cycles
python query_clickhouse.py --summary   # Show the audience what data exists

# 2. Deploy a pre-built dashboard or create one with Claude Code
python deploy_checkout_dashboard.py

# 3. Open http://localhost:8080 and explore
#    - Search tab: filter by service, see traces and logs
#    - Dashboards tab: view the deployed dashboard

# 4. Clean up between demos
./cleanup_dashboards.sh --force
```

See `demo-script.md` for a full scripted walkthrough with progressive complexity levels.

## Stopping

```bash
docker compose down        # Stop container (data persisted in volume)
docker compose down -v     # Stop and delete all data
```

## Project Structure

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
