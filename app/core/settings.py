"""Application settings and configuration."""

import os
from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    # Environment
    env: str = Field(default="dev", alias="ENV")
    timezone: str = Field(default="Europe/Kyiv", alias="TZ")

    # Database
    postgres_host: str = Field(alias="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, alias="POSTGRES_PORT")
    postgres_db: str = Field(alias="POSTGRES_DB")
    postgres_user: str = Field(alias="POSTGRES_USER")
    postgres_password: str = Field(alias="POSTGRES_PASSWORD")

    # Security
    secret_key: str = Field(alias="SECRET_KEY")
    access_token_expire_minutes: int = Field(
        default=4320, alias="ACCESS_TOKEN_EXPIRE_MINUTES"
    )

    # Telegram Bot
    telegram_bot_token: str = Field(alias="TELEGRAM_BOT_TOKEN")
    
    # WebApp URL
    webapp_url: str = Field(default="https://your-domain.com", alias="WEBAPP_URL")

    # Google Sheets (disabled)
    # sheets_spreadsheet_id: str = Field(alias="SHEETS_SPREADSHEET_ID")
    # google_service_account_json_path: str = Field(
    #     alias="GOOGLE_SERVICE_ACCOUNT_JSON_PATH"
    # )

    # Admin credentials
    admin_email: str = Field(default="admin@schoola.local", alias="ADMIN_EMAIL")
    admin_password: str = Field(default="admin123", alias="ADMIN_PASSWORD")
    
    # Domain (optional)
    domain: Optional[str] = Field(default="localhost", alias="DOMAIN")

    @property
    def database_url(self) -> str:
        """Get async database URL."""
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def database_url_sync(self) -> str:
        """Get sync database URL for Alembic."""
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Global settings instance
settings = get_settings()
