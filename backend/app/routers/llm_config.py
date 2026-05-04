"""Operator LLM-config router (v3.2).

Admin-only surface that powers the in-app /settings page. Five
endpoints:

* ``GET /api/llm-config`` — current effective config (key redacted).
* ``PUT /api/llm-config`` — partial update; encrypts the API key.
* ``GET /api/llm-config/models`` — proxies the configured provider's
  ``/v1/models`` and annotates each entry with the tri-state
  vision/strict-json heuristic from ``app.llm.capabilities``.
* ``POST /api/llm-config/test`` — quick check: lists models, confirms
  the configured ``model`` (and any vision/pricing override) appears.
  Doesn't spend tokens.
* ``POST /api/llm-config/test-vision`` — deep check: sends a tiny
  embedded JPEG through ``vision_completion`` with a minimal strict
  schema. Stamps an ``LLMUsage`` row tagged ``feature="config_test"``.

The "test" endpoints accept an optional :class:`LLMConfigUpdate` body
so the UI can validate values **before** persisting them — it builds
a transient client against the prospective settings without touching
the singleton row.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import database, models, schemas
from ..llm import LLMError, LLMProviderError, OpenAICompatibleClient
from ..llm.budget import _floor_to_utc_day, estimate_cost_usd
from ..llm.capabilities import detect_strict_json, detect_vision
from ..security import require_admin
from ..services import llm_config as svc

logger = logging.getLogger(__name__)
audit_logger = logging.getLogger("app.llm_config")

router = APIRouter(prefix="/llm-config", tags=["llm-config"])


_TEST_PIXEL_PATH = Path(__file__).resolve().parent.parent.parent / "assets" / "test_pixel.jpg"

# Minimal strict schema for the deep test. The model just needs to
# emit ``{"ok": true}`` to prove vision + strict JSON both work.
_PING_SCHEMA: Dict[str, Any] = {
    "name": "vision_ping",
    "strict": True,
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "ok": {"type": "boolean"},
            "description": {"type": "string"},
        },
        "required": ["ok", "description"],
    },
}


def _today_costs(db: Session, user: models.User) -> Dict[str, float]:
    """Today's per-feature cost rollup for the current admin."""
    today = _floor_to_utc_day(datetime.now(timezone.utc))
    rows = db.execute(
        select(models.LLMUsage)
        .where(models.LLMUsage.user_id == user.id)
        .where(models.LLMUsage.usage_date == today)
    ).scalars().all()
    out = {"vision": 0.0, "pricing": 0.0}
    for row in rows:
        if row.feature in out:
            out[row.feature] += float(row.cost_usd or 0.0)
    return out


@router.get("", response_model=schemas.LLMConfigRead)
def read_config(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(require_admin),
):
    eff = svc.get_effective_for_db(db)
    spend = _today_costs(db, current_user)
    api_key_last4 = eff.api_key[-4:] if len(eff.api_key) >= 4 else None
    return schemas.LLMConfigRead(
        base_url=eff.base_url,
        api_key_set=bool(eff.api_key),
        api_key_last4=api_key_last4,
        model=eff.model,
        vision_model=eff.vision_model,
        pricing_model=eff.pricing_model,
        timeout_seconds=eff.timeout_seconds,
        response_healing=eff.response_healing,
        vision_enabled=eff.vision_enabled,
        pricing_enabled=eff.pricing_enabled,
        vision_daily_cap_usd=eff.vision_daily_cap_usd,
        pricing_daily_cap_usd=eff.pricing_daily_cap_usd,
        sources=dict(eff.sources),
        today_vision_cost_usd=spend["vision"],
        today_pricing_cost_usd=spend["pricing"],
    )


def _payload_to_dict(payload: schemas.LLMConfigUpdate) -> Dict[str, Any]:
    """Convert the PUT body to the dict shape ``apply_update`` expects.

    ``api_key`` is split off because the service handles it specially.
    Other ``None``s are dropped so they're treated as "leave unchanged".
    """
    raw = payload.model_dump(exclude_none=False)
    raw.pop("api_key", None)
    return {k: v for k, v in raw.items() if v is not None}


@router.put("", response_model=schemas.LLMConfigRead)
def update_config(
    payload: schemas.LLMConfigUpdate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(require_admin),
):
    update_dict = _payload_to_dict(payload)
    try:
        svc.apply_update(
            db,
            update_dict,
            actor=current_user,
            api_key=payload.api_key,
        )
    except svc.ConfigUpdateError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return read_config(db=db, current_user=current_user)


# ------------------------------------------------------------------
# Helpers shared by /models, /test, /test-vision
# ------------------------------------------------------------------


