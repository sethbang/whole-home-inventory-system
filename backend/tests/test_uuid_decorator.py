"""UUID TypeDecorator tests.

The decorator used to silently replace any non-v4 UUID with a fresh v4. That
behavior hid real bugs (e.g. if a v1 UUID arrived from an external integration
it was silently clobbered, making 'my row vanished' nearly impossible to
diagnose). The decorator now preserves caller input and only emits a warning.
"""

from __future__ import annotations

import logging
import uuid

import pytest

from app.models import UUID


def _decorator() -> UUID:
    return UUID()


def test_v4_uuid_round_trips_unchanged():
    dec = _decorator()
    original = uuid.uuid4()
    bound = dec.process_bind_param(original, dialect=None)
    assert bound == str(original)

    read_back = dec.process_result_value(bound, dialect=None)
    assert read_back == original
    assert read_back.version == 4


def test_v4_uuid_string_round_trips_unchanged():
    dec = _decorator()
    original_str = str(uuid.uuid4())
    bound = dec.process_bind_param(original_str, dialect=None)
    assert bound == original_str


def test_v1_uuid_preserved_with_warning(caplog):
    """A v1 UUID arrives — we must NOT replace it, but we must warn."""
    dec = _decorator()
    v1 = uuid.uuid1()
    assert v1.version == 1

    with caplog.at_level(logging.WARNING, logger="app.models"):
        bound = dec.process_bind_param(v1, dialect=None)

    assert bound == str(v1)  # preserved, not replaced
    assert any("non-v4" in r.getMessage() for r in caplog.records)


def test_malformed_string_raises_value_error():
    """Fail loud on garbage input rather than silently producing a new UUID."""
    dec = _decorator()
    with pytest.raises(ValueError):
        dec.process_bind_param("not-a-uuid", dialect=None)


def test_none_passes_through():
    dec = _decorator()
    assert dec.process_bind_param(None, dialect=None) is None
    assert dec.process_result_value(None, dialect=None) is None


def test_non_v4_result_value_preserved(caplog):
    """On read, a non-v4 UUID stored in the DB must not be silently rewritten."""
    dec = _decorator()
    v1 = uuid.uuid1()
    stored = str(v1)

    with caplog.at_level(logging.WARNING, logger="app.models"):
        result = dec.process_result_value(stored, dialect=None)

    assert result == v1
    assert any("non-v4" in r.getMessage() for r in caplog.records)
