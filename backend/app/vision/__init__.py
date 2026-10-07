"""Vision auto-fill (v3.1).

User photographs an item, the LLM returns structured metadata. See
the v3.1 section of the plan for the full story.

Gated behind ``settings.VISION_ENABLED``. When off (the default), the
router returns 503 and no LLM HTTP is ever sent.
"""

from .service import VisionService

__all__ = ["VisionService"]
