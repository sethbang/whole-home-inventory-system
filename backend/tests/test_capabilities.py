"""Tests for app.llm.capabilities — fixture-driven tri-state detection."""

from __future__ import annotations

import pytest

from app.llm.capabilities import detect_strict_json, detect_vision


# ---- Vision detection ----------------------------------------------------


def test_venice_explicit_false() -> None:
    """Venice exposes supportsVision=False on text-only models."""
    entry = {
        "id": "llama-3.2-3b",
        "model_spec": {
            "capabilities": {
                "supportsVision": False,
                "supportsResponseSchema": True,
                "supportsMultipleImages": False,
            }
        },
        "type": "text",
    }
    assert detect_vision(entry) is False


def test_venice_explicit_true() -> None:
    entry = {
        "id": "qwen2.5-vl",
        "model_spec": {"capabilities": {"supportsVision": True}},
    }
    assert detect_vision(entry) is True


def test_openrouter_input_modalities_image() -> None:
    """OpenRouter's modern shape: architecture.input_modalities."""
    entry = {
        "id": "google/gemini-2.5-flash",
        "architecture": {
            "input_modalities": ["text", "image"],
            "output_modalities": ["text"],
        },
    }
    assert detect_vision(entry) is True


def test_openrouter_input_modalities_text_only() -> None:
    entry = {
        "id": "mistralai/mistral-7b",
        "architecture": {
            "input_modalities": ["text"],
            "output_modalities": ["text"],
        },
    }
    assert detect_vision(entry) is False


def test_openrouter_modality_string_legacy() -> None:
    entry = {
        "id": "openai/gpt-4o",
        "architecture": {"modality": "text+image->text"},
    }
    assert detect_vision(entry) is True


def test_modality_string_text_only() -> None:
    entry = {"id": "x", "architecture": {"modality": "text->text"}}
    assert detect_vision(entry) is False


def test_openai_no_capability_fields_returns_none() -> None:
    """Raw OpenAI /v1/models has no modality info."""
    entry = {
        "id": "gpt-4o-mini",
        "object": "model",
        "created": 1700000000,
        "owned_by": "openai",
    }
    assert detect_vision(entry) is None


def test_ollama_v1_models_returns_none() -> None:
    entry = {"id": "llama3.2", "object": "model"}
    assert detect_vision(entry) is None


def test_empty_object_returns_none() -> None:
    assert detect_vision({}) is None


def test_multimodal_boolean_alias() -> None:
    assert detect_vision({"id": "x", "multimodal": True}) is True
    assert detect_vision({"id": "x", "isMultimodal": False}) is False


def test_snake_case_supports_vision() -> None:
    assert detect_vision({"id": "x", "supports_vision": True}) is True


def test_uppercased_modality_token_matches() -> None:
    """Tokens are matched case-insensitively in modality lists."""
    assert (
        detect_vision({"id": "x", "input_modalities": ["TEXT", "IMAGE"]}) is True
    )


def test_modality_list_with_visual_token() -> None:
    assert detect_vision({"id": "x", "modalities": ["text", "visual"]}) is True


def test_explicit_true_wins_over_list_silence() -> None:
    """If both signals exist and the explicit one says yes, return True."""
    entry = {
        "id": "x",
        "supportsVision": True,
        "input_modalities": ["text"],
    }
    assert detect_vision(entry) is True


# ---- Strict-JSON detection ----------------------------------------------


def test_venice_supports_response_schema_true() -> None:
    entry = {
        "id": "llama-3.2-3b",
        "model_spec": {"capabilities": {"supportsResponseSchema": True}},
    }
    assert detect_strict_json(entry) is True


def test_venice_supports_response_schema_false() -> None:
    entry = {
        "id": "ancient-model",
        "model_spec": {"capabilities": {"supportsResponseSchema": False}},
    }
    assert detect_strict_json(entry) is False


def test_openrouter_no_strict_json_field_returns_none() -> None:
    """OR's /v1/models doesn't expose strict-schema support."""
    entry = {
        "id": "anthropic/claude-sonnet-4.6",
        "architecture": {"input_modalities": ["text", "image"]},
    }
    assert detect_strict_json(entry) is None


def test_structured_outputs_alias() -> None:
    assert (
        detect_strict_json({"id": "x", "structured_outputs": True}) is True
    )


def test_supports_json_schema_alias() -> None:
    assert (
        detect_strict_json({"id": "x", "supportsJsonSchema": True}) is True
    )


@pytest.mark.parametrize("value", [None, "yes", 1, []])
def test_strict_json_non_bool_values_are_ignored(value) -> None:
    entry = {"id": "x", "supportsResponseSchema": value}
    assert detect_strict_json(entry) is None
