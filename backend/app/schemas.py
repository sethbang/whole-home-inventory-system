from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Literal, Optional

from pydantic import UUID4, BaseModel, ConfigDict, EmailStr, Field

from .ebay.schemas import EbayFields
from .facebook.schemas import FbFields


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
