"""Daily LLM usage tracking + budget guard (v3.1).

Every vision and pricing call round-trips through this module. The
``record_usage`` helper upserts into ``llm_usage`` (one row per
``(user_id, usage_date, feature)``). The ``DailyBudgetGuard`` reads
the same row before the call fires and raises HTTPException 402
when the daily cap is exceeded.

Cost estimates are derived from token counts using a small rate
table. Providers charge at the model level — the numbers here are
order-of-magnitude accurate, not billing-grade. The point is to
surface a "you're about to burn \\$50 on this" signal, not to drive
invoices.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Literal

from fastapi import HTTPException
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .. import models
from ..services import llm_config as llm_config_service

logger = logging.getLogger(__name__)


Feature = Literal["vision", "pricing"]

# Rough per-1M-token USD prices for the models we default to. Used for
# cost estimation only. Keep low-resolution — getting the right order
# of magnitude is what matters for the daily cap.
_DEFAULT_RATES: Dict[str, Dict[str, float]] = {
    # Gemini 2.5 Flash via OpenRouter: $0.30/1M in, $2.50/1M out.
    "google/gemini-2.5-flash": {"in": 0.30, "out": 2.50},
    # Gemini 3 Flash Preview: $0.50/1M in, $3.00/1M out (derived from
    # observed billing on a probe call: 1328 prompt + 285 completion =
    # $0.001519 → $0.50/$3.00 per 1M).
    "google/gemini-3-flash-preview": {"in": 0.50, "out": 3.00},
    # Claude Sonnet 4.6: $3/1M in, $15/1M out.
    "anthropic/claude-sonnet-4.6": {"in": 3.0, "out": 15.0},
    # GPT-4o: $2.50/1M in, $10/1M out.
    "openai/gpt-4o": {"in": 2.50, "out": 10.0},
}
# Fallback when the model isn't in the table. Middle-of-the-road
# reasoning model price — intentionally conservative so unknown
# providers get flagged by the cap rather than silently blowing through.
_FALLBACK_RATE = {"in": 2.0, "out": 10.0}


def _floor_to_utc_day(when: datetime) -> datetime:
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    day = when.astimezone(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    # Store as naive UTC so the DB comparison is dialect-neutral.
    return day.replace(tzinfo=None)


def estimate_cost_usd(
    *, model: str, tokens_in: int, tokens_out: int
) -> float:
    """Best-effort cost calculation in USD.

    Pulls the rate for ``model`` from the default table, falling back
    to a conservative estimate when the model is unknown. Returns
    dollars (not cents).
    """
    rates = _DEFAULT_RATES.get(model, _FALLBACK_RATE)
    return (tokens_in / 1_000_000.0) * rates["in"] + (
        tokens_out / 1_000_000.0
    ) * rates["out"]


def _cap_for(feature: Feature, db: Session | None = None) -> float:
    """Resolve the daily cap from the operator-editable config.

    The DB-backed cap overrides the env value when set; otherwise we
    fall back to ``settings.*``. The optional ``db`` argument lets
    callers reuse an open Session; without it we hit the cached
    EffectiveLLMConfig (rebuilt on every save).
    """
    if db is not None:
        eff = llm_config_service.get_effective_for_db(db)
    else:
        eff = llm_config_service.get_effective()
    if feature == "vision":
        return eff.vision_daily_cap_usd
    if feature == "pricing":
        return eff.pricing_daily_cap_usd
    raise ValueError(f"unknown feature: {feature}")


class DailyBudgetGuard:
    """Read-modify-write guard for the per-(user, day, feature) cap."""

    def __init__(self, db: Session, user: models.User) -> None:
        self.db = db
        self.user = user

    def _row(
        self, feature: Feature, today: datetime
    ) -> models.LLMUsage | None:
        stmt = select(models.LLMUsage).where(
            models.LLMUsage.user_id == self.user.id,
            models.LLMUsage.usage_date == today,
            models.LLMUsage.feature == feature,
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def check_or_raise(self, feature: Feature) -> None:
        """Raise HTTPException 402 when today's spend exceeds the cap.

        Best-effort: a call's cost is only known *after* the provider
        responds, so the cap blocks the *next* call once a recorded row
        crosses it — it cannot pre-empt a call already in flight. Two
        requests that pass this check concurrently will both run; the
        overshoot is bounded to those in-flight calls. The cap is a
        spend signal, not a hard billing limit.
        """
        cap = _cap_for(feature, db=self.db)
        if cap <= 0:
            return
        today = _floor_to_utc_day(datetime.now(timezone.utc))
        row = self._row(feature, today)
        current = row.cost_usd if row is not None else 0.0
        if current >= cap:
            logger.warning(
                "daily %s cap reached for user=%s ($%.2f >= $%.2f)",
                feature,
                self.user.id,
                current,
                cap,
            )
            raise HTTPException(
                status_code=402,
                detail=(
                    f"Daily {feature} cost cap (${cap:.2f}) reached. "
                    "Try again tomorrow or raise the cap in settings."
                ),
            )

    def record_usage(
        self,
        feature: Feature,
        *,
        model: str,
        usage: Dict[str, Any],
        cost_usd: float | None = None,
    ) -> None:
        """Upsert today's rollup row with the latest call's counts.

        ``usage`` is the dict returned by
        :meth:`OpenAICompatibleClient.structured_completion` under
        the ``usage`` key. Recognized fields:
        ``prompt_tokens``, ``completion_tokens``.
        """
        tokens_in = int(usage.get("prompt_tokens", 0))
        tokens_out = int(usage.get("completion_tokens", 0))
        computed_cost = (
            cost_usd
            if cost_usd is not None
            else estimate_cost_usd(
                model=model, tokens_in=tokens_in, tokens_out=tokens_out
            )
        )

        today = _floor_to_utc_day(datetime.now(timezone.utc))

        # Accumulate atomically. A read-modify-write in Python loses
        # updates when two calls for the same (user, day, feature) race;
        # an in-DB ``SET col = col + :delta`` cannot. The day's first
        # call finds no row to UPDATE and falls through to INSERT; if a
        # concurrent call wins that INSERT, the unique index
        # ``ix_llm_usage_user_date_feature`` rejects ours and we retry
        # the now-present UPDATE.
        def _accumulate() -> int:
            result = self.db.execute(
                update(models.LLMUsage)
                .where(
                    models.LLMUsage.user_id == self.user.id,
                    models.LLMUsage.usage_date == today,
                    models.LLMUsage.feature == feature,
                )
                .values(
                    tokens_in=models.LLMUsage.tokens_in + tokens_in,
                    tokens_out=models.LLMUsage.tokens_out + tokens_out,
                    cost_usd=models.LLMUsage.cost_usd + computed_cost,
                    request_count=models.LLMUsage.request_count + 1,
                )
                .execution_options(synchronize_session=False)
            )
            return result.rowcount

        if _accumulate() > 0:
            self.db.commit()
            return

        # No row for today yet — insert the first one.
        self.db.add(
            models.LLMUsage(
                user_id=self.user.id,
                usage_date=today,
                feature=feature,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                cost_usd=computed_cost,
                request_count=1,
            )
        )
        try:
            self.db.commit()
        except IntegrityError:
            # A concurrent call inserted the row between our UPDATE and
            # our INSERT — fold our counts into the now-existing row.
            self.db.rollback()
            _accumulate()
            self.db.commit()
