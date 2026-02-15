#!/usr/bin/env bash
# =============================================================================
# Create LLM Observability Dashboard via MongoDB Direct Insert
# =============================================================================
#
# This is the WORKING approach for trace-based dashboards. The REST API v2
# does NOT support traces (otel_traces), only logs/events.
#
# Usage:
#   bash create_dashboard_mongo.sh --list       # List dashboards
#   bash create_dashboard_mongo.sh --create     # Create LLM Observability dashboard
#   bash create_dashboard_mongo.sh --recreate   # Delete existing + create new
#   bash create_dashboard_mongo.sh --delete ID  # Delete a dashboard by ID
# =============================================================================

set -euo pipefail

CONTAINER="hyperdx-local"
DASHBOARD_NAME="LLM Observability Dashboard"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

mongo_eval() {
    docker exec "$CONTAINER" mongo --quiet --eval "$1"
}

get_team_id() {
    mongo_eval 'db=db.getSiblingDB("hyperdx"); print(db.teams.findOne({})._id.str)'
}

get_traces_source_id() {
    mongo_eval 'db=db.getSiblingDB("hyperdx"); var s=db.sources.findOne({kind:"trace"}); print(s?s._id.str:"")'
}

list_sources() {
    echo "Available data sources:"
    mongo_eval '
        db = db.getSiblingDB("hyperdx");
        db.sources.find({}, {_id: 1, name: 1, kind: 1}).forEach(function(s) {
            print("  " + s.kind + ": " + s._id.str + " (" + s.name + ")");
        });
    '
}

# ---------------------------------------------------------------------------
# Dashboard operations
# ---------------------------------------------------------------------------

list_dashboards() {
    echo "Dashboards in HyperDX:"
    mongo_eval '
        db = db.getSiblingDB("hyperdx");
        db.dashboards.find({}, {_id: 1, name: 1, tags: 1}).forEach(function(d) {
            var tags = (d.tags || []).join(", ");
            print("  [" + d._id.str + "] " + d.name + (tags ? " [" + tags + "]" : ""));
        });
    '
}

delete_dashboard() {
    local id="$1"
    mongo_eval "
        db = db.getSiblingDB('hyperdx');
        var result = db.dashboards.deleteOne({_id: ObjectId('$id')});
        print(result.deletedCount > 0 ? 'Deleted.' : 'Not found.');
    "
}

delete_by_name() {
    mongo_eval "
        db = db.getSiblingDB('hyperdx');
        var result = db.dashboards.deleteMany({name: '$DASHBOARD_NAME'});
        print('Deleted ' + result.deletedCount + ' dashboard(s) named \"$DASHBOARD_NAME\"');
    "
}

