"""
Module: config.py
Purpose: Typed application settings loaded from environment variables.
Dependencies: pydantic-settings
Author: ApplyPilot
"""
from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration sourced from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Core
    app_env: str = Field(default="development")
    database_url: str = Field(default="postgresql+psycopg2://applypilot:applypilot@db:5432/applypilot")
    redis_url: str = Field(default="redis://redis:6379/0")

    # Auth
    jwt_secret: str = Field(default="dev-only-insecure-change-me")
    jwt_algorithm: str = Field(default="HS256")
    access_token_ttl_min: int = Field(default=30)
    refresh_token_ttl_days: int = Field(default=14)

    # Storage (MinIO / S3-compatible)
    s3_endpoint: str = Field(default="minio:9000")
    s3_access_key: str = Field(default="minioadmin")
    s3_secret_key: str = Field(default="minioadmin")
    s3_bucket: str = Field(default="applypilot")
    s3_secure: bool = Field(default=False)

    # Encryption for OAuth tokens (Fernet key, used Phase 4)
    fernet_key: str = Field(default="")

    # CORS
    cors_origins: str = Field(default="http://localhost:3000")

    # Rate limiting
    rate_limit_per_min: int = Field(default=120)

    @property
    def cors_origin_list(self) -> list[str]:
        """Return CORS origins as a list."""
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()


settings = get_settings()
