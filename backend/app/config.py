"""
Application configuration loaded from environment variables / .env file.
"""

import os
from functools import lru_cache
from typing import Annotated

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode


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
    nvidia_voicechat_enabled: bool = False
    nvidia_voicechat_model: str = "nemotron-voicechat"
    nvidia_voicechat_upstream_url: str = ""
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

    # Voice gateway
    # NoDecode prevents pydantic-settings from JSON-parsing the env var —
    # VOICE_PROVIDER_ORDER is a plain comma-separated string.
    voice_provider_order: Annotated[list[str], NoDecode] = ["voicechat", "legacy"]
    voice_local_stt_url: str = ""
    voice_local_tts_url: str = ""
    voice_session_max_seconds: int = 840

    @field_validator("voice_provider_order", mode="before")
    @classmethod
    def parse_voice_provider_order(cls, value):
        if isinstance(value, str):
            return [part.strip() for part in value.split(",") if part.strip()]
        return value

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
    }


@lru_cache
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()
