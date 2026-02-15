#!/usr/bin/env python3
"""
AI-Powered Dashboard Builder for HyperDX.

Uses Claude to analyze ClickHouse data and auto-generate dashboard definitions.
Pipeline: Discover -> Analyze -> Generate -> Create

Usage:
    python ai_dashboard_builder.py                            # Auto-discover and create
    python ai_dashboard_builder.py --dry-run                  # Generate JSON only
    python ai_dashboard_builder.py --prompt "Focus on cost"   # Custom focus
    python ai_dashboard_builder.py --model claude-3-5-haiku-20241022
"""

import argparse
import json
import os
import subprocess
import sys

import anthropic
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CONTAINER = "hyperdx-local"

CLAUDE_SYSTEM_PROMPT = """You are an expert at creating HyperDX dashboard definitions.
You will be given a summary of data available in a ClickHouse-backed observability platform
and you must generate a JSON dashboard definition.

## DASHBOARD TILE FORMAT

Each tile must use this exact structure:
{
    "id": "unique-kebab-case-id",
    "x": <0-11>, "y": <row>, "w": <1-12>, "h": <1-6>,
    "config": {
        "name": "Human Readable Name",
        "source": "{{TRACES_SOURCE_ID}}",
        "select": [{
            "aggFn": "<aggregation_function>",
            "aggCondition": "",
            "aggConditionLanguage": "sql",
            "valueExpression": "<field_expression>"
        }],
        "where": "<sql_filter> AND type = 'span'",
        "whereLanguage": "sql",
        "displayType": "<chart_type>",
        "granularity": "auto"
    }
}

## RULES (CRITICAL - VIOLATIONS WILL BREAK THE DASHBOARD)

1. whereLanguage MUST be "sql" -- never "lucene"
2. where clauses use ClickHouse SQL: _string_attributes['field.name'] != '' AND type = 'span'
   - ALWAYS include type = 'span' in WHERE clauses
3. aggFn must be one of: count, sum, avg, min, max, count_distinct, last_value
   - DO NOT use p50, p95, p99 (they do not work)
4. displayType must be one of: number, line, stacked_bar, bar, area
5. valueExpression for count must be "" (empty string)
6. _duration is already in milliseconds. Use "_duration" directly (no division needed).
7. String attributes: _string_attributes['field'] (Map(String, String))
   Numeric attributes: _number_attributes['field'] (Map(String, Float64))
   - Token counts are numeric: _number_attributes['gen_ai.usage.input_tokens']
   - Model names are strings: _string_attributes['gen_ai.request.model']
   - Duration: "_duration" (already in ms, Float64)
   - For string values used in math, use toFloat64OrZero()
8. For number displayType, include numberFormat:
   {"factor":1,"output":"number","mantissa":2,"thousandSeparated":true,"average":false,"decimalBytes":false}
9. Grid is 12 columns wide. Tiles should not overlap.
10. source must always be "{{TRACES_SOURCE_ID}}" (placeholder replaced at import time)
11. Multiple items in "select" array for multi-series charts.
12. DO NOT use groupBy (not supported in config format).

## OUTPUT FORMAT

Return ONLY a valid JSON object:
{
    "name": "Dashboard Name",
    "tags": ["tag1", "tag2"],
    "tiles": [ ...tile objects... ]
}

No markdown, no code fences, just raw JSON."""


# ---------------------------------------------------------------------------
# ClickHouse Discovery
# ---------------------------------------------------------------------------

def get_clickhouse_client():
    """Create a ClickHouse client."""
    import clickhouse_connect

    ch_url = os.getenv("CLICKHOUSE_URL", "http://localhost:8123")
    host = ch_url.replace("http://", "").replace("https://", "").split(":")[0]
    port = int(ch_url.split(":")[-1]) if ":" in ch_url.split("//")[-1] else 8123

    # Try default user first
    try:
        client = clickhouse_connect.get_client(host=host, port=port, username="default", password="")
        client.query("SELECT 1")
        return client
    except Exception:
        pass

    # Fallback to api/api
    try:
        client = clickhouse_connect.get_client(host=host, port=port, username="api", password="api")
        client.query("SELECT 1")
        return client
    except Exception as e:
        print(f"ERROR: Could not connect to ClickHouse: {e}")
        sys.exit(1)


