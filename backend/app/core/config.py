"""Application settings, loaded from environment variables (never hard-coded secrets)."""

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "GuessIngs"
    environment: str = Field(default="development", pattern="^(development|test|production)$")
    database_url: str = "postgresql+psycopg://guessings:guessings@localhost:5432/guessings"
    redis_url: str | None = None

    # Auth
    secret_key: str = Field(default="dev-insecure-secret-change-me-please-0123456789", min_length=32)
    access_token_minutes: int = 60 * 24 * 7
    cookie_secure: bool = False
    cookie_domain: str | None = None
    # Only trust X-Forwarded-For when running behind a known reverse proxy.
    trust_proxy: bool = False

    # CORS (only needed if the frontend is served from another origin)
    cors_origins: list[str] = ["http://localhost:3000"]

    # AI
    anthropic_api_key: str | None = None
    ai_model: str = "claude-opus-5"
    ai_enabled: bool = True
    ai_timeout_seconds: float = 45.0

    # OCR / uploads
    max_upload_mb: int = 8
    tesseract_cmd: str | None = None

    # Rate limits (requests per window)
    rate_limit_auth_per_minute: int = 10
    rate_limit_analyze_per_minute: int = 20
    rate_limit_default_per_minute: int = 120

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, v):
        if isinstance(v, str):
            return [o.strip() for o in v.split(",") if o.strip()]
        return v

    @property
    def ai_available(self) -> bool:
        return bool(self.ai_enabled and self.anthropic_api_key)

    def validate_production(self) -> None:
        if self.environment == "production":
            if self.secret_key.startswith("dev-insecure"):
                raise RuntimeError("SECRET_KEY must be set in production")
            if not self.cookie_secure:
                raise RuntimeError("COOKIE_SECURE must be true in production")


@lru_cache
def get_settings() -> Settings:
    return Settings()
