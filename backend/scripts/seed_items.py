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
    # --- Batch 2 ---------------------------------------------------------
    {
        "name": 'Apple iPad Pro 12.9" (M2)',
        "category": "Electronics",
        "location": "Home Office",
        "brand": "Apple",
        "model_number": "MNXF3LL/A",
        "serial_number": "APL-IPADPRO-V8H21",
        "purchase_date": _date_ago(420),
        "purchase_price": 1499.00,
        "current_value": 950.00,
        "warranty_expiration": _date_ahead(60),
        "notes": "Space Gray, 256GB, Wi-Fi + Cellular. AppleCare+ to 2026-07.",
        "images": 2,
        "prompt": (
            "Hyperrealistic studio product photo of a silver Apple iPad Pro "
            "tablet with a black Magic Keyboard attached on a clean walnut "
            "desk, an Apple Pencil resting beside it, soft daylight, sharp "
            "focus, photorealistic, blank screen, no text or watermarks."
        ),
        "created_at_days_ago": 45,
    },
    {
        "name": "Sonos Beam (Gen 2)",
        "category": "Electronics",
        "location": "Living Room",
        "brand": "Sonos",
        "model_number": "BEAM2US1BLK",
        "purchase_date": _date_ago(220),
        "purchase_price": 499.00,
        "current_value": 320.00,
        "warranty_expiration": _date_ahead(140),
        "notes": "Black. HDMI eARC to the Bravia.",
        "images": 1,
        "prompt": (
            "Photorealistic photo of a slim black Sonos Beam soundbar mounted "
            "on a media console under a wall-mounted flat-screen TV in a "
            "modern living room, ambient evening lighting, sharp focus, no "
            "text or watermarks."
        ),
        "created_at_days_ago": 220,
    },
    {
        "name": "Eero 6+ Mesh Wi-Fi (3-pack)",
        "category": "Electronics",
        "location": "Hallway",
        "brand": "Amazon",
        "model_number": "L010311",
        "purchase_date": _date_ago(370),
        "purchase_price": 299.00,
        "current_value": 180.00,
        "notes": "Three pucks: hallway gateway, basement, upstairs landing.",
        "images": 1,
        "prompt": (
            "Studio product photo of three small white Eero mesh wi-fi router "
            "pucks lined up on a clean white surface, soft directional light, "
            "sharp focus, photorealistic, no text or watermarks."
        ),
        "created_at_days_ago": 370,
    },
    {
        "name": "Bose QuietComfort Ultra Headphones",
        "category": "Electronics",
        "location": "Home Office",
        "brand": "Bose",
        "model_number": "QC-Ultra",
        "serial_number": "BOSE-QCU-44219",
        "purchase_date": _date_ago(95),
        "purchase_price": 429.00,
        "current_value": 320.00,
        "warranty_expiration": _date_ahead(635),
        "notes": "Black. Replacement ear cushions ordered 2026-04.",
        "images": 2,
        "prompt": (
            "Hyperrealistic studio product photo of black over-ear "
            "noise-cancelling Bose headphones resting on a walnut desk beside "
            "a closed laptop, soft directional light, sharp detail on the "
            "leather cushioning and headband, photorealistic, no text or "
            "watermarks."
        ),
        "created_at_days_ago": 95,
    },
    {
        "name": "Nintendo Switch OLED",
        "category": "Electronics",
        "location": "Family Room",
        "brand": "Nintendo",
        "model_number": "HEG-001",
        "serial_number": "NIN-OLED-87213",
        "barcode": "045496882129",
        "purchase_date": _date_ago(640),
        "purchase_price": 349.99,
        "current_value": 220.00,
        "notes": "White. Pro controller + 256GB SD card.",
        "images": 1,
        "prompt": (
            "Photorealistic photo of a Nintendo Switch OLED handheld gaming "
            "console on a coffee table, blue-and-red Joy-Cons attached, blank "
            "vibrant screen, soft living-room lighting, sharp focus, no text."
        ),
        "created_at_days_ago": 14,
    },
    {
        "name": "Canon EOS R8 Mirrorless Camera",
        "category": "Electronics",
        "location": "Home Office",
        "brand": "Canon",
        "model_number": "EOS R8",
        "serial_number": "CAN-R8-22019",
        "purchase_date": _date_ago(170),
        "purchase_price": 1499.00,
        "current_value": 1180.00,
        "warranty_expiration": _date_ahead(560),
        "notes": "Body + RF 24-105mm f/4-7.1 IS STM kit lens.",
        "images": 2,
        "prompt": (
            "Studio product photo of a black Canon mirrorless camera with a "
            "24-105mm zoom lens attached on a textured grey backdrop, "
            "side-lit, sharp detail on the buttons and dial, photorealistic, "
            "no text or watermarks."
        ),
        "created_at_days_ago": 170,
    },
    {
        "name": "LG WashTower (WKEX200HWA)",
        "category": "Appliances",
        "location": "Laundry Room",
        "brand": "LG",
        "model_number": "WKEX200HWA",
        "serial_number": "LG-WT-117732",
        "purchase_date": _date_ago(900),
        "purchase_price": 2399.00,
        "current_value": 1500.00,
        "warranty_expiration": _date_ahead(165),
        "notes": "White. Single-unit stacked. Dryer vent cleaned 2026-02.",
        "images": 1,
        "prompt": (
            "Photorealistic photo of a stacked white LG WashTower washer-dryer "
            "unit installed in a clean laundry room with a folding counter "
            "beside it, soft daylight from a small window, sharp focus, no "
            "text."
        ),
        "created_at_days_ago": 900,
    },
    {
        "name": "iRobot Roomba j7+",
        "category": "Electronics",
        "location": "Hallway Closet",
        "brand": "iRobot",
        "model_number": "j7+",
        "serial_number": "IRB-J7P-30122",
        "purchase_date": _date_ago(480),
        "purchase_price": 599.00,
        "current_value": 280.00,
        "notes": "Self-emptying base in the laundry room.",
        "images": 1,
        "prompt": (
            "Photorealistic photo of a round black iRobot Roomba robot vacuum "
            "docked on its tall self-emptying charging base on a hardwood "
            "floor in a hallway, soft natural light, sharp focus, no text or "
            "watermarks."
        ),
        "created_at_days_ago": 480,
    },
    {
        "name": "Herman Miller Aeron Chair (Size B)",
        "category": "Furniture",
        "location": "Home Office",
        "brand": "Herman Miller",
        "model_number": "AER1B23DW",
        "purchase_date": _date_ago(1700),
        "purchase_price": 1645.00,
        "current_value": 950.00,
        "warranty_expiration": _date_ahead(2500),
        "notes": "Graphite. Posture fit + adjustable arms. 12-yr warranty.",
        "images": 2,
        "prompt": (
            "Photorealistic photo of a black Herman Miller Aeron office chair "
            "behind a wooden desk in a modern home office, soft window light "
            "from the side, photorealistic, sharp detail on the woven mesh "
            "back, no text."
        ),
        "created_at_days_ago": 200,
    },
    {
        "name": "Crate & Barrel Lounge II Daybed",
        "category": "Furniture",
        "location": "Family Room",
        "brand": "Crate & Barrel",
        "model_number": "LoungeII-Day",
        "purchase_date": _date_ago(1100),
        "purchase_price": 2199.00,
        "current_value": 950.00,
        "notes": "Cement-grey performance fabric. Slipcovers professionally cleaned 2026-01.",
        "images": 1,
        "prompt": (
            "Photorealistic photo of a deep light-grey upholstered daybed "
            "sofa with several throw pillows in a sunlit family room with a "
            "cream area rug, photorealistic, sharp focus, no text."
        ),
        "created_at_days_ago": 1100,
    },
    {
        "name": "Pottery Barn Benchwright Dining Table",
        "category": "Furniture",
        "location": "Dining Room",
        "brand": "Pottery Barn",
        "model_number": "Benchwright-86",
        "purchase_date": _date_ago(1850),
        "purchase_price": 1899.00,
        "current_value": 1100.00,
        "notes": 'Rustic mahogany, 86". Six matching Benchwright chairs.',
        "images": 2,
        "prompt": (
            "Photorealistic photo of a long rectangular weathered-oak "
            "farmhouse dining table with six matching upholstered chairs in "
            "a sunlit dining room with hardwood floors, photorealistic, soft "
            "window light, sharp focus on wood grain, no text or watermarks."
        ),
        "created_at_days_ago": 240,
    },
    {
        "name": "Article Sven Sofa (Charme Tan)",
        "category": "Furniture",
        "location": "Family Room",
        "brand": "Article",
        "model_number": "Sven-Charme-72",
        "purchase_date": _date_ago(380),
        "purchase_price": 1499.00,
        "current_value": 950.00,
        "notes": "Charme tan tufted leather, 72\".",
        "images": 1,
        "prompt": (
            "Photorealistic photo of a tan tufted leather mid-century sofa "
            "in a sunlit family room with a wool area rug and a wooden "
            "coffee table, photorealistic, sharp focus on leather grain, no "
            "text."
        ),
        "created_at_days_ago": 380,
    },
    {
        "name": "CB2 Stairway Wall-Mounted Bookcase",
        "category": "Furniture",
        "location": "Home Office",
        "brand": "CB2",
        "model_number": "Stairway-White",
        "purchase_date": _date_ago(2100),
        "purchase_price": 749.00,
        "current_value": 280.00,
        "notes": "White, two-section, anchored to wall stud.",
        "images": 1,
        "prompt": (
            "Photorealistic photo of a tall white wall-mounted bookcase "
            "filled with neatly arranged hardback books and a few decorative "
            "objects, modern home-office wall behind it, soft daylight, "
            "sharp focus, no text or watermarks."
        ),
        "created_at_days_ago": 130,
    },
    {
        "name": "Le Creuset 7.25 qt Round Dutch Oven",
        "category": "Kitchen",
        "location": "Kitchen",
        "brand": "Le Creuset",
        "model_number": "LS2501-2867",
        "purchase_date": _date_ago(2400),
        "purchase_price": 449.95,
        "current_value": 280.00,
        "notes": "Cerise (cherry red).",
        "images": 1,
        "prompt": (
            "Studio product photo of a glossy cherry-red Le Creuset enameled "
            "cast-iron Dutch oven with the lid slightly ajar on a marble "
            "countertop, soft natural light, sharp focus, photorealistic, no "
            "text."
        ),
        "created_at_days_ago": 320,
    },
    {
        "name": "Wüsthof Classic Ikon 8\" Chef's Knife",
        "category": "Kitchen",
        "location": "Kitchen",
        "brand": "Wüsthof",
        "model_number": "4596-7/20",
        "purchase_date": _date_ago(720),
        "purchase_price": 199.95,
        "current_value": 130.00,
        "notes": "Honed weekly, professionally sharpened twice a year.",
        "images": 1,
        "prompt": (
            "Studio product photo of a high-end black-handled chef's knife "
            "on a maple cutting board with finely chopped herbs nearby, soft "
            "directional light, sharp focus on the polished blade edge, "
            "photorealistic, no text."
        ),
        "created_at_days_ago": 720,
    },
    {
        "name": "Breville Barista Express Espresso Machine",
        "category": "Kitchen",
        "location": "Kitchen",
        "brand": "Breville",
        "model_number": "BES870XL",
        "serial_number": "BRV-BES870-66104",
        "purchase_date": _date_ago(560),
        "purchase_price": 749.95,
        "current_value": 480.00,
        "warranty_expiration": _date_ahead(45),
        "notes": "Brushed stainless. Descaled monthly; filter swap 2026-03.",
        "images": 2,
        "prompt": (
            "Photorealistic photo of a brushed-stainless-steel home espresso "
            "machine on a kitchen counter with a small portafilter beside "
            "it and two ceramic espresso cups, warm morning light, sharp "
            "focus, no text."
        ),
        "created_at_days_ago": 560,
    },
    {
        "name": "SodaStream Terra",
        "category": "Kitchen",
        "location": "Kitchen",
        "brand": "SodaStream",
        "model_number": "Terra",
        "purchase_date": _date_ago(140),
        "purchase_price": 99.99,
        "current_value": 70.00,
        "notes": "Black. CO2 cylinder swapped 2026-04.",
        "images": 1,
        "prompt": (
            "Studio product photo of a black countertop SodaStream "
            "sparkling-water maker with a clear empty bottle attached, on a "
            "marble counter, soft daylight, sharp focus, photorealistic, no "
            "text."
        ),
        "created_at_days_ago": 140,
    },
    {
        "name": "Ryobi 18V One+ HP Brushless Circular Saw",
        "category": "Tools",
        "location": "Garage",
        "brand": "Ryobi",
        "model_number": "PBLCS300B",
        "purchase_date": _date_ago(260),
        "purchase_price": 179.00,
        "current_value": 130.00,
        "notes": "Tool only — runs off the existing 4Ah HP battery set.",
        "images": 1,
        "prompt": (
            "Studio product photo of a green-and-black Ryobi cordless "
            "circular saw with a battery attached, resting on a workbench "
            "with sawdust nearby, sharp focus, photorealistic, no text."
        ),
        "created_at_days_ago": 260,
    },
    {
        "name": "Husky 52\" 9-Drawer Mobile Workbench",
        "category": "Tools",
        "location": "Garage",
        "brand": "Husky",
        "model_number": "HOLT5209BB1M",
        "purchase_date": _date_ago(1300),
        "purchase_price": 698.00,
        "current_value": 420.00,
        "notes": "Black + yellow. Matched matching wall cabinet sold separately.",
        "images": 1,
        "prompt": (
            "Photorealistic photo of a heavy-duty black-and-yellow Husky "
            "rolling tool workbench with a solid wood top in a clean, "
            "well-lit garage, photorealistic, soft overhead light, sharp "
            "focus, no text or watermarks."
        ),
        "created_at_days_ago": 1300,
    },
    {
        "name": "Stihl MS 250 Gas Chainsaw",
        "category": "Tools",
        "location": "Garage",
        "brand": "Stihl",
        "model_number": "MS 250",
        "serial_number": "STL-MS250-19844",
        "purchase_date": _date_ago(2700),
        "purchase_price": 469.00,
        "current_value": 220.00,
        "notes": "16\" bar. Serviced 2025-09; chain sharpened.",
        "images": 1,
        "prompt": (
            "Studio product photo of an orange-and-grey Stihl gas-powered "
            "chainsaw resting on a wooden workbench, slightly used "
            "appearance, soft directional light, sharp focus, "
            "photorealistic, no text."
        ),
        "created_at_days_ago": 60,
    },
    {
        "name": "Big Green Egg Large Ceramic Kamado Smoker",
        "category": "Tools",
        "location": "Backyard Patio",
        "brand": "Big Green Egg",
        "model_number": "EGE2017",
        "purchase_date": _date_ago(950),
        "purchase_price": 1199.00,
        "current_value": 950.00,
        "notes": "Large. On Acacia table cart, conv'EGGtor included.",
        "images": 2,
        "prompt": (
            "Photorealistic photo of a large green ceramic kamado-style "
            "egg-shaped barbecue smoker on its wooden cart on a stone patio "
            "at golden hour, lid open showing charcoal grate, sharp focus, "
            "photorealistic, no text."
        ),
        "created_at_days_ago": 950,
    },
    {
        "name": "The North Face Borealis Backpack",
        "category": "Clothing",
        "location": "Mudroom",
        "brand": "The North Face",
        "model_number": "NF0A52SE",
        "purchase_date": _date_ago(420),
        "purchase_price": 99.00,
        "current_value": 60.00,
        "notes": "Cosmic blue. 28L. Used as travel daypack.",
        "images": 1,
        "prompt": (
            "Studio product photo of a navy-blue North Face Borealis hiking "
            "daypack standing upright on a clean white background, soft "
            "side light, sharp focus on stitching and zippers, "
            "photorealistic, no text."
        ),
        "created_at_days_ago": 420,
    },
    {
        "name": "Specialized Rockhopper 29 Mountain Bike",
        "category": "Sports",
        "location": "Garage",
        "brand": "Specialized",
        "model_number": "Rockhopper-29-XL",
        "serial_number": "SPC-RH29-WB72119",
        "purchase_date": _date_ago(800),
        "purchase_price": 800.00,
        "current_value": 480.00,
        "notes": "Matte black, XL frame. Tubes patched 2026-03.",
        "images": 2,
        "prompt": (
            "Photorealistic photo of a matte-black hardtail mountain bike "
            "with 29-inch knobby tires leaning against a clean white garage "
            "wall, soft daylight, sharp focus on the frame and components, "
            "photorealistic, no text."
        ),
        "created_at_days_ago": 800,
    },
    {
        "name": "Yeti Tundra 65 Hard Cooler",
        "category": "Outdoor",
        "location": "Garage",
        "brand": "Yeti",
        "model_number": "Tundra-65-Tan",
        "purchase_date": _date_ago(1500),
        "purchase_price": 425.00,
        "current_value": 280.00,
        "notes": "Tan. Holds ice 4-5 days even in summer trips.",
        "images": 1,
        "prompt": (
            "Studio product photo of a tan rotomolded hard-shell cooler with "
            "the lid closed on a wooden patio surface, photorealistic, soft "
            "natural light, sharp focus on the textured shell, no text."
        ),
        "created_at_days_ago": 1500,
    },
    # --- Batch 3 (Appliances/Sports/Outdoor expansion) -------------------
    {
        "name": 'Wolf 36" Gas Range (DF36650)',
        "category": "Appliances",
        "location": "Kitchen",
        "brand": "Wolf",
        "model_number": "DF36650",
        "serial_number": "WLF-DF36650-44218",
        "purchase_date": _date_ago(1300),
        "purchase_price": 7495.00,
        "current_value": 5200.00,
        "warranty_expiration": _date_ahead(700),
        "notes": "Stainless 6-burner. Annual service 2026-01.",
        "images": 2,
        "prompt": (
            "Hyperrealistic studio kitchen photo of a 36-inch stainless-steel "
            "professional dual-fuel gas range with six brass-tipped burners "
            "and red knobs, set into a clean modern kitchen with a marble "
            "counter and subway-tile backsplash, soft daylight, sharp focus, "
            "no text or watermarks."
        ),
        "created_at_days_ago": 1300,
    },
    {
        "name": "Samsung Bespoke 4-Door Flex Refrigerator",
        "category": "Appliances",
        "location": "Kitchen",
        "brand": "Samsung",
        "model_number": "RF29BB89008M",
        "serial_number": "SMG-BSPK-RF29-66821",
        "purchase_date": _date_ago(900),
        "purchase_price": 3499.00,
        "current_value": 2400.00,
        "warranty_expiration": _date_ahead(95),
        "notes": "Custom panel kit (matte navy).",
        "images": 2,
        "prompt": (
            "Photorealistic photo of a tall four-door French-door "
            "refrigerator with a flat matte navy finish in a modern kitchen, "
            "integrated handles, stainless interior visible through one open "
            "door, soft daylight, sharp focus, no text or watermarks."
        ),
        "created_at_days_ago": 900,
    },
    {
        "name": "Bosch 800 Series Dishwasher (SHPM78Z55N)",
        "category": "Appliances",
        "location": "Kitchen",
        "brand": "Bosch",
        "model_number": "SHPM78Z55N",
        "purchase_date": _date_ago(800),
        "purchase_price": 1299.00,
        "current_value": 850.00,
        "warranty_expiration": _date_ahead(165),
        "notes": "Stainless. CrystalDry; 3rd rack.",
        "images": 1,
        "prompt": (
            "Photorealistic close-up of a stainless-steel built-in "
            "dishwasher set into a row of modern kitchen cabinetry with a "
            "slightly open door showing three racks, soft kitchen lighting, "
            "sharp focus, photorealistic, no text or watermarks."
        ),
        "created_at_days_ago": 800,
    },
    {
        "name": "GE Profile PEM31SFSS Microwave",
        "category": "Appliances",
        "location": "Kitchen",
        "brand": "GE",
        "model_number": "PEM31SFSS",
        "purchase_date": _date_ago(1500),
        "purchase_price": 239.00,
        "current_value": 110.00,
        "notes": "Stainless countertop.",
        "images": 1,
        "prompt": (
            "Studio product photo of a stainless-steel countertop microwave "
            "oven on a marble kitchen counter, button keypad visible, soft "
            "natural light, sharp focus, photorealistic, no text or "
            "watermarks."
        ),
        "created_at_days_ago": 1500,
    },
    {
        "name": "Rinnai RU199iN Tankless Water Heater",
        "category": "Appliances",
        "location": "Basement",
        "brand": "Rinnai",
        "model_number": "RU199iN",
        "serial_number": "RNI-RU199-30022",
        "purchase_date": _date_ago(1200),
        "purchase_price": 1799.00,
        "current_value": 1100.00,
        "warranty_expiration": _date_ahead(1100),
        "notes": "Indoor natural gas. Flushed 2026-02.",
        "images": 1,
        "prompt": (
            "Photorealistic photo of a slim white wall-mounted indoor "
            "tankless natural-gas water heater installed in a clean "
            "unfinished basement with copper pipes and a vent flue, soft "
            "overhead light, sharp focus, no text or watermarks."
        ),
        "created_at_days_ago": 1200,
    },
    {
        "name": "Coway Airmega 400 Air Purifier",
        "category": "Appliances",
        "location": "Master Bedroom",
        "brand": "Coway",
        "model_number": "AP-2015F",
        "purchase_date": _date_ago(450),
        "purchase_price": 649.00,
        "current_value": 420.00,
        "warranty_expiration": _date_ahead(360),
        "notes": "HEPA + carbon. Filters last replaced 2026-03.",
        "images": 1,
        "prompt": (
            "Studio photo of a sleek tall white tower air purifier with a "
            "circular touch-control top in a softly lit modern bedroom "
            "corner, subtle fabric chair beside it, sharp focus, "
            "photorealistic, no text or watermarks."
        ),
        "created_at_days_ago": 60,
    },
    {
        "name": "Honda HRX217VKA Self-Propelled Lawn Mower",
        "category": "Outdoor",
        "location": "Shed",
        "brand": "Honda",
        "model_number": "HRX217VKA",
        "serial_number": "HND-HRX217-44712",
        "purchase_date": _date_ago(1500),
        "purchase_price": 749.00,
        "current_value": 480.00,
        "notes": "GCV200 engine. Blades sharpened 2026-04.",
        "images": 2,
        "prompt": (
            "Photorealistic photo of a red-and-black Honda self-propelled "
            "walk-behind lawn mower on a freshly cut backyard lawn, golden "
            "hour lighting, hint of grass clippings, sharp focus, "
            "photorealistic, no text or watermarks."
        ),
        "created_at_days_ago": 1500,
    },
    {
        "name": "REI Co-op Half Dome 2 Plus Tent",
        "category": "Outdoor",
        "location": "Garage",
        "brand": "REI",
        "model_number": "Half-Dome-2-Plus",
        "purchase_date": _date_ago(950),
        "purchase_price": 329.00,
        "current_value": 200.00,
        "notes": "3-season, packed in storage tote.",
        "images": 1,
        "prompt": (
            "Photorealistic outdoor photo of a yellow-and-grey two-person "
            "freestanding dome backpacking tent fully pitched in a quiet "
            "meadow campsite at golden hour, rainfly partially open, sharp "
            "focus, photorealistic, no text or watermarks."
        ),
        "created_at_days_ago": 950,
    },
    {
        "name": "Solo Stove Bonfire 2.0",
        "category": "Outdoor",
        "location": "Backyard Patio",
        "brand": "Solo Stove",
        "model_number": "BONFIRE-2",
        "purchase_date": _date_ago(280),
        "purchase_price": 399.99,
        "current_value": 290.00,
        "notes": "With stand + lid + carry case.",
        "images": 1,
        "prompt": (
            "Photorealistic patio photo of a circular stainless-steel "
            "smokeless fire pit with a low active wood flame inside, set on "
            "a stone patio at dusk with two empty Adirondack chairs nearby, "
            "sharp focus, photorealistic, no text."
        ),
        "created_at_days_ago": 280,
    },
    {
        "name": "Coleman Classic 2-Burner Propane Stove",
        "category": "Outdoor",
        "location": "Garage",
        "brand": "Coleman",
        "model_number": "2000020931",
        "purchase_date": _date_ago(1100),
        "purchase_price": 69.99,
        "current_value": 40.00,
        "notes": "Used on car-camping trips. New regulator 2025.",
        "images": 1,
        "prompt": (
            "Studio product photo of a classic green Coleman two-burner "
            "propane camping stove with the lid open showing twin burners, "
            "set on a weathered wooden picnic table, sharp focus, "
            "photorealistic, no text or watermarks."
        ),
        "created_at_days_ago": 1100,
    },
    {
        "name": "Peloton Bike+",
        "category": "Sports",
        "location": "Basement",
        "brand": "Peloton",
        "model_number": "Bike-Plus",
        "serial_number": "PEL-BIKEP-90212",
        "purchase_date": _date_ago(750),
        "purchase_price": 2495.00,
        "current_value": 1400.00,
        "notes": "Calibrated 2026-02. All-Access membership.",
        "images": 2,
        "prompt": (
            "Photorealistic photo of a black premium indoor cycling bike "
            "with a large rotating touchscreen monitor in a clean modern "
            "home gym with rubber flooring, soft daylight from a window, "
            "sharp focus, photorealistic, no text or watermarks."
        ),
        "created_at_days_ago": 750,
    },
    {
        "name": "Bowflex SelectTech 552 Adjustable Dumbbells",
        "category": "Sports",
        "location": "Basement",
        "brand": "Bowflex",
        "model_number": "SelectTech-552",
        "purchase_date": _date_ago(380),
        "purchase_price": 429.00,
        "current_value": 290.00,
        "notes": "5-52.5 lb. With stand.",
        "images": 1,
        "prompt": (
            "Studio product photo of a pair of black adjustable dumbbells "
            "resting on a vertical stand on rubber gym flooring, sharp focus "
            "on the numbered weight selector dials, soft directional light, "
            "photorealistic, no text."
        ),
        "created_at_days_ago": 380,
    },
    {
        "name": "Callaway Rogue ST Max Iron Set (5-PW)",
        "category": "Sports",
        "location": "Garage",
        "brand": "Callaway",
        "model_number": "Rogue-ST-Max-5PW",
        "purchase_date": _date_ago(900),
        "purchase_price": 899.00,
        "current_value": 520.00,
        "notes": "Steel shafts, regular flex. Bag separate.",
        "images": 1,
        "prompt": (
            "Studio product photo of a fanned-out set of six modern golf "
            "irons with chrome heads and black grips lined up against a "
            "soft grey backdrop, sharp focus, photorealistic, no text or "
            "watermarks."
        ),
        "created_at_days_ago": 900,
    },
    {
        "name": "Wilson Blade 98 v8 Tennis Racquet",
        "category": "Sports",
        "location": "Garage",
        "brand": "Wilson",
        "model_number": "Blade-98-v8",
        "purchase_date": _date_ago(360),
        "purchase_price": 249.00,
        "current_value": 140.00,
        "notes": "16x19 string pattern. Restrung 2026-03.",
        "images": 1,
        "prompt": (
            "Studio product photo of a modern green-and-black tennis "
            "racquet lying on a hard tennis court surface with three yellow "
            "tennis balls beside it, soft directional light, sharp focus, "
            "photorealistic, no text."
        ),
        "created_at_days_ago": 360,
    },
    {
        "name": "Ring Video Doorbell Pro 2",
        "category": "Electronics",
        "location": "Front Porch",
        "brand": "Ring",
        "model_number": "DBPro2",
        "purchase_date": _date_ago(420),
        "purchase_price": 229.99,
        "current_value": 140.00,
        "notes": "Hardwired. Pre-roll + 3D motion.",
        "images": 1,
        "prompt": (
            "Photorealistic close-up of a sleek black-and-silver smart "
            "video doorbell mounted beside the doorframe of a modern home's "
            "front porch, soft daylight, sharp focus on the camera lens, "
            "photorealistic, no text or watermarks."
        ),
        "created_at_days_ago": 420,
    },
    {
        "name": "Apple Watch Ultra 2 (49mm Titanium)",
        "category": "Electronics",
        "location": "Master Bedroom",
        "brand": "Apple",
        "model_number": "MRER3LL/A",
        "serial_number": "APL-WUTRA2-V99102",
        "purchase_date": _date_ago(220),
        "purchase_price": 799.00,
        "current_value": 560.00,
        "warranty_expiration": _date_ahead(495),
        "notes": "Trail Loop band. AppleCare+.",
        "images": 1,
        "prompt": (
            "Hyperrealistic studio product photo of a rugged titanium "
            "smartwatch with a green woven Trail Loop band resting on a "
            "slate-grey surface, blank black watch face, sharp focus on the "
            "digital crown and side button, photorealistic, no text on the "
            "screen."
        ),
        "created_at_days_ago": 220,
    },
    {
        "name": "Denon AVR-X3800H 9.4ch AV Receiver",
        "category": "Electronics",
        "location": "Living Room",
        "brand": "Denon",
        "model_number": "AVR-X3800H",
        "serial_number": "DEN-AVR3800-72119",
        "purchase_date": _date_ago(330),
        "purchase_price": 1799.00,
        "current_value": 1200.00,
        "warranty_expiration": _date_ahead(395),
        "notes": "Atmos/DTS:X. Audyssey-calibrated 2026-01.",
        "images": 2,
        "prompt": (
            "Studio product photo of a wide black home-theater AV receiver "
            "with a glowing front-panel display, large central volume knob, "
            "and input selector knobs, set on a low media console, sharp "
            "focus, photorealistic, no text overlay."
        ),
        "created_at_days_ago": 330,
    },
    {
        "name": "Brother HL-L2350DW Mono Laser Printer",
        "category": "Electronics",
        "location": "Home Office",
        "brand": "Brother",
        "model_number": "HL-L2350DW",
        "purchase_date": _date_ago(1600),
        "purchase_price": 129.00,
        "current_value": 60.00,
        "notes": "Toner replaced 2026-02 (TN-760).",
        "images": 1,
        "prompt": (
            "Photorealistic photo of a compact black monochrome laser "
            "printer on a wooden home-office desk beside a small stack of "
            "plain white paper, soft daylight, sharp focus, photorealistic, "
            "no text on the paper."
        ),
        "created_at_days_ago": 1600,
    },
    {
        "name": "West Elm Mid-Century Bed Frame (Queen)",
        "category": "Furniture",
        "location": "Master Bedroom",
        "brand": "West Elm",
        "model_number": "MidCentury-Bed-Q",
        "purchase_date": _date_ago(1100),
        "purchase_price": 1399.00,
        "current_value": 700.00,
        "notes": "Acorn finish.",
        "images": 1,
        "prompt": (
            "Photorealistic bedroom photo of a low mid-century walnut "
            "platform bed frame with tapered legs and a slatted headboard "
            "in a sunlit master bedroom, white linen sheets neatly made, "
            "soft window light, sharp focus on the wood grain, no text."
        ),
        "created_at_days_ago": 1100,
    },
    {
        "name": "Casper Wave Hybrid Mattress (Queen)",
        "category": "Furniture",
        "location": "Master Bedroom",
        "brand": "Casper",
        "model_number": "Wave-Hybrid-Q",
        "purchase_date": _date_ago(1100),
        "purchase_price": 2495.00,
        "current_value": 900.00,
        "warranty_expiration": _date_ahead(2400),
        "notes": "On the West Elm frame. Replaced 2025-06 under warranty.",
        "images": 1,
        "prompt": (
            "Studio product photo of a thick white-and-grey premium "
            "mattress standing upright against a clean light wall, showing "
            "the layered cross-section of foam and pocketed coils, soft "
            "directional light, sharp focus, photorealistic, no text."
        ),
        "created_at_days_ago": 320,
    },
    {
        "name": "All-Clad D3 Stainless 10-piece Cookware Set",
        "category": "Kitchen",
        "location": "Kitchen",
        "brand": "All-Clad",
        "model_number": "401488R",
        "purchase_date": _date_ago(2000),
        "purchase_price": 1299.00,
        "current_value": 700.00,
        "notes": "Tri-ply 18/10. Bonded 2-piece handles.",
        "images": 2,
        "prompt": (
            "Studio product photo of a fanned-out set of polished tri-ply "
            "stainless-steel cookware - frypans, saucepans, a stockpot, and "
            "matching lids - arranged on a marble surface, soft directional "
            "light revealing the brushed-and-polished finish, sharp focus, "
            "photorealistic, no text."
        ),
        "created_at_days_ago": 2000,
    },
    {
        "name": "Anova Precision Cooker Pro",
        "category": "Kitchen",
        "location": "Kitchen",
        "brand": "Anova",
        "model_number": "AN500-US00",
        "purchase_date": _date_ago(800),
        "purchase_price": 399.00,
        "current_value": 260.00,
        "notes": "1200W. Stored in pantry between uses.",
        "images": 1,
        "prompt": (
            "Photorealistic kitchen-counter shot of a black cylindrical "
            "sous vide immersion circulator clipped to the side of a clear "
            "plastic container half full of water with a vacuum-sealed "
            "pouch inside, soft natural light, sharp focus, photorealistic, "
            "no text."
        ),
        "created_at_days_ago": 800,
    },
    {
        "name": "Tumi Alpha 3 International Carry-On",
        "category": "Clothing",
        "location": "Master Bedroom",
        "brand": "Tumi",
        "model_number": "117166-1041",
        "purchase_date": _date_ago(900),
        "purchase_price": 895.00,
        "current_value": 580.00,
        "notes": 'Anthracite. 22" expandable.',
        "images": 1,
        "prompt": (
            "Studio product photo of a sleek anthracite-grey four-wheel "
            "carry-on ballistic-nylon roller suitcase with a telescoping "
            "handle extended, soft directional light, sharp focus on "
            "stitching and zippers, photorealistic, no text or watermarks."
        ),
        "created_at_days_ago": 900,
    },
    {
        "name": "Salomon Quest 4 GTX Hiking Boots",
        "category": "Clothing",
        "location": "Mudroom",
        "brand": "Salomon",
        "model_number": "Quest-4-GTX",
        "purchase_date": _date_ago(380),
        "purchase_price": 230.00,
        "current_value": 150.00,
        "notes": "Men's 10.5. GoreTex; 50+ mi on the soles.",
        "images": 1,
        "prompt": (
            "Studio product photo of a pair of well-used brown leather "
            "Gore-Tex hiking boots side-by-side on a weathered wooden "
            "surface, subtle dirt on the soles, soft directional light, "
            "sharp focus, photorealistic, no text."
        ),
        "created_at_days_ago": 380,
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


def existing_item_names(db, user: models.User) -> set[str]:
    """Return the set of item names already owned by the seed user.

    Used for per-name idempotency: only entries whose ``name`` isn't
    already present get inserted. This makes ``SEED_ITEMS`` additive —
    appending more entries and re-running picks up just the new ones,
    no flag-bumping needed.
    """
    return {
        row.name
        for row in db.query(models.Item).filter(models.Item.owner_id == user.id).all()
    }


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

        present = existing_item_names(db, user)
        to_seed = [e for e in SEED_ITEMS if e["name"] not in present]
        skipped = len(SEED_ITEMS) - len(to_seed)
        if not to_seed:
            print(
                f"All {len(SEED_ITEMS)} seed item(s) already present for user "
                f"'{user.username}'; nothing to do."
            )
            return 0

        total_images = sum(entry["images"] for entry in to_seed)
        msg = (
            f"Seeding {len(to_seed)} new item(s) for user '{user.username}' "
            f"(~{total_images} images via Venice nano-banana-2)"
        )
        if skipped:
            msg += f"; {skipped} entry(ies) already present, skipped"
        print(msg + "...")

        upload_dir = settings.upload_path
        wall_started = time.monotonic()
        item_count = 0
        image_count = 0

        for idx, entry in enumerate(to_seed, start=1):
            label = entry["name"]
            n_imgs = int(entry["images"])
            print(f"  [{idx:2d}/{len(to_seed)}] {label} — generating {n_imgs} image(s)...", end=" ", flush=True)

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