def discover_data() -> dict:
    """Query ClickHouse to catalog available data."""
    print("Step 1/4: Discovering data in ClickHouse...")
    client = get_clickhouse_client()
    discovery = {}

    # Tables
    result = client.query("SHOW TABLES")
    discovery["tables"] = [row[0] for row in result.result_rows]
    print(f"  Found {len(discovery['tables'])} tables: {', '.join(discovery['tables'])}")

    # gen_ai.* attributes
    try:
        result = client.query("""
            SELECT DISTINCT arrayJoin(_string_attributes.keys) as attr_key
            FROM log_stream
            WHERE attr_key LIKE 'gen_ai.%' AND type = 'span'
            ORDER BY attr_key
        """)
        discovery["gen_ai_attributes"] = [row[0] for row in result.result_rows]
        print(f"  Found {len(discovery['gen_ai_attributes'])} gen_ai.* attributes")
    except Exception:
        discovery["gen_ai_attributes"] = []
        print("  No gen_ai.* attributes found")

    # Services
    try:
        result = client.query("SELECT DISTINCT _service FROM log_stream WHERE type = 'span' ORDER BY _service")
        discovery["services"] = [row[0] for row in result.result_rows]
        print(f"  Found {len(discovery['services'])} services: {', '.join(discovery['services'])}")
    except Exception:
        discovery["services"] = []

    # Models
    try:
        result = client.query("""
            SELECT DISTINCT _string_attributes['gen_ai.request.model'] as model
            FROM log_stream WHERE model != '' AND type = 'span'
            ORDER BY model
        """)
        discovery["models"] = [row[0] for row in result.result_rows]
        print(f"  Found {len(discovery['models'])} models: {', '.join(discovery['models'])}")
    except Exception:
        discovery["models"] = []

    # Data distribution
    try:
        result = client.query("""
            SELECT
                count(*) as total_traces,
                countIf(_string_attributes['gen_ai.request.model'] != '') as llm_traces,
                min(timestamp) as earliest,
                max(timestamp) as latest,
                count(DISTINCT _service) as services,
                count(DISTINCT _string_attributes['gen_ai.request.model']) as models
            FROM log_stream
            WHERE type = 'span'
        """)
        if result.result_rows:
            row = result.result_rows[0]
            discovery["data_distribution"] = {
                "total_traces": row[0],
                "llm_traces": row[1],
                "earliest": str(row[2]),
                "latest": str(row[3]),
                "services": row[4],
                "models": row[5],
            }
            print(f"  Total traces: {row[0]:,}, LLM traces: {row[1]:,}")
    except Exception:
        discovery["data_distribution"] = {}

    # Per-model stats
    try:
        result = client.query("""
            SELECT
                _string_attributes['gen_ai.request.model'] as model,
                count(*) as cnt,
                avg(_number_attributes['gen_ai.usage.input_tokens']) as avg_input,
                avg(_number_attributes['gen_ai.usage.output_tokens']) as avg_output,
                avg(_duration) as avg_latency_ms
            FROM log_stream
            WHERE _string_attributes['gen_ai.request.model'] != '' AND type = 'span'
            GROUP BY model
        """)
        discovery["model_stats"] = [
            {
                "model": row[0],
                "count": row[1],
                "avg_input_tokens": round(row[2], 1),
                "avg_output_tokens": round(row[3], 1),
                "avg_latency_ms": round(row[4], 1),
            }
            for row in result.result_rows
        ]
    except Exception:
        discovery["model_stats"] = []

    return discovery


# ---------------------------------------------------------------------------
# Claude Analysis & Generation
# ---------------------------------------------------------------------------

def generate_dashboard(discovery: dict, custom_prompt: str = "", model: str = "claude-sonnet-4-20250514") -> dict:
    """Send discovery data to Claude and get a dashboard definition."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY not set in .env")
        print("  Get your key at: https://console.anthropic.com/")
        sys.exit(1)

    print(f"\nStep 2/4: Analyzing data with Claude ({model})...")

    # Build the user prompt
    user_prompt = f"""Here is a summary of the data available in the ClickHouse-backed HyperDX observability platform:

## Available Tables
{json.dumps(discovery.get('tables', []), indent=2)}

## gen_ai.* Attributes Found
{json.dumps(discovery.get('gen_ai_attributes', []), indent=2)}

## Services
{json.dumps(discovery.get('services', []), indent=2)}

