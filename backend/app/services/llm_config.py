"""LLMConfigService — DB-backed operator-editable LLM provider config.

Single source of truth for everything the ``OpenAICompatibleClient``
and the budget guard need: base URL, API key, model names, daily
caps, feature flags, response-healing toggle. Each field falls back
to ``settings.*`` env values when the DB row is empty/null, so an
operator who never touches the new UI keeps the behavior they had
before v3.2.

The API key is stored encrypted (Fernet, key derived from
``SECRET_KEY``); decrypt lives behind :meth:`effective_api_key`.

Hot reload: a process-local cache holds the most recent
:class:`EffectiveLLMConfig` and is invalidated on every successful
``apply_update`` (or by an external cache-invalidation signal — the
ARQ worker subscribes to a Redis key when ``REDIS_URL`` is set, but
the synchronous-mode default uses the same FastAPI process and
shares this cache directly).

Public surface:

* :func:`get_effective` — return the cached :class:`EffectiveLLMConfig`,
  building it from the DB (with env fallback) on first read.
* :func:`get_effective_for_db(db)` — same shape but builds against the
  caller-supplied session, used by code paths that don't want to take
  a fresh ``SessionLocal``.
* :func:`apply_update(db, payload, actor)` — persist a partial update,
  encrypting the new key when present, rebuilding the cache, returning
  the freshly-effective config.
* :func:`load_db_row(db)` — read-only helper that returns the singleton
  row (or None when the DB hasn't been migrated yet).
* :func:`invalidate_cache()` — clear the cache. Tests + external
  cache-bust signals call this.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from typing import Any, Dict, List, Literal, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import database, models, security_crypto
from ..settings import _is_private_llm_host, settings
from ..utctime import utcnow

logger = logging.getLogger(__name__)
audit_logger = logging.getLogger("app.llm_config")


FieldSource = Literal["db", "env", "default"]


@dataclass(frozen=True)
class EffectiveLLMConfig:
    """Resolved view of the LLM config for runtime consumers.

    Every field has a non-None value (the env or the hard-coded default
    fills in for nulls). ``api_key`` is the plaintext value — only the
    service / client layer ever sees it. ``key_set`` is the cheap
    "is there a usable key" predicate for the API surface.
    """

    base_url: str
    api_key: str
    model: str
    vision_model: str
    pricing_model: str
    timeout_seconds: int
    response_healing: bool
    vision_enabled: bool
    pricing_enabled: bool
    vision_daily_cap_usd: float
    pricing_daily_cap_usd: float
    sources: Dict[str, FieldSource]


# Module-level cache + lock. Each process keeps its own copy.
_cache_lock = threading.Lock()
_cache: Optional[EffectiveLLMConfig] = None


def invalidate_cache() -> None:
    """Drop the cached config so the next read rebuilds from DB+env."""
    global _cache
    with _cache_lock:
        _cache = None


def load_db_row(db: Session) -> Optional[models.LLMConfig]:
    """Return the singleton row, or None if the table is empty."""
    return db.execute(
        select(models.LLMConfig).where(models.LLMConfig.id == 1)
    ).scalar_one_or_none()


def _decrypt_or_none(ciphertext: Optional[str]) -> Optional[str]:
    if not ciphertext:
        return None
    try:
        return security_crypto.decrypt(ciphertext)
    except security_crypto.DecryptionError:
        # SECRET_KEY rotated underneath the stored ciphertext, or the
        # backup was restored onto a different host. Fall back to env;
        # log loudly so operators know their stored key is now garbage.
        logger.error(
            "llm_config.api_key_ciphertext failed to decrypt; "
            "falling back to env. Re-save the key in the UI to "
            "re-encrypt with the current SECRET_KEY."
        )
        return None


def _resolve_field(
    db_value: Any, env_value: Any, env_label: str
) -> tuple[Any, FieldSource]:
    """Choose the DB value when set; otherwise the env value."""
    if db_value is None or db_value == "":
        return env_value, ("env" if env_value not in (None, "") else "default")
    return db_value, "db"


def _build_effective(row: Optional[models.LLMConfig]) -> EffectiveLLMConfig:
    """Merge the DB row (may be None) with env defaults into one record."""
    sources: Dict[str, FieldSource] = {}

    base_url, sources["base_url"] = _resolve_field(
        row.base_url if row else None, settings.LLM_BASE_URL, "LLM_BASE_URL"
    )
    api_key_db = _decrypt_or_none(row.api_key_ciphertext) if row else None
    api_key, sources["api_key"] = _resolve_field(
        api_key_db, settings.LLM_API_KEY, "LLM_API_KEY"
    )

    # Default model. Always non-empty: settings.LLM_MODEL has a default of
    # ``google/gemini-2.5-flash``.
    model, sources["model"] = _resolve_field(
        row.model if row else None, settings.LLM_MODEL, "LLM_MODEL"
    )

    # vision_model / pricing_model fall back to ``model`` (the default
    # field), matching the existing settings.vision_model() /
    # settings.pricing_model() helpers.
    raw_vision = row.vision_model if row else None
    if not raw_vision:
        # Env override wins over the implicit "= model" only when set.
        raw_vision = settings.LLM_VISION_MODEL or None
    vision_model = raw_vision or model
    sources["vision_model"] = (
        "db"
        if (row and row.vision_model)
        else ("env" if settings.LLM_VISION_MODEL else "default")
    )

    raw_pricing = row.pricing_model if row else None
    if not raw_pricing:
        raw_pricing = settings.LLM_PRICING_MODEL or None
    pricing_model = raw_pricing or model
    sources["pricing_model"] = (
        "db"
        if (row and row.pricing_model)
        else ("env" if settings.LLM_PRICING_MODEL else "default")
    )

    timeout, sources["timeout_seconds"] = _resolve_field(
        row.timeout_seconds if row else None,
        settings.LLM_TIMEOUT_SECONDS,
        "LLM_TIMEOUT_SECONDS",
    )

    healing, sources["response_healing"] = _resolve_field(
        row.response_healing if row else None,
        settings.LLM_RESPONSE_HEALING,
        "LLM_RESPONSE_HEALING",
    )

    vision_enabled, sources["vision_enabled"] = _resolve_field(
        row.vision_enabled if row else None,
        settings.VISION_ENABLED,
        "VISION_ENABLED",
    )
    pricing_enabled, sources["pricing_enabled"] = _resolve_field(
        row.pricing_enabled if row else None,
        settings.PRICING_ENABLED,
        "PRICING_ENABLED",
    )
    vision_cap, sources["vision_daily_cap_usd"] = _resolve_field(
        row.vision_daily_cap_usd if row else None,
        settings.VISION_DAILY_COST_CAP_USD,
        "VISION_DAILY_COST_CAP_USD",
    )
    pricing_cap, sources["pricing_daily_cap_usd"] = _resolve_field(
        row.pricing_daily_cap_usd if row else None,
        settings.PRICING_DAILY_COST_CAP_USD,
        "PRICING_DAILY_COST_CAP_USD",
    )

    return EffectiveLLMConfig(
        base_url=base_url or "",
        api_key=api_key or "",
        model=model,
        vision_model=vision_model,
        pricing_model=pricing_model,
        timeout_seconds=int(timeout),
        response_healing=bool(healing),
        vision_enabled=bool(vision_enabled),
        pricing_enabled=bool(pricing_enabled),
        vision_daily_cap_usd=float(vision_cap),
        pricing_daily_cap_usd=float(pricing_cap),
        sources=sources,
    )


def get_effective_for_db(db: Session) -> EffectiveLLMConfig:
    """Build the effective config against the caller-supplied session."""
    row = None
    try:
        row = load_db_row(db)
    except Exception:
        # Schema not migrated yet (e.g. early bootstrap, broken DB).
        # Fall back to env; the runtime stays usable.
        logger.warning(
            "llm_config table missing or unreadable; using env values only"
        )
    return _build_effective(row)


def get_effective() -> EffectiveLLMConfig:
    """Return the cached effective config, building it on first call.

    Code paths that already have a Session in hand should prefer
    :func:`get_effective_for_db` to avoid opening a transient
    SessionLocal. The cache lives at module scope so subsequent calls
    are zero-cost.
    """
    global _cache
    with _cache_lock:
        if _cache is not None:
            return _cache
    # Build outside the lock to keep contention low.
    db: Session = database.SessionLocal()
    try:
        built = get_effective_for_db(db)
    finally:
        db.close()
    with _cache_lock:
        _cache = built
    return built


# ------------------------------------------------------------------
# Mutations
# ------------------------------------------------------------------


_MUTABLE_FIELDS = {
    "base_url",
    "model",
    "vision_model",
    "pricing_model",
    "timeout_seconds",
    "response_healing",
    "vision_enabled",
    "pricing_enabled",
    "vision_daily_cap_usd",
    "pricing_daily_cap_usd",
}


class ConfigUpdateError(ValueError):
    """Raised on validation errors during apply_update."""


def _validate_payload(payload: Dict[str, Any]) -> None:
    """Cross-cutting validation: privacy guard + numeric ranges."""
    base_url = payload.get("base_url")
    if (
        base_url
        and not settings.LLM_ALLOW_CLOUD
        and not _is_private_llm_host(base_url)
    ):
        raise ConfigUpdateError(
            "LLM_ALLOW_CLOUD=false in env: base_url must point at "
            "localhost or a private-range IP."
        )
    timeout = payload.get("timeout_seconds")
    if timeout is not None and (timeout <= 0 or timeout > 600):
        raise ConfigUpdateError("timeout_seconds must be between 1 and 600")
    for cap_key in ("vision_daily_cap_usd", "pricing_daily_cap_usd"):
        cap = payload.get(cap_key)
        if cap is not None and cap < 0:
            raise ConfigUpdateError(f"{cap_key} must be >= 0")


def apply_update(
    db: Session,
    payload: Dict[str, Any],
    actor: Optional[models.User] = None,
    *,
    api_key: Optional[str] = None,
    clear_api_key: bool = False,
) -> EffectiveLLMConfig:
    """Persist a partial update, encrypt the API key if supplied.

    ``payload`` is a dict whose keys are a subset of ``_MUTABLE_FIELDS``.
    Empty strings clear a string field back to env-fallback; ``None`` is
    treated the same way (the GET shape distinguishes "unset" from
    "explicit empty"; the PUT side collapses both to clear).

    ``api_key`` (when not None) becomes the new plaintext key,
    encrypted on the way in. ``clear_api_key=True`` drops the stored
    key and reverts to env-fallback. Passing both is an error.

    Logs a structured audit line via the ``app.llm_config`` logger
    on success.
    """
    if api_key is not None and clear_api_key:
        raise ConfigUpdateError("cannot both set and clear the API key")

    extra = set(payload) - _MUTABLE_FIELDS
    if extra:
        raise ConfigUpdateError(f"unknown fields: {sorted(extra)}")

    _validate_payload(payload)

    row = load_db_row(db)
    if row is None:
        row = models.LLMConfig(id=1, updated_at=utcnow())
        db.add(row)

    fields_changed: List[str] = []
    for key in _MUTABLE_FIELDS:
        if key not in payload:
            continue
        new_value = payload[key]
        if isinstance(new_value, str) and new_value == "":
            new_value = None
        if getattr(row, key) != new_value:
            setattr(row, key, new_value)
            fields_changed.append(key)

    key_rotated = False
    if clear_api_key:
        if row.api_key_ciphertext is not None:
            row.api_key_ciphertext = None
            fields_changed.append("api_key")
            key_rotated = True
    elif api_key is not None:
        # Encrypt the new key. Empty string means "use env value", same
        # convention as the other string fields.
        if api_key == "":
            if row.api_key_ciphertext is not None:
                row.api_key_ciphertext = None
                fields_changed.append("api_key")
                key_rotated = True
        else:
            row.api_key_ciphertext = security_crypto.encrypt(api_key)
            fields_changed.append("api_key")
            key_rotated = True

    row.updated_at = utcnow()
    if actor is not None:
        row.updated_by = actor.id

    db.commit()
    db.refresh(row)
    invalidate_cache()

    audit_logger.info(
        "llm_config updated",
        extra={
            "actor_id": str(actor.id) if actor is not None else None,
            "actor_username": (
                actor.username if actor is not None else None
            ),
            "fields_changed": fields_changed,
            "key_rotated": key_rotated,
        },
    )

    return get_effective_for_db(db)