def _resolve_overrides(
    eff: svc.EffectiveLLMConfig,
    payload: Optional[schemas.LLMConfigUpdate],
) -> Dict[str, Any]:
    """Return URL/key/model resolved to the effective + payload mix.

    The /test endpoints accept an optional payload so the UI can
    validate values **before** saving. Anything missing in the
    payload falls back to the persisted effective config.
    """
    overrides: Dict[str, Any] = {
        "base_url": eff.base_url,
        "api_key": eff.api_key,
        "model": eff.model,
        "vision_model": eff.vision_model,
        "pricing_model": eff.pricing_model,
        "timeout_seconds": eff.timeout_seconds,
    }
    if payload is None:
        return overrides
    if payload.base_url is not None and payload.base_url != "":
        overrides["base_url"] = payload.base_url
    if payload.api_key is not None and payload.api_key != "":
        overrides["api_key"] = payload.api_key
    if payload.model:
        overrides["model"] = payload.model
        # vision/pricing default to model unless they have their own
        # override below.
        overrides["vision_model"] = payload.model
        overrides["pricing_model"] = payload.model
    if payload.vision_model:
        overrides["vision_model"] = payload.vision_model
    if payload.pricing_model:
        overrides["pricing_model"] = payload.pricing_model
    if payload.timeout_seconds:
        overrides["timeout_seconds"] = payload.timeout_seconds
    return overrides


async def _list_models_from_provider(
    base_url: str, api_key: str, timeout_seconds: int
) -> List[Dict[str, Any]]:
    """Hit ``{base_url}/models`` and return the raw entries.

    Most OpenAI-compatible providers expose this; the response shape
    varies (raw OpenAI uses ``{"data": [...]}``; some providers wrap
    differently). We accept both ``response["data"]`` and a top-level
    list so a wider swath of providers Just Works.
    """
    if not base_url or not api_key:
        raise HTTPException(
            status_code=400,
            detail="base_url and api_key are required to list models.",
        )
    url = base_url.rstrip("/") + "/models"
    async with httpx.AsyncClient(timeout=timeout_seconds) as client:
        try:
            response = await client.get(
                url,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Accept": "application/json",
                },
            )
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=502,
                detail=f"Could not reach {url}: {exc}",
            )
    if response.status_code == 401:
        raise HTTPException(
            status_code=401, detail="Provider rejected the API key (HTTP 401)."
        )
    if response.status_code >= 400:
        raise HTTPException(
            status_code=502,
            detail=(
                f"Provider returned HTTP {response.status_code}: "
                f"{response.text[:300]}"
            ),
        )
    body = response.json()
    if isinstance(body, list):
        return body
    if isinstance(body, dict):
        if isinstance(body.get("data"), list):
            return body["data"]
        if isinstance(body.get("models"), list):
            return body["models"]
    raise HTTPException(
        status_code=502,
        detail="Provider /v1/models response was not in a recognized shape.",
    )


def _annotate_model(entry: Dict[str, Any]) -> schemas.LLMModelEntry:
    return schemas.LLMModelEntry(
        id=str(entry.get("id") or entry.get("name") or ""),
        owned_by=entry.get("owned_by") or entry.get("vendor"),
        supports_vision=detect_vision(entry),
        supports_strict_json=detect_strict_json(entry),
    )


@router.get("/models", response_model=schemas.LLMModelListResponse)
async def list_models(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(require_admin),
):
    eff = svc.get_effective_for_db(db)
    raw = await _list_models_from_provider(
        eff.base_url, eff.api_key, eff.timeout_seconds
    )
    annotated = [_annotate_model(e) for e in raw if isinstance(e, dict)]
    annotated = [m for m in annotated if m.id]
    return schemas.LLMModelListResponse(models=annotated)


@router.post("/test", response_model=schemas.LLMTestResponse)
async def test_connection(
    payload: Optional[schemas.LLMConfigUpdate] = None,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(require_admin),
):
    """Quick: verify URL+key, confirm configured models exist."""
    eff = svc.get_effective_for_db(db)
    over = _resolve_overrides(eff, payload)
    base_url = over["base_url"]
    api_key = over["api_key"]
    model = over["model"]
    if not base_url or not api_key:
        return schemas.LLMTestResponse(
            ok=False,
            base_url=base_url or "",
            model=model or "",
            detail="base_url and api_key must both be set.",
        )

    try:
        raw = await _list_models_from_provider(
            base_url, api_key, over["timeout_seconds"]
        )
    except HTTPException as exc:
        return schemas.LLMTestResponse(
            ok=False, base_url=base_url, model=model, detail=str(exc.detail)
        )

    ids = {str(e.get("id") or e.get("name") or "") for e in raw if isinstance(e, dict)}
    checks: Dict[str, Any] = {"models_listed": len(ids)}
    missing: List[str] = []
    for label, name in (
        ("model", over["model"]),
        ("vision_model", over["vision_model"]),
        ("pricing_model", over["pricing_model"]),
    ):
        present = name in ids if ids else None
        checks[f"{label}_present"] = present
        if present is False:
            missing.append(f"{label}={name}")

    if missing:
        return schemas.LLMTestResponse(
            ok=False,
            base_url=base_url,
            model=model,
            detail=(
                "Provider /v1/models doesn't list: " + ", ".join(missing)
            ),
            checks=checks,
        )
    return schemas.LLMTestResponse(
        ok=True,
        base_url=base_url,
        model=model,
        detail="Provider reachable, configured models all present.",
        checks=checks,
    )


