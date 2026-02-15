#!/usr/bin/env python3
"""
Generate realistic LLM observability demo trace data via OpenTelemetry.

No real LLM calls are made -- this purely simulates trace data with
gen_ai.* semantic conventions for testing HyperDX dashboards.

Usage:
    python generate_demo_data.py                          # 100 traces (default)
    python generate_demo_data.py --count 500              # 500 traces
    python generate_demo_data.py --services text-to-sql   # one service only
    python generate_demo_data.py --error-rate 0.1         # 10% error rate
"""

import argparse
import os
import random
import time
import uuid
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.trace import StatusCode

load_dotenv()

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

SERVICES = {
    "text-to-sql-service": {
        "models": ["claude-sonnet-4-20250514", "gpt-4o"],
        "systems": ["anthropic", "openai"],
    },
    "vector-rag-service": {
        "models": ["claude-sonnet-4-20250514", "claude-3-5-haiku-20241022"],
        "systems": ["anthropic", "anthropic"],
    },
    "chatbot-service": {
        "models": ["gpt-4o", "gpt-4o-mini"],
        "systems": ["openai", "openai"],
    },
}

SAMPLE_QUESTIONS = [
    "What is the average house price in London?",
    "Show me sales by region for Q4 2024",
    "How many users signed up last month?",
    "What are the top 10 products by revenue?",
    "Compare customer churn rates across segments",
    "What is our monthly recurring revenue trend?",
    "Show me the error rate for the payment service",
    "How many active users do we have today?",
    "What is the average response time for our API?",
    "List all orders with total above $1000",
    "What are the most common support ticket categories?",
    "Show me the conversion funnel for the signup flow",
    "What is our customer acquisition cost by channel?",
    "How does this quarter compare to last quarter?",
    "What are the peak usage hours for our platform?",
]

SAMPLE_SQL = [
    "SELECT AVG(price) FROM houses WHERE city = 'London'",
    "SELECT region, SUM(amount) FROM sales WHERE quarter = 'Q4' GROUP BY region",
    "SELECT COUNT(*) FROM users WHERE created_at >= '2024-12-01'",
    "SELECT product_name, SUM(revenue) FROM orders GROUP BY product_name ORDER BY 2 DESC LIMIT 10",
    "SELECT segment, COUNT(*) * 100.0 / total FROM customers GROUP BY segment",
]

SAMPLE_ANSWERS = [
    "Based on the data, the average house price in London is approximately 523,000 GBP.",
    "Here are the sales figures by region for Q4 2024: North: $1.2M, South: $890K, East: $1.1M, West: $950K.",
    "A total of 12,453 new users signed up last month, representing a 15% increase from the previous month.",
    "The top products by revenue are: Widget Pro ($450K), Dashboard Plus ($380K), Analytics Suite ($290K).",
    "Customer churn analysis shows Enterprise at 2.1%, SMB at 5.8%, and Startup at 12.3%.",
    "Monthly recurring revenue has grown from $2.1M to $2.8M over the last 6 months.",
    "The payment service error rate is currently 0.3%, down from 1.2% last week.",
    "There are currently 45,231 active users today, which is within the normal range.",
]

ERROR_TYPES = [
    ("RateLimitError", "Rate limit exceeded. Please retry after 30 seconds."),
    ("TimeoutError", "Request timed out after 30000ms."),
    ("InvalidRequestError", "Maximum context length exceeded: 128000 tokens."),
]


_providers: dict = {}


def create_tracer(service_name: str) -> trace.Tracer:
    """Create (or reuse) an OpenTelemetry tracer for the given service."""
    if service_name not in _providers:
        resource = Resource.create({
            "service.name": service_name,
            "service.version": "1.0.0",
            "deployment.environment": "demo",
        })
        provider = TracerProvider(resource=resource)
        endpoint = os.getenv("OTLP_ENDPOINT", "http://localhost:4318") + "/v1/traces"
        exporter = OTLPSpanExporter(endpoint=endpoint)
        provider.add_span_processor(BatchSpanProcessor(exporter, max_export_batch_size=512))
        _providers[service_name] = provider
    return _providers[service_name].get_tracer(service_name)


def random_latency(base_ms: float, jitter_ms: float, outlier_chance: float = 0.05) -> float:
    """Return a latency in seconds with occasional outliers."""
    if random.random() < outlier_chance:
        return (base_ms * random.uniform(3, 10) + random.uniform(0, jitter_ms)) / 1000.0
    return (base_ms + random.uniform(0, jitter_ms)) / 1000.0


