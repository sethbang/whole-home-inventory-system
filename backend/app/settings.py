import ipaddress
from functools import lru_cache
from pathlib import Path
from typing import Annotated, List
from urllib.parse import urlparse

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

_PLACEHOLDER_SECRETS = {
    "your-secret-key-stored-in-env",
    "change-me",
    "changeme",
    "secret",
    "",
}


def _is_private_llm_host(url: str) -> bool:
    """True when the LLM base URL points at localhost or a private IP.

    Used by the LLM_ALLOW_CLOUD=false privacy guard. Accepts a range
    of common local setups: localhost, 127.0.0.0/8, 10/8, 172.16/12,
    192.168/16, and IPv6 loopback. Hostnames that can't be resolved
    are treated as non-private — fail-closed is safer here than
    fail-open, since the setting exists precisely to prevent data
    exfiltration.
    """
    try:
        host = urlparse(url).hostname
    except (ValueError, TypeError):
        return False
    if not host:
        return False
    host_lower = host.lower()
    if host_lower in {"localhost", "ollama", "whis-ollama", "host.docker.internal"}:
        return True
    try:
        addr = ipaddress.ip_address(host)
    except ValueError:
        # Not an IP literal. Any named hostname other than the
        # allow-list above is treated as public.
        return False
    return addr.is_loopback or addr.is_private


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Auth
    BYPASS_AUTH: bool = False
    SECRET_KEY: str = ""
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Paths
    UPLOAD_DIR: str = "./uploads"
    BACKUP_DIR: str = "./backups"
    DATABASE_URL: str = ""

    # Database connection tuning — only Postgres honors pool_size /
    # max_overflow / pool_recycle. SQLite ignores them (single-file,
    # single-writer).
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_RECYCLE_SECONDS: int = 1800

    # Background job queue (ARQ). When unset, enqueuers fall back to
    # synchronous execution so the default `docker compose up` (no
    # Redis) still works end-to-end. Set to ``redis://redis:6379/0`` in
    # compose to activate the worker profile.
    REDIS_URL: str = ""

    # --- v3.1: shared LLM layer -------------------------------------------
    # LLM adapter is OpenAI-compatible — works with OpenRouter, Venice.ai,
    # LocalAI, Ollama's /v1 endpoint, or any other provider exposing the
    # same API surface. When LLM_BASE_URL is unset, the vision and pricing
    # routers 503 via their feature-flag gates; the rest of the app runs
    # unchanged.
    LLM_BASE_URL: str = ""
    LLM_API_KEY: str = ""
    # Default vision model. Cheap, good cost/quality on OpenRouter; swap
    # via env for other providers.
    LLM_MODEL: str = "google/gemini-2.5-flash"
    # Pricing reasoning model. Defaults to LLM_MODEL if blank; set to a
    # model that supports tool calling + structured outputs when using a
    # non-OpenRouter provider.
    LLM_PRICING_MODEL: str = ""
    LLM_TIMEOUT_SECONDS: int = 90
    # Hard kill-switch for privacy mode. When False, LLM_BASE_URL must
    # resolve to localhost or a private-range IP; the app refuses to
    # start otherwise.
    LLM_ALLOW_CLOUD: bool = True
    # Enable OpenRouter's Response Healing plugin on every structured-
    # output call — zero-cost safety net for truncation / markdown
    # wrapping / trailing commas. See OR_docs/OR_response-healing.md.
    LLM_RESPONSE_HEALING: bool = True

    # --- v3.1: Vision auto-fill -------------------------------------------
    VISION_ENABLED: bool = False
    VISION_MAX_IMAGES_PER_REQUEST: int = 4
    VISION_DAILY_COST_CAP_USD: float = 5.0
    # Never log image bytes; only sha256 hashes for correlation.
    VISION_LOG_IMAGE_HASHES_ONLY: bool = True

    # --- v3.1: Item-value search ------------------------------------------
    PRICING_ENABLED: bool = False
    # CSV, ordered priority: e.g. "ebay,llm" runs the eBay provider
    # first, falls back to the LLM+web_search provider on no-result.
    PRICING_PROVIDERS: Annotated[List[str], NoDecode] = Field(
        default_factory=lambda: ["ebay", "llm"]
    )
    PRICING_CACHE_DAYS: int = 14
    PRICING_MAX_SAMPLES: int = 30
    PRICING_MULTIPROVIDER: bool = False
    PRICING_DAILY_COST_CAP_USD: float = 5.0
    # OR web_search server tool knobs — match the parameters on
    # openrouter:web_search. See OR_docs/OR_web-search.md.
    PRICING_WEB_SEARCH_MAX_RESULTS: int = 5
    PRICING_WEB_SEARCH_MAX_TOTAL: int = 20
    PRICING_WEB_SEARCH_DOMAINS: Annotated[List[str], NoDecode] = Field(
        default_factory=lambda: [
            "ebay.com",
            "mercari.com",
            "bonanza.com",
        ]
    )

    # --- eBay Browse API (separate from the LLM's web search) -------------
    EBAY_APP_ID: str = ""
    EBAY_CERT_ID: str = ""
    EBAY_MARKETPLACE_ID: str = "EBAY_US"
    # production | sandbox. Sandbox has smaller inventory but doesn't
    # consume prod rate limit.
    EBAY_ENVIRONMENT: str = "production"

    # CORS — NoDecode prevents pydantic-settings from JSON-decoding before
    # our validator splits the comma-separated env form.
    CORS_ORIGINS: Annotated[List[str], NoDecode] = Field(
        default_factory=lambda: [
            "https://localhost:5173",
            "https://192.168.1.122:5173",
        ]
    )
    CORS_ALLOW_METHODS: Annotated[List[str], NoDecode] = Field(
        default_factory=lambda: [
            "GET",
            "POST",
            "PUT",
            "DELETE",
            "OPTIONS",
            "HEAD",
            "PATCH",
        ]
    )
    CORS_ALLOW_HEADERS: Annotated[List[str], NoDecode] = Field(
        default_factory=lambda: [
            "Content-Type",
            "Authorization",
            "Accept",
            "Origin",
            "X-Requested-With",
        ]
    )

    # Upload limits
    MAX_UPLOAD_BYTES: int = 10 * 1024 * 1024
    MAX_IMAGE_DIMENSION: int = 8000

    # Logging / debug
    LOG_LEVEL: str = "INFO"
    # One of "console" (human-readable pretty-print) or "json" (line-delimited
    # JSON for log aggregators). Empty string means "auto-pick from DEBUG":
    # console when DEBUG=true, json otherwise.
    LOG_FORMAT: str = ""
    DEBUG: bool = False

    # OpenTelemetry — tracer provider is always installed, but the exporter
    # only spins up when OTEL_ENABLED=true. Unconfigured deployments pay
    # essentially nothing for the import cost.
    OTEL_ENABLED: bool = False
    OTEL_SERVICE_NAME: str = "whis-backend"
    OTEL_EXPORTER_OTLP_ENDPOINT: str = "http://localhost:4317"

    @field_validator(
        "CORS_ORIGINS",
        "CORS_ALLOW_METHODS",
        "CORS_ALLOW_HEADERS",
        "PRICING_PROVIDERS",
        "PRICING_WEB_SEARCH_DOMAINS",
        mode="before",
    )
    @classmethod
    def _split_csv(cls, value):
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    def model_post_init(self, _context) -> None:
        secret_missing = not self.SECRET_KEY or self.SECRET_KEY in _PLACEHOLDER_SECRETS
        if not self.BYPASS_AUTH and secret_missing:
            raise RuntimeError(
                "SECRET_KEY must be set to a non-placeholder value when BYPASS_AUTH is false. "
                "Generate one with: python -c 'import secrets; print(secrets.token_urlsafe(64))'"
            )

        # v3.1: feature flags imply the LLM layer must be configured.
        # Failing fast here means operators get an actionable error at
        # startup rather than 500s on the first vision/pricing request.
        if (self.VISION_ENABLED or self.PRICING_ENABLED) and not self.LLM_BASE_URL:
            raise RuntimeError(
                "VISION_ENABLED or PRICING_ENABLED is true but LLM_BASE_URL is unset. "
                "Set it to e.g. https://openrouter.ai/api/v1 and supply LLM_API_KEY, "
                "or disable the feature flags."
            )
        if (self.VISION_ENABLED or self.PRICING_ENABLED) and not self.LLM_API_KEY:
            raise RuntimeError(
                "VISION_ENABLED or PRICING_ENABLED is true but LLM_API_KEY is unset."
            )

        # LLM_ALLOW_CLOUD=false means the base URL must point at something
        # local — belt-and-suspenders privacy guard that catches the
        # common "meant to use Ollama but left OpenRouter set" mistake.
        if self.LLM_BASE_URL and not self.LLM_ALLOW_CLOUD:
            if not _is_private_llm_host(self.LLM_BASE_URL):
                raise RuntimeError(
                    f"LLM_ALLOW_CLOUD=false but LLM_BASE_URL ({self.LLM_BASE_URL}) "
                    "does not resolve to localhost or a private-range IP."
                )

    def pricing_model(self) -> str:
        """Resolve the pricing model, defaulting to the vision model."""
        return self.LLM_PRICING_MODEL or self.LLM_MODEL

    def resolve_log_format(self) -> str:
        """Return "console" or "json" after applying the DEBUG-aware default."""
        explicit = (self.LOG_FORMAT or "").strip().lower()
        if explicit in {"console", "json"}:
            return explicit
        return "console" if self.DEBUG else "json"

    @property
    def upload_path(self) -> Path:
        return Path(self.UPLOAD_DIR).resolve()

    @property
    def backup_path(self) -> Path:
        return Path(self.BACKUP_DIR).resolve()


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
