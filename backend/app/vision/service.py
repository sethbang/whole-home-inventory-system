"""VisionService — orchestrates the LLM call + usage accounting.

Synchronous API (runs inside the ARQ worker, not on a request
thread). Caller passes image bytes + optional hints; the service
returns a :class:`VisionResult` envelope or raises an
``HTTPException`` when the budget cap has been reached.

The envelope shape is what ``GET /api/jobs/{id}`` surfaces under
``result``. Frontend consumers decode it via the OpenAPI-generated
``VisionResult`` type.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from .. import models
from ..llm import DailyBudgetGuard, LLMError, LLMProviderError, OpenAICompatibleClient
from ..llm.prompts import VISION_SYSTEM_PROMPT
from ..schemas_llm import (
    PROMPT_VERSION,
    VISION_SUGGESTION_SCHEMA,
    VisionResult,
    VisionSuggestion,
)
from ..services import llm_config as llm_config_service
from ..settings import settings

logger = logging.getLogger(__name__)


class VisionService:
    """Façade over the async OpenAI-compatible client.

    Exposes both sync and async entry points:

    * :meth:`identify_async` — the canonical coroutine, awaited directly
      by FastAPI's async handlers and the ARQ worker task.
    * :meth:`identify` — sync shim that wraps the coroutine with
      :func:`asyncio.run`. Used by tests and any future non-async
      caller (CLI scripts, one-off jobs). Must NOT be called from
      within a running event loop — it will raise "asyncio.run()
      cannot be called from a running event loop".
    """

    def __init__(self, db: Session, user: models.User) -> None:
        self.db = db
        self.user = user

    def identify(
        self,
        images: Iterable[bytes],
        *,
        hints: Optional[Dict[str, Any]] = None,
        client: Optional[OpenAICompatibleClient] = None,
    ) -> VisionResult:
        """Synchronous entry point. Wraps :meth:`identify_async`."""
        return asyncio.run(
            self.identify_async(images, hints=hints, client=client)
        )

    async def identify_async(
        self,
        images: Iterable[bytes],
        *,
        hints: Optional[Dict[str, Any]] = None,
        client: Optional[OpenAICompatibleClient] = None,
    ) -> VisionResult:
        """Run vision identification end-to-end (async).

        Preflight:
          1. Feature flag + config (settings.VISION_ENABLED, LLM_BASE_URL, LLM_API_KEY).
          2. Image count (bounded by VISION_MAX_IMAGES_PER_REQUEST).
          3. Daily budget cap.
        Call:
          4. structured_completion with the vision schema.
        Post:
          5. Record usage (tokens + cost).
          6. Validate the response with Pydantic for defense-in-depth.
          7. Wrap in a VisionResult with provenance metadata.
        """
        # Resolve effective config first so a UI-driven feature-flag /
        # model change goes live without a restart.
        eff = llm_config_service.get_effective_for_db(self.db)

        if not eff.vision_enabled:
            raise HTTPException(
                status_code=503, detail="Vision auto-fill is disabled on this deployment."
            )

        image_list = list(images)
        if not image_list:
            raise HTTPException(status_code=400, detail="At least one image is required.")
        if len(image_list) > settings.VISION_MAX_IMAGES_PER_REQUEST:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Too many images: got {len(image_list)}, "
                    f"max is {settings.VISION_MAX_IMAGES_PER_REQUEST}."
                ),
            )

        guard = DailyBudgetGuard(self.db, self.user)
        guard.check_or_raise("vision")

        vision_model = eff.vision_model
        client = client or OpenAICompatibleClient()

        try:
            response = await client.vision_completion(
                system_prompt=VISION_SYSTEM_PROMPT,
                images=image_list,
                hints=hints,
                schema=VISION_SUGGESTION_SCHEMA,
                model=vision_model,
            )
        except LLMProviderError:
            # Pre-parse error — the content was garbage. Record a
            # zero-cost usage marker so the cap guard sees the
            # request happened, then surface.
            guard.record_usage(
                "vision",
                model=vision_model,
                usage={"prompt_tokens": 0, "completion_tokens": 0},
            )
            raise HTTPException(
                status_code=502,
                detail="Vision provider returned an unparseable response.",
            )
        except LLMError as exc:
            logger.exception("vision LLM call failed: %s", exc)
            raise HTTPException(
                status_code=502, detail="Vision provider call failed."
            )

        usage = response.get("usage", {})
        guard.record_usage("vision", model=vision_model, usage=usage)

        # Second-pass validation. Strict mode + response healing
        # should already guarantee schema-valid JSON, but this
        # catches the (rare) case of a provider that silently
        # ignored strict mode.
        try:
            suggestion = VisionSuggestion.model_validate(response["data"])
        except Exception:
            logger.exception("vision response failed Pydantic validation: %s", response["data"])
            raise HTTPException(
                status_code=502,
                detail="Vision provider returned a response that didn't match the expected schema.",
            )

        from ..llm.budget import estimate_cost_usd  # local to avoid import cycles

        tokens_in = int(usage.get("prompt_tokens", 0))
        tokens_out = int(usage.get("completion_tokens", 0))
        cost = estimate_cost_usd(
            model=vision_model, tokens_in=tokens_in, tokens_out=tokens_out
        )
        return VisionResult(
            suggestion=suggestion,
            provider=client.provider,
            model=vision_model,
            prompt_version=PROMPT_VERSION,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost_usd_estimate=cost,
            queried_at=datetime.now(timezone.utc),
        )
