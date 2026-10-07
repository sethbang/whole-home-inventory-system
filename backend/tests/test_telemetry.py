"""OpenTelemetry skeleton tests.

``setup_telemetry`` is gated by ``OTEL_ENABLED``. When off it's a no-op
and no spans are produced. When on we install a tracer provider and
instrument FastAPI + SQLAlchemy. The test injects an in-memory exporter
via the ``force_processor`` escape hatch so we can assert spans are
actually generated for a request without standing up an OTLP collector.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.settings import settings
from app.telemetry import setup_telemetry


def test_setup_skips_when_otel_disabled(monkeypatch):
    monkeypatch.setattr(settings, "OTEL_ENABLED", False)
    sub_app = FastAPI()
    assert setup_telemetry(sub_app) is False


def test_setup_installs_when_enabled_with_forced_processor():
    """force_processor path installs regardless of OTEL_ENABLED (test-only)."""
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
        InMemorySpanExporter,
    )

    sub_app = FastAPI()
    exporter = InMemorySpanExporter()
    assert setup_telemetry(sub_app, force_processor=SimpleSpanProcessor(exporter))


def test_request_produces_span_when_enabled():
    """Hit an endpoint under the instrumented app and check for a span."""
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
        InMemorySpanExporter,
    )

    sub_app = FastAPI()

    @sub_app.get("/trace-me")
    def _handler():
        return {"ok": True}

    exporter = InMemorySpanExporter()
    setup_telemetry(sub_app, force_processor=SimpleSpanProcessor(exporter))

    with TestClient(sub_app) as client:
        resp = client.get("/trace-me")
    assert resp.status_code == 200

    spans = exporter.get_finished_spans()
    # There is at least one span for the HTTP request. The exact name
    # depends on the instrumentor version; we just assert the GET /trace-me
    # route surfaces somewhere in the collected spans.
    span_names = [s.name for s in spans]
    assert any("trace-me" in n or "GET" in n for n in span_names), (
        f"expected a span for GET /trace-me, got: {span_names}"
    )


def test_setup_is_idempotent():
    """Calling setup_telemetry twice must not raise."""
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
        InMemorySpanExporter,
    )

    sub_app = FastAPI()
    p1 = SimpleSpanProcessor(InMemorySpanExporter())
    p2 = SimpleSpanProcessor(InMemorySpanExporter())
    assert setup_telemetry(sub_app, force_processor=p1) is True
    assert setup_telemetry(sub_app, force_processor=p2) is True
