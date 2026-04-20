"""Rate limiting via slowapi.

In-memory counters — resets on worker restart, doesn't share across
workers. That's fine for a single-worker household deployment; v3.0
will swap in a Redis backend when the job queue arrives. Replacing the
backend at that point is one constructor argument.

Keys: the ``rate_limit_key`` function prefers the authenticated user's
username (parsed cheaply from the JWT) and falls back to the caller's
IP. This means:

- Unauth'd endpoints like ``/api/token`` are always IP-keyed, which is
  what you want for login throttling (one attacker on one IP can't
  burn through another user's budget).
- Auth'd endpoints are user-keyed, so expensive operations like exports
  or restores can't be starved by a noisy neighbor on the same NAT.
"""

from __future__ import annotations

import logging

import jwt
from fastapi import Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from .settings import settings

logger = logging.getLogger(__name__)


def rate_limit_key(request: Request) -> str:
    """Key per authenticated user when possible, else per IP.

    JWT decode failures fall back to IP silently — we don't want a
    malformed token to either break rate limiting or become an error
    before auth dependencies have a chance to return their own 401.
    """
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        token = auth[7:].strip()
        if token and token != "dev_token":
            try:
                payload = jwt.decode(
                    token,
                    settings.SECRET_KEY,
                    algorithms=[settings.ALGORITHM],
                )
                username = payload.get("sub")
                if username:
                    return f"user:{username}"
            except jwt.InvalidTokenError:
                # Fall through to IP keying; auth layer will return 401.
                pass
    return f"ip:{get_remote_address(request)}"


limiter = Limiter(key_func=rate_limit_key, default_limits=[])


def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    """Keep the response body generic so we don't leak the limit policy."""
    logger.warning(
        "rate limit exceeded on %s %s (detail=%s)",
        request.method,
        request.url.path,
        exc.detail,
    )
    return JSONResponse(
        status_code=429,
        content={
            "detail": "Too many requests. Please slow down and try again later.",
            "status_code": 429,
        },
        headers={"Retry-After": "60"},
    )
