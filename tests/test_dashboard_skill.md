# ClickStack Dashboard Skill — Test Suite

> **Purpose:** Repeatable evaluation guide for the `/hyperdx-dashboard` skill.
> Each test is a prompt you paste into a **fresh** Claude Code session (with the
> skill available) and a checklist to grade the output.
>
> **Prerequisites:**
> - ClickStack container running: `docker compose up -d`
> - Sample data loaded: `./setup.sh`
> - Python venv activated: `source .venv/bin/activate`

---

## Validation Rules Reference

The 21 rules referenced throughout this document:

| # | Rule | Summary |
|---|------|---------|
| R1 | Lucene `where` | `where` uses Lucene syntax (`service:frontend`), never SQL. `whereLanguage: "lucene"` present. |
| R2 | ClickHouse column names | `valueExpression` uses ClickHouse columns (`Duration`, `ServiceName`), not HyperDX names (`duration`, `service`) |
| R3 | `tiles` array | Top-level key is `tiles` (not `charts`) |
| R4 | `config` with `select` | Each tile has `config` with `select` array (not `series`) |
| R5 | Multi-select consistency | All select items share the tile's `where` and `groupBy` |
| R6 | `count` has empty valueExpression | When `aggFn` is `count`, use `valueExpression: ""` |
| R7 | `numberFormat` required | `displayType: "number"` tiles must have `numberFormat` |
| R8 | `tags` required | Dashboard must have `tags: []` (even if empty) |
| R9 | Grid bounds | `x + w <= 24` for every tile; no overlapping positions |
| R10 | `groupBy` is objects | `groupBy` is always objects (`[{"valueExpression": "Col"}]` or `[]`) |
| R11 | Metrics use `source: "metrics"` | Metrics tiles use `source: "metrics"` with `metricName` and `metricDataType` |
| R12 | Required tile config fields | Must have `source`, `displayType`, `whereLanguage`, `where`, `select`, `groupBy` |
| R13 | `groupBy: []` on time tiles | Time tiles without grouping still need `groupBy: []` |
| R14 | Descriptive dashboard name | Dashboard name is meaningful, not generic |
| R15 | Tile IDs | Kebab-case, max 36 characters, unique across the dashboard |
| R16 | Table tiles | `displayType: "table"` tiles have `groupBy` with objects |
| R17 | Metrics fields | Metrics tiles have `metricName`, `metricDataType`, and `valueExpression: "Value"` |
| R18 | No `type:span`/`type:log` | Never use `type:span` or `type:log` in where — silently returns 0 rows |
| R19 | Select items complete | Every select item has all 3 fields: `aggFn`, `valueExpression`, `aggCondition` |
| R20 | Quantile format | Use `aggFn: "quantile"` with `level`, not `p50`/`p95`/`p99` |
| R21 | Source is string | `source` is `"traces"`, `"logs"`, or `"metrics"` (not a dynamic ID) |

---

## Category 1: Auto-Discovery (AI proposes the dashboard)

### T01 — Full Auto-Discovery (Zero Guidance)

**Prompt:**

```
Create a dashboard for the data in this system. Discover what's available and build something useful.
```

**Expected Behavior:**
- Skill queries ClickHouse to discover tables, services, and attributes
- Proposes a dashboard covering the most significant services and metrics
- Includes a mix of KPIs, time-series, and at least one table tile

**Validation Checklist:**

| # | Check | Pass? |
|---|-------|-------|
| 1 | Dashboard has a descriptive name (not generic like "Dashboard 1") | |
| 2 | At least 6 tiles covering multiple services | |
| 3 | At least 2 KPI tiles (`displayType: "number"`) with valid `numberFormat` | |
| 4 | At least 2 time tiles (`displayType: "line"`) with `groupBy: []` | |
| 5 | All `where` clauses use Lucene syntax with `whereLanguage: "lucene"` | |
| 6 | All `valueExpression` use ClickHouse column names (not `duration`, `service`) | |
| 7 | Grid layout valid: no `x + w > 24`, heights follow convention | |
| 8 | `tags: []` present at dashboard level | |
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
- Discovers error-related data (SeverityText, StatusCode, failed operations)
- Uses `source: "logs"` for error log counts, `source: "traces"` for span errors
- Focuses dashboard on error rates, error counts, error logs

