"""Tests for the v3.1 daily-cost cap guard."""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from app import models
from app.llm.budget import (
    DailyBudgetGuard,
    _floor_to_utc_day,
    estimate_cost_usd,
)
from app.settings import settings


def test_estimate_cost_knows_default_models():
    # 1M in + 500K out on gemini-2.5-flash.
    cost = estimate_cost_usd(
        model="google/gemini-2.5-flash",
        tokens_in=1_000_000,
        tokens_out=500_000,
    )
    # 0.30 + (2.50 * 0.5) = 1.55
    assert 1.54 < cost < 1.56


def test_estimate_cost_falls_back_for_unknown_model():
    cost = estimate_cost_usd(
        model="some-self-hosted-7b", tokens_in=1_000_000, tokens_out=1_000_000
    )
    # 2.0 + 10.0 fallback rate
    assert 11.99 < cost < 12.01


def test_guard_records_first_call_and_enforces_cap(db_session, user, monkeypatch):
    # Tight cap so one record trips the guard.
    monkeypatch.setattr(settings, "VISION_DAILY_COST_CAP_USD", 0.01)

    guard = DailyBudgetGuard(db_session, user)
    # First call: cap hasn't been reached — no raise.
    guard.check_or_raise("vision")

    # Record a call with enough tokens to blow the $0.01 cap.
    guard.record_usage(
        "vision",
        model="anthropic/claude-sonnet-4.6",
        usage={"prompt_tokens": 10_000, "completion_tokens": 2_000},
    )

    row = (
        db_session.query(models.LLMUsage)
        .filter_by(user_id=user.id, feature="vision")
        .one()
    )
    assert row.request_count == 1
    assert row.tokens_in == 10_000
    assert row.tokens_out == 2_000
    assert row.cost_usd > 0.01

    # Second call now trips the guard.
    with pytest.raises(HTTPException) as exc:
        guard.check_or_raise("vision")
    assert exc.value.status_code == 402
    assert "cap" in exc.value.detail.lower()


def test_guard_accumulates_across_calls(db_session, user, monkeypatch):
    monkeypatch.setattr(settings, "PRICING_DAILY_COST_CAP_USD", 1000.0)
    guard = DailyBudgetGuard(db_session, user)

    for _ in range(3):
        guard.record_usage(
            "pricing",
            model="google/gemini-2.5-flash",
            usage={"prompt_tokens": 1000, "completion_tokens": 500},
        )

    row = (
        db_session.query(models.LLMUsage)
        .filter_by(user_id=user.id, feature="pricing")
        .one()
    )
    assert row.request_count == 3
    assert row.tokens_in == 3000
    assert row.tokens_out == 1500


def test_guard_is_per_feature(db_session, user, monkeypatch):
    """Vision usage must not count against the pricing cap, and vice versa."""
    monkeypatch.setattr(settings, "VISION_DAILY_COST_CAP_USD", 0.001)
    monkeypatch.setattr(settings, "PRICING_DAILY_COST_CAP_USD", 1000.0)

    guard = DailyBudgetGuard(db_session, user)
    guard.record_usage(
        "vision",
        model="anthropic/claude-sonnet-4.6",
        usage={"prompt_tokens": 100_000, "completion_tokens": 10_000},
    )

    # Vision guard should now refuse.
    with pytest.raises(HTTPException):
        guard.check_or_raise("vision")
    # Pricing guard should still allow — separate row.
    guard.check_or_raise("pricing")


def test_guard_is_per_user(db_session, user, monkeypatch):
    from app import security

    monkeypatch.setattr(settings, "VISION_DAILY_COST_CAP_USD", 0.001)

    other = models.User(
        email="other@example.com",
        username="other",
        hashed_password=security.get_password_hash("x"),
        is_active=True,
    )
    db_session.add(other)
    db_session.commit()
    db_session.refresh(other)

    DailyBudgetGuard(db_session, user).record_usage(
        "vision",
        model="anthropic/claude-sonnet-4.6",
        usage={"prompt_tokens": 100_000, "completion_tokens": 10_000},
    )

    # Alice is over cap; Bob isn't.
    with pytest.raises(HTTPException):
        DailyBudgetGuard(db_session, user).check_or_raise("vision")
    DailyBudgetGuard(db_session, other).check_or_raise("vision")


def test_guard_no_cap_means_never_raises(db_session, user, monkeypatch):
    """A cap of 0.0 or negative disables enforcement."""
    monkeypatch.setattr(settings, "VISION_DAILY_COST_CAP_USD", 0.0)
    guard = DailyBudgetGuard(db_session, user)
    guard.record_usage(
        "vision",
        model="anthropic/claude-sonnet-4.6",
        usage={"prompt_tokens": 1_000_000, "completion_tokens": 1_000_000},
    )
    # Zero cap skips the check entirely.
    guard.check_or_raise("vision")


def test_floor_to_utc_day_normalizes_to_midnight():
    from datetime import datetime, timezone

    # Afternoon UTC → midnight UTC that day.
    afternoon = datetime(2026, 4, 22, 14, 30, 45, tzinfo=timezone.utc)
    assert _floor_to_utc_day(afternoon).replace(tzinfo=None) == datetime(
        2026, 4, 22
    )