@router.post("/test-vision", response_model=schemas.LLMVisionTestResponse)
async def test_vision(
    payload: Optional[schemas.LLMConfigUpdate] = None,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(require_admin),
):
    """Deep: send a tiny image through vision_completion with a strict schema."""
    eff = svc.get_effective_for_db(db)
    over = _resolve_overrides(eff, payload)
    if not over["base_url"] or not over["api_key"]:
        return schemas.LLMVisionTestResponse(
            ok=False,
            model=over["vision_model"] or "",
            detail="base_url and api_key must both be set.",
        )
    if not _TEST_PIXEL_PATH.exists():
        # Belt-and-suspenders: the asset is checked into the repo.
        return schemas.LLMVisionTestResponse(
            ok=False,
            model=over["vision_model"] or "",
            detail=f"Test asset missing on disk: {_TEST_PIXEL_PATH}",
        )

    try:
        client = OpenAICompatibleClient(
            base_url=over["base_url"],
            api_key=over["api_key"],
            timeout_seconds=over["timeout_seconds"],
        )
    except LLMError as exc:
        return schemas.LLMVisionTestResponse(
            ok=False, model=over["vision_model"] or "", detail=str(exc)
        )

    image_bytes = _TEST_PIXEL_PATH.read_bytes()
    try:
        result = await client.vision_completion(
            system_prompt=(
                "You are a vision test probe. Respond with the strict JSON "
                "schema: set ok=true and a short description of what you see."
            ),
            images=[image_bytes],
            schema=_PING_SCHEMA,
            model=over["vision_model"],
        )
    except LLMProviderError as exc:
        return schemas.LLMVisionTestResponse(
            ok=False,
            model=over["vision_model"],
            detail=f"Provider returned an unparseable response: {exc}",
        )
    except LLMError as exc:
        return schemas.LLMVisionTestResponse(
            ok=False,
            model=over["vision_model"],
            detail=f"Vision call failed: {exc}",
        )
    except Exception as exc:  # noqa: BLE001 — surface any provider error verbatim
        logger.exception("test-vision unexpected failure")
        return schemas.LLMVisionTestResponse(
            ok=False,
            model=over["vision_model"],
            detail=f"Vision call failed: {type(exc).__name__}: {exc}",
        )

    parsed = result.get("data")
    usage = result.get("usage") or {}
    tokens_in = int(usage.get("prompt_tokens", 0))
    tokens_out = int(usage.get("completion_tokens", 0))
    cost = estimate_cost_usd(
        model=over["vision_model"], tokens_in=tokens_in, tokens_out=tokens_out
    )

    # Upsert today's rollup row so the spend display reflects test
    # traffic. ``llm_usage`` has a UNIQUE(user_id, usage_date, feature)
    # constraint, so a second test run on the same day must accumulate
    # into the existing row rather than INSERT a duplicate.
    today = _floor_to_utc_day(datetime.now(timezone.utc))
    row = db.execute(
        select(models.LLMUsage)
        .where(models.LLMUsage.user_id == current_user.id)
        .where(models.LLMUsage.usage_date == today)
        .where(models.LLMUsage.feature == "config_test")
    ).scalar_one_or_none()
    if row is None:
        row = models.LLMUsage(
            user_id=current_user.id,
            usage_date=today,
            feature="config_test",
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost_usd=cost,
            request_count=1,
        )
        db.add(row)
    else:
        row.tokens_in = (row.tokens_in or 0) + tokens_in
        row.tokens_out = (row.tokens_out or 0) + tokens_out
        row.cost_usd = (row.cost_usd or 0.0) + cost
        row.request_count = (row.request_count or 0) + 1
    db.commit()

    ok = isinstance(parsed, dict) and parsed.get("ok") is True
    return schemas.LLMVisionTestResponse(
        ok=ok,
        model=over["vision_model"],
        detail=None if ok else "Provider didn't echo ok=true in the strict schema.",
        parsed_response=parsed if isinstance(parsed, dict) else None,
        usage=usage,
        cost_usd=cost,
    )
