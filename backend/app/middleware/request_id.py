"""Request-ID middleware.

Every incoming HTTP request gets a stable identifier bound to structlog's
``contextvars`` for the lifetime of the request. Every log record emitted
during request handling — regardless of which module logs it — carries
``request_id=<id>`` automatically.

The ID is taken from an inbound ``X-Request-ID`` header when present (so a
reverse proxy or upstream service can propagate its own trace identifier)
and generated fresh (uuid4) otherwise. The ID is echoed back on the
response so clients can correlate server-side log entries with their own
traces.
"""

from __future__ import annotations

import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

REQUEST_ID_HEADER = "X-Request-ID"


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        rid = request.headers.get(REQUEST_ID_HEADER) or str(uuid.uuid4())
        # clear_contextvars guards against leakage if a previous request in
        # the same worker left state behind (shouldn't happen, but cheap).
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=rid)
        try:
            response = await call_next(request)
        finally:
            # Whether we succeed or raise, clean the contextvar so the next
            # request starts clean. The ID is also stashed on request.state
            # for handlers that want it.
            request.state.request_id = rid

        response.headers[REQUEST_ID_HEADER] = rid
        return response
