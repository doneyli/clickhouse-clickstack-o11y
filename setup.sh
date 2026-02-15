#!/usr/bin/env bash
# =============================================================================
# One-command setup for HyperDX AI Dashboard Builder
# =============================================================================
#
# This script is idempotent -- safe to run multiple times.
#
# Usage:
#   ./setup.sh
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "============================================================"
echo "  HyperDX AI Dashboard Builder -- Setup"
echo "============================================================"
echo ""

# ---------------------------------------------------------------------------
# Step 1: .env file
# ---------------------------------------------------------------------------

echo "[1/8] Checking .env file..."
if [ ! -f .env ]; then
    cp .env.example .env
    echo "  Created .env from .env.example"
else
    echo "  .env already exists"
fi

# ---------------------------------------------------------------------------
# Step 2: Python virtual environment
# ---------------------------------------------------------------------------

echo "[2/8] Setting up Python virtual environment..."
if [ ! -d .venv ]; then
    python3 -m venv .venv
    echo "  Created .venv"
else
    echo "  .venv already exists"
fi
source .venv/bin/activate
pip install -q -r requirements.txt
echo "  Dependencies installed"

# ---------------------------------------------------------------------------
# Step 3: Docker Compose
# ---------------------------------------------------------------------------

echo "[3/8] Starting HyperDX via Docker Compose..."
docker compose up -d
echo "  Container started"

# ---------------------------------------------------------------------------
# Step 4: Wait for HyperDX UI
# ---------------------------------------------------------------------------

echo "[4/8] Waiting for HyperDX UI (port 8080)..."
MAX_WAIT=120
WAITED=0
while ! curl -sf http://localhost:8080 > /dev/null 2>&1; do
    if [ $WAITED -ge $MAX_WAIT ]; then
        echo "  ERROR: HyperDX UI did not become available within ${MAX_WAIT}s"
        echo "  Check logs: docker logs hyperdx-local"
        exit 1
    fi
    sleep 2
    WAITED=$((WAITED + 2))
    if [ $((WAITED % 10)) -eq 0 ]; then
        echo "  Still waiting... (${WAITED}s)"
    fi
done
echo "  HyperDX UI is up (took ${WAITED}s)"

# ---------------------------------------------------------------------------
# Step 5: Wait for ClickHouse
# ---------------------------------------------------------------------------

echo "[5/8] Waiting for ClickHouse (port 8123)..."
WAITED=0
while ! curl -sf http://localhost:8123/ping > /dev/null 2>&1; do
    if [ $WAITED -ge $MAX_WAIT ]; then
        echo "  ERROR: ClickHouse did not become available within ${MAX_WAIT}s"
        exit 1
    fi
    sleep 2
    WAITED=$((WAITED + 2))
done
echo "  ClickHouse is up"

# ---------------------------------------------------------------------------
# Step 6: Retrieve API key
# ---------------------------------------------------------------------------

echo "[6/8] Bootstrapping HyperDX team, user, and source..."
# Wait a moment for MongoDB to be ready
sleep 3

# Bootstrap team, user, and traces source (idempotent)
API_KEY=$(docker exec hyperdx-local mongo --quiet --eval '
db = db.getSiblingDB("hyperdx");

// Ensure team exists
var team = db.teams.findOne({});
if (!team) {
    db.teams.insertOne({ name: "Local Team", createdAt: new Date(), updatedAt: new Date() });
    team = db.teams.findOne({});
}

// Ensure user exists with API key
var user = db.users.findOne({});
if (!user) {
    var key = team._id.str + "0000000000000000";
    db.users.insertOne({
        email: "local@hyperdx.io",
        name: "Local User",
        team: team._id,
        accessKey: key,
        createdAt: new Date(),
        updatedAt: new Date()
    });
    user = db.users.findOne({});
}

// Ensure traces source exists
var src = db.sources.findOne({kind: "trace"});
if (!src) {
    db.sources.insertOne({
        name: "Backend Traces",
        kind: "trace",
        team: team._id,
        from: { format: "internal", databaseName: "default", tableName: "log_stream" },
        createdAt: new Date(),
        updatedAt: new Date()
    });
}

print(user.accessKey);
' 2>/dev/null || echo "")

if [ -n "$API_KEY" ] && [ "$API_KEY" != "undefined" ] && [ "$API_KEY" != "null" ]; then
    # Update .env with the API key (only if not already set)
    if grep -q "^HYPERDX_API_KEY=$" .env; then
        sed -i.bak "s/^HYPERDX_API_KEY=$/HYPERDX_API_KEY=$API_KEY/" .env && rm -f .env.bak
        echo "  API key saved to .env: $API_KEY"
    else
        echo "  API key already set in .env"
    fi
    echo "  Team, user, and traces source ready"
else
    echo "  WARNING: Could not bootstrap MongoDB (may need manual setup)"
fi

# ---------------------------------------------------------------------------
# Step 7: Generate demo traces
# ---------------------------------------------------------------------------

echo "[7/8] Generating demo traces..."
python generate_demo_data.py --count 100
echo "  Demo traces generated"

# ---------------------------------------------------------------------------
# Step 8: Create default dashboards
# ---------------------------------------------------------------------------

echo "[8/8] Creating default dashboards..."
# Wait for traces to be ingested
sleep 5
bash create_dashboard_mongo.sh --create
bash dashboards/import_dashboards.sh cost-tracking
echo "  Dashboards created"

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

echo ""
echo "============================================================"
echo "  SETUP COMPLETE!"
echo "============================================================"
echo ""
echo "  HyperDX UI:        http://localhost:8080"
echo "  HyperDX API:       http://localhost:8000"
echo "  ClickHouse HTTP:   http://localhost:8123"
echo "  OTLP HTTP:         http://localhost:4318"
echo ""
echo "  Next steps:"
echo "    1. Open http://localhost:8080 in your browser"
echo "    2. Go to Dashboards to see the auto-created dashboards"
echo "    3. Generate more data:  python generate_demo_data.py --count 500"
echo "    4. Query ClickHouse:    python query_clickhouse.py --summary"
echo "    5. AI Dashboard Builder: python ai_dashboard_builder.py --dry-run"
echo ""
echo "  To use the AI Dashboard Builder, set ANTHROPIC_API_KEY in .env"
echo ""
