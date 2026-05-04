"""Seed the local DB with a curated dozen of diverse items + Venice.ai photos.

Generates 1-3 product photos per item via Venice.ai's nano-banana-2 model
and writes everything (Item rows, ItemImage rows, JPGs, WebP thumbnails)
into the configured DB and ``settings.upload_path``.

Idempotent: each seeded item is tagged with
``custom_fields.user_defined.seeded = "v1"``. On re-run, the script bails
out cleanly if any sentinel-tagged items exist for the dev user.

Partial failures: if the script raises mid-run after some items have been
committed, delete the seeded rows + their image files manually before
re-running. SQL: ``DELETE FROM items WHERE
json_extract(custom_fields,'$.user_defined.seeded')='v1';`` — the cascade
on ``item_images.item_id`` cleans up the image rows automatically. Then
``rm backend/uploads/<filenames>`` for the orphan files.

Usage (from backend/, with venv active):
    # Either:
    VENICE_API_KEY=sk-... python scripts/seed_items.py
    # Or, with backend/.env pointing at Venice:
    LLM_BASE_URL=https://api.venice.ai/api/v1 LLM_API_KEY=sk-... \
        python scripts/seed_items.py

Seed-user resolution: defaults to a 'developer' user, falling back to the
sole user when only one exists. Override with SEED_USER=<username>.
"""

from __future__ import annotations

import base64
import io
import logging
import os
import sys
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

os.environ.setdefault("BYPASS_AUTH", "true")

import httpx  # noqa: E402
from PIL import Image, ImageOps  # noqa: E402

from app import models  # noqa: E402
from app.database import SessionLocal  # noqa: E402
from app.services.images import (  # noqa: E402
    THUMBNAIL_PREFIX,
    THUMBNAIL_QUALITY,
    THUMBNAIL_SIZE,
)
from app.settings import settings  # noqa: E402

logger = logging.getLogger("seed_items")

VENICE_HOST = "https://api.venice.ai/api/v1"
DEFAULT_USERNAME = "developer"
SEED_SENTINEL = "v1"


# --- Curated item set ---------------------------------------------------
# Each entry mixes required (name/category/location) + optional fields,
# a per-item image-gen prompt, and an `images` count (1-4) handed to
# Venice via the `variants` parameter so each item is one HTTP call.
#
# `created_at_days_ago` backdates created_at across a ~6-month window so
# the Reports / Dashboard "recent" sort isn't all bunched at runtime.

NOW = datetime.utcnow()


def _date_ago(days: int) -> datetime:
    return NOW - timedelta(days=days)


def _date_ahead(days: int) -> datetime:
    return NOW + timedelta(days=days)