**Validation Checklist:**

| # | Check | Pass? |
|---|-------|-------|
| 1 | Dashboard name reflects error/failure theme | |
| 2 | KPI for total error count (`aggFn: "count"`, `valueExpression: ""`, `where` filters for errors) | |
| 3 | Time tile showing error rate over time | |
| 4 | At least one tile with `where` containing `level:error` or similar error filter | |
| 5 | Correct `source` usage (`"logs"` for severity-based errors) | |
| 6 | No `valueExpression` on any `count` aggregation | |
| 7 | Successfully deploys and renders | |

**Rules Primarily Tested:** R1, R6, R4, R8, R15, R21

---

### T03 — Service-Scoped Auto-Discovery

**Prompt:**

```
Create a dashboard specifically for the checkout service. Show me everything important about it.
```

**Expected Behavior:**
- Discovers the checkout service name
- All tiles scoped to that service via `where`
- Covers latency, throughput, errors, and top operations

**Validation Checklist:**

| # | Check | Pass? |
|---|-------|-------|
| 1 | Every tile's `where` includes the checkout service filter | |
| 2 | KPI for avg or quantile latency with `valueExpression: "Duration"` and `numberFormat` | |
| 3 | KPI for request count | |
| 4 | Time tile for latency or throughput over time | |
| 5 | Table showing top operations (`groupBy` with SpanName object) | |
| 6 | All tile IDs are descriptive kebab-case, max 36 chars | |
| 7 | Successfully deploys and renders | |

**Rules Primarily Tested:** R1, R2, R7, R8, R10, R15, R16

---

## Category 2: User-Specified Charts

### T04 — Exact KPI Specification

**Prompt:**

```
Create a dashboard called "Service Health KPIs" with exactly these 4 tiles in a row:
1. Total request count across all services
2. Average latency
3. P99 latency
4. Error count (level = error)
```

**Expected Behavior:**
- Creates exactly 4 KPI tiles, no more, no fewer
- Laid out in a single row (y=0, w=6 each, x=0,6,12,18 in 24-col grid)
- Correct aggregation functions and valueExpression usage

**Validation Checklist:**

| # | Check | Pass? |
|---|-------|-------|
| 1 | Exactly 4 tiles, all `displayType: "number"` | |
| 2 | Tile 1: `aggFn: "count"`, `valueExpression: ""` | |
| 3 | Tile 2: `aggFn: "avg"`, `valueExpression: "Duration"` | |
| 4 | Tile 3: `aggFn: "quantile"`, `level: 0.99`, `valueExpression: "Duration"` | |
| 5 | Tile 4: `aggFn: "count"`, `where` contains `level:error`, `valueExpression: ""` | |
| 6 | All 4 have `numberFormat` | |
| 7 | Layout: `w: 6, h: 2` for all; `x: 0, 6, 12, 18`; same `y` | |
| 8 | Dashboard name is exactly "Service Health KPIs" | |
| 9 | Successfully deploys and renders | |

**Rules Primarily Tested:** R6, R7, R8, R9, R14, R15, R20

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
- Skill recognizes SQL-style filters and old v1 column names
- **Translates** them properly: `_duration` → `Duration` in valueExpression, `_service = 'frontend'` → `service:frontend` in Lucene where
- Uses `aggFn: "quantile"` with `level: 0.95` (not `p95`)

**Validation Checklist:**

