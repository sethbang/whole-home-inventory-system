import logging
import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    TypeDecorator,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import expression

from app.database import Base

logger = logging.getLogger(__name__)


class UUID(TypeDecorator):
    """Platform-independent UUID type.

    Stored as a 36-character string in SQLite. Any valid RFC-4122 UUID is
    accepted and round-tripped faithfully. Non-v4 UUIDs used to be silently
    replaced with a fresh v4 — that masked bugs when UUIDs from other sources
    landed in the DB. Now we log a warning and keep the caller's value.
    Malformed strings raise ``ValueError`` as the caller expects from ``uuid``.
    """

    impl = String(36)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        if isinstance(value, uuid.UUID):
            if value.version != 4:
                logger.warning(
                    "storing non-v4 UUID (version=%s): %s", value.version, value
                )
            return str(value)
        # String (or bytes) form. Let uuid.UUID do the parsing; it raises
        # ValueError on malformed input, which SQLAlchemy will surface to the
        # caller.
        uuid_obj = uuid.UUID(value)
        if uuid_obj.version != 4:
            logger.warning(
                "storing non-v4 UUID (version=%s): %s", uuid_obj.version, uuid_obj
            )
        return str(uuid_obj)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        uuid_obj = uuid.UUID(value)
        if uuid_obj.version != 4:
            logger.warning(
                "reading non-v4 UUID (version=%s) from storage: %s",
                uuid_obj.version,
                uuid_obj,
            )
        return uuid_obj


class User(Base):
    __tablename__ = "users"

    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)
    # First successfully registered user is promoted to admin. Subsequent
    # registrations default to False. Used to gate the LLM operator
    # dashboard at /api/llm-config and the frontend /settings route.
    is_admin = Column(
        Boolean, nullable=False, default=False, server_default=expression.false()
    )
    created_at = Column(DateTime, default=datetime.utcnow)
    items = relationship("Item", back_populates="owner")
    backups = relationship("Backup", back_populates="owner")


class Item(Base):
    __tablename__ = "items"

    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    name = Column(String, index=True)
    category = Column(String, index=True)
    location = Column(String, index=True)
    brand = Column(String)
    model_number = Column(String)
    serial_number = Column(String)
    barcode = Column(String, index=True)
    purchase_date = Column(DateTime)
    purchase_price = Column(Float)
    current_value = Column(Float)
    warranty_expiration = Column(DateTime)
    notes = Column(String)
    custom_fields = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # --- v2.2 pre-wire for the v3.1 pricing feature ------------------------
    # Dedicated columns (rather than hiding these in ``custom_fields``) so
    # the UI can sort/filter by estimated value and "last checked" without
    # JSON-column gymnastics. Populated by v3.1's PricingService; left
    # NULL until the first estimate is requested.
    estimated_value_low = Column(Float, nullable=True)
    estimated_value_median = Column(Float, nullable=True)
    estimated_value_high = Column(Float, nullable=True)
    price_last_checked = Column(DateTime, nullable=True)
    price_provider = Column(String(32), nullable=True)

    owner_id = Column(UUID, ForeignKey("users.id"))
    owner = relationship("User", back_populates="items")
    images = relationship(
        "ItemImage", back_populates="item", cascade="all, delete-orphan"
    )


class ItemImage(Base):
    __tablename__ = "item_images"

    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    item_id = Column(UUID, ForeignKey("items.id", ondelete="CASCADE"))
    filename = Column(String)
    file_path = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    # v3.0: populated by the ARQ thumbnail_generate task after upload.
    # Remains NULL while the job is in flight (or when the worker isn't
    # active and the fallback path runs thumbnails inline in the
    # request).
    thumbnail_path = Column(String, nullable=True)
    thumbnail_generated_at = Column(DateTime, nullable=True)

    item = relationship("Item", back_populates="images")


class Backup(Base):
    __tablename__ = "backups"

    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    owner_id = Column(UUID, ForeignKey("users.id"))
    filename = Column(String)
    file_path = Column(String)
    size_bytes = Column(Integer)
    item_count = Column(Integer)
    image_count = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String)  # 'completed', 'failed', 'in_progress'
    error_message = Column(String, nullable=True)

    owner = relationship("User", back_populates="backups")


class PriceCache(Base):
    """Cached resale-price estimates keyed by (identity_hash, provider).

    Populated by v3.1's PricingService. Stored alongside ``items`` so
    the same DB backup captures the warmed cache — operationally nice
    for self-hosted deployments that don't want to burn through their
    eBay quota after every migration.

    v2.2 provisioned this with only ``identity_hash`` as the PK; v3.1's
    ``20260422_0007_price_cache_composite_pk`` migration promotes it
    to the composite ``(identity_hash, provider)`` form so the same
    hash can host one entry per provider.
    """

    __tablename__ = "price_cache"

    identity_hash = Column(String(64), primary_key=True)
    provider = Column(String(32), primary_key=True)
    payload = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False, index=True)


class LLMConfig(Base):
    """Singleton row for the operator-editable LLM provider config.

    Lives behind the /api/llm-config router. Every column is nullable
    so a missing value falls back to the corresponding ``settings.*``
    env value. The API key is stored encrypted (Fernet, key derived
    from ``SECRET_KEY``); the rest are plain values.

    There is exactly one row in this table; the application enforces
    ``id == 1`` at the service layer rather than via a check
    constraint so the cross-dialect migration stays trivial.
    """

    __tablename__ = "llm_config"

    id = Column(Integer, primary_key=True)
    base_url = Column(String, nullable=True)
    # Fernet ciphertext of the plaintext API key. Decrypted on demand by
    # the service layer; never logged. NULL means "fall back to env".
    api_key_ciphertext = Column(String, nullable=True)
    model = Column(String, nullable=True)
    vision_model = Column(String, nullable=True)
    pricing_model = Column(String, nullable=True)
    timeout_seconds = Column(Integer, nullable=True)
    response_healing = Column(Boolean, nullable=True)
    vision_enabled = Column(Boolean, nullable=True)
    pricing_enabled = Column(Boolean, nullable=True)
    vision_daily_cap_usd = Column(Float, nullable=True)
    pricing_daily_cap_usd = Column(Float, nullable=True)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
    # Convenience: who saved last. Not enforced by the schema (the
    # actor is also written to the audit log).
    updated_by = Column(UUID, ForeignKey("users.id"), nullable=True)


class LLMUsage(Base):
    """Per-(user, date, feature) usage rollup for the v3.1 LLM layer.

    One row per (user_id, usage_date, feature) tuple — the budget
    guard reads this to enforce VISION_DAILY_COST_CAP_USD /
    PRICING_DAILY_COST_CAP_USD without a full table scan. We upsert
    into the row on every call: accumulate token counts, increment
    request_count, add cost_usd. Date is stored as a plain DateTime
    (naive UTC midnight) so the unique constraint works cross-dialect.
    """

    __tablename__ = "llm_usage"

    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID, ForeignKey("users.id"), nullable=False, index=True)
    # Floor to the UTC calendar day. The service layer computes this
    # once per request so the upsert key is deterministic.
    usage_date = Column(DateTime, nullable=False, index=True)
    # 'vision' | 'pricing'. Not an enum — we want to extend without
    # a migration when v3.2 adds a new feature.
    feature = Column(String(32), nullable=False)
    tokens_in = Column(Integer, nullable=False, default=0)
    tokens_out = Column(Integer, nullable=False, default=0)
    cost_usd = Column(Float, nullable=False, default=0.0)
    request_count = Column(Integer, nullable=False, default=0)
