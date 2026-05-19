from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Literal, Optional

from pydantic import UUID4, BaseModel, ConfigDict, EmailStr, Field

from .ebay.schemas import EbayFields
from .facebook.schemas import FbFields

# Re-export the LLM-facing schemas so OpenAPI picks them up under the
# same ``components/schemas/<Name>`` namespace. Frontend call sites
# will import them from the generated `api/types.ts` without needing
# to know they originated in app.schemas_llm.
from .schemas_llm import (  # noqa: F401 — intentional re-export for OpenAPI
    PriceEstimate,
    PriceEstimateEnvelope,
    PriceSource,
    VisionResult,
    VisionSuggestion,
)

__schemas_llm_exports__ = [
    "PriceEstimate",
    "PriceEstimateEnvelope",
    "PriceSource",
    "VisionResult",
    "VisionSuggestion",
]


class CustomFieldsSchema(BaseModel):
    """Structured shape of ``Item.custom_fields``.

    Top-level is strict: only ``ebay``, ``facebook``, and ``user_defined``
    are accepted. Unknown keys at this level produce a 422 at request
    time — this is the v2.3 plug for the "JSON column accepts anything"
    gap flagged in the post-2.0 audit. The ``user_defined`` catchall
    preserves the operator-level flexibility that people actually use
    (hand-added tags, photography rating, loaner tracking, etc.) without
    giving up the schema discipline around the integrations.
    """

    ebay: Optional[EbayFields] = None
    facebook: Optional[FbFields] = None
    user_defined: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid")

    @classmethod
    def coerce_from_raw(
        cls, raw: Optional[Dict[str, Any]]
    ) -> Optional["CustomFieldsSchema"]:
        """Lenient entrypoint for operator-controlled inputs (CSV import, etc.).

        Recognized keys (``ebay`` / ``facebook`` / ``user_defined``) pass
        through with type validation. Any other top-level keys are folded
        into ``user_defined`` rather than rejected — this keeps legacy
        hand-edited custom_fields shapes importable while the strict
        schema still guards the HTTP API at the POST/PUT boundary.
        """
        if raw is None:
            return None
        if not isinstance(raw, dict):
            raise ValueError("custom_fields must be a JSON object")

        known: Dict[str, Any] = {}
        unknown: Dict[str, Any] = {}
        for key, value in raw.items():
            if key in {"ebay", "facebook"}:
                known[key] = value
            elif key == "user_defined" and isinstance(value, dict):
                # Merge any pre-existing user_defined into the catchall.
                unknown.update(value)
            else:
                unknown[key] = value
        if unknown:
            known["user_defined"] = unknown
        return cls.model_validate(known)


class UserBase(BaseModel):
    email: EmailStr
    username: str


class UserCreate(UserBase):
    password: str


class User(UserBase):
    id: UUID4
    is_active: bool
    is_admin: bool = False
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None


class ItemBase(BaseModel):
    name: str
    category: str
    location: str
    brand: Optional[str] = None
    model_number: Optional[str] = None
    serial_number: Optional[str] = None
    barcode: Optional[str] = None
    purchase_date: Optional[datetime] = None
    purchase_price: Optional[float] = None
    current_value: Optional[float] = None
    warranty_expiration: Optional[datetime] = None
    notes: Optional[str] = None
    custom_fields: Optional[Dict[str, Any]] = None


class ItemCreate(ItemBase):
    # Override with strict schema for HTTP-bound writes. ItemBase keeps the
    # permissive Dict[str, Any] shape so response parsing tolerates any
    # legacy JSON-column content that predates v2.3.
    custom_fields: Optional[CustomFieldsSchema] = None


class ItemUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    location: Optional[str] = None
    brand: Optional[str] = None
    model_number: Optional[str] = None
    serial_number: Optional[str] = None
    barcode: Optional[str] = None
    purchase_date: Optional[datetime] = None
    purchase_price: Optional[float] = None
    current_value: Optional[float] = None
    warranty_expiration: Optional[datetime] = None
    notes: Optional[str] = None
    custom_fields: Optional[CustomFieldsSchema] = None


class ItemImage(BaseModel):
    id: UUID4
    item_id: UUID4
    filename: str
    file_path: str
    created_at: datetime
    # Populated asynchronously by the thumbnail_generate ARQ task (v3.0).
    # Frontend renders this when present, falls back to ``file_path``
    # otherwise.
    thumbnail_path: Optional[str] = None
    thumbnail_generated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class Item(ItemBase):
    id: UUID4
    owner_id: UUID4
    created_at: datetime
    updated_at: datetime
    images: List[ItemImage] = []

    # v2.2 pre-wire for the v3.1 pricing feature. Always NULL in v2.2 — the
    # fields are surfaced on the response shape now so the frontend can be
    # built against a stable schema ahead of the feature actually shipping.
    estimated_value_low: Optional[float] = None
    estimated_value_median: Optional[float] = None
    estimated_value_high: Optional[float] = None
    price_last_checked: Optional[datetime] = None
    price_provider: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class SearchFilter(BaseModel):
    query: Optional[str] = None
    category: Optional[str] = None
    location: Optional[str] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    sort_by: Optional[str] = None
    sort_desc: bool = False
    page: int = 1
    page_size: int = 10


class ItemList(BaseModel):
    items: List[Item]
    total: int
    page: int
    page_size: int

    model_config = ConfigDict(from_attributes=True)


class LocationCount(BaseModel):
    """One row per distinct location with the caller's item count.

    Drives the Browse page's rooms sidebar — see GET /api/locations/counts.
    Empty / null locations are filtered out by the service.
    """

    location: str
    count: int


class BackupBase(BaseModel):
    pass


class BackupCreate(BackupBase):
    pass