| # | Check | Pass? |
|---|-------|-------|
| 1 | `where` uses Lucene: `service:frontend` (NOT `_service = 'frontend'`) | |
| 2 | `valueExpression` uses `Duration` (NOT `_duration` or `duration`) | |
| 3 | Error count uses `where` with `level:error` (NOT `severity_text = 'ERROR'`) | |
| 4 | Custom attribute uses `SpanAttributes['app.order.amount']` in valueExpression | |
| 5 | `groupBy: [{"valueExpression": "SpanName"}]` (as object array) | |
| 6 | All 21 validation rules pass | |
| 7 | Successfully deploys and renders | |

**Rules Primarily Tested:** R1, R2, R6, R10, R19, R20

---

### T06 — Multi-Select and GroupBy

**Prompt:**

```
Build a dashboard with:
1. A single tile showing avg, p50, p90, and p99 latency as separate lines over time for the frontend service
2. A tile showing request count over time grouped by service (top 5)
```

**Expected Behavior:**
- Tile 1: 4 select items in one tile, all using `displayType: "line"`
- Tile 2: single select item with `groupBy: [{"valueExpression": "ServiceName"}]`

**Validation Checklist:**

| # | Check | Pass? |
|---|-------|-------|
| 1 | Tile 1 has 4 select items with `displayType: "line"` | |
| 2 | Select items use `quantile` with levels 0.5, 0.9, 0.99 and `avg` | |
| 3 | All select items have `valueExpression: "Duration"` | |
| 4 | Tile 2 has `groupBy: [{"valueExpression": "ServiceName"}]` | |
| 5 | Tile 2 uses `aggFn: "count"`, `valueExpression: ""` | |
| 6 | `tags: []` present at dashboard level | |
| 7 | Successfully deploys and renders | |

**Rules Primarily Tested:** R5, R10, R13, R14, R19, R20

---

### T07 — Metrics-Only Dashboard

**Prompt:**

```
Create a metrics dashboard showing system resource utilization. Include CPU usage, memory usage, and any other system metrics you can find. Use both KPI tiles and time-series charts.
```

**Expected Behavior:**
- Skill queries ClickHouse metric tables to discover available system metrics
- All tiles use `source: "metrics"` with `metricName` and `metricDataType`
- `valueExpression: "Value"` for all metrics aggregations

**Validation Checklist:**

| # | Check | Pass? |
|---|-------|-------|
| 1 | All tiles have `source: "metrics"` (not `"traces"` or `"logs"`) | |
| 2 | Every tile config has `metricName` and `metricDataType` fields | |
| 3 | `metricDataType` is valid (`"Gauge"`, `"Sum"`, `"Histogram"`, or `"Summary"`) | |
| 4 | `valueExpression: "Value"` for all metric aggregations | |
| 5 | At least 2 KPI tiles with `numberFormat` | |
| 6 | At least 2 time-series tiles | |
| 7 | Successfully deploys and renders | |

**Rules Primarily Tested:** R11, R17, R8, R21

---

### T08 — Multiple Display Types

**Prompt:**

```
Create a comprehensive dashboard that demonstrates different chart types: KPI numbers, time-series lines, stacked bars, and a table. Use the frontend service as the data source.
```

**Expected Behavior:**
- Creates tiles with various displayTypes
- All scoped to frontend service

**Validation Checklist:**

| # | Check | Pass? |
|---|-------|-------|
| 1 | Contains `displayType: "number"` tile with `numberFormat` | |
| 2 | Contains `displayType: "line"` tile with `groupBy: []` | |
| 3 | Contains `displayType: "stacked_bar"` tile with `groupBy` objects | |
| 4 | Contains `displayType: "table"` tile with `groupBy` objects | |
| 5 | All tiles scoped to frontend service in `where` | |
| 6 | Grid layout is valid (no overflow, proper heights) | |
| 7 | Successfully deploys and renders | |

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
| 1 | Produces a valid, non-empty dashboard (at least 4 tiles) | |
| 2 | Dashboard has a meaningful name | |
| 3 | All 21 validation rules pass | |
| 4 | Successfully deploys and renders | |
| 5 | Tiles show actual data (not empty/zero) | |

