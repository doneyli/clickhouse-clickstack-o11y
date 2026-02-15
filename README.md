# HyperDX AI Dashboard Builder

Build and manage HyperDX observability dashboards for LLM workloads. Includes a demo data generator, pre-built dashboards, and an AI-powered dashboard builder that uses Claude to analyze your ClickHouse data and auto-generate dashboard definitions.

## Quick Start

```bash
cd clickhouse-clickstack-o11y
./setup.sh
```

Then visit [http://localhost:8080](http://localhost:8080) to see HyperDX with dashboards and demo data.

## Architecture

```
                    ┌─────────────────────────────────────────────┐
                    │          HyperDX Local Container            │
 OTLP Traces ──────►  OTEL Collector ──► ClickHouse (log_stream) │
 (port 4318)        │                                             │
                    │  MongoDB (dashboards, config)               │
                    │  HyperDX UI (port 8080)                     │
                    │  HyperDX API (port 8000)                    │
                    └─────────────────────────────────────────────┘
                           ▲                    ▲
                           │                    │
              Dashboard creation          SQL queries
              (MongoDB insert)        (ClickHouse HTTP 8123)
                           │                    │
                    ┌──────┴────────────────────┴──────┐
                    │        AI Dashboard Builder       │
                    │  1. Discover (ClickHouse queries) │
                    │  2. Analyze  (Claude API)         │
                    │  3. Generate (JSON dashboard)     │
                    │  4. Create   (MongoDB insert)     │
                    └──────────────────────────────────┘
```

## Usage

### Generate Demo Data

```bash
python generate_demo_data.py                          # 100 traces (default)
python generate_demo_data.py --count 500              # 500 traces
python generate_demo_data.py --services text-to-sql   # one service only
python generate_demo_data.py --error-rate 0.1         # 10% error rate
```

Generates synthetic LLM observability traces across three services (text-to-sql, vector-rag, chatbot) using OpenTelemetry gen_ai.* semantic conventions.

### Query ClickHouse

```bash
python query_clickhouse.py --summary                  # Data summary
python query_clickhouse.py --attributes               # gen_ai.* attributes
python query_clickhouse.py --services                 # All services
python query_clickhouse.py --query "SELECT count(*) FROM log_stream WHERE type='span'"
```

### Create Dashboards via MongoDB (Recommended)

```bash
bash create_dashboard_mongo.sh --create               # Create LLM dashboard
bash create_dashboard_mongo.sh --list                  # List dashboards
bash create_dashboard_mongo.sh --recreate              # Delete + recreate
bash create_dashboard_mongo.sh --delete <ID>           # Delete by ID
```

### Import Pre-built Dashboards

```bash
bash dashboards/import_dashboards.sh                   # Import all
bash dashboards/import_dashboards.sh llm-observability # Import one
bash dashboards/import_dashboards.sh cost-tracking     # Import cost dashboard
```

### Create Dashboards via REST API (Logs Only)

```bash
python create_dashboard_api.py --create               # Create sample log dashboard
python create_dashboard_api.py --list                  # List dashboards
```

> **Note:** The REST API v2 only supports logs/events, NOT traces. Use the MongoDB approach for LLM observability dashboards.

### AI Dashboard Builder

```bash
python ai_dashboard_builder.py                         # Auto-discover and create
python ai_dashboard_builder.py --dry-run               # Generate JSON only
python ai_dashboard_builder.py --prompt "Focus on cost" # Custom focus
python ai_dashboard_builder.py --model claude-3-5-haiku-20241022
```

Requires `ANTHROPIC_API_KEY` in `.env`.

## How the AI Dashboard Builder Works

1. **Discover**: Queries ClickHouse to catalog tables, gen_ai.* attributes, services, models, and data distribution
2. **Analyze**: Sends the schema/data summary to Claude with a detailed system prompt containing tile format rules
3. **Generate**: Claude returns a JSON dashboard definition following HyperDX's internal config format
4. **Validate**: Checks the generated JSON against known rules (whereLanguage, aggFn, displayType, etc.)
5. **Create**: Inserts the dashboard into HyperDX via MongoDB direct insert

## Dashboard API Reference

### Approach 1: REST API v2 (`/api/v2/dashboards`)

- Bearer token auth
- Uses `series` format with `dataSource: "events"` or `"metrics"`
- **Does NOT support traces (otel_traces)**
- Suitable for log and metric dashboards only

### Approach 2: MongoDB Direct Insert (Recommended)

- Uses `config` format (what the UI uses internally)
- **Supports ALL data sources including traces**
- Must use `whereLanguage: "sql"` (Lucene silently fails on `_string_attributes`)
- Requires team ID and source IDs from MongoDB

## Known Gotchas

1. **External API v2 does NOT support traces**: `dataSource: "events"` maps to logs, NOT traces. Must use MongoDB direct insert for trace dashboards.
2. **HyperDX v1 uses `log_stream` table**: All spans, logs, and events go into `log_stream`. Filter spans with `type = 'span'`.
3. **Attribute maps**: String attributes in `_string_attributes` (Map(String, String)), numeric in `_number_attributes` (Map(String, Float64)).
4. **Lucene fails on attributes**: `whereLanguage: "lucene"` silently returns no data for `_string_attributes`. MUST use `whereLanguage: "sql"`.
5. **p50/p95/p99 not supported**: Config format tiles don't translate percentile aggFn. Use `avg`/`max` or custom `valueExpression` with `quantile()`.
6. **groupBy not supported in config format**: Create separate tiles instead.
7. **numberFormat required**: Without it, number tiles show raw unformatted values.
8. **`_duration` is already in milliseconds**: No conversion needed (it's a materialized Float64 column).
9. **MongoDB shell is `mongo` not `mongosh`**: HyperDX Local uses legacy shell.
10. **API key retrieval**: Auth skipped in Local mode but API still expects Bearer token. Get from MongoDB: `db.users.findOne({}).accessKey`

## Troubleshooting

**HyperDX won't start:**
```bash
docker logs hyperdx-local
docker compose down -v && docker compose up -d  # Reset
```

**No data in dashboards:**
```bash
python generate_demo_data.py --count 100
python query_clickhouse.py --summary  # Verify data is ingested
```

**ClickHouse connection fails:**
```bash
curl http://localhost:8123/ping  # Should return "Ok."
```

**Dashboard tiles show no data:**
- Verify `whereLanguage: "sql"` (not "lucene")
- Check the time range in the HyperDX UI (traces spread across last 24h)
- Verify source ID matches traces: `bash create_dashboard_mongo.sh --list`

## Project Structure

```
clickhouse-clickstack-o11y/
├── README.md
├── .gitignore
├── .env.example
├── docker-compose.yaml
├── setup.sh                          # One-command setup
├── requirements.txt                  # Python deps
├── generate_demo_data.py             # Demo LLM trace generator
├── create_dashboard_api.py           # Dashboard creation via REST API v2
├── create_dashboard_mongo.sh         # Dashboard creation via MongoDB
├── ai_dashboard_builder.py           # AI-powered dashboard builder
├── query_clickhouse.py               # ClickHouse query utility
├── dashboards/
│   ├── llm-observability.json        # Pre-built dashboard definition
│   ├── cost-tracking.json            # Pre-built cost dashboard
│   └── import_dashboards.sh          # Import script
└── sql/
    └── llm-observability-queries.sql # Reference SQL queries
```