SEED_ITEMS: list[dict[str, Any]] = [
    {
        "name": 'Sony Bravia 65" A95L OLED TV',
        "category": "Electronics",
        "location": "Living Room",
        "brand": "Sony",
        "model_number": "XR-65A95L",
        "serial_number": "SNY-A95L-7QH22",
        "barcode": "027242926295",
        "purchase_date": _date_ago(190),
        "purchase_price": 3299.99,
        "current_value": 2400.00,
        "warranty_expiration": _date_ahead(540),
        "notes": "Calibrated for Movie/Filmmaker mode. HDMI 1 = AVR (eARC).",
        "user_defined_extras": {"room_owner": "shared", "condition": "excellent"},
        "images": 3,
        "prompt": (
            "Hyperrealistic studio product photo of a 65-inch Sony OLED 4K "
            "television mounted on a low walnut media console in a modern "
            "living room. Subtle cinematic lighting, sharp focus, soft "
            "background bokeh, no text or watermarks, no people."
        ),
        "created_at_days_ago": 190,
    },
    {
        "name": "West Elm Hamilton Leather Sofa",
        "category": "Furniture",
        "location": "Living Room",
        "brand": "West Elm",
        "model_number": "Hamilton-86",
        "purchase_date": _date_ago(720),
        "purchase_price": 2499.00,
        "current_value": 1100.00,
        "notes": "Saddle leather, 86\". Conditioned with Lexol every 6 mo.",
        "images": 2,
        "prompt": (
            "Hyperrealistic photo of a saddle-brown leather Chesterfield-style "
            "sofa in a sunlit living room with a hardwood floor and a small "
            "potted plant nearby. Natural window light, photographic detail "
            "on the leather grain, no text or watermarks."
        ),
        "created_at_days_ago": 720,
    },
    {
        "name": "KitchenAid Pro 600 Stand Mixer",
        "category": "Kitchen",
        "location": "Kitchen",
        "brand": "KitchenAid",
        "model_number": "KP26M1XER",
        "serial_number": "KA-PRO600-44129",
        "barcode": "883049031668",
        "purchase_date": _date_ago(1450),
        "purchase_price": 449.95,
        "current_value": 280.00,
        "notes": "Empire Red. Bowl + paddle + whisk + dough hook included.",
        "images": 2,
        "prompt": (
            "Photorealistic kitchen-counter shot of a red KitchenAid Pro 600 "
            "stand mixer with the dough hook attached. Marble countertop, "
            "subway-tile backsplash, soft morning light, sharp focus, no text."
        ),
        "created_at_days_ago": 60,
    },
    {
        "name": "DeWalt 20V MAX XR Cordless Drill Kit",
        "category": "Tools",
        "location": "Garage",
        "brand": "DeWalt",
        "model_number": "DCD791D2",
        "serial_number": "DW-DCD791-00913",
        "purchase_date": _date_ago(380),
        "purchase_price": 199.00,
        "current_value": 130.00,
        "warranty_expiration": _date_ahead(720),
        "notes": "Two 2.0Ah batteries + charger + soft case.",
        "images": 2,
        "prompt": (
            "Studio product photo of a yellow-and-black DeWalt 20V cordless "
            "drill resting on a workbench beside two battery packs and a "
            "charger. Workshop background slightly blurred, sharp focus on "
            "the drill, photographic, no text."
        ),
        "created_at_days_ago": 380,
    },
    {
        "name": "Patagonia Down Sweater Hoody",
        "category": "Clothing",
        "location": "Coat Closet",
        "brand": "Patagonia",
        "model_number": "84702",
        "purchase_date": _date_ago(280),
        "purchase_price": 329.00,
        "current_value": 180.00,
        "notes": "Smolder Blue, men's large. 800-fill recycled down.",
        "images": 1,
        "prompt": (
            "Studio photo of a deep blue Patagonia down hooded jacket on a "
            "wooden hanger against a neutral grey wall, soft side-lighting, "
            "showing texture of the down baffles, no text or watermarks."
        ),
        "created_at_days_ago": 280,
    },
    {
        "name": "Dell XPS 15 9530 Laptop",
        "category": "Electronics",
        "location": "Home Office",
        "brand": "Dell",
        "model_number": "XPS-9530",
        "serial_number": "DLL-9530-AHJ77",
        "purchase_date": _date_ago(110),
        "purchase_price": 2299.00,
        "current_value": 1700.00,
        "warranty_expiration": _date_ahead(620),
        "notes": "i7-13700H, 32GB RAM, 1TB NVMe. ProSupport Plus to 2027-12.",
        "user_defined_extras": {"asset_tag": "WHIS-DEV-LAP-002"},
        "images": 2,
        "prompt": (
            "Hyperrealistic photo of a sleek silver Dell XPS 15 laptop open "
            "on a wooden home-office desk with a minimal desk lamp and a "
            "ceramic mug nearby. Soft daylight, shallow depth of field, "
            "sharp focus on the laptop, no text or screen content."
        ),
        "created_at_days_ago": 110,
    },
    {
        "name": "Google Nest Learning Thermostat (3rd Gen)",
        "category": "Electronics",
        "location": "Hallway",
        "brand": "Google",
        "model_number": "T3007ES",
        "purchase_date": _date_ago(1100),
        "purchase_price": 249.00,
        "current_value": 90.00,
        "notes": "Stainless ring. Paired with the upstairs Nest Temperature Sensor.",
        "images": 1,
        "prompt": (
            "Close-up photo of a circular stainless-steel Nest Learning "
            "Thermostat mounted on a clean off-white interior wall, ambient "
            "morning light, soft shadow, photorealistic, no text overlay."
        ),
        "created_at_days_ago": 30,
    },
    {
        "name": "Weber Spirit II E-310 Gas Grill",
        "category": "Tools",
        "location": "Backyard Patio",
        "brand": "Weber",
        "model_number": "45010001",
        "serial_number": "WBR-SPIRIT-22188",
        "purchase_date": _date_ago(540),
        "purchase_price": 569.00,
        "current_value": 420.00,
        "warranty_expiration": _date_ahead(1460),
        "notes": "Black. Cast-iron porcelain-coated grates replaced 2026-02.",
        "images": 2,
        "prompt": (
            "Photorealistic patio scene of a black Weber three-burner gas "
            "grill on a stone patio at golden hour, lid open, clean grates "
            "visible, hint of greenery in the background, no people, no text."
        ),
        "created_at_days_ago": 540,
    },
    {
        "name": "IKEA Malm 6-Drawer Dresser",
        "category": "Furniture",
        "location": "Master Bedroom",
        "brand": "IKEA",
        "model_number": "Malm-6",
        "purchase_date": _date_ago(2900),
        "purchase_price": 229.00,
        "current_value": 90.00,
        "notes": "Black-brown. Anchored to wall stud per recall guidance.",
        "images": 1,
        "prompt": (
            "Photorealistic bedroom photo of a dark espresso six-drawer IKEA "
            "Malm-style dresser against a warm-white wall, with a small "
            "ceramic vase on top. Soft morning window light, sharp focus, no "
            "text or watermarks."
        ),
        "created_at_days_ago": 90,
    },
    {
        "name": "Dyson V11 Animal Cordless Vacuum",
        "category": "Tools",
        "location": "Hallway Closet",
        "brand": "Dyson",
        "model_number": "SV15",
        "serial_number": "DYS-V11-99023",
        "purchase_date": _date_ago(810),
        "purchase_price": 599.99,
        "current_value": 320.00,
        "warranty_expiration": _date_ahead(190),
        "notes": "Replaced battery 2025-11. Filters rinsed monthly.",
        "images": 2,
        "prompt": (
            "Studio product photo of a purple-and-blue Dyson cordless stick "
            "vacuum standing upright on a hardwood floor with the wand "
            "extended, soft natural light, photographic, sharp focus on the "
            "cyclonic head, no text."
        ),
        "created_at_days_ago": 7,
    },
    {
        "name": "Vitamix 5200 Standard Blender",
        "category": "Kitchen",
        "location": "Kitchen",
        "brand": "Vitamix",
        "model_number": "001372",
        "purchase_date": _date_ago(2200),
        "purchase_price": 449.00,
        "current_value": 220.00,
        "notes": "Black. 7-year warranty expired 2025-08.",
        "images": 1,
        "prompt": (
            "Hyperrealistic kitchen-counter photo of a black Vitamix 5200 "
            "blender with a clear pitcher full of green smoothie, marble "
            "countertop, soft morning light from a window, sharp focus, no "
            "text or watermarks."
        ),
        "created_at_days_ago": 150,
    },
    {
        "name": "Allen Edmonds Park Avenue Oxfords",
        "category": "Clothing",
        "location": "Coat Closet",
        "brand": "Allen Edmonds",
        "model_number": "5845",
        "purchase_date": _date_ago(160),
        "purchase_price": 425.00,
        "current_value": 280.00,
        "notes": "Black, 10.5D. Recrafted once (~2024).",
        "images": 1,
        "prompt": (
            "Studio product photo of a pair of polished black Allen Edmonds "
            "cap-toe oxford dress shoes side-by-side on a dark walnut "
            "surface, soft directional light revealing leather sheen, sharp "
            "focus, no text."
        ),
        "created_at_days_ago": 160,
    },
]


