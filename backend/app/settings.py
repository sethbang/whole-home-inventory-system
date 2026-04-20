from functools import lru_cache
from pathlib import Path
from typing import Annotated, List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


_PLACEHOLDER_SECRETS = {
    "your-secret-key-stored-in-env",
    "change-me",
    "changeme",
    "secret",
    "",
}


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

    # CORS — NoDecode prevents pydantic-settings from JSON-decoding before
    # our validator splits the comma-separated env form.
    CORS_ORIGINS: Annotated[List[str], NoDecode] = Field(
        default_factory=lambda: [
            "https://localhost:5173",
            "https://192.168.1.122:5173",
        ]
    )
    CORS_ALLOW_METHODS: Annotated[List[str], NoDecode] = Field(
        default_factory=lambda: ["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"]
    )
    CORS_ALLOW_HEADERS: Annotated[List[str], NoDecode] = Field(
        default_factory=lambda: ["Content-Type", "Authorization", "Accept", "Origin", "X-Requested-With"]
    )

    # Upload limits
    MAX_UPLOAD_BYTES: int = 10 * 1024 * 1024
    MAX_IMAGE_DIMENSION: int = 8000

    # Logging / debug
    LOG_LEVEL: str = "INFO"
    DEBUG: bool = False

    @field_validator("CORS_ORIGINS", "CORS_ALLOW_METHODS", "CORS_ALLOW_HEADERS", mode="before")
    @classmethod
    def _split_csv(cls, value):
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    def model_post_init(self, _context) -> None:
        if not self.BYPASS_AUTH:
            if not self.SECRET_KEY or self.SECRET_KEY in _PLACEHOLDER_SECRETS:
                raise RuntimeError(
                    "SECRET_KEY must be set to a non-placeholder value when BYPASS_AUTH is false. "
                    "Generate one with: python -c 'import secrets; print(secrets.token_urlsafe(64))'"
                )

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
