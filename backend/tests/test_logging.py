"""Structured logging + request-ID middleware tests."""

from __future__ import annotations

import io
import json
import logging

import pytest
import structlog

from app import logging_config
from app.settings import settings

# ---------------------------------------------------------------------------
# LOG_FORMAT resolution
# ---------------------------------------------------------------------------


def test_resolve_log_format_explicit_json(monkeypatch):
    monkeypatch.setattr(settings, "LOG_FORMAT", "json")
    monkeypatch.setattr(settings, "DEBUG", True)
    assert settings.resolve_log_format() == "json"


def test_resolve_log_format_explicit_console(monkeypatch):
    monkeypatch.setattr(settings, "LOG_FORMAT", "console")
    monkeypatch.setattr(settings, "DEBUG", False)
    assert settings.resolve_log_format() == "console"


def test_resolve_log_format_defaults_to_console_in_debug(monkeypatch):
    monkeypatch.setattr(settings, "LOG_FORMAT", "")
    monkeypatch.setattr(settings, "DEBUG", True)
    assert settings.resolve_log_format() == "console"


def test_resolve_log_format_defaults_to_json_in_prod(monkeypatch):
    monkeypatch.setattr(settings, "LOG_FORMAT", "")
    monkeypatch.setattr(settings, "DEBUG", False)
    assert settings.resolve_log_format() == "json"


def test_resolve_log_format_rejects_garbage(monkeypatch):
    """Unknown values fall back to the DEBUG-derived default."""
    monkeypatch.setattr(settings, "LOG_FORMAT", "klingon")
    monkeypatch.setattr(settings, "DEBUG", False)
    assert settings.resolve_log_format() == "json"


# ---------------------------------------------------------------------------
# Renderer output
# ---------------------------------------------------------------------------


def _capture_log(monkeypatch, log_format: str, emit) -> str:
    """Configure logging to log_format, capture stderr output, return it."""
    monkeypatch.setattr(settings, "LOG_FORMAT", log_format)
    monkeypatch.setattr(settings, "DEBUG", False)

    buf = io.StringIO()

    # Rebuild the handler pointing at our buffer rather than sys.stderr.
    fmt = settings.resolve_log_format()
    shared = logging_config._shared_processors()
    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared,
        processor=logging_config._renderer(fmt),
    )
    handler = logging.StreamHandler(buf)
    handler.setFormatter(formatter)
    root = logging.getLogger()
    old_handlers = list(root.handlers)
    old_level = root.level
    for h in old_handlers:
        root.removeHandler(h)
    root.addHandler(handler)
    root.setLevel(logging.DEBUG)

    try:
        structlog.configure(
            processors=shared
            + [structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=False,
        )
        emit()
        handler.flush()
        return buf.getvalue()
    finally:
        root.removeHandler(handler)
        for h in old_handlers:
            root.addHandler(h)
        root.setLevel(old_level)
        # Let subsequent tests reconfigure from scratch.
        structlog.reset_defaults()


def test_json_format_emits_parseable_json(monkeypatch):
    def emit():
        logger = structlog.get_logger("test.logger")
        logger.info("hello", foo=1, bar="two")

    output = _capture_log(monkeypatch, "json", emit)
    # Take the last non-empty line — there might be timestamper metadata in others.
    line = [ln for ln in output.strip().splitlines() if ln.strip()][-1]
    parsed = json.loads(line)
    assert parsed["event"] == "hello"
    assert parsed["foo"] == 1
    assert parsed["bar"] == "two"
    assert parsed["level"] == "info"
    assert parsed["logger"] == "test.logger"
    assert "timestamp" in parsed


def test_console_format_is_human_readable(monkeypatch):
    def emit():
        logger = structlog.get_logger("test.console")
        logger.warning("visible-event", code=42)

    output = _capture_log(monkeypatch, "console", emit)
    assert "visible-event" in output
    assert "42" in output
    # ConsoleRenderer doesn't produce JSON-parseable lines.
    with pytest.raises(json.JSONDecodeError):
        json.loads(output.strip().splitlines()[-1])


def test_stdlib_logger_also_gets_json_format(monkeypatch):
    """logging.getLogger(...) callers must render through the same pipeline."""

    def emit():
        logging.getLogger("stdlib.test").info("stdlib-event", extra={"scope": "x"})

    output = _capture_log(monkeypatch, "json", emit)
    parsed = json.loads([ln for ln in output.strip().splitlines() if ln.strip()][-1])
    assert parsed["event"] == "stdlib-event"
    assert parsed["level"] == "info"


# ---------------------------------------------------------------------------
# Request-ID middleware
# ---------------------------------------------------------------------------


def test_request_id_generated_when_missing(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    rid = resp.headers.get("X-Request-ID")
    assert rid
    # Generated IDs are UUID-shaped.
    assert len(rid) >= 32
    assert "-" in rid


def test_request_id_propagated_when_supplied(client):
    supplied = "my-upstream-trace-id-7890"
    resp = client.get("/api/health", headers={"X-Request-ID": supplied})
    assert resp.status_code == 200
    assert resp.headers.get("X-Request-ID") == supplied


def test_request_id_bound_to_structlog_context(client):
    """During a request the context var should include request_id.

    We register a throwaway test-only route on the app that captures the
    current contextvars, hit it, and assert the middleware bound request_id.
    """
    from app import main as main_module

    captured: dict = {}

    async def _peek():
        captured["ctx"] = structlog.contextvars.get_contextvars().copy()
        return {"ok": True}

    main_module.app.add_api_route("/api/_peek_contextvars", _peek, methods=["GET"])
    try:
        resp = client.get(
            "/api/_peek_contextvars", headers={"X-Request-ID": "trace-abc-123"}
        )
        assert resp.status_code == 200
        assert captured["ctx"].get("request_id") == "trace-abc-123"
    finally:
        # Remove the test-only route so it doesn't linger into other tests.
        main_module.app.router.routes = [
            r
            for r in main_module.app.router.routes
            if getattr(r, "path", None) != "/api/_peek_contextvars"
        ]


def test_request_id_cleared_between_requests(client):
    """Two requests with different IDs must get different echoed IDs."""
    r1 = client.get("/api/health", headers={"X-Request-ID": "first"})
    r2 = client.get("/api/health", headers={"X-Request-ID": "second"})
    assert r1.headers["X-Request-ID"] == "first"
    assert r2.headers["X-Request-ID"] == "second"
