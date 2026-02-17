# HyperDX Dashboard Skill — Test Suite

> **Purpose:** Repeatable evaluation guide for the `/hyperdx-dashboard` skill.
> Each test is a prompt you paste into a **fresh** Claude Code session (with the
> skill available) and a checklist to grade the output.
>
> **Prerequisites:**
> - HyperDX container running: `docker compose up -d`
> - Sample data loaded: `./setup.sh`
> - Python venv activated: `source .venv/bin/activate`

---

## Validation Rules Reference

The 17 rules referenced throughout this document:

| # | Rule | Summary |
|---|------|---------|
| R1 | Lucene `where` | `where` uses Lucene syntax (`service:frontend`), never SQL |
| R2 | HyperDX field names | `field` uses HyperDX names (`duration`, `service`), not ClickHouse columns (`_duration`, `_service`) |
| R3 | `charts` array | Top-level key is `charts` (not `tiles`) |
| R4 | `series` array | Each chart has `series` (not `config`/`select`) |
| R5 | Multi-series consistency | All series in a chart share the same `groupBy` |
| R6 | `count` has no `field` | When `aggFn` is `count`, omit `field` entirely |
| R7 | `numberFormat` required | `type: "number"` KPI tiles must have `numberFormat` with all 6 properties |
| R8 | `seriesReturnType` | Every chart has `seriesReturnType: "column"` |
| R9 | Grid bounds | `x + w <= 12` for every chart; no overlapping positions |
| R10 | `groupBy` is an array | `groupBy` is always an array (e.g., `["span_name"]` or `[]`) |
| R11 | Metrics require `table: "metrics"` | Metric series use `table: "metrics"`, not `"logs"` |
| R12 | No banned fields | No `source`, `displayType`, `whereLanguage`, `granularity`, `config`, `select` |
| R13 | `groupBy: []` on multi-series | Time charts with multiple series use `groupBy: []` |
| R14 | Descriptive dashboard name | Dashboard name is meaningful, not generic |
| R15 | Chart IDs | Kebab-case, max 36 characters, unique across the dashboard |
| R16 | Table charts | `type: "table"` charts have `groupBy` array and `sortOrder` |
| R17 | Metrics field format | Metrics `field` follows `"name - DataType"` format with matching `metricDataType` |

---

## Category 1: Auto-Discovery (AI proposes the dashboard)

### T01 — Full Auto-Discovery (Zero Guidance)

**Prompt:**

```
Create a dashboard for the data in this system. Discover what's available and build something useful.
```

**Expected Behavior:**
- Skill runs `--summary`, `--attributes`, `--services` to discover data
- Proposes a dashboard covering the most significant services and metrics
- Includes a mix of KPIs, time-series, and at least one table or search chart

**Validation Checklist:**

| # | Check | Pass? |
|---|-------|-------|
| 1 | Dashboard has a descriptive name (not generic like "Dashboard 1") | |
| 2 | At least 6 charts covering multiple services | |
| 3 | At least 2 KPI tiles (`type: "number"`) with valid `numberFormat` | |
| 4 | At least 2 time-series charts (`type: "time"`) with `groupBy: []` | |
| 5 | All `where` clauses use Lucene syntax | |
| 6 | All fields use HyperDX names (not `_duration`, `_service`) | |
| 7 | Grid layout valid: no `x + w > 12`, heights follow convention | |
| 8 | `seriesReturnType: "column"` on every chart | |
| 9 | Successfully deploys via API (HTTP 200) | |
| 10 | Renders in UI at `http://localhost:8080/dashboards` | |

**Rules Primarily Tested:** R1, R2, R4, R7, R8, R9, R10, R14

---

### T02 — Scoped Auto-Discovery (Topic: Errors & Failures)

**Prompt:**

```
Build me an error monitoring dashboard. Focus on failures, errors, and anything that looks unhealthy.
```

**Expected Behavior:**
- Discovers error-related data (severity_text/level, error spans, failed operations)
- Focuses dashboard on error rates, error counts, error logs

**Validation Checklist:**

| # | Check | Pass? |
|---|-------|-------|
| 1 | Dashboard name reflects error/failure theme | |
| 2 | KPI for total error count (`aggFn: "count"`, `where` filters for errors, **no `field`** on count) | |
| 3 | Time-series showing error rate over time | |
| 4 | At least one chart with `where` containing `level:error` or similar error filter | |
| 5 | Search chart showing recent error events (with `fields` array) | |
| 6 | No `field` property on any `count` aggregation series | |
| 7 | Successfully deploys and renders | |