create_dashboard() {
    local team_id
    local traces_source_id

    team_id=$(get_team_id)
    traces_source_id=$(get_traces_source_id)

    if [ -z "$team_id" ]; then
        echo "ERROR: Could not retrieve team ID from MongoDB"
        exit 1
    fi
    if [ -z "$traces_source_id" ]; then
        echo "ERROR: Could not retrieve traces source ID from MongoDB"
        list_sources
        exit 1
    fi

    echo "Team ID: $team_id"
    echo "Traces Source ID: $traces_source_id"
    echo ""

    # Build the dashboard JSON with 8 tiles
    local dashboard_json
    read -r -d '' dashboard_json << 'ENDJSON' || true
{
    "name": "LLM Observability Dashboard",
    "tags": ["llm", "observability", "auto-generated"],
    "tiles": [
        {
            "id": "total-llm-requests",
            "x": 0, "y": 0, "w": 3, "h": 2,
            "config": {
                "name": "Total LLM Requests",
                "source": "TRACES_SOURCE_PLACEHOLDER",
                "select": [{
                    "aggFn": "count",
                    "aggCondition": "",
                    "aggConditionLanguage": "sql",
                    "valueExpression": ""
                }],
                "where": "_string_attributes['gen_ai.request.model'] != '' AND type = 'span'",
                "whereLanguage": "sql",
                "displayType": "number",
                "granularity": "auto",
                "numberFormat": {
                    "factor": 1,
                    "output": "number",
                    "mantissa": 0,
                    "thousandSeparated": true,
                    "average": false,
                    "decimalBytes": false
                }
            }
        },
        {
            "id": "total-input-tokens",
            "x": 3, "y": 0, "w": 3, "h": 2,
            "config": {
                "name": "Total Input Tokens",
                "source": "TRACES_SOURCE_PLACEHOLDER",
                "select": [{
                    "aggFn": "sum",
                    "aggCondition": "",
                    "aggConditionLanguage": "sql",
                    "valueExpression": "_number_attributes['gen_ai.usage.input_tokens']"
                }],
                "where": "_string_attributes['gen_ai.request.model'] != '' AND type = 'span'",
                "whereLanguage": "sql",
                "displayType": "number",
                "granularity": "auto",
                "numberFormat": {
                    "factor": 1,
                    "output": "number",
                    "mantissa": 0,
                    "thousandSeparated": true,
                    "average": false,
                    "decimalBytes": false
                }
            }
        },
        {
            "id": "total-output-tokens",
            "x": 6, "y": 0, "w": 3, "h": 2,
            "config": {
                "name": "Total Output Tokens",
                "source": "TRACES_SOURCE_PLACEHOLDER",
                "select": [{
                    "aggFn": "sum",
                    "aggCondition": "",
                    "aggConditionLanguage": "sql",
                    "valueExpression": "_number_attributes['gen_ai.usage.output_tokens']"
                }],
                "where": "_string_attributes['gen_ai.request.model'] != '' AND type = 'span'",
                "whereLanguage": "sql",
                "displayType": "number",
                "granularity": "auto",
                "numberFormat": {
                    "factor": 1,
                    "output": "number",
                    "mantissa": 0,
                    "thousandSeparated": true,
                    "average": false,
                    "decimalBytes": false
                }
            }
        },
        {
            "id": "avg-latency-ms",
            "x": 9, "y": 0, "w": 3, "h": 2,
            "config": {
                "name": "Avg Latency (ms)",
                "source": "TRACES_SOURCE_PLACEHOLDER",
                "select": [{
                    "aggFn": "avg",
                    "aggCondition": "",
                    "aggConditionLanguage": "sql",
                    "valueExpression": "_duration"
                }],
                "where": "_string_attributes['gen_ai.request.model'] != '' AND type = 'span'",
                "whereLanguage": "sql",
                "displayType": "number",
                "granularity": "auto",
                "numberFormat": {
                    "factor": 1,
                    "output": "number",
                    "mantissa": 2,
                    "thousandSeparated": true,
                    "average": false,
                    "decimalBytes": false
                }
            }
        },
        {
            "id": "llm-requests-over-time",
            "x": 0, "y": 2, "w": 6, "h": 3,
            "config": {
                "name": "LLM Requests Over Time",
                "source": "TRACES_SOURCE_PLACEHOLDER",
                "select": [{
                    "aggFn": "count",
                    "aggCondition": "",
                    "aggConditionLanguage": "sql",
                    "valueExpression": ""
                }],
                "where": "_string_attributes['gen_ai.request.model'] != '' AND type = 'span'",
                "whereLanguage": "sql",
                "displayType": "line",
                "granularity": "auto"
            }
        },
        {
            "id": "token-usage-over-time",
            "x": 6, "y": 2, "w": 6, "h": 3,
            "config": {
                "name": "Token Usage Over Time",
                "source": "TRACES_SOURCE_PLACEHOLDER",
                "select": [
                    {
                        "aggFn": "sum",
                        "aggCondition": "",
                        "aggConditionLanguage": "sql",
                        "valueExpression": "_number_attributes['gen_ai.usage.input_tokens']"
                    },
                    {
                        "aggFn": "sum",
                        "aggCondition": "",
                        "aggConditionLanguage": "sql",
                        "valueExpression": "_number_attributes['gen_ai.usage.output_tokens']"
                    }
                ],
                "where": "_string_attributes['gen_ai.request.model'] != '' AND type = 'span'",
                "whereLanguage": "sql",
                "displayType": "stacked_bar",
                "granularity": "auto"
            }
        },
        {
            "id": "avg-latency-over-time",
            "x": 0, "y": 5, "w": 6, "h": 3,
            "config": {
                "name": "Avg Latency Over Time (ms)",
                "source": "TRACES_SOURCE_PLACEHOLDER",
                "select": [{
                    "aggFn": "avg",
                    "aggCondition": "",
                    "aggConditionLanguage": "sql",
                    "valueExpression": "_duration"
                }],
                "where": "_string_attributes['gen_ai.request.model'] != '' AND type = 'span'",
                "whereLanguage": "sql",
                "displayType": "line",
                "granularity": "auto"
            }
        },
        {
            "id": "max-latency-over-time",
            "x": 6, "y": 5, "w": 6, "h": 3,
            "config": {
                "name": "Max Latency Over Time (ms)",
                "source": "TRACES_SOURCE_PLACEHOLDER",
                "select": [{
                    "aggFn": "max",
                    "aggCondition": "",
                    "aggConditionLanguage": "sql",
                    "valueExpression": "_duration"
                }],
                "where": "_string_attributes['gen_ai.request.model'] != '' AND type = 'span'",
                "whereLanguage": "sql",
                "displayType": "line",
                "granularity": "auto"
            }
        }
    ]
}
ENDJSON

    # Replace source placeholder
    dashboard_json="${dashboard_json//TRACES_SOURCE_PLACEHOLDER/$traces_source_id}"

    # Escape for MongoDB shell (single quotes inside JS)
    # We pass the JSON directly into the mongo eval
    mongo_eval "
        db = db.getSiblingDB('hyperdx');
        var dashboard = $dashboard_json;
        dashboard.team = ObjectId('$team_id');
        dashboard.createdAt = new Date();
        dashboard.updatedAt = new Date();
        var result = db.dashboards.insertOne(dashboard);
        if (result.insertedId) {
            print('SUCCESS: Dashboard created with ID: ' + result.insertedId.str);
        } else {
            print('FAILED: Could not create dashboard');
        }
    "

    echo ""
    echo "View dashboard at: http://localhost:8080/dashboards"
}

# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

usage() {
    echo "Usage: $0 [--list|--create|--recreate|--delete ID]"
    echo ""
    echo "  --list       List all dashboards"
    echo "  --create     Create LLM Observability dashboard"
    echo "  --recreate   Delete existing + create new"
    echo "  --delete ID  Delete a dashboard by ObjectId"
    echo ""
    echo "NOTE: This uses MongoDB direct insert (config format) which supports"
    echo "      ALL data sources including traces. The REST API v2 does NOT"
    echo "      support traces -- use this script for LLM observability dashboards."
}

case "${1:-}" in
    --list)
        list_dashboards
        ;;
    --create)
        echo "Creating $DASHBOARD_NAME..."
        echo ""
        create_dashboard
        ;;
    --recreate)
        echo "Recreating $DASHBOARD_NAME..."
        delete_by_name
        echo ""
        create_dashboard
        ;;
    --delete)
        if [ -z "${2:-}" ]; then
            echo "ERROR: --delete requires a dashboard ID"
            exit 1
        fi
        delete_dashboard "$2"
        ;;
    *)
        usage
        ;;
esac
