#!/usr/bin/env bash
# =============================================================================
# Import pre-built dashboard JSON files into HyperDX via MongoDB
# =============================================================================
#
# Usage:
#   bash dashboards/import_dashboards.sh                    # Import all
#   bash dashboards/import_dashboards.sh llm-observability  # Import one
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONTAINER="hyperdx-local"

# ---------------------------------------------------------------------------
# Get IDs from MongoDB
# ---------------------------------------------------------------------------

get_team_id() {
    docker exec "$CONTAINER" mongo --quiet --eval \
        'db=db.getSiblingDB("hyperdx"); print(db.teams.findOne({})._id.str)'
}

get_traces_source_id() {
    docker exec "$CONTAINER" mongo --quiet --eval \
        'db=db.getSiblingDB("hyperdx"); var s=db.sources.findOne({kind:"trace"}); print(s?s._id.str:"")'
}

# ---------------------------------------------------------------------------
# Import a single dashboard JSON file
# ---------------------------------------------------------------------------

import_dashboard() {
    local json_file="$1"
    local team_id="$2"
    local traces_source_id="$3"

    if [ ! -f "$json_file" ]; then
        echo "ERROR: File not found: $json_file"
        return 1
    fi

    local dashboard_name
    dashboard_name=$(python3 -c "import json; print(json.load(open('$json_file'))['name'])")

    echo "Importing: $dashboard_name"
    echo "  Source: $json_file"

    # Read JSON and replace placeholders
    local dashboard_json
    dashboard_json=$(sed "s/{{TRACES_SOURCE_ID}}/$traces_source_id/g" "$json_file")

    # Insert via MongoDB
    docker exec "$CONTAINER" mongo --quiet --eval "
        db = db.getSiblingDB('hyperdx');
        var dashboard = $dashboard_json;
        dashboard.team = ObjectId('$team_id');
        dashboard.createdAt = new Date();
        dashboard.updatedAt = new Date();
        dashboard.__v = 0;
        var result = db.dashboards.insertOne(dashboard);
        if (result.insertedId) {
            print('  SUCCESS: ID = ' + result.insertedId.str);
        } else {
            print('  FAILED');
        }
    "
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

echo "Retrieving HyperDX configuration..."
team_id=$(get_team_id)
traces_source_id=$(get_traces_source_id)

if [ -z "$team_id" ] || [ -z "$traces_source_id" ]; then
    echo "ERROR: Could not retrieve team ID or traces source ID"
    echo "  Is HyperDX running? Try: docker compose up -d"
    exit 1
fi

echo "  Team ID: $team_id"
echo "  Traces Source ID: $traces_source_id"
echo ""

# Determine which dashboards to import
if [ -n "${1:-}" ]; then
    # Import specific dashboard
    import_dashboard "$SCRIPT_DIR/$1.json" "$team_id" "$traces_source_id"
else
    # Import all JSON files
    for json_file in "$SCRIPT_DIR"/*.json; do
        import_dashboard "$json_file" "$team_id" "$traces_source_id"
        echo ""
    done
fi

echo ""
echo "View dashboards at: http://localhost:8080/dashboards"