**Rules Primarily Tested:** R1, R6, R4, R8, R15

---

### T03 — Service-Scoped Auto-Discovery

**Prompt:**

```
Create a dashboard specifically for the checkout service. Show me everything important about it.
```

**Expected Behavior:**
- Discovers the checkout service name (may be `checkoutservice` or similar)
- All charts scoped to that service via `where`
- Covers latency, throughput, errors, and top operations

**Validation Checklist:**

| # | Check | Pass? |
|---|-------|-------|
| 1 | Every chart's `where` includes the checkout service filter | |
| 2 | KPI for avg or p95 latency with `field: "duration"` and appropriate `numberFormat` | |
| 3 | KPI for request count | |
| 4 | Time-series for latency or throughput over time | |
| 5 | Table showing top span_names by count or avg duration (`groupBy: ["span_name"]`, `sortOrder` present) | |
| 6 | All chart IDs are descriptive kebab-case, max 36 chars | |
| 7 | Successfully deploys and renders | |

**Rules Primarily Tested:** R1, R2, R7, R8, R10, R15, R16

---

## Category 2: User-Specified Charts

### T04 — Exact KPI Specification

**Prompt:**

```
Create a dashboard called "Service Health KPIs" with exactly these 4 tiles in a row:
1. Total request count across all services
2. Average latency in ms
3. P99 latency in ms
4. Error count (level = error)
```

**Expected Behavior:**
- Creates exactly 4 KPI tiles, no more, no fewer
- Laid out in a single row (y=0, w=3 each, x=0,3,6,9)
- Correct aggregation functions and field usage

**Validation Checklist:**

| # | Check | Pass? |
|---|-------|-------|
| 1 | Exactly 4 charts, all `type: "number"` | |
| 2 | Chart 1: `aggFn: "count"`, no `field` | |
| 3 | Chart 2: `aggFn: "avg"`, `field: "duration"` | |
| 4 | Chart 3: `aggFn: "p99"`, `field: "duration"` | |
| 5 | Chart 4: `aggFn: "count"`, `where` contains `level:error`, no `field` | |
| 6 | All 4 have `numberFormat` with all 6 required properties | |
| 7 | Layout: `w: 3, h: 2` for all; `x: 0, 3, 6, 9`; same `y` | |
| 8 | Dashboard name is exactly "Service Health KPIs" | |
| 9 | Successfully deploys and renders | |

**Rules Primarily Tested:** R6, R7, R8, R9, R14, R15

---

### T05 — SQL/ClickHouse Syntax Trap

**Prompt:**

```
Create a dashboard with:
- Average _duration where _service = 'frontend' grouped by span_name
- Count where severity_text = 'ERROR'
- P95 of _number_attributes['app.order.amount'] for checkoutservice
```

**Expected Behavior:**
- Skill recognizes SQL-style filters and ClickHouse column names
- **Translates** them to Lucene syntax and HyperDX field names
- Does NOT blindly copy the user's syntax into the JSON

**Validation Checklist:**

| # | Check | Pass? |
|---|-------|-------|
| 1 | `where` uses Lucene: `service:frontend` (NOT `_service = 'frontend'`) | |
| 2 | `field` uses `duration` (NOT `_duration`) | |
| 3 | Error count uses `where` with `level:ERROR` (NOT `severity_text = 'ERROR'`) | |
| 4 | Custom attribute uses field name directly: `app.order.amount` (NOT `_number_attributes['...']`) | |
| 5 | `groupBy: ["span_name"]` (as array) | |
| 6 | All 17 validation rules pass | |
| 7 | Successfully deploys and renders | |

**Rules Primarily Tested:** R1, R2, R6, R10, R12

---

### T06 — Multi-Series and GroupBy Charts

**Prompt:**

```
Build a dashboard with:
1. A single chart showing avg, p50, p90, and p99 latency as separate lines over time for the frontend service
2. A chart showing request count over time grouped by service (top 5)
```

**Expected Behavior:**
- Chart 1: 4 series in one chart, all `type: "time"` with identical `groupBy`
- Chart 2: single series with `groupBy: ["service"]`

**Validation Checklist:**

| # | Check | Pass? |
|---|-------|-------|
| 1 | Chart 1 has exactly 4 series, all `type: "time"` | |
| 2 | All 4 series have identical `groupBy: []` (multi-series consistency rule) | |
| 3 | aggFns are `avg`, `p50`, `p90`, `p99` with `field: "duration"` | |
| 4 | Chart 2 has `groupBy: ["service"]` | |
| 5 | Chart 2 uses `aggFn: "count"`, no `field` | |
| 6 | Both charts have `seriesReturnType: "column"` | |
| 7 | Successfully deploys and renders | |

