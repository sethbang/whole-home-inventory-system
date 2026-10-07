"""OpenTelemetry setup, gated behind ``OTEL_ENABLED``.

The tracer provider is installed lazily — only when the feature is turned
on — so a self-hosted deployment that doesn't care about tracing pays
nothing at runtime. When enabled, spans are exported via OTLP gRPC to
``OTEL_EXPORTER_OTLP_ENDPOINT``; FastAPI request spans and SQLAlchemy
engine spans are both captured.

Call order matters: this needs to run AFTER ``FastAPI()`` is instantiated
but BEFORE the first request is served, because the FastAPI instrumentor
wraps the app's middleware stack.
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import FastAPI

from .settings import settings

logger = logging.getLogger(__name__)


def setup_telemetry(
    app: FastAPI,
    *,
    force_processor: Optional[object] = None,
) -> bool:
    """Install tracer provider and instrument FastAPI + SQLAlchemy.

    Returns True when telemetry was wired up, False when skipped. Safe to
    call multiple times — subsequent calls after the first enabled run are
    no-ops because the OTel SDK only allows one global tracer provider.

    ``force_processor`` is a test-only escape hatch: pass a
    ``SimpleSpanProcessor(InMemorySpanExporter())`` and the OTLP exporter
    wiring is skipped.
    """
    if not settings.OTEL_ENABLED and force_processor is None:
        logger.debug("OTEL_ENABLED=false; skipping tracer setup")
        return False

    # Import lazily so production startup doesn't pay the SDK import cost
    # when the feature is off.
    from opentelemetry import trace
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    # Respect an already-installed provider (pytest-order issue if a prior
    # test enabled telemetry, for example). OTel's API doesn't expose a
    # "replace" so we check for the default NoOp provider and only swap
    # it out.
    current = trace.get_tracer_provider()
    if isinstance(current, TracerProvider):
        provider = current
    else:
        provider = TracerProvider(
            resource=Resource.create({"service.name": settings.OTEL_SERVICE_NAME})
        )
        trace.set_tracer_provider(provider)

    if force_processor is not None:
        provider.add_span_processor(force_processor)
    else:
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
            OTLPSpanExporter,
        )

        exporter = OTLPSpanExporter(endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT)
        provider.add_span_processor(BatchSpanProcessor(exporter))
        logger.info(
            "OTEL enabled; exporting to %s", settings.OTEL_EXPORTER_OTLP_ENDPOINT
        )

    # Instrumentors are idempotent; calling twice is safe.
    FastAPIInstrumentor.instrument_app(app)
    # SQLAlchemyInstrumentor wraps every Engine created before or after the
    # call, which is what we want for the sync engine in database.py.
    SQLAlchemyInstrumentor().instrument(enable_commenter=False)
    return True
