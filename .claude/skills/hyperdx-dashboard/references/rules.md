# Rules & Validation Checklist

## All Rules

| # | Rule | What Breaks If Violated |
|---|------|------------------------|
| 1 | `where` uses **Lucene syntax** with `whereLanguage: "lucene"` | SQL syntax like `ServiceName = 'checkout'` in where fails. Use Lucene: `service:checkout span_name:my-span` |
| 2 | `valueExpression` uses **ClickHouse column names** (e.g., `Duration`, `ServiceName`) | HyperDX abstracted names like `duration`, `service` don't work in valueExpression |
| 3 | Top-level array is `tiles`, NOT `charts` | API validation error — `tiles` and `tags` are required |
| 4 | `displayType` must be valid: `line`, `stacked_bar`, `number`, `table`, `markdown` | Invalid types render blank. No `time`, `histogram`, `search` — those are old format. |
| 5 | `aggFn` must be valid | **Standard:** `count`, `sum`, `avg`, `min`, `max`, `count_distinct`, `last_value`. **Quantile:** `quantile` with `level` field (e.g., `0.95`). No `p50`/`p90`/`p95`/`p99` — use `quantile` + `level`. |
| 6 | `valueExpression: ""` for `count` aggFn | Including a column with `count` may cause errors. |
| 7 | `Duration` in `otel_traces` is **nanoseconds** (UInt64) | Not milliseconds. HyperDX UI handles display formatting. |
| 8 | `numberFormat` required for `displayType: "number"` tiles | KPI tiles without it show raw unformatted numbers. |
| 9 | Grid is **24 columns wide**; `x + w <= 24` | Tiles with `x + w > 24` overflow, overlap, or disappear. |
| 10 | `groupBy` is array of **objects** `[{"valueExpression": "Col"}]` or empty `[]` | Passing strings like `["ServiceName"]` fails Zod validation. |
| 11 | **Deploy via API only** — `POST http://localhost:8000/dashboards` | No auth required for local mode. Direct DB inserts may cause issues. |
| 12 | `tags: []` required at dashboard level | API validation error if missing. |
| 13 | All select items in a tile share the same `where`, `groupBy`, `displayType` | Per-item filtering uses `aggCondition`, not separate `where`. |
| 14 | Always include: `whereLanguage: "lucene"` on every tile config, `groupBy: []` on time tiles | Omitting `whereLanguage` may default to wrong parser. |
| 15 | `h: 2` for `displayType: "number"` (KPI), `h: 3` for all other tile types | Inconsistent heights break row alignment. |
| 16 | Tile `id` must be descriptive kebab-case, max 36 chars | Omitting generates UUIDs — unreadable in debugging. |
| 17 | Metrics tiles need `metricName` and `metricDataType` in config | Missing → no data or API error. `metricDataType`: `"Gauge"`, `"Sum"`, `"Histogram"`, `"Summary"`. |
| 18 | **NEVER use `type:span` or `type:log`** in `where` | Internal field — not searchable via Lucene. Silently returns 0 rows. |
| 19 | `select` items require all 3 fields: `aggFn`, `valueExpression`, `aggCondition` | Missing fields cause Zod validation error. Use empty `""` for optional fields. |
| 20 | Quantile uses `aggFn: "quantile"` + `level: 0.95` | Not `p95`. Old `p50`/`p90`/`p95`/`p99` aggFn values don't exist. |
| 21 | `source` is a string (`"traces"`, `"logs"`, `"metrics"`) NOT a source ID | Source IDs are dynamic and change per container restart. |

## Post-Generation Validation Checklist

**For every tile**, print the checklist below with `[ok]` or `[FAIL]` for each item. Fix all `[FAIL]` items before deploying. Do NOT skip this step.

- [ ] **1. `where` uses Lucene syntax** — `service:value span_name:value` NOT SQL. `whereLanguage: "lucene"` present. **NEVER `type:span` or `type:log`**.
- [ ] **2. `valueExpression` uses ClickHouse column names** — `Duration` NOT `duration`; `ServiceName` NOT `service`; `SpanAttributes['key']` NOT just `key`
- [ ] **3. Top-level key is `tiles`** — NOT `charts`
- [ ] **4. `displayType` is valid** — `line`, `stacked_bar`, `number`, `table`, or `markdown`
- [ ] **5. `aggFn` is valid** — `count`, `sum`, `avg`, `min`, `max`, `count_distinct`, `last_value`, or `quantile` (with `level`)
- [ ] **6. `count` has empty `valueExpression`** — `valueExpression: ""` for count aggregation
- [ ] **7. `numberFormat` on all KPI tiles** — present on every `displayType: "number"` config
- [ ] **8. No grid overflow** — `x + w <= 24` for every tile
- [ ] **9. `select` items have all 3 fields** — `aggFn`, `valueExpression`, `aggCondition` all present
- [ ] **10. `tags: []` at dashboard level** — required even if empty
- [ ] **11. `source` on all tile configs** — `"traces"`, `"logs"`, or `"metrics"`
- [ ] **12. `groupBy` on time tiles** — `groupBy: []` present (even when not grouping), items are objects
- [ ] **13. Multi-select consistency** — all select items share the tile's `where` and `groupBy`
- [ ] **14. Height convention** — `h: 2` for `displayType: "number"` (KPI), `h: 3` for all others
- [ ] **15. Tile ID is kebab-case** — descriptive, max 36 chars, explicitly provided
- [ ] **16. Metrics tiles have `metricName` and `metricDataType`** — present on every metrics source tile
- [ ] **17. `whereLanguage: "lucene"` present** — on every tile config

### Validation Output Format

Print validation results per tile before deploying. Example:

```
Tile "total-requests":
  [ok]  1. Lucene syntax, whereLanguage present
  [ok]  2. valueExpression uses column names
  [ok]  3. tiles array
  [ok]  4. Valid displayType (number)
  [ok]  5. Valid aggFn (count)
  [ok]  6. Empty valueExpression for count
  [ok]  7. numberFormat present
  [ok]  8. Grid: x=0 w=6 → 6 <= 24
  [ok]  9. Select items complete (aggFn, valueExpression, aggCondition)
  [ok] 10. tags present
  [ok] 11. source: "traces"
  [ok] 12. groupBy: [] present
  [ok] 13. Single select — consistent
  [ok] 14. h=2 (KPI)
  [ok] 15. id="total-requests" (kebab-case)
  [ok] 16. N/A (not metrics)
  [ok] 17. whereLanguage: "lucene" present
  Result: ALL PASS

Tile "latency-over-time":
  [ok]  1. Lucene syntax, whereLanguage present
  [ok]  2. valueExpression: "Duration" (column name)
  [ok]  3. tiles array
  [ok]  4. Valid displayType (line)
  [ok]  5. Valid aggFn (avg)
  [ok]  6. N/A (not count)
  [ok]  7. N/A (not KPI)
  [ok]  8. Grid: x=0 w=12 → 12 <= 24
  [ok]  9. Select items complete
  [ok] 10. tags present
  [ok] 11. source: "traces"
  [ok] 12. groupBy: [{"valueExpression": "SpanName"}]
  [ok] 13. Single select — consistent
  [ok] 14. h=3 (chart)
  [ok] 15. id="latency-over-time" (kebab-case)
  [ok] 16. N/A (not metrics)
  [ok] 17. whereLanguage: "lucene" present
  Result: ALL PASS
```

If any item shows `[FAIL]`, fix the tile JSON and re-validate before proceeding to deploy.