class Backup(BackupBase):
    id: UUID4
    owner_id: UUID4
    filename: str
    file_path: str
    size_bytes: int
    item_count: int
    image_count: int
    created_at: datetime
    status: str
    error_message: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class BackupList(BaseModel):
    backups: List[Backup]


class ImportResult(BaseModel):
    success: bool
    message: str
    items_imported: int
    errors: Optional[List[str]] = None


class ExportFormat(BaseModel):
    format: str  # "csv" or "json"


class Error(BaseModel):
    detail: str


class RestoreRequest(BaseModel):
    """Body schema for POST /backups/{id}/restore when committing a restore.

    When ``dry_run=true`` is set on the query string the body is ignored and a
    preview is returned instead. When ``dry_run=false`` (or omitted) the caller
    MUST provide ``confirm_item_count`` that matches the current server-side
    count of their items; a mismatch is rejected with 409 to guard against
    accidental data loss from a stale UI.
    """

    confirm_item_count: Optional[int] = None


class RestoreResponse(BaseModel):
    success: bool
    message: str
    # Populated on a committed restore.
    items_restored: Optional[int] = None
    images_restored: Optional[int] = None
    errors: Optional[List[str]] = None
    # Populated on a dry-run preview.
    dry_run: bool = False
    current_item_count: Optional[int] = None
    backup_item_count: Optional[int] = None
    backup_image_count: Optional[int] = None


# --- Background-job contracts (v3.0) -----------------------------------------


class JobStatus(str, Enum):
    """Finite state machine for an ARQ job as the frontend sees it.

    Maps roughly onto ARQ's internal states (``deferred`` / ``queued``
    collapse to ``queued``; ``in_progress`` is ``running``;
    ``complete``/``failed`` are terminal).
    """

    queued = "queued"
    running = "running"
    complete = "complete"
    failed = "failed"
    not_found = "not_found"


class JobReference(BaseModel):
    """Discriminator body returned when an endpoint enqueues a job.

    The ``kind`` literal lets endpoints return a union type like
    ``JobReference | Backup`` and have the frontend branch on one
    field. When the sync-fallback path fires, the endpoint returns
    the full resource instead and the ``kind`` discriminator is
    missing.
    """

    kind: Literal["job"] = "job"
    job_id: str


class JobDetail(BaseModel):
    """Response shape of GET /api/jobs/{job_id}."""

    job_id: str
    status: JobStatus
    # Populated only on terminal states.
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    queued_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None


# --- LLM operator-dashboard contracts (v3.2) ---------------------------------


class LLMConfigRead(BaseModel):
    """GET /api/llm-config response.

    The plaintext API key is never returned. ``api_key_last4`` shows
    the last four characters so the operator can confirm which key is
    active without ever sending the full secret to the browser; the
    full secret is also redacted from logs by the audit logger.
    ``sources`` reports per-field provenance — ``db`` (set in the UI),
    ``env`` (still inheriting from the env var), or ``default``
    (no value set anywhere).
    """

    base_url: str
    api_key_set: bool
    api_key_last4: Optional[str] = None
    model: str
    vision_model: str
    pricing_model: str
    timeout_seconds: int
    response_healing: bool
    vision_enabled: bool
    pricing_enabled: bool
    vision_daily_cap_usd: float
    pricing_daily_cap_usd: float
    sources: Dict[str, str]
    # Convenience for the UI's "current spend" card. Populated only
    # for the current authenticated admin's daily totals — the
    # singleton is global but spend is per-user.
    today_vision_cost_usd: float = 0.0
    today_pricing_cost_usd: float = 0.0


class LLMConfigUpdate(BaseModel):
    """PUT /api/llm-config request body.

    Every field is optional. ``None`` means "leave unchanged"; an
    empty string or 0 (where applicable) means "clear back to env".
    The API key has its own behavior:
        * ``api_key`` omitted → leave stored value untouched
        * ``api_key`` empty string → clear stored value, fall back to env
        * ``api_key`` non-empty string → encrypt and persist as the new key
    """

    base_url: Optional[str] = None
    api_key: Optional[str] = None
    model: Optional[str] = None
    vision_model: Optional[str] = None
    pricing_model: Optional[str] = None
    timeout_seconds: Optional[int] = None
    response_healing: Optional[bool] = None
    vision_enabled: Optional[bool] = None
    pricing_enabled: Optional[bool] = None
    vision_daily_cap_usd: Optional[float] = None
    pricing_daily_cap_usd: Optional[float] = None


class LLMModelEntry(BaseModel):
    """One entry in GET /api/llm-config/models.

    ``supports_vision`` and ``supports_strict_json`` are tri-state:
    ``True``/``False``/``None``. ``None`` means the provider's
    /v1/models response didn't carry a capability flag we recognized;
    the operator should run the deep test to verify.
    """

    id: str
    owned_by: Optional[str] = None
    supports_vision: Optional[bool] = None
    supports_strict_json: Optional[bool] = None


class LLMModelListResponse(BaseModel):
    """GET /api/llm-config/models response."""

    models: List[LLMModelEntry]


class LLMTestResponse(BaseModel):
    """POST /api/llm-config/test response.

    ``ok`` rolls up the overall result; ``checks`` carries the
    individual sub-checks so the UI can render a clear breakdown.
    """

    ok: bool
    base_url: str
    model: str
    detail: Optional[str] = None
    checks: Dict[str, Any] = Field(default_factory=dict)


class LLMVisionTestResponse(BaseModel):
    """POST /api/llm-config/test-vision response."""

    ok: bool
    model: str
    detail: Optional[str] = None
    parsed_response: Optional[Dict[str, Any]] = None
    usage: Optional[Dict[str, Any]] = None
    cost_usd: Optional[float] = None
