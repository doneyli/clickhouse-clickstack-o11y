-- =============================================================================
-- LLM Observability Reference Queries for ClickHouse (HyperDX v1 log_stream)
-- =============================================================================
-- These queries work against the HyperDX v1 log_stream table.
-- String attributes: _string_attributes map. Numeric attributes: _number_attributes map.
-- _duration is a materialized Float64 already in milliseconds.
-- All span queries must include `type = 'span'` in their WHERE clause.
-- =============================================================================

-- 1. Total LLM requests (last 24 hours)
SELECT count(*) AS total_llm_requests
FROM log_stream
WHERE type = 'span'
  AND _string_attributes['gen_ai.request.model'] != ''
  AND timestamp >= now() - INTERVAL 24 HOUR;

-- 2. Token usage totals
SELECT
    sum(_number_attributes['gen_ai.usage.input_tokens']) AS total_input_tokens,
    sum(_number_attributes['gen_ai.usage.output_tokens']) AS total_output_tokens,
    total_input_tokens + total_output_tokens AS total_tokens
FROM log_stream
WHERE type = 'span'
  AND _string_attributes['gen_ai.request.model'] != ''
  AND timestamp >= now() - INTERVAL 24 HOUR;

-- 3. Cost estimation with model-specific pricing
SELECT
    _string_attributes['gen_ai.request.model'] AS model,
    count(*) AS requests,
    sum(_number_attributes['gen_ai.usage.input_tokens']) AS input_tokens,
    sum(_number_attributes['gen_ai.usage.output_tokens']) AS output_tokens,
    -- Approximate pricing (USD per token)
    sum(
        _number_attributes['gen_ai.usage.input_tokens'] *
        CASE _string_attributes['gen_ai.request.model']
            WHEN 'claude-sonnet-4-20250514' THEN 0.000003
            WHEN 'claude-3-5-haiku-20241022' THEN 0.0000008
            WHEN 'gpt-4o' THEN 0.0000025
            WHEN 'gpt-4o-mini' THEN 0.00000015
            ELSE 0.000003
        END
        +
        _number_attributes['gen_ai.usage.output_tokens'] *
        CASE _string_attributes['gen_ai.request.model']
            WHEN 'claude-sonnet-4-20250514' THEN 0.000015
            WHEN 'claude-3-5-haiku-20241022' THEN 0.000004
            WHEN 'gpt-4o' THEN 0.00001
            WHEN 'gpt-4o-mini' THEN 0.0000006
            ELSE 0.000015
        END
    ) AS estimated_cost_usd
FROM log_stream
WHERE type = 'span'
  AND _string_attributes['gen_ai.request.model'] != ''
  AND timestamp >= now() - INTERVAL 24 HOUR
GROUP BY model
ORDER BY estimated_cost_usd DESC;

-- 4. Latency percentiles (LLM spans only)
SELECT
    quantile(0.50)(_duration) AS p50_ms,
    quantile(0.75)(_duration) AS p75_ms,
    quantile(0.90)(_duration) AS p90_ms,
    quantile(0.95)(_duration) AS p95_ms,
    quantile(0.99)(_duration) AS p99_ms,
    max(_duration) AS max_ms
FROM log_stream
WHERE type = 'span'
  AND _string_attributes['gen_ai.request.model'] != ''
  AND timestamp >= now() - INTERVAL 24 HOUR;

-- 5. Hourly token usage
SELECT
    toStartOfHour(timestamp) AS hour,
    sum(_number_attributes['gen_ai.usage.input_tokens']) AS input_tokens,
    sum(_number_attributes['gen_ai.usage.output_tokens']) AS output_tokens
FROM log_stream
WHERE type = 'span'
  AND _string_attributes['gen_ai.request.model'] != ''
  AND timestamp >= now() - INTERVAL 24 HOUR
GROUP BY hour
ORDER BY hour;

-- 6. Requests by model and service
SELECT
    _service,
    _string_attributes['gen_ai.request.model'] AS model,
    count(*) AS requests,
    round(avg(_duration), 2) AS avg_latency_ms
FROM log_stream
WHERE type = 'span'
  AND _string_attributes['gen_ai.request.model'] != ''
  AND timestamp >= now() - INTERVAL 24 HOUR
GROUP BY _service, model
ORDER BY requests DESC;

-- 7. Error rate analysis
SELECT
    _string_attributes['gen_ai.request.model'] AS model,
    count(*) AS total_requests,
    countIf(_string_attributes['otel.status_code'] = 'ERROR') AS errors,
    round(countIf(_string_attributes['otel.status_code'] = 'ERROR') * 100.0 / count(*), 2) AS error_rate_pct
FROM log_stream
WHERE type = 'span'
  AND _string_attributes['gen_ai.request.model'] != ''
  AND timestamp >= now() - INTERVAL 24 HOUR
GROUP BY model
ORDER BY error_rate_pct DESC;

-- 8. Recent LLM calls with prompt/completion previews
SELECT
    timestamp,
    _service,
    span_name,
    _string_attributes['gen_ai.request.model'] AS model,
    _string_attributes['gen_ai.system'] AS system,
    _number_attributes['gen_ai.usage.input_tokens'] AS input_tokens,
    _number_attributes['gen_ai.usage.output_tokens'] AS output_tokens,
    round(_duration, 2) AS latency_ms,
    substring(_string_attributes['gen_ai.prompt.0.content'], 1, 80) AS prompt_preview,
    substring(_string_attributes['gen_ai.completion.0.content'], 1, 80) AS completion_preview
FROM log_stream
WHERE type = 'span'
  AND _string_attributes['gen_ai.request.model'] != ''
ORDER BY timestamp DESC
LIMIT 20;
