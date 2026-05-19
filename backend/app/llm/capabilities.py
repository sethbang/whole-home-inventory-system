"""Heuristic capability detection for ``/v1/models`` entries (v3.2).

Different OpenAI-compatible providers describe capabilities very
differently — and the ones that don't describe them at all are still
common (raw OpenAI, Ollama). This module walks each model entry
recursively looking for keys whose names indicate vision support or
strict-JSON-schema (``response_format: json_schema``) support and
returns a tri-state result:

* ``True``  — the provider explicitly says yes
* ``False`` — the provider explicitly says no
* ``None``  — no capability flag found; the caller should treat the
  model as "unknown" and rely on the user (or the live test endpoint)
  for the answer.

Hard-coded model name allowlists were considered and rejected: they
rot fast, miss new releases, and only solve the easy half of the
problem. The capability flags shipped by providers like Venice and
OpenRouter are far more authoritative when they exist.
"""

from __future__ import annotations

from typing import Any, Iterable, Optional

# Boolean-style keys that flip on / off vision support.
_VISION_BOOL_KEYS = frozenset(
    {
        "supportsVision",
        "supports_vision",
        "vision",
        "multimodal",
        "isMultimodal",
        "is_multimodal",
        "supportsImage",
        "supports_image",
    }
)

# Keys whose value is a list of modalities (strings). Vision is true
# when any element is a vision-typed token.
_MODALITY_LIST_KEYS = frozenset(
    {
        "input_modalities",
        "inputModalities",
        "modalities",
        "supported_modalities",
        "supportedModalities",
    }
)

# Keys whose value is a single modality string.
_MODALITY_STR_KEYS = frozenset({"modality", "input_modality"})

# Tokens (case-insensitive substrings) that indicate vision in a
# modality string or list element.
_VISION_TOKENS = ("image", "vision", "visual")

# Strict-JSON / response-format support flags.
_STRICT_JSON_BOOL_KEYS = frozenset(
    {
        "supportsResponseSchema",
        "supports_response_schema",
        "supportsResponseFormat",
        "supports_response_format",
        "supportsJsonSchema",
        "supports_json_schema",
        "responseSchema",
        "structuredOutputs",
        "structured_outputs",
        "supports_structured_outputs",
    }
)


def _walk(node: Any) -> Iterable[tuple[str, Any]]:
    """Yield every (key, value) pair in a nested dict/list structure."""
    if isinstance(node, dict):
        for k, v in node.items():
            yield k, v
            yield from _walk(v)
    elif isinstance(node, list):
        for v in node:
            yield from _walk(v)


def _has_vision_token(value: Any) -> bool:
    if isinstance(value, str):
        lowered = value.lower()
        return any(tok in lowered for tok in _VISION_TOKENS)
    return False


def _modality_list_says_vision(items: Any) -> Optional[bool]:
    """For a list-typed modality value, decide vision support tri-state."""
    if not isinstance(items, list):
        return None
    if not items:
        return None
    if any(_has_vision_token(item) for item in items):
        return True
    # All elements are strings, none mention image/vision.
    if all(isinstance(item, str) for item in items):
        return False
    return None


def detect_vision(model_obj: Any) -> Optional[bool]:
    """Tri-state vision-capability detection.

    Walks the model entry recursively. The first match wins, ranked:

    1. Explicit boolean key (``supportsVision``, ``multimodal``, ...).
    2. Modality list (``input_modalities`` etc.).
    3. Modality string (``modality``, ``input_modality``).

    Returns ``None`` when no relevant key is present.
    """
    explicit_false_seen = False
    for k, v in _walk(model_obj):
        if k in _VISION_BOOL_KEYS and isinstance(v, bool):
            if v:
                return True
            explicit_false_seen = True
            continue
        if k in _MODALITY_LIST_KEYS:
            decision = _modality_list_says_vision(v)
            if decision is True:
                return True
            if decision is False:
                explicit_false_seen = True
        if k in _MODALITY_STR_KEYS and isinstance(v, str):
            if _has_vision_token(v):
                return True
            explicit_false_seen = True
    return False if explicit_false_seen else None


def detect_strict_json(model_obj: Any) -> Optional[bool]:
    """Tri-state strict-JSON-schema-capability detection.

    Looks for boolean flags whose names suggest JSON-schema /
    structured-output support. Returns ``None`` when no relevant key
    is present.
    """
    explicit_false_seen = False
    for k, v in _walk(model_obj):
        if k in _STRICT_JSON_BOOL_KEYS and isinstance(v, bool):
            if v:
                return True
            explicit_false_seen = True
    return False if explicit_false_seen else None
