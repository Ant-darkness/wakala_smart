from functools import lru_cache
from typing import Literal

from pydantic import SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
        validate_default=True,
    )

    # Application
    APP_NAME: str = "WAKALA SMART API"
    APP_VERSION: str = "1.0.0"
    APP_ENV: Literal["development", "testing", "production"] = "development"
    DEBUG: bool = False

    # API
    API_V1_PREFIX: str = "/api/v1"

    # Database
    DATABASE_URL: str
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 1800
    DB_ECHO: bool = False

    # Security
    SECRET_KEY: SecretStr
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    @field_validator("API_V1_PREFIX")
    @classmethod
    def validate_api_prefix(cls, value: str) -> str:
        value = value.strip()

        if not value.startswith("/"):
            raise ValueError("API_V1_PREFIX must start with '/'.")

        if value != "/":
            value = value.rstrip("/")

        return value

    @field_validator("DATABASE_URL")
    @classmethod
    def validate_database_url(cls, value: str) -> str:
        value = value.strip()

        if not value.startswith("postgresql+psycopg://"):
            raise ValueError("DATABASE_URL must use PostgreSQL with the psycopg driver.")

        if "CHANGE_ME" in value or "YOUR_PASSWORD" in value:
            raise ValueError("DATABASE_URL contains a placeholder credential.")

        return value

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, value: SecretStr) -> SecretStr:
        secret = value.get_secret_value()

        if len(secret) < 32:
            raise ValueError("SECRET_KEY must contain at least 32 characters.")

        return value

    @field_validator("ACCESS_TOKEN_EXPIRE_MINUTES")
    @classmethod
    def validate_token_expiry(cls, value: int) -> int:
        if not 1 <= value <= 1440:
            raise ValueError("ACCESS_TOKEN_EXPIRE_MINUTES must be between 1 and 1440.")

        return value

    @field_validator("DB_POOL_SIZE")
    @classmethod
    def validate_pool_size(cls, value: int) -> int:
        if value < 1:
            raise ValueError("DB_POOL_SIZE must be at least 1.")

        return value

    @field_validator("DB_MAX_OVERFLOW")
    @classmethod
    def validate_max_overflow(cls, value: int) -> int:
        if value < 0:
            raise ValueError("DB_MAX_OVERFLOW cannot be negative.")

        return value

    @field_validator("DB_POOL_TIMEOUT", "DB_POOL_RECYCLE")
    @classmethod
    def validate_pool_timeouts(cls, value: int) -> int:
        if value < 1:
            raise ValueError("Database pool timeout values must be positive.")

        return value

    @model_validator(mode="after")
    def validate_environment(self):
        if self.APP_ENV == "production":
            if self.DEBUG:
                raise ValueError("DEBUG must be False in production.")

            if self.DB_ECHO:
                raise ValueError("DB_ECHO must be False in production.")

        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
