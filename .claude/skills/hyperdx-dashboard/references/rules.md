# Rules & Validation Checklist (v2 API)

## All Rules

| # | Rule | What Breaks If Violated |
|---|------|------------------------|
| 1 | `where` uses **Lucene syntax** with `whereLanguage: "lucene"` on each series | SQL syntax like `ServiceName = 'checkout'` in where fails. Use Lucene: `ServiceName:checkout SpanName:my-span`. Lucene uses **ClickHouse column names directly** — NOT HyperDX-mapped names like `service`, `level`, `span_name`. |
| 2 | `field` uses **ClickHouse column names** (e.g., `Duration`, `ServiceName`) | HyperDX abstracted names like `duration`, `service` don't work in field |
| 3 | Top-level is `tiles` with `series` array. NOT `charts`, NOT `config.select[]` | API validation error — v2 uses `tiles[].series[]` |
| 4 | Series `type` must be valid: `time`, `number`, `table`, `search`, `markdown` | Zod discriminated union validation error |
| 5 | `displayType` only on `type: "time"` series: `line` or `stacked_bar` | Other series types have no displayType field |
| 6 | `aggFn` must be valid: `avg`, `count`, `count_distinct`, `last_value`, `max`, `min`, `quantile`, `sum`, `any`, `none` | Zod enum validation error. No `p50`/`p90`/`p95`/`p99` — use `quantile` + `level`. |
| 7 | `field: ""` (or omit) for `count` aggFn | Including a column with `count` may cause errors |
| 8 | `Duration` in `otel_traces` is **nanoseconds** (UInt64) | Not milliseconds. HyperDX UI handles display formatting. |
| 9 | `numberFormat` recommended for `type: "number"` series | KPI tiles without it show raw unformatted numbers |
| 10 | Grid is **24 columns wide**; `x + w <= 24` | Tiles with `x + w > 24` overflow, overlap, or disappear |
| 11 | `groupBy` is array of **strings** `["Col"]` or `[]`. Max 10. Only on `time`/`table`. | Objects like `{"valueExpression": "Col"}` fail v2 validation |
| 12 | **Deploy via v2 API** — `POST /api/v2/dashboards` with Bearer auth | Unauthenticated requests get 401. Use `clickstack-local-v2-api-key`. |
| 13 | `tags` at dashboard level (array of strings, can be empty) | Max 50 tags, max 32 chars each |
| 14 | Each series has its own `where` filter — no shared filter | Unlike internal API, v2 has per-series where |
| 15 | `whereLanguage: "lucene"` on every series that has a `where` | Omitting may default to wrong parser |
| 16 | `h: 3` for `type: "number"` (KPI), `h: 6` for `type: "time"`, `h: 5` for `type: "table"` | Inconsistent heights break row alignment |
| 17 | Tile `name` is **required**, top-level on tile (NOT nested in config) | API validation error |
| 18 | Metrics series need `metricName` and `metricDataType` (lowercase) | Missing → no data or API error. Values: `gauge`, `sum`, `histogram`, `summary`, `exponential histogram`. |
| 19 | **NEVER use `type:span` or `type:log`** in `where` | Internal field — not searchable via Lucene. Silently returns 0 rows. |
| 20 | Quantile uses `aggFn: "quantile"` + `level: 0.95` | Not `p95`. Old `p50`/`p90`/`p95`/`p99` aggFn values don't exist. |
| 21 | `sourceId` must be a **source ID** from `GET /sources` (NOT a kind string) | Kind strings like `"traces"` are rejected. Fetch IDs: `SRC = {s['kind']: s['id'] for s in requests.get('/sources').json()}` |
| 22 | All series in a tile must have the **same `type`** | Zod validation error: "All series must have the same type" |
| 23 | Max 5 series per tile | Array max length enforced by Zod |

## Post-Generation Validation Checklist

**For every tile**, print the checklist below with `[ok]` or `[FAIL]` for each item. Fix all `[FAIL]` items before deploying. Do NOT skip this step.

