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


class DeviceHeartbeat(BaseModel):
    hostname: str
    ip_address: str | None = None
    client_version: str | None = None


class SystemStatsResponse(BaseModel):
    system_name: str
    total_seconds: int
    session_count: int
