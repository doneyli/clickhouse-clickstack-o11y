---
  Demo Order

  1. Pre-flight

  docker compose up -d
  python stream_data.py --cycle 60 &     # stream live data in the background
  # Verify data exists:
  curl -s "http://localhost:8123/?user=api&password=api" --data "SELECT ServiceName, count() FROM otel_traces GROUP BY ServiceName ORDER BY count() DESC"


  2. Basic — Auto-Discovery (paste into fresh session)

  Create a dashboard for the checkout service. Show me everything
  important about it.


  3. Cleanup

  ./cleanup_dashboards.sh


  4. Intermediate — SQL Syntax Trap (paste into fresh session)

  Create a dashboard with:
  - Average Duration where ServiceName = 'frontend' grouped by
  SpanName
  - Count where SeverityText = 'ERROR'
  - P95 of SpanAttributes['app.order.amount'] for checkout

  (The AI should recognize these are ClickHouse column names and
  translate them properly for the tiles format — using
  valueExpression for ClickHouse columns, Lucene for where.)


  5. Cleanup

  ./cleanup_dashboards.sh


  6. Advanced — Pixel-Perfect Spec (paste into fresh session)

  Create a dashboard called "Frontend Performance" with this exact
   layout:
  Row 1 (y=0): Four KPI tiles (w=6, h=2 each):
    - "Total Requests" at x=0: count of all spans for frontend
  service
    - "Avg Latency" at x=6: average duration for frontend
    - "P99 Latency" at x=12: p99 duration for frontend
    - "Error Rate" at x=18: count of errors for frontend
  Row 2 (y=2): Two half-width charts (w=12, h=3):
    - "Latency Over Time" at x=0: avg duration over time for
  frontend, grouped by span_name
    - "Requests by Operation" at x=12: count over time for
  frontend, grouped by span_name
  Row 3 (y=5): One full-width table (w=24, h=3):
    - "Top Operations": count grouped by span_name, sorted
  descending


  7. Cleanup

  ./cleanup_dashboards.sh


  8. Full Test Suite

  Run through tests/test_dashboard_skill.md (all 14 tests)

  ---
  The cleanup script (cleanup_dashboards.sh) lists all dashboards,
   asks for confirmation (or use --force to skip), and deletes
  them via the API. Run it between each demo prompt to start
  clean.
