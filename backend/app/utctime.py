"""Naive UTC timestamp helper.

``datetime.utcnow()`` is deprecated (removal scheduled). This helper is
the exact behavioural equivalent — a *naive* datetime carrying UTC wall
time — so it is a drop-in replacement that keeps the existing naive
``DateTime`` columns and naive/naive comparisons working unchanged.
"""

from datetime import datetime, timezone


def utcnow() -> datetime:
    """Return the current UTC time as a naive datetime (tzinfo=None)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)