def random_past_time(hours: int = 24) -> datetime:
    """Return a random datetime within the last `hours` hours."""
    offset = random.uniform(0, hours * 3600)
    return datetime.now(timezone.utc) - timedelta(seconds=offset)


def set_llm_attributes(span, service_name: str, is_error: bool, error_rate: float):
    """Set gen_ai.* semantic convention attributes on a span."""
    svc = SERVICES[service_name]
    model_idx = random.randint(0, len(svc["models"]) - 1)
    model = svc["models"][model_idx]
    system = svc["systems"][model_idx]

    question = random.choice(SAMPLE_QUESTIONS)
    answer = random.choice(SAMPLE_ANSWERS)

    span.set_attribute("gen_ai.system", system)
    span.set_attribute("gen_ai.request.model", model)
    span.set_attribute("gen_ai.prompt.0.role", "user")
    span.set_attribute("gen_ai.prompt.0.content", question)

    if is_error:
        error_type, error_msg = random.choice(ERROR_TYPES)
        span.set_attribute("gen_ai.completion.0.role", "error")
        span.set_attribute("gen_ai.completion.0.content", f"{error_type}: {error_msg}")
        span.set_status(StatusCode.ERROR, error_msg)
        span.set_attribute("error.type", error_type)
        input_tokens = random.randint(50, 500)
        output_tokens = 0
    else:
        span.set_attribute("gen_ai.completion.0.role", "assistant")
        span.set_attribute("gen_ai.completion.0.content", answer)
        span.set_status(StatusCode.OK)
        input_tokens = random.randint(50, 5000)
        output_tokens = random.randint(100, 3000)

    span.set_attribute("gen_ai.usage.input_tokens", input_tokens)
    span.set_attribute("gen_ai.usage.output_tokens", output_tokens)

    return model, input_tokens, output_tokens


def generate_text_to_sql(tracer, error_rate: float) -> dict:
    """Generate a text-to-sql-service trace hierarchy."""
    is_error = random.random() < error_rate
    stats = {"input_tokens": 0, "output_tokens": 0, "model": ""}

    with tracer.start_as_current_span("text-to-sql-query") as root:
        root.set_attribute("query.id", str(uuid.uuid4()))

        # Child: parse-question (no LLM)
        with tracer.start_as_current_span("parse-question") as parse_span:
            time.sleep(random_latency(20, 30))
            parse_span.set_attribute("parse.method", "regex+nlp")

        # Child: generate-sql (LLM call)
        with tracer.start_as_current_span("generate-sql") as gen_span:
            model, inp, out = set_llm_attributes(gen_span, "text-to-sql-service", is_error, error_rate)
            stats["model"] = model
            stats["input_tokens"] += inp
            stats["output_tokens"] += out
            gen_span.set_attribute("gen_ai.completion.0.content",
                                   random.choice(SAMPLE_SQL) if not is_error else gen_span.attributes.get("gen_ai.completion.0.content", ""))
            time.sleep(random_latency(500, 2000))

        if not is_error:
            # Child: execute-sql (no LLM)
            with tracer.start_as_current_span("execute-sql") as exec_span:
                time.sleep(random_latency(100, 500))
                exec_span.set_attribute("sql.rows_returned", random.randint(1, 1000))

            # Child: format-response (LLM call)
            with tracer.start_as_current_span("format-response") as fmt_span:
                model, inp, out = set_llm_attributes(fmt_span, "text-to-sql-service", False, 0)
                stats["input_tokens"] += inp
                stats["output_tokens"] += out
                time.sleep(random_latency(300, 1000))

    return stats


def generate_vector_rag(tracer, error_rate: float) -> dict:
    """Generate a vector-rag-service trace hierarchy."""
    is_error = random.random() < error_rate
    stats = {"input_tokens": 0, "output_tokens": 0, "model": ""}

    with tracer.start_as_current_span("rag-pipeline") as root:
        root.set_attribute("pipeline.id", str(uuid.uuid4()))

        # Child: embed-query
        with tracer.start_as_current_span("embed-query") as embed_span:
            time.sleep(random_latency(50, 100))
            embed_span.set_attribute("embedding.model", "text-embedding-3-small")
            embed_span.set_attribute("embedding.dimensions", 1536)

        # Child: vector-search (no LLM)
        with tracer.start_as_current_span("vector-search") as search_span:
            time.sleep(random_latency(30, 80))
            search_span.set_attribute("vector.results", random.randint(3, 10))
            search_span.set_attribute("vector.similarity_threshold", 0.75)

        # Child: generate-answer (LLM call)
        with tracer.start_as_current_span("generate-answer") as gen_span:
            model, inp, out = set_llm_attributes(gen_span, "vector-rag-service", is_error, error_rate)
            stats["model"] = model
            stats["input_tokens"] += inp
            stats["output_tokens"] += out
            time.sleep(random_latency(800, 3000))

    return stats


