from functools import lru_cache
from urllib.parse import urlparse

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Lingua AI Translator API"
    app_env: str = "development"
    log_level: str = "INFO"
    database_url: str = "postgresql+asyncpg://localhost:5432/lingua"
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]
    azure_translator_key: str | None = None
    azure_translator_endpoint: str = "https://api.cognitive.microsofttranslator.com"
    azure_translator_region: str | None = None
    azure_translator_timeout_seconds: float = 10.0
    rate_limit_requests: int = 60
    rate_limit_characters: int = 100_000
    rate_limit_window_seconds: int = 60
    redis_url: str | None = None
    translation_cache_enabled: bool = False
    translation_cache_ttl_seconds: int = 300

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @field_validator("database_url")
    @classmethod
    def require_postgresql(cls, value: str) -> str:
        if not value.startswith("postgresql+asyncpg://"):
            raise ValueError("DATABASE_URL must use postgresql+asyncpg://")
        return value

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @field_validator("azure_translator_key", "azure_translator_region", mode="before")
    @classmethod
    def normalize_optional_secret_values(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None

    @field_validator("azure_translator_endpoint")
    @classmethod
    def require_azure_endpoint(cls, value: str) -> str:
        parsed = urlparse(value.rstrip("/"))
        host = (parsed.hostname or "").lower()
        if parsed.scheme != "https" or not host:
            raise ValueError("AZURE_TRANSLATOR_ENDPOINT must be an HTTPS Azure Translator endpoint")
        if host != "api.cognitive.microsofttranslator.com" and not host.endswith(
            ".cognitiveservices.azure.com"
        ):
            raise ValueError("AZURE_TRANSLATOR_ENDPOINT must point to an Azure Translator host")
        return value.rstrip("/")

    @field_validator("azure_translator_timeout_seconds")
    @classmethod
    def require_bounded_timeout(cls, value: float) -> float:
        if value <= 0 or value > 60:
            raise ValueError("AZURE_TRANSLATOR_TIMEOUT_SECONDS must be between 0 and 60")
        return value

    @field_validator("rate_limit_requests", "rate_limit_characters", "rate_limit_window_seconds")
    @classmethod
    def require_positive_limits(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("Rate and usage limits must be positive")
        return value

    @field_validator("translation_cache_ttl_seconds")
    @classmethod
    def require_positive_cache_ttl(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("TRANSLATION_CACHE_TTL_SECONDS must be positive")
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
