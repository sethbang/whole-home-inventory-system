"""Structured logging setup.

structlog wraps stdlib ``logging`` so existing ``logging.getLogger(__name__)``
calls throughout the codebase keep working — they now emit through the same
renderer that structlog-native loggers use, so the output format is uniform
regardless of which logger a module happens to grab.

``LOG_FORMAT`` is the operator knob:

* ``console`` — human-readable pretty-printing, colored. Good for dev.
* ``json``    — line-delimited JSON. What you want in production log
  aggregators.
* *(unset)*   — auto-picks: ``console`` when ``DEBUG=true``, ``json``
  otherwise.

Request IDs are bound via ``structlog.contextvars`` in the HTTP middleware
and merged into every log record emitted during that request, regardless of
which module does the emitting.
"""

from __future__ import annotations

import logging
import sys

import structlog

from .settings import settings


def _shared_processors() -> list:
    """Processors applied to every record, structlog-native or stdlib."""
    return [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]


def _renderer(fmt: str):
    if fmt == "json":
        return structlog.processors.JSONRenderer()
    # colors=False so output is safe to pipe and friendly in CI logs.
    return structlog.dev.ConsoleRenderer(colors=False)


def setup_logging() -> None:
    """(Re)configure stdlib + structlog. Idempotent — safe to call in tests."""
    fmt = settings.resolve_log_format()
    level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    shared = _shared_processors()

    # Configure structlog's own pipeline. ``wrap_for_formatter`` hands the
    # event_dict off to stdlib's formatter so both paths share the renderer.
    structlog.configure(
        processors=shared + [structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared,
        processor=_renderer(fmt),
    )

    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    # Drop any previously-installed handlers (basicConfig from older runs,
    # uvicorn defaults installed post-import, etc.) so we're the only output.
    for h in list(root.handlers):
        root.removeHandler(h)
    root.addHandler(handler)
    root.setLevel(level)


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Preferred factory for new code. Existing logging.getLogger calls keep working."""
    return structlog.get_logger(name)