def generate_chatbot(tracer, error_rate: float) -> dict:
    """Generate a chatbot-service trace (single LLM span)."""
    is_error = random.random() < error_rate
    stats = {"input_tokens": 0, "output_tokens": 0, "model": ""}

    with tracer.start_as_current_span("chat-completion") as span:
        model, inp, out = set_llm_attributes(span, "chatbot-service", is_error, error_rate)
        stats["model"] = model
        stats["input_tokens"] += inp
        stats["output_tokens"] += out
        span.set_attribute("chat.conversation_id", str(uuid.uuid4()))
        span.set_attribute("chat.turn", random.randint(1, 20))
        time.sleep(random_latency(400, 2000))

    return stats


SERVICE_GENERATORS = {
    "text-to-sql-service": generate_text_to_sql,
    "vector-rag-service": generate_vector_rag,
    "chatbot-service": generate_chatbot,
}

SERVICE_ALIASES = {
    "text-to-sql": "text-to-sql-service",
    "vector-rag": "vector-rag-service",
    "chatbot": "chatbot-service",
}


def main():
    parser = argparse.ArgumentParser(description="Generate demo LLM observability traces")
    parser.add_argument("--count", type=int, default=100, help="Number of traces to generate (default: 100)")
    parser.add_argument("--services", type=str, default=None,
                        help="Comma-separated list of services (text-to-sql, vector-rag, chatbot)")
    parser.add_argument("--error-rate", type=float, default=0.05,
                        help="Error rate 0.0-1.0 (default: 0.05)")
    args = parser.parse_args()

    # Resolve service list
    if args.services:
        service_names = []
        for s in args.services.split(","):
            s = s.strip()
            resolved = SERVICE_ALIASES.get(s, s)
            if resolved not in SERVICE_GENERATORS:
                print(f"Unknown service: {s}")
                print(f"Available: {', '.join(SERVICE_ALIASES.keys())}")
                return
            service_names.append(resolved)
    else:
        service_names = list(SERVICE_GENERATORS.keys())

    print(f"Generating {args.count} traces across {len(service_names)} service(s)...")
    print(f"  Services: {', '.join(service_names)}")
    print(f"  Error rate: {args.error_rate:.0%}")
    print(f"  OTLP endpoint: {os.getenv('OTLP_ENDPOINT', 'http://localhost:4318')}")
    print()

    # Track stats
    stats = {svc: {"count": 0, "input_tokens": 0, "output_tokens": 0} for svc in service_names}

    for i in range(args.count):
        service_name = random.choice(service_names)
        tracer = create_tracer(service_name)
        generator = SERVICE_GENERATORS[service_name]

        result = generator(tracer, args.error_rate)

        stats[service_name]["count"] += 1
        stats[service_name]["input_tokens"] += result["input_tokens"]
        stats[service_name]["output_tokens"] += result["output_tokens"]

        if (i + 1) % 25 == 0:
            print(f"  Generated {i + 1}/{args.count} traces...")

    # Flush all spans from all providers
    for provider in _providers.values():
        if hasattr(provider, "force_flush"):
            provider.force_flush()

    # Print summary
    print()
    print("=" * 60)
    print("GENERATION COMPLETE")
    print("=" * 60)
    total_input = 0
    total_output = 0
    for svc, s in stats.items():
        print(f"  {svc}: {s['count']} traces, {s['input_tokens']:,} input tokens, {s['output_tokens']:,} output tokens")
        total_input += s["input_tokens"]
        total_output += s["output_tokens"]
    print(f"  TOTAL: {args.count} traces, {total_input:,} input tokens, {total_output:,} output tokens")
    print()
    ui_url = os.getenv("HYPERDX_UI_URL", "http://localhost:8080")
    print(f"View traces in HyperDX: {ui_url}/search")
    print()


if __name__ == "__main__":
    main()