# --- Venice.ai integration ----------------------------------------------


class CredentialError(RuntimeError):
    pass


def resolve_credentials() -> tuple[str, str]:
    venice_key = os.environ.get("VENICE_API_KEY", "").strip()
    if venice_key:
        return venice_key, VENICE_HOST

    base = (settings.LLM_BASE_URL or "").rstrip("/")
    if base and "venice.ai" in base.lower() and settings.LLM_API_KEY:
        if not base.endswith("/v1"):
            base = base + "/v1"
        normalized = base.rsplit("/v1", 1)[0] + "/v1"
        return settings.LLM_API_KEY, normalized

    raise CredentialError(
        "No Venice.ai credentials. Set VENICE_API_KEY=sk-... in your "
        "environment, or set LLM_BASE_URL=https://api.venice.ai/api/v1 "
        "+ LLM_API_KEY in backend/.env."
    )


def venice_generate_images(
    *, api_key: str, base_url: str, prompt: str, variants: int
) -> list[bytes]:
    """Single POST to /image/generate. Returns ``variants`` JPEG byte blobs."""
    body = {
        "model": "nano-banana-2",
        "prompt": prompt,
        "aspect_ratio": "1:1",
        "resolution": "1K",
        "format": "jpeg",
        "variants": max(1, min(variants, 4)),
        "safe_mode": False,
        "hide_watermark": True,
    }
    url = f"{base_url}/image/generate"

    # Three attempts on 429/5xx with simple exponential backoff. nano-banana-2
    # 1K calls take ~25-30s server-side, so the timeout is generous.
    last_exc: Exception | None = None
    for attempt in range(3):
        try:
            resp = httpx.post(
                url,
                json=body,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                timeout=240,
            )
            if resp.status_code == 200:
                payload = resp.json()
                images = payload.get("images") or []
                if not images:
                    raise RuntimeError(f"empty images[] in 200 response: {payload}")
                return [base64.b64decode(b64) for b64 in images]
            if resp.status_code in (429, 500, 502, 503, 504):
                last_exc = RuntimeError(
                    f"HTTP {resp.status_code}: {resp.text[:300]}"
                )
            else:
                # Non-retryable 4xx — surface immediately.
                raise RuntimeError(
                    f"HTTP {resp.status_code}: {resp.text[:300]}"
                )
        except httpx.HTTPError as exc:
            last_exc = exc
        sleep_for = 2 ** attempt
        logger.warning("retrying after %ss (attempt %s/3): %s", sleep_for, attempt + 1, last_exc)
        time.sleep(sleep_for)
    raise RuntimeError(f"venice image generation failed after 3 attempts: {last_exc}")


