"""One-shot smoke test for Venice.ai's nano-banana-2 image endpoint.

Run before the seed_items.py seeder to confirm credentials work and image
quality is acceptable. Generates a single image, writes it under
backend/uploads/, and prints timing + bytes.

Usage (from backend/):
    # Either point LLM_BASE_URL at Venice and use LLM_API_KEY:
    LLM_BASE_URL=https://api.venice.ai/api/v1 LLM_API_KEY=sk-... \
        python scripts/test_venice_image.py
    # Or use a dedicated VENICE_API_KEY override (URL is hardcoded):
    VENICE_API_KEY=sk-... python scripts/test_venice_image.py

Optional overrides:
    SMOKE_PROMPT     — image prompt (default: a cozy reading nook)
    SMOKE_RESOLUTION — "1K" / "2K" / "4K" (default 1K)
"""

from __future__ import annotations

import base64
import os
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Settings has a fail-fast on missing SECRET_KEY when BYPASS_AUTH != true.
# We don't actually need auth to run a smoke test, so mirror bootstrap.py.
os.environ.setdefault("BYPASS_AUTH", "true")

import httpx  # noqa: E402

from app.settings import settings  # noqa: E402

VENICE_HOST = "https://api.venice.ai/api/v1"
DEFAULT_PROMPT = (
    "A cozy reading nook with a leather armchair, a small side table holding a "
    "ceramic mug of coffee, soft window light from the left, photorealistic, "
    "shallow depth of field, no text or watermarks."
)


def resolve_credentials() -> tuple[str, str]:
    """Pick (api_key, base_url) from env. Returns Venice-pinned URL.

    Priority:
      1. VENICE_API_KEY env override (URL pinned to api.venice.ai).
      2. settings.LLM_API_KEY when settings.LLM_BASE_URL points at Venice.
    Otherwise: instructive exit.
    """
    venice_key = os.environ.get("VENICE_API_KEY", "").strip()
    if venice_key:
        return venice_key, VENICE_HOST

    base = (settings.LLM_BASE_URL or "").rstrip("/")
    if base and "venice.ai" in base.lower() and settings.LLM_API_KEY:
        # Normalize trailing /v1 if present.
        if not base.endswith("/v1"):
            base = base + "/v1"
        return settings.LLM_API_KEY, base.rsplit("/v1", 1)[0] + "/v1"

    print(
        "ERROR: no Venice.ai credentials found.\n"
        "  Either set VENICE_API_KEY=sk-... in your environment,\n"
        "  or set LLM_BASE_URL=https://api.venice.ai/api/v1 + LLM_API_KEY in backend/.env.",
        file=sys.stderr,
    )
    sys.exit(1)


def main() -> int:
    api_key, base_url = resolve_credentials()
    url = f"{base_url}/image/generate"

    prompt = os.environ.get("SMOKE_PROMPT") or DEFAULT_PROMPT
    resolution = os.environ.get("SMOKE_RESOLUTION", "1K")

    body = {
        "model": "nano-banana-2",
        "prompt": prompt,
        "aspect_ratio": "1:1",
        "resolution": resolution,
        "format": "jpeg",
        "variants": 1,
        "safe_mode": False,
        "hide_watermark": True,
    }

    print(f"POST {url}")
    print(
        f"  model=nano-banana-2  resolution={resolution}  aspect_ratio=1:1  variants=1"
    )

    started = time.monotonic()
    try:
        resp = httpx.post(
            url,
            json=body,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            timeout=180,
        )
    except httpx.HTTPError as exc:
        print(f"ERROR: HTTP transport failure: {exc}", file=sys.stderr)
        return 2
    elapsed_ms = int((time.monotonic() - started) * 1000)

    if resp.status_code != 200:
        print(
            f"ERROR: HTTP {resp.status_code}: {resp.text[:500]}",
            file=sys.stderr,
        )
        return 3

    payload = resp.json()
    images = payload.get("images") or []
    if not images:
        print(
            f"ERROR: response had no images. Body: {payload}",
            file=sys.stderr,
        )
        return 4

    blurred = resp.headers.get("x-venice-is-blurred", "").lower() == "true"
    violation = (
        resp.headers.get("x-venice-is-content-violation", "").lower() == "true"
    )

    img_bytes = base64.b64decode(images[0])
    upload_dir = settings.upload_path
    upload_dir.mkdir(parents=True, exist_ok=True)
    out_name = f"venice_smoke_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.jpg"
    out_path = upload_dir / out_name
    out_path.write_bytes(img_bytes)

    print(f"  total={elapsed_ms}ms  bytes={len(img_bytes)}")
    print(f"  request_id={payload.get('id', '?')}")
    timing = payload.get("timing") or {}
    if timing:
        print(
            f"  inference={int(timing.get('inferenceDuration', 0))}ms  "
            f"queue={int(timing.get('inferenceQueueTime', 0))}ms  "
            f"preprocess={int(timing.get('inferencePreprocessingTime', 0))}ms"
        )
    if blurred:
        print("  WARN: response was blurred (safe_mode triggered).")
    if violation:
        print("  WARN: response flagged as content violation.")
    print(f"Wrote {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