**Rules Primarily Tested:** R5, R10, R13, R14

---

### T07 — Metrics-Only Dashboard

**Prompt:**

```
Create a metrics dashboard showing system resource utilization. Include CPU usage, memory usage, and any other system metrics you can find. Use both KPI tiles and time-series charts.
```

**Expected Behavior:**
- Skill queries `metric_stream` to discover available system metrics
- All charts use `table: "metrics"` (NOT `"logs"`)
- All metrics series have `metricDataType` and correct field format

**Validation Checklist:**

| # | Check | Pass? |
|---|-------|-------|
| 1 | All series have `table: "metrics"` (not `"logs"`) | |
| 2 | Every series has a `metricDataType` field (`"Gauge"`, `"Sum"`, `"Histogram"`, or `"Summary"`) | |
| 3 | Every `field` follows `"name - DataType"` format (e.g., `"system.cpu.utilization - Gauge"`) | |
| 4 | `metricDataType` value matches the suffix in the `field` name | |
| 5 | At least 2 KPI tiles with `numberFormat` | |
| 6 | At least 2 time-series charts | |
| 7 | Successfully deploys and renders with actual data visible | |

**Rules Primarily Tested:** R11, R16, R17, R8

---

### T08 — All Chart Types in One Dashboard

**Prompt:**

```
Create a comprehensive dashboard that demonstrates every chart type: KPI numbers, time-series, a table, a histogram, a search/log viewer, and a markdown section header. Use the frontend service as the data source.
```

**Expected Behavior:**
- Creates exactly 6 charts, one of each type
- All scoped to frontend service

**Validation Checklist:**

| # | Check | Pass? |
|---|-------|-------|
| 1 | Contains `type: "number"` chart with `numberFormat` | |
| 2 | Contains `type: "time"` chart with `groupBy: []` | |
| 3 | Contains `type: "table"` chart with `groupBy` array and `sortOrder` | |
| 4 | Contains `type: "histogram"` chart with `field`, no `aggFn`, no `groupBy` | |
| 5 | Contains `type: "search"` chart with `fields` array, no `aggFn`, no `groupBy` | |
| 6 | Contains `type: "markdown"` chart with only `type` and `content` in series | |
| 7 | All non-markdown charts have `table: "logs"` and scoped to frontend | |
| 8 | Grid layout is valid (no overflow, proper heights) | |
| 9 | Successfully deploys and renders | |

**Rules Primarily Tested:** R3, R4, R9, R12, R14, R15

---

## Category 3: Vague-to-Detailed Spectrum

### T09 — Maximally Vague

**Prompt:**

```
Make me a dashboard
```

**Expected Behavior:**
- Skill should NOT fail or produce an empty dashboard
- Should auto-discover data and make reasonable choices
- May ask clarifying questions OR proceed with a general-purpose dashboard

**Validation Checklist:**

| # | Check | Pass? |
|---|-------|-------|
| 1 | Produces a valid, non-empty dashboard (at least 4 charts) | |
| 2 | Dashboard has a meaningful name | |
| 3 | All 17 validation rules pass | |
| 4 | Successfully deploys and renders | |
| 5 | Charts show actual data (not empty/zero) | |

**Rules Primarily Tested:** R3, R4, R9, R11, R14 (broad coverage)

---

### T10 — Moderate Detail

**Prompt:**

```
I want a dashboard for monitoring our e-commerce checkout flow. Show me latency trends, error rates, and the slowest operations. Include some KPI tiles at the top.
```

**Expected Behavior:**
- Identifies checkout-related services and operations
- Structures dashboard with KPI row at top, charts below
- Covers the 3 requested areas: latency trends, error rates, slowest operations

**Validation Checklist:**

| # | Check | Pass? |
|---|-------|-------|
| 1 | KPI tiles on top row (lowest `y` value, `h: 2`) | |
| 2 | Time-series chart for latency trends (`field: "duration"`, time type) | |
| 3 | Chart showing error rates (count with error filter, or rate aggFn) | |
| 4 | Table chart for slowest operations (`groupBy` with `sortOrder: "desc"`, `aggFn` like `avg` or `p95`) | |
| 5 | Logical layout (KPIs at top, details below) | |
| 6 | Successfully deploys and renders | |

**Rules Primarily Tested:** R7, R8, R14, R15, R16

---

### T11 — Extremely Detailed Specification

**Prompt:**