# --- Disk + thumbnail helpers -------------------------------------------


def write_jpg_and_thumbnail(
    upload_dir: Path, jpg_bytes: bytes
) -> tuple[str, str, datetime]:
    """Write the JPG + a 512×512 WebP thumbnail. Returns (filename,
    thumbnail_path_relative, thumbnail_generated_at).

    Mirrors the on-disk + DB conventions in app/services/images.py:
      - JPG named ``YYYYMMDD_HHMMSS_<uuid4>.jpg``
      - Thumbnail named ``thumb_<basename>.webp``
      - file_path / thumbnail_path stored as ``uploads/<name>`` (relative)
    """
    upload_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_{uuid.uuid4()}.jpg"
    on_disk = upload_dir / filename
    on_disk.write_bytes(jpg_bytes)

    base_stem = on_disk.stem
    thumb_name = f"{THUMBNAIL_PREFIX}{base_stem}.webp"
    thumb_path = upload_dir / thumb_name

    with Image.open(io.BytesIO(jpg_bytes)) as img:
        oriented = ImageOps.exif_transpose(img)
        if oriented.mode not in ("RGB", "RGBA"):
            oriented = oriented.convert("RGB")
        fitted = ImageOps.fit(oriented, THUMBNAIL_SIZE, Image.Resampling.LANCZOS)
        fitted.save(
            thumb_path, format="WEBP", quality=THUMBNAIL_QUALITY, method=4
        )

    return filename, os.path.join("uploads", thumb_name), datetime.utcnow()


# --- Main ---------------------------------------------------------------


