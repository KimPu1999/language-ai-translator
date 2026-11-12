from functools import lru_cache
from typing import Annotated
from urllib.parse import urlparse

from pydantic import SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Lingua AI Translator API"
    app_env: str = "development"
    log_level: str = "INFO"
    database_url: str = "postgresql+asyncpg://localhost:5432/lingua"
    cors_origins: Annotated[list[str], NoDecode] = [
        "http://localhost:3000",
        "http://localhost:5173",
    ]
    azure_translator_key: str | None = None
    azure_translator_endpoint: str = "https://api.cognitive.microsofttranslator.com"
    azure_translator_region: str | None = None
    azure_translator_timeout_seconds: float = 10.0
    azure_speech_key: str | None = None
    azure_speech_region: str | None = None
    azure_speech_timeout_seconds: float = 30.0
    speech_rate_limit_requests: int = 30
    speech_rate_limit_bytes: int = 50_000_000
    speech_rate_limit_characters: int = 100_000
    rate_limit_requests: int = 60
    rate_limit_characters: int = 100_000
    rate_limit_window_seconds: int = 60
    redis_url: str | None = None
    translation_cache_enabled: bool = False
    translation_cache_ttl_seconds: int = 300
    ocr_tesseract_command: str = "tesseract"
    ocr_provider: str = "tesseract"
    ocr_timeout_seconds: float = 20.0
    ocr_max_upload_bytes: int = 8 * 1024 * 1024
    ocr_max_pixels: int = 20_000_000
    ocr_google_cloud_enabled: bool = False
    ocr_google_cloud_project_id: str | None = None
    ocr_google_cloud_credentials_json: SecretStr | None = None
    ocr_rate_limit_requests: int = 30
    ocr_rate_limit_bytes: int = 100_000_000
    document_max_upload_bytes: int = 10 * 1024 * 1024
    document_max_pages: int = 30
    document_max_characters: int = 50_000
    document_max_segment_characters: int = 3_000
    document_jobs_enabled: bool = False
    document_guest_mode_enabled: bool = False
    document_guest_capability_token: SecretStr | None = None
    document_storage_root: str = "/var/lib/lingua/documents"
    document_job_expiration_hours: int = 24
    document_job_max_attempts: int = 3
    document_job_rate_limit_requests: int = 10
    document_job_time_limit_seconds: int = 150
    document_pdf_font_path: str | None = None
    auth_session_ttl_seconds: int = 60 * 60 * 24 * 30
    auth_action_token_ttl_seconds: int = 15 * 60
    auth_cookie_name: str = "lingua_session"
    auth_csrf_cookie_name: str = "lingua_csrf"
    auth_cookie_secure: bool = False
    auth_public_base_url: str = "http://localhost:5173"
    auth_password_min_length: int = 8
    auth_login_rate_limit_attempts: int = 5
    auth_action_rate_limit_attempts: int = 10
    auth_rate_limit_window_seconds: int = 300
    auth_smtp_host: str | None = None
    auth_smtp_port: int = 587
    auth_smtp_username: str | None = None
    auth_smtp_password: SecretStr | None = None
    auth_smtp_from: str | None = None
    auth_smtp_starttls: bool = True
    auth_dev_mailbox_dir: str | None = None

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

    @field_validator(
        "azure_translator_key",
        "azure_translator_region",
        "azure_speech_key",
        "azure_speech_region",
        mode="before",
    )
    @classmethod
    def normalize_optional_secret_values(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None

    @field_validator("ocr_google_cloud_project_id", mode="before")
    @classmethod
    def normalize_optional_cloud_project(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None

    @field_validator("ocr_provider")
    @classmethod
    def validate_ocr_provider(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"tesseract", "google-cloud-vision"}:
            raise ValueError("OCR_PROVIDER must be tesseract or google-cloud-vision")
        return normalized

    @field_validator("ocr_google_cloud_credentials_json", mode="before")
    @classmethod
    def normalize_cloud_credentials(cls, value: str | SecretStr | None) -> str | SecretStr | None:
        if value is None:
            return None
        raw = value.get_secret_value() if isinstance(value, SecretStr) else value
        return raw.strip() or None

    @field_validator("document_guest_capability_token", mode="before")
    @classmethod
    def normalize_guest_token(cls, value: str | SecretStr | None) -> str | SecretStr | None:
        if value is None:
            return None
        raw = value.get_secret_value() if isinstance(value, SecretStr) else value
        return raw.strip() or None

    @model_validator(mode="after")
    def validate_speech_configuration(self) -> "Settings":
        if bool(self.azure_speech_key) != bool(self.azure_speech_region):
            raise ValueError("AZURE_SPEECH_KEY and AZURE_SPEECH_REGION must be configured together")
        return self

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

    @field_validator("azure_speech_timeout_seconds")
    @classmethod
    def require_bounded_speech_timeout(cls, value: float) -> float:
        if value <= 0 or value > 120:
            raise ValueError("AZURE_SPEECH_TIMEOUT_SECONDS must be between 0 and 120")
        return value

    @field_validator("rate_limit_requests", "rate_limit_characters", "rate_limit_window_seconds")
    @classmethod
    def require_positive_limits(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("Rate and usage limits must be positive")
        return value

    @field_validator(
        "speech_rate_limit_requests",
        "speech_rate_limit_bytes",
        "speech_rate_limit_characters",
    )
    @classmethod
    def require_positive_speech_limits(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("Speech rate and usage limits must be positive")
        return value

    @field_validator("translation_cache_ttl_seconds")
    @classmethod
    def require_positive_cache_ttl(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("TRANSLATION_CACHE_TTL_SECONDS must be positive")
        return value

    @field_validator("ocr_timeout_seconds")
    @classmethod
    def require_bounded_ocr_timeout(cls, value: float) -> float:
        if value <= 0 or value > 120:
            raise ValueError("OCR_TIMEOUT_SECONDS must be between 0 and 120")
        return value

    @field_validator("ocr_max_upload_bytes", "ocr_max_pixels")
    @classmethod
    def require_positive_ocr_limits(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("OCR limits must be positive")
        return value

    @field_validator("ocr_rate_limit_requests", "ocr_rate_limit_bytes")
    @classmethod
    def require_positive_ocr_rate_limits(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("OCR rate and usage limits must be positive")
        return value

    @field_validator(
        "document_max_upload_bytes",
        "document_max_pages",
        "document_max_characters",
        "document_max_segment_characters",
    )
    @classmethod
    def require_positive_document_limits(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("Document limits must be positive")
        return value

    @field_validator(
        "document_job_expiration_hours",
        "document_job_max_attempts",
        "document_job_rate_limit_requests",
        "document_job_time_limit_seconds",
    )
    @classmethod
    def require_positive_job_limits(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("Document job limits must be positive")
        return value

    @field_validator(
        "auth_session_ttl_seconds",
        "auth_action_token_ttl_seconds",
        "auth_password_min_length",
        "auth_login_rate_limit_attempts",
        "auth_action_rate_limit_attempts",
        "auth_rate_limit_window_seconds",
        "auth_smtp_port",
    )
    @classmethod
    def require_positive_auth_limits(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("Authentication limits must be positive")
        return value

    @field_validator("auth_password_min_length")
    @classmethod
    def require_secure_password_length(cls, value: int) -> int:
        if not 8 <= value <= 12:
            raise ValueError("AUTH_PASSWORD_MIN_LENGTH must be between 8 and 12")
        return value

    @field_validator(
        "auth_smtp_host", "auth_smtp_username", "auth_smtp_from", "auth_dev_mailbox_dir",
        mode="before",
    )
    @classmethod
    def normalize_optional_auth_values(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None

    @field_validator("auth_public_base_url")
    @classmethod
    def validate_auth_public_base_url(cls, value: str) -> str:
        parsed = urlparse(value.rstrip("/"))
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("AUTH_PUBLIC_BASE_URL must be an absolute HTTP(S) URL")
        return value.rstrip("/")

    @field_validator("auth_smtp_password", mode="before")
    @classmethod
    def normalize_smtp_password(
        cls, value: str | SecretStr | None
    ) -> str | SecretStr | None:
        if value is None:
            return None
        raw = value.get_secret_value() if isinstance(value, SecretStr) else value
        return raw.strip() or None

    @model_validator(mode="after")
    def validate_email_configuration(self) -> "Settings":
        smtp_values = (
            self.auth_smtp_host,
            self.auth_smtp_username,
            self.auth_smtp_password,
            self.auth_smtp_from,
        )
        if any(smtp_values) and not all(smtp_values):
            raise ValueError(
                "AUTH_SMTP_HOST, AUTH_SMTP_USERNAME, AUTH_SMTP_PASSWORD and AUTH_SMTP_FROM "
                "must be configured together"
            )
        if self.auth_dev_mailbox_dir and self.app_env.lower() != "development":
            raise ValueError("AUTH_DEV_MAILBOX_DIR is allowed only in development")
        if self.app_env.lower() in {"production", "prod"}:
            if not self.auth_cookie_secure:
                raise ValueError("AUTH_COOKIE_SECURE must be true in production")
            if not self.auth_public_base_url.startswith("https://"):
                raise ValueError("AUTH_PUBLIC_BASE_URL must use HTTPS in production")
            if not self.redis_url:
                raise ValueError(
                    "REDIS_URL is required in production for distributed rate limiting"
                )
        return self

    @model_validator(mode="after")
    def validate_guest_document_mode(self) -> "Settings":
        if self.document_guest_mode_enabled and self.app_env.lower() != "development":
            raise ValueError("DOCUMENT_GUEST_MODE_ENABLED is allowed only in development")
        if self.document_guest_mode_enabled and not self.document_guest_capability_token:
            raise ValueError("DOCUMENT_GUEST_CAPABILITY_TOKEN is required for guest mode")
        if self.document_jobs_enabled and not self.redis_url:
            raise ValueError("REDIS_URL is required when document jobs are enabled")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
