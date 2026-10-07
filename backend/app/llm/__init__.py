"""Shared LLM layer for WHIS v3.1.

Everything that talks to OpenRouter / Venice.ai / LocalAI / Ollama flows
through ``OpenAICompatibleClient``. Features gate on
``settings.VISION_ENABLED`` / ``settings.PRICING_ENABLED`` — when both
are off, nothing in this package runs.
"""

from .budget import DailyBudgetGuard, estimate_cost_usd
from .openai_compatible import LLMError, LLMProviderError, OpenAICompatibleClient

__all__ = [
    "DailyBudgetGuard",
    "LLMError",
    "LLMProviderError",
    "OpenAICompatibleClient",
    "estimate_cost_usd",
]