def find_seed_user(db) -> models.User:
    """Resolve the user that owns the seeded items.

    Priority:
      1. ``SEED_USER`` env var (exact username match) — explicit override.
      2. ``DEFAULT_USERNAME`` ("developer") if such a user exists.
      3. Single-user fallback: when exactly one user exists, use them.
    Otherwise: print available usernames and exit 1.
    """
    requested = os.environ.get("SEED_USER", "").strip()
    if requested:
        user = (
            db.query(models.User).filter(models.User.username == requested).first()
        )
        if not user:
            available = [u.username for u in db.query(models.User).all()]
            print(
                f"ERROR: SEED_USER={requested!r} not found. "
                f"Available: {available}",
                file=sys.stderr,
            )
            sys.exit(1)
        return user

    user = (
        db.query(models.User).filter(models.User.username == DEFAULT_USERNAME).first()
    )
    if user:
        return user

    all_users = db.query(models.User).all()
    if len(all_users) == 1:
        only = all_users[0]
        print(f"(no '{DEFAULT_USERNAME}' user; defaulting to single user '{only.username}')")
        return only

    available = [u.username for u in all_users]
    print(
        f"ERROR: cannot resolve seed user. Set SEED_USER=<username> "
        f"explicitly. Available: {available}",
        file=sys.stderr,
    )
    sys.exit(1)


def already_seeded(db, user: models.User) -> int:
    """Return count of items for the user carrying the seed sentinel."""
    rows = db.query(models.Item).filter(models.Item.owner_id == user.id).all()
    count = 0
    for item in rows:
        cf = item.custom_fields or {}
        ud = cf.get("user_defined") if isinstance(cf, dict) else None
        if isinstance(ud, dict) and ud.get("seeded") == SEED_SENTINEL:
            count += 1
    return count


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    try:
        api_key, base_url = resolve_credentials()
    except CredentialError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    db = SessionLocal()
    try:
        user = find_seed_user(db)

        existing = already_seeded(db, user)
        if existing:
            print(
                f"{existing} seeded item(s) already present for user "
                f"'{user.username}'; skipping. To re-seed, delete items "
                f"with custom_fields.user_defined.seeded='{SEED_SENTINEL}'."
            )
            return 0

        total_images = sum(entry["images"] for entry in SEED_ITEMS)
        print(
            f"Seeding {len(SEED_ITEMS)} items for user '{user.username}' "
            f"(~{total_images} images via Venice nano-banana-2)..."
        )

        upload_dir = settings.upload_path
        wall_started = time.monotonic()
        item_count = 0
        image_count = 0

        for idx, entry in enumerate(SEED_ITEMS, start=1):
            label = entry["name"]
            n_imgs = int(entry["images"])
            print(f"  [{idx:2d}/{len(SEED_ITEMS)}] {label} — generating {n_imgs} image(s)...", end=" ", flush=True)

            t0 = time.monotonic()
            jpg_blobs = venice_generate_images(
                api_key=api_key,
                base_url=base_url,
                prompt=entry["prompt"],
                variants=n_imgs,
            )
            elapsed = time.monotonic() - t0

            user_defined = {"seeded": SEED_SENTINEL}
            user_defined.update(entry.get("user_defined_extras") or {})

            item = models.Item(
                owner_id=user.id,
                name=entry["name"],
                category=entry["category"],
                location=entry["location"],
                brand=entry.get("brand"),
                model_number=entry.get("model_number"),
                serial_number=entry.get("serial_number"),
                barcode=entry.get("barcode"),
                purchase_date=entry.get("purchase_date"),
                purchase_price=entry.get("purchase_price"),
                current_value=entry.get("current_value"),
                warranty_expiration=entry.get("warranty_expiration"),
                notes=entry.get("notes"),
                custom_fields={"user_defined": user_defined},
                created_at=_date_ago(int(entry.get("created_at_days_ago", 0))),
            )
            db.add(item)
            db.flush()  # assign item.id for ItemImage FKs

            for jpg in jpg_blobs:
                filename, thumb_rel, thumb_gen_at = write_jpg_and_thumbnail(
                    upload_dir, jpg
                )
                db.add(
                    models.ItemImage(
                        item_id=item.id,
                        filename=filename,
                        file_path=os.path.join("uploads", filename),
                        thumbnail_path=thumb_rel,
                        thumbnail_generated_at=thumb_gen_at,
                    )
                )
                image_count += 1

            db.commit()  # commit per item so a mid-run crash leaves a recoverable state
            item_count += 1
            print(f"ok ({elapsed:.1f}s)")

        wall_elapsed = time.monotonic() - wall_started
        print(
            f"Seeded {item_count} items, {image_count} images written to "
            f"{upload_dir}. Total wall time {wall_elapsed:.1f}s."
        )
        return 0

    except Exception:
        db.rollback()
        logger.exception("seed run aborted")
        return 2
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
