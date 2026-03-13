"""
Session service — business logic for session start/end.
"""

from app.db import get_conn
from app.utils.normalization import normalize_fields
from app.repositories import session_repository
from app.models.api_models import StartEvent, EndEvent


def start_session(ev: StartEvent) -> dict:
    """Process a session start event.

    1. Normalize incoming fields.
    2. Close any stale open sessions for this device.
    3. Insert a new session.
    4. Return the new session_id.
    """
    rom, system_name, emulator, core = normalize_fields(
        ev.rom_path, ev.system_name, ev.emulator, ev.core
    )

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            session_repository.close_stale_sessions(cur, ev.pi_hostname, ev.started_at)
            session_id = session_repository.insert_session(
                cur, ev.pi_hostname, rom, system_name, emulator, core, ev.started_at
            )
    finally:
        conn.close()

    return {"session_id": session_id}


def end_session(ev: EndEvent) -> dict:
    """Process a session end event.

    Updates the session row with ended_at and duration_seconds.
    """
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            session_repository.update_session_end(
                cur, ev.session_id, ev.ended_at, ev.duration_seconds
            )
    finally:
        conn.close()

    return {"ok": True}
