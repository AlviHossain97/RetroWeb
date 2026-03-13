"""
Application configuration loaded from environment variables / .env file.
"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    db_host: str = "127.0.0.1"
    db_port: int = 3306
    db_user: str = "pistation_app"
    db_password: str = "NEWPASS"
    db_name: str = "pistation"
    db_charset: str = "utf8mb4"
    db_pool_size: int = 5

    # App
    app_title: str = "PiStation Stats API"
    app_version: str = "dashboard_v2"
    app_env: str = "production"

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
    }


@lru_cache
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()
