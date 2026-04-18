"""
Application configuration loaded from environment variables / .env file.
"""

import os
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    db_host: str = "127.0.0.1"
    db_port: int = 3306
    db_user: str = "pistation_app"
    db_password: str = os.getenv("PISTATION_DB_PASSWORD", "")
    db_name: str = "pistation"
    db_charset: str = "utf8mb4"
    db_pool_size: int = 5

    # App
    app_title: str = "PiStation Stats API"
    app_version: str = "dashboard_v2"
    app_env: str = "production"

    # Web Grounding & AI Setup
    nvidia_api_key: str = ""
    nvidia_model: str = "stepfun-ai/step-3.5-flash"
    web_search_mode: str = "auto"  # auto, always, never
    searxng_url: str = ""
    tavily_api_key: str = os.getenv("TAVILY_API_KEY", "")
    search_top_k: int = 5
    fetch_top_k: int = 3
    request_timeout_seconds: int = 10
    cache_ttl_seconds: int = 3600
    grounded_temperature: float = 0.2
    normal_temperature: float = 0.7

    # Image generation (ImageRouter)
    imagerouter_api_key: str = os.getenv("IMAGEROUTER_API_KEY", "")
    imagerouter_image_model: str = "google/nano-banana-2:free"

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
    }


@lru_cache
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()
