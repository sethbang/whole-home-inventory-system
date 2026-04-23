"""Emit the FastAPI OpenAPI schema as JSON on stdout.

Consumed by ``frontend/scripts/generate-api-types.mjs`` which pipes
the output into ``openapi-typescript`` to produce the committed
``frontend/src/api/openapi.d.ts``.

Run with BYPASS_AUTH=true so importing ``app.main`` doesn't hit the
SECRET_KEY fail-fast check. The dump itself doesn't exercise auth.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

os.environ.setdefault("BYPASS_AUTH", "true")
# Silence info-level logs so stdout is pure JSON that openapi-typescript
# can consume without preprocessing.
os.environ.setdefault("LOG_LEVEL", "ERROR")

from app.main import app  # noqa: E402

if __name__ == "__main__":
    json.dump(app.openapi(), sys.stdout, indent=2)
    sys.stdout.write("\n")