## Models
{json.dumps(discovery.get('models', []), indent=2)}

## Data Distribution
{json.dumps(discovery.get('data_distribution', {}), indent=2)}

## Per-Model Statistics
{json.dumps(discovery.get('model_stats', []), indent=2)}

Please create a comprehensive LLM observability dashboard with 8-12 tiles covering:
- Key metrics (request counts, token usage, latency)
- Time-series charts (requests over time, token usage over time, latency trends)
- Cost analysis if token data is available
- Mix of number tiles and chart tiles for a well-balanced layout"""

    if custom_prompt:
        user_prompt += f"\n\nAdditional requirements: {custom_prompt}"

    client = anthropic.Anthropic(api_key=api_key)

    print("  Sending data summary to Claude...")
    response = client.messages.create(
        model=model,
        max_tokens=8192,
        system=CLAUDE_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )

    # Extract the response text
    response_text = response.content[0].text.strip()

    # Try to parse JSON (handle potential markdown fences)
    if response_text.startswith("```"):
        # Strip markdown code fences
        lines = response_text.split("\n")
        start = 1 if lines[0].startswith("```") else 0
        end = len(lines) - 1 if lines[-1].strip() == "```" else len(lines)
        response_text = "\n".join(lines[start:end])

    try:
        dashboard = json.loads(response_text)
    except json.JSONDecodeError as e:
        print(f"ERROR: Claude returned invalid JSON: {e}")
        print(f"Response text:\n{response_text[:500]}...")
        sys.exit(1)

    tile_count = len(dashboard.get("tiles", []))
    print(f"  Generated dashboard: \"{dashboard.get('name', 'Untitled')}\" with {tile_count} tiles")

    # Token usage
    input_tokens = response.usage.input_tokens
    output_tokens = response.usage.output_tokens
    print(f"  Claude usage: {input_tokens:,} input tokens, {output_tokens:,} output tokens")

    return dashboard


# ---------------------------------------------------------------------------
# MongoDB Import
# ---------------------------------------------------------------------------

def mongo_eval(script: str) -> str:
    """Run a MongoDB script in the HyperDX container."""
    result = subprocess.check_output(
        ["docker", "exec", CONTAINER, "mongo", "--quiet", "--eval", script],
        stderr=subprocess.STDOUT,
    )
    return result.decode().strip()


def import_dashboard(dashboard: dict) -> str:
    """Insert a dashboard into HyperDX via MongoDB."""
    print("\nStep 4/4: Creating dashboard in HyperDX...")

    # Get team ID
    team_id = mongo_eval(
        'db=db.getSiblingDB("hyperdx"); print(db.teams.findOne({})._id.str)'
    )
    if not team_id:
        print("ERROR: Could not retrieve team ID from MongoDB")
        sys.exit(1)

    # Get traces source ID
    traces_source_id = mongo_eval(
        'db=db.getSiblingDB("hyperdx"); var s=db.sources.findOne({kind:"trace"}); print(s?s._id.str:"")'
    )
    if not traces_source_id:
        print("ERROR: Could not retrieve traces source ID from MongoDB")
        sys.exit(1)

    print(f"  Team ID: {team_id}")
    print(f"  Traces Source ID: {traces_source_id}")

    # Replace placeholder in the dashboard
    dashboard_str = json.dumps(dashboard).replace("{{TRACES_SOURCE_ID}}", traces_source_id)

    # Insert via MongoDB
    mongo_script = f"""
    db = db.getSiblingDB('hyperdx');
    var dashboard = {dashboard_str};
    dashboard.team = ObjectId('{team_id}');
    dashboard.createdAt = new Date();
    dashboard.updatedAt = new Date();
    var result = db.dashboards.insertOne(dashboard);
    if (result.insertedId) {{
        print(result.insertedId.str);
    }} else {{
        print('FAILED');
    }}
    """

    result = mongo_eval(mongo_script)
    if result == "FAILED" or not result:
        print("ERROR: Failed to create dashboard")
        sys.exit(1)

    print(f"  Dashboard created with ID: {result}")
    return result


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_dashboard(dashboard: dict) -> list:
    """Validate a dashboard definition against known rules."""
    print("\nStep 3/4: Validating dashboard definition...")
    errors = []

    if "name" not in dashboard:
        errors.append("Missing 'name' field")
    if "tiles" not in dashboard or not dashboard["tiles"]:
        errors.append("Missing or empty 'tiles' array")
        return errors

    valid_agg_fns = {"count", "sum", "avg", "min", "max", "count_distinct", "last_value"}
    valid_display_types = {"number", "line", "stacked_bar", "bar", "area"}
    invalid_agg_fns = {"p50", "p95", "p99", "percentile"}

    for i, tile in enumerate(dashboard["tiles"]):
        tile_name = tile.get("config", {}).get("name", f"tile-{i}")
        config = tile.get("config", {})

        # Check whereLanguage
        if config.get("whereLanguage") == "lucene":
            errors.append(f"Tile '{tile_name}': whereLanguage must be 'sql', not 'lucene'")

        # Check displayType
        dt = config.get("displayType", "")
        if dt and dt not in valid_display_types:
            errors.append(f"Tile '{tile_name}': invalid displayType '{dt}'")

        # Check select items
        for j, sel in enumerate(config.get("select", [])):
            agg = sel.get("aggFn", "")
            if agg in invalid_agg_fns:
                errors.append(f"Tile '{tile_name}': aggFn '{agg}' is not supported, use avg/max instead")
            elif agg and agg not in valid_agg_fns:
                errors.append(f"Tile '{tile_name}': invalid aggFn '{agg}'")

            # count should have empty valueExpression
            if agg == "count" and sel.get("valueExpression", "") != "":
                errors.append(f"Tile '{tile_name}': count aggFn should have empty valueExpression")

        # Check numberFormat for number tiles
        if dt == "number" and "numberFormat" not in config:
            errors.append(f"Tile '{tile_name}': number displayType should include numberFormat")

        # Check source placeholder
        source = config.get("source", "")
        if source and source != "{{TRACES_SOURCE_ID}}" and len(source) != 24:
            errors.append(f"Tile '{tile_name}': source should be '{{{{TRACES_SOURCE_ID}}}}' or a valid ObjectId")

        # Check for groupBy (not supported)
        if "groupBy" in config:
            errors.append(f"Tile '{tile_name}': groupBy is not supported in config format")

    if errors:
        print(f"  Found {len(errors)} validation issue(s):")
        for err in errors:
            print(f"    - {err}")
    else:
        print(f"  All {len(dashboard['tiles'])} tiles validated successfully")

    return errors


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="AI-powered dashboard builder for HyperDX",
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Generate JSON only, don't create in HyperDX")
    parser.add_argument("--prompt", type=str, default="",
                        help="Custom focus for the dashboard (e.g., 'Focus on cost')")
    parser.add_argument("--model", type=str, default="claude-sonnet-4-20250514",
                        help="Claude model to use (default: claude-sonnet-4-20250514)")
    parser.add_argument("--output", type=str, default="",
                        help="Save generated JSON to file")
    args = parser.parse_args()

    print("=" * 60)
    print("AI Dashboard Builder for HyperDX")
    print("=" * 60)
    print()

    # Step 1: Discover data
    discovery = discover_data()

    if not discovery.get("gen_ai_attributes"):
        print("\nWARNING: No gen_ai.* attributes found in ClickHouse.")
        print("  Run demo data generator first: python generate_demo_data.py")
        if not args.dry_run:
            sys.exit(1)

    # Step 2: Generate dashboard with Claude
    dashboard = generate_dashboard(discovery, args.prompt, args.model)

    # Step 3: Validate
    errors = validate_dashboard(dashboard)

    # Save to file if requested
    if args.output:
        with open(args.output, "w") as f:
            json.dump(dashboard, f, indent=2)
        print(f"\nSaved dashboard JSON to: {args.output}")

    if args.dry_run:
        print("\n--- Generated Dashboard JSON ---")
        print(json.dumps(dashboard, indent=2))
        print("\nDry run complete. Use without --dry-run to create in HyperDX.")
        return

    if errors:
        print("\nWARNING: Dashboard has validation issues. Attempting to create anyway...")

    # Step 4: Import into HyperDX
    dashboard_id = import_dashboard(dashboard)

    ui_url = os.getenv("HYPERDX_UI_URL", "http://localhost:8080")
    print(f"\n{'=' * 60}")
    print("DONE!")
    print(f"{'=' * 60}")
    print(f"View dashboard at: {ui_url}/dashboards")
    print()


if __name__ == "__main__":
    main()