**Rules Primarily Tested:** R3, R4, R9, R11, R14 (broad coverage)

---

### T10 — Moderate Detail

**Prompt:**

```
I want a dashboard for monitoring our e-commerce checkout flow. Show me latency trends, error rates, and the slowest operations. Include some KPI tiles at the top.
```

**Expected Behavior:**
- Identifies checkout-related services and operations
- Structures dashboard with KPI row at top, tiles below
- Covers the 3 requested areas: latency trends, error rates, slowest operations

**Validation Checklist:**

| # | Check | Pass? |
|---|-------|-------|
| 1 | KPI tiles on top row (lowest `y` value, `h: 2`) | |
| 2 | Time tile for latency trends (`valueExpression: "Duration"`, `displayType: "line"`) | |
| 3 | Tile showing error rates (count with error filter) | |
| 4 | Table tile for slowest operations (`groupBy` objects, `displayType: "table"`) | |
| 5 | Logical layout (KPIs at top, details below) | |
| 6 | Successfully deploys and renders | |

**Rules Primarily Tested:** R7, R8, R14, R15, R16

---

### T11 — Extremely Detailed Specification

**Prompt:**

```
Create a dashboard called "Frontend Performance" with this exact layout:
Row 1 (y=0): Four KPI tiles (w=6, h=2 each):
  - "Total Requests" at x=0: count of all spans for frontend service
  - "Avg Latency" at x=6: average duration for frontend
  - "P99 Latency" at x=12: p99 duration for frontend
  - "Error Rate" at x=18: count of errors for frontend
Row 2 (y=2): Two half-width charts (w=12, h=3):
  - "Latency Over Time" at x=0: avg duration over time for frontend, grouped by span_name
  - "Requests by Operation" at x=12: count over time for frontend, grouped by span_name
Row 3 (y=5): One full-width table (w=24, h=3):
  - "Top Operations": count grouped by span_name, sorted descending
```

**Expected Behavior:**
- Creates the dashboard exactly as specified
- Follows the exact layout coordinates (24-col grid)
- Uses the exact tile names

**Validation Checklist:**

| # | Check | Pass? |
|---|-------|-------|
| 1 | Dashboard name is "Frontend Performance" | |
| 2 | Exactly 7 tiles | |
| 3 | Row 1: 4 KPI tiles at exact positions (x=0,6,12,18; y=0; w=6; h=2) | |
| 4 | Row 2: 2 line tiles at exact positions (x=0,12; y=2; w=12; h=3) | |
| 5 | Row 3: 1 table tile at exact position (x=0; y=5; w=24; h=3) | |
| 6 | Tile names match specification exactly | |
| 7 | Latency KPIs use `numberFormat` | |
| 8 | Table has `groupBy: [{"valueExpression": "SpanName"}]` | |
| 9 | `groupBy` objects on both row-2 tiles | |
| 10 | All where clauses filter for frontend service | |
| 11 | Successfully deploys and renders | |

**Rules Primarily Tested:** R7, R8, R9, R10, R13, R14, R15, R16

---

### T12 — Old v1 Format Terminology Trap

**Prompt:**

```
Create a dashboard with charts that have a series array. Use type "time" for line charts and table: "logs" for the data source. Add asRatio: false and field: "duration". Set groupBy to ["span_name"].
```

**Expected Behavior:**
- Skill recognizes that the user is describing the OLD v1 API format
- Translates the intent into the correct tiles format
- Does NOT include any v1-format fields in the output JSON

**Validation Checklist:**

