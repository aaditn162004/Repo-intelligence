"""
OpenTelemetry setup for RepoIntel.

Phase 1 / free by default: traces are printed to the console (stdout). No
external service, no account, no cost. If you later want a dashboard (SigNoz,
Grafana Cloud, Datadog, …) set OTEL_EXPORTER_OTLP_ENDPOINT and the same traces
are shipped there instead — no code change.

Tracing is OFF unless you opt in, so production stays quiet:
  - set OTEL_ENABLED=true                -> console exporter (Phase 1)
  - set OTEL_EXPORTER_OTLP_ENDPOINT=...  -> OTLP exporter (implies enabled)

Everything here is no-op-safe: if tracing is disabled, `get_tracer()` returns
the OpenTelemetry no-op tracer, so the `@traced` decorator and any spans added
around the codebase cost effectively nothing and change no behaviour.
"""

from __future__ import annotations

import functools
import inspect
import os
from typing import Callable, Optional

import structlog
from opentelemetry import trace

logger = structlog.get_logger()

_SERVICE_NAME = os.getenv("OTEL_SERVICE_NAME", "repointel-api")
_configured = False


def _is_enabled() -> bool:
    if os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT"):
        return True
    return os.getenv("OTEL_ENABLED", "").strip().lower() in ("1", "true", "yes", "on")


def setup_telemetry(app=None) -> None:
    """Configure the global tracer provider + auto-instrumentation.

    Idempotent and safe to call when disabled. Pass the FastAPI `app` to enable
    automatic per-request spans.
    """
    global _configured
    if _configured:
        return

    if not _is_enabled():
        logger.info(
            "OpenTelemetry disabled — set OTEL_ENABLED=true for console traces, "
            "or OTEL_EXPORTER_OTLP_ENDPOINT to ship to a backend"
        )
        return

    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import (
        BatchSpanProcessor,
        ConsoleSpanExporter,
        SimpleSpanProcessor,
    )

    provider = TracerProvider(resource=Resource.create({"service.name": _SERVICE_NAME}))

    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    if endpoint:
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

        provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
        logger.info("OpenTelemetry: exporting traces via OTLP", endpoint=endpoint)
    else:
        # Console is immediate (SimpleSpanProcessor) so you see spans as they close.
        provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
        logger.info("OpenTelemetry: exporting traces to console (Phase 1)")

    trace.set_tracer_provider(provider)

    _instrument_libraries(app)
    _configured = True


def _instrument_libraries(app) -> None:
    """Best-effort auto-instrumentation. A missing optional package is non-fatal."""
    if app is not None:
        try:
            from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

            FastAPIInstrumentor.instrument_app(app)
        except Exception as exc:  # noqa: BLE001
            logger.warning("OTel FastAPI instrumentation skipped", error=str(exc))

    try:
        from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

        HTTPXClientInstrumentor().instrument()
    except Exception as exc:  # noqa: BLE001
        logger.warning("OTel httpx instrumentation skipped", error=str(exc))

    try:
        from opentelemetry.instrumentation.redis import RedisInstrumentor

        RedisInstrumentor().instrument()
    except Exception as exc:  # noqa: BLE001
        logger.warning("OTel redis instrumentation skipped", error=str(exc))


def get_tracer(name: str = "repointel"):
    """Return a tracer. No-op tracer when telemetry is disabled."""
    return trace.get_tracer(name)


def traced(name: Optional[str] = None) -> Callable:
    """Decorator that wraps a function call in a span (sync or async).

    No-op when telemetry is disabled. Exceptions are recorded on the span and the
    span status is set to error automatically (start_as_current_span default).

        @traced("agent.planner")
        def planner_node(state): ...
    """

    def decorator(fn: Callable) -> Callable:
        span_name = name or f"{fn.__module__}.{fn.__qualname__}"

        if inspect.iscoroutinefunction(fn):

            @functools.wraps(fn)
            async def async_wrapper(*args, **kwargs):
                with get_tracer().start_as_current_span(span_name):
                    return await fn(*args, **kwargs)

            return async_wrapper

        @functools.wraps(fn)
        def sync_wrapper(*args, **kwargs):
            with get_tracer().start_as_current_span(span_name):
                return fn(*args, **kwargs)

        return sync_wrapper

    return decorator