```
Create a dashboard called "Frontend Performance" with this exact layout:
Row 1 (y=0): Four KPI tiles (w=3, h=2 each):
  - "Total Requests" at x=0: count of all spans for frontend service
  - "Avg Latency" at x=3: average duration for frontend, format as ms with 2 decimals
  - "P99 Latency" at x=6: p99 duration for frontend, format as ms with 2 decimals
  - "Error Rate" at x=9: count of errors for frontend
Row 2 (y=2): Two half-width charts (w=6, h=3):
  - "Latency Over Time" at x=0: avg duration over time for frontend, grouped by span_name
  - "Requests by Operation" at x=6: count over time for frontend, grouped by span_name
Row 3 (y=5): One full-width table (w=12, h=3):
  - "Top Operations": count grouped by span_name, sorted descending
```

**Expected Behavior:**
- Creates the dashboard exactly as specified
- Follows the exact layout coordinates
- Uses the exact chart names

**Validation Checklist:**

| # | Check | Pass? |
|---|-------|-------|
| 1 | Dashboard name is "Frontend Performance" | |
| 2 | Exactly 7 charts | |
| 3 | Row 1: 4 KPI tiles at exact positions (x=0,3,6,9; y=0; w=3; h=2) | |
| 4 | Row 2: 2 time charts at exact positions (x=0,6; y=2; w=6; h=3) | |
| 5 | Row 3: 1 table chart at exact position (x=0; y=5; w=12; h=3) | |
| 6 | Chart names match specification exactly | |
| 7 | Latency KPIs use `numberFormat` with `mantissa: 2` | |
| 8 | Table has `sortOrder: "desc"` and `groupBy: ["span_name"]` | |
| 9 | `groupBy: ["span_name"]` on both row-2 charts, matching within each chart's series | |
| 10 | All where clauses filter for frontend service | |
| 11 | Successfully deploys and renders | |

**Rules Primarily Tested:** R7, R8, R9, R10, R13, R14, R15, R16

---

### T12 — Old-Format Terminology Trap

**Prompt:**

```
Create a dashboard with tiles that have a config block with select fields. Use displayType "line" and set the source to "events". Add a whereLanguage of "sql" and set granularity to "1m".
```

**Expected Behavior:**
- Skill recognizes that the user is describing the OLD MongoDB format
- Translates the intent into the correct API format
- Does NOT include any old-format fields in the output JSON

**Validation Checklist:**

| # | Check | Pass? |
|---|-------|-------|
| 1 | Output uses `charts` (NOT `tiles`) | |
| 2 | Output uses `series` (NOT `config`/`select`) | |
| 3 | No `displayType`, `source`, `whereLanguage`, or `granularity` fields present | |
| 4 | Charts use valid series structure with proper `type`, `aggFn`, etc. | |
| 5 | Successfully deploys and renders | |

**Rules Primarily Tested:** R3, R4, R12

---

### T13 — Large Dashboard (Scale Test)

**Prompt:**

```
Create a comprehensive observability dashboard covering ALL services in the system. For each service, include a KPI tile showing request count and a time-series chart showing latency over time. Add an error summary section at the bottom.
```

**Expected Behavior:**
- Discovers all services (expect 10+ from OTel Demo)
- Creates 20+ charts without layout errors
- Grid layout remains valid across many rows

**Validation Checklist:**

| # | Check | Pass? |
|---|-------|-------|
| 1 | At least 10 services represented | |
| 2 | At least 20 charts total | |
| 3 | All `x + w <= 12` (no grid overflow even with many charts) | |
| 4 | No duplicate chart IDs | |
| 5 | All chart IDs are kebab-case, max 36 chars | |
| 6 | `y` values increment properly (no overlapping charts) | |
| 7 | Successfully deploys via API | |
| 8 | Renders without UI errors | |

**Rules Primarily Tested:** R9, R15, R16 (at scale)

---

### T14 — Non-Existent Service (Graceful Handling)

**Prompt:**

```
Create a dashboard for the "payment-gateway-v3" service showing latency, throughput, and errors.
```

**Expected Behavior:**
- Skill discovers that "payment-gateway-v3" doesn't exist
- Either: (a) informs user and suggests closest match, or (b) uses closest match and notes the substitution
- Does NOT create a dashboard with empty/broken charts

**Validation Checklist:**

| # | Check | Pass? |
|---|-------|-------|
| 1 | Skill acknowledges the service doesn't exist | |
| 2 | Either suggests alternatives or uses closest match (e.g., `paymentservice`) | |
| 3 | If a dashboard is created, charts return actual data (not empty) | |
| 4 | No silent failures (charts with zero data and no explanation) | |

