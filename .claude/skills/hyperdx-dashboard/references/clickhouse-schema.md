# ClickHouse v1 Schema Reference

## `log_stream` Table

HyperDX v1 stores all observability data (logs, traces, metrics) in a single `log_stream` table.

### Core Columns

| Column | Type | Description |
|--------|------|-------------|
| `timestamp` | DateTime64 | Event timestamp |
| `type` | String | Record type: `'span'`, `'log'` — always filter with `type = 'span'` for traces |
| `_service` | String | Service name (e.g., `'text-to-sql-service'`) |
| `_duration` | Float64 | Span duration in **milliseconds** (materialized, no division needed) |
| `span_name` | String | Operation/span name |
| `trace_id` | String | Trace ID |
| `span_id` | String | Span ID |
| `parent_span_id` | String | Parent span ID |
| `_string_attributes` | Map(String, String) | All string-valued attributes |
| `_number_attributes` | Map(String, Float64) | All numeric-valued attributes |

### Attribute Maps

Attributes are stored in two typed maps. Using the wrong map returns empty/zero silently.

**`_string_attributes`** — Map(String, String):
| Key | Example Value | Notes |
|-----|---------------|-------|
| `gen_ai.request.model` | `"claude-sonnet-4-20250514"` | Model identifier |
| `gen_ai.system` | `"anthropic"` | Provider system |
| `gen_ai.prompt.0.content` | `"What is..."` | First prompt message |
| `gen_ai.prompt.0.role` | `"user"` | First prompt role |
| `gen_ai.completion.0.content` | `"The answer..."` | First completion |
| `gen_ai.completion.0.role` | `"assistant"` | Completion role |
| `otel.status_code` | `"ERROR"` or `"OK"` | Span status |
| `otel.status_description` | `"RateLimitError: ..."` | Error details |

**`_number_attributes`** — Map(String, Float64):
| Key | Example Value | Notes |
|-----|---------------|-------|
| `gen_ai.usage.input_tokens` | `1500` | Input/prompt tokens |
| `gen_ai.usage.output_tokens` | `350` | Output/completion tokens |

### Common Mistake: Wrong Map

```sql
-- WRONG: tokens are numeric, not string
_string_attributes['gen_ai.usage.input_tokens']   -- returns ''

-- CORRECT
_number_attributes['gen_ai.usage.input_tokens']    -- returns 1500

-- WRONG: model is a string, not numeric
_number_attributes['gen_ai.request.model']         -- returns 0

-- CORRECT
_string_attributes['gen_ai.request.model']         -- returns 'claude-sonnet-4-20250514'
```

## Discovery Queries

### Find all string attributes for gen_ai spans
```sql
SELECT DISTINCT arrayJoin(_string_attributes.keys) AS attr_key
FROM log_stream
WHERE attr_key LIKE 'gen_ai.%' AND type = 'span'
ORDER BY attr_key
```

### Find all numeric attributes for gen_ai spans
```sql
SELECT DISTINCT arrayJoin(_number_attributes.keys) AS attr_key
FROM log_stream
WHERE attr_key LIKE 'gen_ai.%' AND type = 'span'
ORDER BY attr_key
```

### Data distribution overview
```sql
SELECT
    count(*) AS total_traces,
    countIf(_string_attributes['gen_ai.request.model'] != '') AS llm_traces,
    count(DISTINCT _service) AS services,
    count(DISTINCT _string_attributes['gen_ai.request.model']) AS models,
    min(timestamp) AS earliest,
    max(timestamp) AS latest
FROM log_stream
WHERE type = 'span'
```

## Common WHERE Patterns (ClickHouse SQL Only)

**IMPORTANT:** These SQL patterns are for ClickHouse discovery queries (`query_clickhouse.py --query "..."`) only. Dashboard `where` clauses use **Lucene syntax** instead (e.g., `gen_ai.request.model:* service:my-service`). See [rules.md](rules.md) for dashboard rules.

```sql
-- All LLM spans
type = 'span' AND _string_attributes['gen_ai.request.model'] != ''

-- Specific model
type = 'span' AND _string_attributes['gen_ai.request.model'] = 'claude-sonnet-4-20250514'

-- Specific service
type = 'span' AND _service = 'text-to-sql-service'

-- Error spans only
type = 'span' AND _string_attributes['otel.status_code'] = 'ERROR'

-- LLM errors only
type = 'span' AND _string_attributes['gen_ai.request.model'] != '' AND _string_attributes['otel.status_code'] = 'ERROR'

-- Specific provider
type = 'span' AND _string_attributes['gen_ai.system'] = 'anthropic'
```
