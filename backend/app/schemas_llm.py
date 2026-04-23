"""LLM-facing JSON Schemas (v3.0 pre-wire for v3.1).

v3.1 introduces Vision auto-fill and Item-value pricing, both of which
hand JSON Schemas to OpenRouter's ``response_format: json_schema`` so
the model returns schema-valid JSON by construction (see
``OR_docs/OR_structured-outputs.md``).

The schemas themselves will live here once the Pydantic models land.
Staging this module in v3.0 (empty for now) keeps v3.1's import path
stable and makes the contract visible: *one set* of Pydantic models,
published in two ways — OpenAPI → TypeScript for the frontend, JSON
Schema → OpenRouter for the LLM.

Example of what this module will export in v3.1::

    from pydantic import BaseModel
    class VisionSuggestion(BaseModel):
        name: str | None = None
        # … etc.

    VISION_SUGGESTION_SCHEMA: dict = VisionSuggestion.model_json_schema()

Downstream code in ``app.llm.openai_compatible`` will import the
schema constants and pass them to ``structured_completion``.
"""

from __future__ import annotations

# Intentionally empty in v3.0. v3.1 lands the Pydantic models + their
# `.model_json_schema()` constants here.

__all__: list[str] = []
