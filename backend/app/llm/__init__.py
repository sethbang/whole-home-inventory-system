"""Shared LLM layer for WHIS v3.1.

Everything that talks to OpenRouter / Venice.ai / LocalAI / Ollama flows
through ``OpenAICompatibleClient``. Features gate on
``settings.VISION_ENABLED`` / ``settings.PRICING_ENABLED`` — when both
are off, nothing in this package runs.
"""

from .openai_compatible import OpenAICompatibleClient, LLMError, LLMProviderError

__all__ = [
    "OpenAICompatibleClient",
    "LLMError",
    "LLMProviderError",
]
