# Rules & Validation Checklist

## All Rules

| # | Rule | What Breaks If Violated |
|---|------|------------------------|
| 1 | `where` uses **Lucene syntax**, NOT SQL | SQL syntax like `type = 'span' AND _service = '...'` silently fails. Use Lucene: `span_name:cpu-load-sample service:my-service` |
| 2 | `field` uses **HyperDX field names**, NOT ClickHouse columns | `_number_attributes['system.cpu.percent']` won't work. Use `system.cpu.percent`. `_duration` won't work — use `duration`. |
| 3 | Top-level array is `charts`, NOT `tiles` | Dashboard shows empty. The API expects `charts`. |
| 4 | Series `type` must be: `time`, `number`, `table`, `histogram`, `search`, `markdown` | Invalid types render blank. No `line`, `stacked_bar`, `bar`, `area` — those don't exist in this format. |
| 5 | `aggFn` must be valid | **Valid values:** `count`, `count_rate`, `sum`, `avg`, `min`, `max`, `p50`, `p90`, `p95`, `p99`, `count_distinct`, `avg_rate`, `sum_rate`, `min_rate`, `max_rate`, `p50_rate`, `p90_rate`, `p95_rate`, `p99_rate`. Invalid values fail silently. |
| 6 | `field` must be **omitted** for `count` aggFn | Including a field with `count` may cause errors. |
| 7 | `duration` is already in milliseconds | The HyperDX field name `duration` maps to `_duration` (Float64 ms). Don't divide by 1000. |
| 8 | `numberFormat` required for `type: "number"` series | KPI tiles without it show raw unformatted numbers. |
| 9 | Grid is 12 columns wide; `x + w <= 12` | Charts with `x + w > 12` overflow, overlap, or disappear. |
| 10 | `groupBy` is an array of field names | Works for `time` charts to split by a field. E.g., `["span_name"]`. |
| 11 | **Deploy via API only**, never MongoDB direct insert | Direct MongoDB inserts use the wrong team ID and dashboards won't appear in the UI. Always use `POST http://localhost:8000/api/v1/dashboards` with Bearer token auth. |
| 12 | No `source`, `displayType`, `whereLanguage`, `granularity`, `config`, `select` fields | These belong to the old MongoDB format and are silently ignored or cause errors. |
| 13 | All series in a chart must share identical `type` and identical `groupBy` | Mixed types or mismatched `groupBy` silently drops data. |
| 14 | Always emit: `asRatio: false` on every chart, `table: "logs"` (or `"metrics"` for metric data) on every series, `groupBy: []` on every `time` series, `query: ""` at dashboard level | Omitting these creates non-deterministic API behavior. |
| 15 | `h: 2` for `type: "number"` (KPI), `h: 3` for all other chart types | Inconsistent heights break row alignment. |
| 16 | Chart `id` must be descriptive kebab-case, max 36 chars (e.g., `avg-latency-ms`, `requests-over-time`). Always provide `id` explicitly. | Omitting generates UUIDs — unreadable in debugging. |
| 17 | Metrics series require `metricDataType` field (`"Gauge"`, `"Sum"`, `"Histogram"`, `"Summary"`) and `field` in `"name - DataType"` format (e.g., `"system.cpu.utilization - Gauge"`) | Missing `metricDataType` → API error "Metric data type is required". Wrong field format → silently returns no data. |
| 18 | **NEVER use `type:span` or `type:log` in `where`** | The `type` column is internal to HyperDX and NOT searchable via Lucene. Using it silently returns 0 rows. Filter by `service:X` instead, or omit the type filter. |

## Post-Generation Validation Checklist

**For every chart**, print the checklist below with `[ok]` or `[FAIL]` for each item. Fix all `[FAIL]` items before deploying. Do NOT skip this step.

- [ ] **1. `where` uses Lucene syntax** — `span_name:value service:name` NOT SQL `type = 'span' AND ...`. **NEVER use `type:span` or `type:log`** — these silently return 0 rows.
- [ ] **2. `field` uses HyperDX names** — `system.cpu.percent` NOT `_number_attributes['...']`; `duration` NOT `_duration`; `service` NOT `_service`
- [ ] **3. Top-level key is `charts`** — NOT `tiles`
- [ ] **4. Series `type` is valid** — `time`, `number`, `table`, `histogram`, `search`, or `markdown`
- [ ] **5. `aggFn` is valid** — see rule #5 above
- [ ] **6. `count` has no `field`** — field omitted or absent for count aggregation
- [ ] **7. `numberFormat` on all KPI charts** — present on every `type: "number"` series
- [ ] **8. No grid overflow** — `x + w <= 12` for every chart
- [ ] **9. No old-format fields** — no `source`, `displayType`, `whereLanguage`, `granularity`, `config`, `select`, `aggCondition`, `valueExpression`
- [ ] **10. `asRatio: false` present** — on every chart object
- [ ] **11. `table: "logs"` or `"metrics"` on all series** — `"logs"` for traces/spans/logs, `"metrics"` for metric data; except `markdown` type
- [ ] **12. `groupBy` on time series** — `groupBy: []` present on every `time` series (even when not grouping)
- [ ] **13. Multi-series consistency** — all series in a chart share identical `type` and identical `groupBy`
- [ ] **14. Height convention** — `h: 2` for `type: "number"` (KPI), `h: 3` for all others
- [ ] **15. Chart ID is kebab-case** — descriptive, max 36 chars, explicitly provided (no UUIDs)
- [ ] **16. Metrics series have `metricDataType`** — present on every series with `table: "metrics"` (`"Gauge"`, `"Sum"`, `"Histogram"`, or `"Summary"`)
- [ ] **17. Metrics `field` uses `"name - DataType"` format** — e.g., `"system.cpu.utilization - Gauge"`, not just `"system.cpu.utilization"`

### Validation Output Format

Print validation results per chart before deploying. Example:

```
Chart "total-llm-requests":
  [ok]  1. Lucene syntax
  [ok]  2. HyperDX field names
  [ok]  3. charts array
  [ok]  4. Valid series type (number)
  [ok]  5. Valid aggFn (count)
  [ok]  6. No field with count
  [ok]  7. numberFormat present
  [ok]  8. Grid: x=0 w=3 → 3 <= 12
  [ok]  9. No old-format fields
  [ok] 10. asRatio: false
  [ok] 11. table: "logs"
  [ok] 12. N/A (not time series)
  [ok] 13. Single series — consistent
  [ok] 14. h=2 (KPI)
  [ok] 15. id="total-llm-requests" (kebab-case)
  [ok] 16. N/A (not metrics)
  [ok] 17. N/A (not metrics)
  Result: ALL PASS ✓

Chart "requests-over-time":
  [ok]  1. Lucene syntax
  [ok]  2. HyperDX field names
  [ok]  3. charts array
  [ok]  4. Valid series type (time)
  [ok]  5. Valid aggFn (count)
  [ok]  6. No field with count
  [ok]  7. N/A (not KPI)
  [ok]  8. Grid: x=0 w=6 → 6 <= 12
  [ok]  9. No old-format fields
  [ok] 10. asRatio: false
  [ok] 11. table: "logs"
  [ok] 12. groupBy: [] present
  [ok] 13. Single series — consistent
  [ok] 14. h=3 (chart)
  [ok] 15. id="requests-over-time" (kebab-case)
  [ok] 16. N/A (not metrics)
  [ok] 17. N/A (not metrics)
  Result: ALL PASS ✓
```

If any item shows `[FAIL]`, fix the chart JSON and re-validate before proceeding to deploy.