**Rules Primarily Tested:** R1, R2 (robustness)

---

## Scoring Framework

### Per-Test Scoring (100 points)

| Dimension | Points | Criteria |
|-----------|--------|----------|
| **Schema Validity** | 25 | JSON passes all 17 validation rules. Deduct 5 pts per rule violation. |
| **Deployment Success** | 25 | API returns 200, dashboard appears in UI, charts render with data. |
| **Prompt Fidelity** | 25 | Dashboard matches what the user asked for — correct charts, filters, layout, naming. |
| **Data Quality** | 25 | Charts show real data (not empty), correct services/metrics, sensible aggregations. |

### Pass/Fail Threshold

| Result | Criteria |
|--------|----------|
| **Pass** | >= 75 points AND Schema Validity >= 20 AND Deployment Success = 25 |
| **Partial Pass** | >= 50 points (significant issues but shows core competency) |
| **Fail** | < 50 points OR Deployment fails OR dashboard is empty |

### Suite-Level Metrics

- **Overall Score:** Average across all 14 tests
- **Category Scores:** Average per category (Auto-Discovery, User-Specified, Vague-to-Detailed)
- **Rule Coverage Matrix:**

| Rule | T01 | T02 | T03 | T04 | T05 | T06 | T07 | T08 | T09 | T10 | T11 | T12 | T13 | T14 |
|------|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|
| R1   | x   | x   |     |     | x   |     |     |     |     |     |     |     |     | x   |
| R2   | x   |     | x   |     | x   |     |     |     |     |     |     |     |     | x   |
| R3   |     |     |     |     |     |     |     | x   | x   |     |     | x   |     |     |
| R4   | x   | x   |     |     |     |     |     | x   | x   |     |     | x   |     |     |
| R5   |     |     |     |     |     | x   |     |     |     |     |     |     |     |     |
| R6   |     | x   |     | x   | x   |     |     |     |     |     |     |     |     |     |
| R7   | x   |     | x   | x   |     |     |     |     |     | x   | x   |     |     |     |
| R8   | x   | x   | x   | x   |     |     | x   |     |     | x   | x   |     |     |     |
| R9   | x   |     |     | x   |     |     |     | x   | x   |     | x   |     | x   |     |
| R10  | x   |     | x   |     | x   | x   |     |     |     |     | x   |     |     |     |
| R11  |     |     |     |     |     |     | x   |     | x   |     |     |     |     |     |
| R12  |     |     |     |     | x   |     |     | x   |     |     |     | x   |     |     |
| R13  |     |     |     |     |     | x   |     |     |     |     | x   |     |     |     |
| R14  | x   |     |     | x   | x   | x   | x   | x   | x   | x   | x   |     |     |     |
| R15  |     | x   | x   | x   |     |     |     | x   |     | x   | x   |     | x   |     |
| R16  |     |     | x   |     |     |     | x   |     |     | x   | x   |     | x   |     |
| R17  |     |     |     |     |     |     | x   |     |     |     |     |     |     |     |

---

## Execution Instructions

### Running a Test

1. Ensure HyperDX is running: `docker compose up -d`
2. Start a **fresh** Claude Code conversation (to avoid context contamination)
3. Paste the test prompt exactly as written
4. Observe the skill execution (data discovery, JSON generation, validation, deployment)
5. Score using the validation checklist

### Verifying Results

| What to verify | How |
|----------------|-----|
| **API response** | Check HTTP status code from deployment step |
| **JSON validation** | Review the generated dashboard JSON against the checklist |
| **UI verification** | Open `http://localhost:8080/dashboards` and confirm charts render with data |
| **Data presence** | Click into individual charts to verify they're not showing empty results |

### Recording Results

For each test, record:

```
Test ID:     T__
Date:        YYYY-MM-DD
Prompt:      (as written above)
Result:      Pass / Partial Pass / Fail
Score:       __/100
  - Schema Validity:     __/25
  - Deployment Success:  __/25
  - Prompt Fidelity:     __/25
  - Data Quality:        __/25
Rule Violations: (list by rule number, e.g., R6 — field present on count)
Notes:       (unexpected behavior, edge cases)
```

### Quick-Reference: Running All 14 Tests

```bash
# Pre-flight check
docker compose up -d
python query_clickhouse.py --summary   # Verify data is loaded

# Then run each test in a fresh Claude Code session:
#   T01-T03:  Auto-Discovery (Category 1)
#   T04-T08:  User-Specified Charts (Category 2)
#   T09-T14:  Vague-to-Detailed Spectrum (Category 3)
```
