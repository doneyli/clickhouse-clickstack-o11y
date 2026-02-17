# ClickStack Sample Data Demo

Loads the [ClickStack e-commerce sample data](https://clickhouse.com/docs/use-cases/observability/clickstack/getting-started/sample-data) into a local [HyperDX](https://www.hyperdx.io/) instance for exploration and dashboard building.

The sample data comes from the [OpenTelemetry Demo](https://opentelemetry.io/docs/demo/) — a simulated e-commerce store with microservices generating traces, logs, and metrics.

## Prerequisites

- Docker
- Python 3.9+

## Quick Start

```bash
./setup.sh
```

This will:
1. Create a `.env` file from `.env.example`
2. Set up a Python virtual environment and install dependencies
3. Start the HyperDX container via Docker Compose
4. Wait for HyperDX UI and ClickHouse to be ready
5. Bootstrap MongoDB (team, user, API key)
6. Download and load the e-commerce sample data via OTLP

Once complete, open http://localhost:8080 to explore the data.

## Querying Data

```bash
source .venv/bin/activate
python query_clickhouse.py --summary      # Data overview
python query_clickhouse.py --attributes   # All attribute keys
python query_clickhouse.py --services     # All services
python query_clickhouse.py --query "SELECT count(*) FROM log_stream"
```

## Creating Dashboards

Use the `/hyperdx-dashboard` Claude Code skill to create dashboards from the sample data. It discovers available data, generates dashboard JSON, validates it, and deploys via the HyperDX API.
