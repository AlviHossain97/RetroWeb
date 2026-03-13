"""
Pydantic models for API request/response payloads.
"""

from pydantic import BaseModel
from datetime import datetime


class StartEvent(BaseModel):
    """Sent by the client when a game starts."""
    pi_hostname: str
    rom_path: str
    system_name: str | None = None
    emulator: str | None = None
    core: str | None = None
    started_at: datetime
    event_id: str | None = None  # Optional UUID for dedup readiness


class EndEvent(BaseModel):
    """Sent by the client when a game exits."""
    session_id: int
    ended_at: datetime
    duration_seconds: int
