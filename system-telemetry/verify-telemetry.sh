#!/usr/bin/env bash
#
# Verify that system telemetry data is flowing into ClickHouse / HyperDX.
# Queries the ClickHouse HTTP interface on localhost:8123.
#
set -euo pipefail

CH="http://localhost:8123"

query() {
    local sql="$1"
    curl -sf --data-binary "$sql" "$CH"
}

echo "=== System Telemetry Verification ==="
echo

# ---------------------------------------------------------------------------
# 1. Metrics check
# ---------------------------------------------------------------------------
echo "--- 1. Host Metrics (metric_stream) ---"
result=$(query "SELECT name, count(*) AS cnt FROM metric_stream GROUP BY name ORDER BY cnt DESC LIMIT 15 FORMAT PrettyCompact" 2>&1) || true
if [[ -z "$result" || "$result" == *"Exception"* ]]; then
    echo "  No metrics found (or table does not exist)."
    echo "  This is expected if the OTel Collector hasn't been running long,"
    echo "  or if metric_stream has no registered MongoDB source."
else
    echo "$result"
fi
echo

# ---------------------------------------------------------------------------
# 2. Logs check
# ---------------------------------------------------------------------------
echo "--- 2. System Logs (log_stream, type=log) ---"
result=$(query "
    SELECT
        count(*) AS log_count,
        min(timestamp) AS earliest,
        max(timestamp) AS latest
    FROM log_stream
    WHERE type = 'log'
      AND _service = 'macos-host-telemetry'
    FORMAT PrettyCompact
" 2>&1) || true
if [[ -z "$result" || "$result" == *"Exception"* ]]; then
    echo "  No logs found from macos-host-telemetry."
    echo "  Check that /var/log/system.log is readable by the OTel Collector."
else
    echo "$result"
fi
echo

# ---------------------------------------------------------------------------
# 3. Traces check
# ---------------------------------------------------------------------------
echo "--- 3. System Traces (log_stream, type=span) ---"
result=$(query "
    SELECT
        span_name,
        count(*) AS span_count,
        round(avg(_duration), 2) AS avg_duration_ms
    FROM log_stream
    WHERE type = 'span'
      AND _service = 'macos-system-monitor'
    GROUP BY span_name
    ORDER BY span_count DESC
    FORMAT PrettyCompact
" 2>&1) || true
if [[ -z "$result" || "$result" == *"Exception"* ]]; then
    echo "  No trace spans found from macos-system-monitor."
    echo "  Make sure generate_system_traces.py is running."
else
    echo "$result"
fi
echo

# ---------------------------------------------------------------------------
# 4. Trace attributes check
# ---------------------------------------------------------------------------
echo "--- 4. Trace Number Attributes ---"
result=$(query "
    SELECT DISTINCT arrayJoin(mapKeys(_number_attributes)) AS attr
    FROM log_stream
    WHERE type = 'span'
      AND _service = 'macos-system-monitor'
    ORDER BY attr
    LIMIT 30
    FORMAT PrettyCompact
" 2>&1) || true
if [[ -z "$result" || "$result" == *"Exception"* ]]; then
    echo "  No number attributes found."
else
    echo "$result"
fi
echo

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo "--- Summary ---"
total_spans=$(query "SELECT count(*) FROM log_stream WHERE type = 'span' AND _service = 'macos-system-monitor' FORMAT TabSeparated" 2>&1) || total_spans="0"
total_logs=$(query "SELECT count(*) FROM log_stream WHERE type = 'log' AND _service = 'macos-host-telemetry' FORMAT TabSeparated" 2>&1) || total_logs="0"
total_metrics=$(query "SELECT count(*) FROM metric_stream FORMAT TabSeparated" 2>&1) || total_metrics="0"

echo "  Trace spans:  $total_spans"
echo "  Log entries:  $total_logs"
echo "  Metric rows:  $total_metrics"
echo
echo "Done."
