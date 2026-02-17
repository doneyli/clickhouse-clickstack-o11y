#!/usr/bin/env bash
# =============================================================================
# One-command setup for ClickStack Sample Data Demo
# =============================================================================
#
# Downloads the ClickStack e-commerce sample data and loads it into HyperDX.
# This script is idempotent -- safe to run multiple times.
#
# Usage:
#   ./setup.sh
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "============================================================"
echo "  ClickStack Sample Data Demo — Setup"
echo "============================================================"
echo ""

# ---------------------------------------------------------------------------
# Step 1: .env file
# ---------------------------------------------------------------------------

echo "[1/6] Checking .env file..."
if [ ! -f .env ]; then
    cp .env.example .env
    echo "  Created .env from .env.example"
else
    echo "  .env already exists"
fi

# ---------------------------------------------------------------------------
# Step 2: Python virtual environment
# ---------------------------------------------------------------------------

echo "[2/6] Setting up Python virtual environment..."
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

echo "[3/6] Starting HyperDX via Docker Compose..."
docker compose up -d
echo "  Container started"

# ---------------------------------------------------------------------------
# Step 4: Wait for services
# ---------------------------------------------------------------------------

echo "[4/6] Waiting for HyperDX UI (port 8080) and ClickHouse (port 8123)..."
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
# Step 5: Bootstrap MongoDB (team, user, API key, traces source)
# ---------------------------------------------------------------------------

echo "[5/6] Bootstrapping HyperDX team, user, and source..."
sleep 3

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
# Step 6: Download and load sample data
# ---------------------------------------------------------------------------

echo "[6/6] Loading ClickStack e-commerce sample data..."

# Download if not already present
if [ ! -f sample.tar.gz ]; then
    echo "  Downloading sample.tar.gz..."
    curl -O https://storage.googleapis.com/hyperdx/sample.tar.gz
    echo "  Downloaded"
else
    echo "  sample.tar.gz already exists, skipping download"
fi

# Use the API key for ingestion auth
INGEST_KEY="${API_KEY:-}"
if [ -z "$INGEST_KEY" ]; then
    # Try to read from .env
    INGEST_KEY=$(grep '^HYPERDX_API_KEY=' .env | cut -d= -f2)
fi

echo "  Sending data to OTLP endpoint (this may take a few minutes)..."
for filename in $(tar -tf sample.tar.gz); do
    endpoint="http://localhost:4318/v1/${filename%.json}"
    echo "  Loading ${filename%.json}..."
    tar -xOf sample.tar.gz "$filename" | while read -r line; do
        printf '%s\n' "$line" | curl -s -o /dev/null -X POST "$endpoint" \
            -H "Content-Type: application/json" \
            -H "authorization: ${INGEST_KEY}" \
            --data-binary @-
    done
done
echo "  Sample data loaded"

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
echo "    2. Go to Search to explore the e-commerce sample data"
echo "    3. Query ClickHouse:  python query_clickhouse.py --summary"
echo "    4. Use /hyperdx-dashboard skill to create dashboards"
echo ""
