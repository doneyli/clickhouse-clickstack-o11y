# Rules & Validation Checklist

## All Rules

| # | Rule | What Breaks If Violated |
|---|------|------------------------|
| 1 | `where` uses **Lucene syntax**, NOT SQL | SQL syntax like `type = 'span' AND _service = '...'` silently fails. Use Lucene: `span_name:cpu-load-sample service:my-service` |
| 2 | `field` uses **HyperDX field names**, NOT ClickHouse columns | `_number_attributes['system.cpu.percent']` won't work. Use `system.cpu.percent`. `_duration` won't work — use `duration`. |
| 3 | Top-level array is `charts`, NOT `tiles` | Dashboard shows empty. The API expects `charts`. |
| 4 | Series `type` must be: `time`, `number`, `table`, `histogram`, `search`, `markdown` | Invalid types render blank. No `line`, `stacked_bar`, `bar`, `area` — those don't exist in this format. |
| 5 | `aggFn` must be valid | Supported: `count`, `sum`, `avg`, `min`, `max`, `p50`, `p90`, `p95`, `p99`, `count_distinct`, `last_value`, `count_per_sec`, `count_per_min`, `count_per_hour`, plus `_rate` variants. Invalid values fail silently. |
| 6 | `field` must be **omitted** for `count` aggFn | Including a field with `count` may cause errors. |
| 7 | `duration` is already in milliseconds | The HyperDX field name `duration` maps to `_duration` (Float64 ms). Don't divide by 1000. |
| 8 | `numberFormat` required for `type: "number"` series | KPI tiles without it show raw unformatted numbers. |
| 9 | Grid is 12 columns wide; `x + w <= 12` | Charts with `x + w > 12` overflow, overlap, or disappear. |
| 10 | `groupBy` is an array of field names | Works for `time` charts to split by a field. E.g., `["span_name"]`. |
| 11 | **Deploy via API only**, never MongoDB direct insert | Direct MongoDB inserts use the wrong team ID and dashboards won't appear in the UI. Always use `POST http://localhost:8000/dashboards` with Bearer token auth. |
| 12 | No `source`, `displayType`, `whereLanguage`, `granularity`, `config`, `select` fields | These belong to the old MongoDB format and are silently ignored or cause errors. |

## Post-Generation Validation Checklist

Run through this checklist for every chart before deploying:

- [ ] **1. `where` uses Lucene syntax** — `span_name:value service:name` NOT SQL `type = 'span' AND ...`
- [ ] **2. `field` uses HyperDX names** — `system.cpu.percent` NOT `_number_attributes['...']`; `duration` NOT `_duration`; `service` NOT `_service`
- [ ] **3. Top-level key is `charts`** — NOT `tiles`
- [ ] **4. Series `type` is valid** — `time`, `number`, `table`, `histogram`, `search`, or `markdown`
- [ ] **5. `aggFn` is valid** — see rule #5 above
- [ ] **6. `count` has no `field`** — field omitted or absent for count aggregation
- [ ] **7. `numberFormat` on all KPI charts** — present on every `type: "number"` series
- [ ] **8. No grid overflow** — `x + w <= 12` for every chart
- [ ] **9. No old-format fields** — no `source`, `displayType`, `whereLanguage`, `granularity`, `config`, `select`, `aggCondition`, `valueExpression`
- [ ] **10. Deploy via API** — `POST http://localhost:8000/dashboards` with `Authorization: Bearer {TOKEN}`
