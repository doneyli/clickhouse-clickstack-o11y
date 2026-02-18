#!/usr/bin/env bash
# =============================================================================
# One-command setup for ClickStack Sample Data Demo
# =============================================================================
#
# Downloads the ClickStack e-commerce sample data and loads it into ClickStack.
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

echo "[1/5] Checking .env file..."
if [ ! -f .env ]; then
    cp .env.example .env
    echo "  Created .env from .env.example"
else
    echo "  .env already exists"
fi

# ---------------------------------------------------------------------------
# Step 2: Python virtual environment
# ---------------------------------------------------------------------------

echo "[2/5] Setting up Python virtual environment..."
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

echo "[3/5] Starting ClickStack via Docker Compose..."
docker compose up -d
echo "  Container started"

# ---------------------------------------------------------------------------
# Step 4: Wait for services
# ---------------------------------------------------------------------------

echo "[4/5] Waiting for ClickStack UI (port 8080) and ClickHouse (port 8123)..."
MAX_WAIT=120
WAITED=0
while ! curl -sf http://localhost:8080 > /dev/null 2>&1; do
    if [ $WAITED -ge $MAX_WAIT ]; then
        echo "  ERROR: ClickStack UI did not become available within ${MAX_WAIT}s"
        echo "  Check logs: docker logs clickstack-local"
        exit 1
    fi
    sleep 2
    WAITED=$((WAITED + 2))
    if [ $((WAITED % 10)) -eq 0 ]; then
        echo "  Still waiting... (${WAITED}s)"
    fi
done
echo "  ClickStack UI is up (took ${WAITED}s)"

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
# Step 5: Download and load sample data
# ---------------------------------------------------------------------------

echo "[5/5] Loading ClickStack e-commerce sample data..."

# Download if not already present
if [ ! -f sample.tar.gz ]; then
    echo "  Downloading sample.tar.gz..."
    curl -O https://storage.googleapis.com/hyperdx/sample.tar.gz
    echo "  Downloaded"
else
    echo "  sample.tar.gz already exists, skipping download"
fi

echo "  Sending data to OTLP endpoint (this may take a few minutes)..."
for filename in $(tar -tf sample.tar.gz); do
    endpoint="http://localhost:4318/v1/${filename%.json}"
    echo "  Loading ${filename%.json}..."
    tar -xOf sample.tar.gz "$filename" | while read -r line; do
        printf '%s\n' "$line" | curl -s -o /dev/null -X POST "$endpoint" \
            -H "Content-Type: application/json" \
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
echo "  ClickStack UI:     http://localhost:8080"
echo "  ClickStack API:    http://localhost:8000"
echo "  ClickHouse HTTP:   http://localhost:8123"
echo "  OTLP HTTP:         http://localhost:4318"
echo ""
echo "  Next steps:"
echo "    1. Open http://localhost:8080 in your browser"
echo "    2. Go to Search to explore the e-commerce sample data"
echo "    3. Use /hyperdx-dashboard skill to create dashboards"
echo ""
