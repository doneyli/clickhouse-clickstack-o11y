---
  Demo Order

  1. Pre-flight

  docker compose up -d
  python stream_data.py --cycle 60 &     # stream live data in the background
  # Verify e-commerce data exists:
  curl -s "http://localhost:8123/?user=api&password=api" --data "SELECT ServiceName, count() FROM otel_traces GROUP BY ServiceName ORDER BY count() DESC"
  # Verify NGINX data exists:
  curl -s "http://localhost:8123/?user=api&password=api" --data "SELECT count() FROM otel_logs WHERE ServiceName = 'nginx-demo'"


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
  translate them properly for the v2 tiles format — using Lucene
  syntax for where filters and string arrays for groupBy.)


  5. Cleanup

  ./cleanup_dashboards.sh


  6. Advanced — Pixel-Perfect Spec (paste into fresh session)

  Create a dashboard called "Frontend Performance" with this exact
   layout:
  Row 1 (y=0): Four KPI tiles (w=6, h=3 each):
    - "Total Requests" at x=0: count of all spans for frontend
  service
    - "Avg Latency" at x=6: average duration for frontend
    - "P99 Latency" at x=12: p99 duration for frontend
    - "Error Rate" at x=18: count of errors for frontend
  Row 2 (y=3): Two half-width charts (w=12, h=6):
    - "Latency Over Time" at x=0: avg duration over time for
  frontend, grouped by span_name
    - "Requests by Operation" at x=12: count over time for
  frontend, grouped by span_name
  Row 3 (y=9): One full-width table (w=24, h=5):
    - "Top Operations": count grouped by span_name, sorted
  descending


  7. Cleanup

  ./cleanup_dashboards.sh


  8. NGINX — Log Analytics (paste into fresh session)

  Create a dashboard for the NGINX access logs (ServiceName:
  nginx-demo). Include:
  - KPIs: total requests, error count (4xx + 5xx), avg response
  time, unique client IPs
  - Requests over time
  - Errors over time broken down by status code
  - A table of top request paths

  NOTE: NGINX data has historical timestamps (2025-10-20 to
  2025-10-21). Set the UI time range to that period.


  9. Cleanup

  ./cleanup_dashboards.sh


  10. NGINX — Screenshot Migration (paste into fresh session)

  [paste a screenshot of an NGINX dashboard from Grafana/Datadog]
  Recreate this dashboard using the nginx-demo access log data in
  my ClickHouse instance. Add a table showing top client IPs.


  11. Cleanup

  ./cleanup_dashboards.sh


  12. Full Test Suite

  Run through tests/test_dashboard_skill.md (all 14 tests)

  ---
  The cleanup script (cleanup_dashboards.sh) lists all dashboards,
   asks for confirmation (or use --force to skip), and deletes
  them via the API. Run it between each demo prompt to start
  clean.

  NGINX data note: The NGINX access log has historical timestamps
  (2025-10-20 to 2025-10-21). After deploying NGINX dashboards,
  set the UI time range to "Oct 20 – Oct 21, 2025" to see data.
  The e-commerce data uses live timestamps from stream_data.py.