- [ ] **1. `where` uses Lucene syntax with ClickHouse column names** — `ServiceName:value SpanName:value` NOT SQL, NOT HyperDX names (`service`, `level`, `span_name`). `whereLanguage: "lucene"` present on each series. **NEVER `type:span` or `type:log`**.
- [ ] **2. `field` uses ClickHouse column names** — `Duration` NOT `duration`; `ServiceName` NOT `service`; `SpanAttributes['key']` NOT just `key`
- [ ] **3. Top-level key is `tiles` with `series`** — NOT `charts`, NOT `config.select[]`
- [ ] **4. Series `type` is valid** — `time`, `number`, `table`, `search`, or `markdown`
- [ ] **5. `aggFn` is valid** — `avg`, `count`, `count_distinct`, `last_value`, `max`, `min`, `quantile`, `sum`, `any`, or `none` (with `level` for quantile)
- [ ] **6. `count` has empty `field`** — `field: ""` or field omitted for count aggregation
- [ ] **7. `numberFormat` on KPI tiles** — present on `type: "number"` series for readable display
- [ ] **8. No grid overflow** — `x + w <= 24` for every tile
- [ ] **9. `groupBy` is string array** — `["ServiceName"]` or `[]`, NOT objects. Only on `time`/`table`.
- [ ] **10. `tags` at dashboard level** — present (even if empty `[]`)
- [ ] **11. `sourceId` is a source ID** — from `GET /sources`, NOT a kind string like `"traces"`
- [ ] **12. All series have same `type`** — within each tile, every series must share the same type
- [ ] **13. Height convention** — `h: 3` for number (KPI), `h: 6` for time, `h: 5` for table
- [ ] **14. Tile `name` is present** — required, top-level on tile
- [ ] **15. Metrics series have `metricName` and `metricDataType`** — present on every metrics source series, `metricDataType` is lowercase
- [ ] **16. `whereLanguage: "lucene"` present** — on every series with a `where` clause
- [ ] **17. `displayType` only on `time` series** — `"line"` or `"stacked_bar"`. Not on number/table/search/markdown.

### Validation Output Format

Print validation results per tile before deploying. Example:

```
Tile "Total Requests":
  [ok]  1. Lucene syntax, whereLanguage present
  [ok]  2. field uses column names
  [ok]  3. tiles with series array
  [ok]  4. Valid series type (number)
  [ok]  5. Valid aggFn (count)
  [ok]  6. Empty field for count
  [ok]  7. numberFormat present
  [ok]  8. Grid: x=0 w=6 → 6 <= 24
  [ok]  9. groupBy: N/A (number type)
  [ok] 10. tags present
  [ok] 11. sourceId: <trace-source-id> (from GET /sources)
  [ok] 12. All series type: number
  [ok] 13. h=3 (KPI)
  [ok] 14. name="Total Requests" present
  [ok] 15. N/A (not metrics)
  [ok] 16. whereLanguage: "lucene" present
  [ok] 17. N/A (number type, no displayType)
  Result: ALL PASS

Tile "Latency Over Time":
  [ok]  1. Lucene syntax, whereLanguage present
  [ok]  2. field: "Duration" (column name)
  [ok]  3. tiles with series array
  [ok]  4. Valid series type (time)
  [ok]  5. Valid aggFn (avg)
  [ok]  6. N/A (not count)
  [ok]  7. N/A (not KPI)
  [ok]  8. Grid: x=0 w=12 → 12 <= 24
  [ok]  9. groupBy: ["SpanName"] (string array)
  [ok] 10. tags present
  [ok] 11. sourceId: <trace-source-id> (from GET /sources)
  [ok] 12. All series type: time
  [ok] 13. h=6 (time chart)
  [ok] 14. name="Latency Over Time" present
  [ok] 15. N/A (not metrics)
  [ok] 16. whereLanguage: "lucene" present
  [ok] 17. displayType: "line" (time series only)
  Result: ALL PASS
```

If any item shows `[FAIL]`, fix the tile JSON and re-validate before proceeding to deploy.