| # | Check | Pass? |
|---|-------|-------|
| 1 | Output uses `tiles` (NOT `charts`) | |
| 2 | Output uses `config` with `select` (NOT `series`) | |
| 3 | Uses `displayType: "line"` (NOT `type: "time"`) | |
| 4 | Uses `source: "traces"` (NOT `table: "logs"`) | |
| 5 | Uses `valueExpression: "Duration"` (NOT `field: "duration"`) | |
| 6 | Uses `groupBy: [{"valueExpression": "SpanName"}]` (NOT `["span_name"]`) | |
| 7 | No `asRatio`, `charts`, `series`, `table`, `field` in output | |
| 8 | Successfully deploys and renders | |

**Rules Primarily Tested:** R3, R4, R12, R21

---

### T13 — Large Dashboard (Scale Test)

**Prompt:**

```
Create a comprehensive observability dashboard covering ALL services in the system. For each service, include a KPI tile showing request count and a time-series chart showing latency over time. Add an error summary section at the bottom.
```

**Expected Behavior:**
- Discovers all services (expect 10+ from OTel Demo)
- Creates 20+ tiles without layout errors
- Grid layout remains valid across many rows

**Validation Checklist:**

| # | Check | Pass? |
|---|-------|-------|
| 1 | At least 10 services represented | |
| 2 | At least 20 tiles total | |
| 3 | All `x + w <= 24` (no grid overflow even with many tiles) | |
| 4 | No duplicate tile IDs | |
| 5 | All tile IDs are kebab-case, max 36 chars | |
| 6 | `y` values increment properly (no overlapping tiles) | |
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
- Does NOT create a dashboard with empty/broken tiles

**Validation Checklist:**

| # | Check | Pass? |
|---|-------|-------|
| 1 | Skill acknowledges the service doesn't exist | |
| 2 | Either suggests alternatives or uses closest match | |
| 3 | If a dashboard is created, tiles return actual data (not empty) | |
| 4 | No silent failures (tiles with zero data and no explanation) | |

**Rules Primarily Tested:** R1, R2 (robustness)

---

## Scoring Framework

### Per-Test Scoring (100 points)

| Dimension | Points | Criteria |
|-----------|--------|----------|
| **Schema Validity** | 25 | JSON passes all 21 validation rules. Deduct 5 pts per rule violation. |
| **Deployment Success** | 25 | API returns 200, dashboard appears in UI, tiles render with data. |
| **Prompt Fidelity** | 25 | Dashboard matches what the user asked for — correct tiles, filters, layout, naming. |
| **Data Quality** | 25 | Tiles show real data (not empty/zero), correct services/metrics, sensible aggregations. |

### Pass/Fail Threshold

| Result | Criteria |
|--------|----------|
| **Pass** | >= 75 points AND Schema Validity >= 20 AND Deployment Success = 25 |
| **Partial Pass** | >= 50 points (significant issues but shows core competency) |
| **Fail** | < 50 points OR Deployment fails OR dashboard is empty |

---

## Execution Instructions

### Running a Test

1. Ensure ClickStack is running: `docker compose up -d`
2. Start a **fresh** Claude Code conversation (to avoid context contamination)
3. Paste the test prompt exactly as written
4. Observe the skill execution (data discovery, JSON generation, validation, deployment)
5. Score using the validation checklist

### Verifying Results

| What to verify | How |
|----------------|-----|
| **API response** | Check HTTP status code from deployment step |
| **JSON validation** | Review the generated dashboard JSON against the checklist |
| **UI verification** | Open `http://localhost:8080/dashboards` and confirm tiles render with data |
| **Data presence** | Click into individual tiles to verify they're not showing empty results |

### Quick-Reference: Running All 14 Tests

```bash
# Pre-flight check
docker compose up -d
curl -s "http://localhost:8123/?user=api&password=api" \
  --data "SELECT ServiceName, count() FROM otel_traces GROUP BY ServiceName ORDER BY count() DESC"

# Then run each test in a fresh Claude Code session:
#   T01-T03:  Auto-Discovery (Category 1)
#   T04-T08:  User-Specified Charts (Category 2)
#   T09-T14:  Vague-to-Detailed Spectrum (Category 3)
```
