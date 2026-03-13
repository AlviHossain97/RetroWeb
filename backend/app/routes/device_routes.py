"""
Device-related API routes.
"""

from fastapi import APIRouter
from app.db import get_conn
from app.repositories import device_repository
from app.models.api_models import DeviceHeartbeat

router = APIRouter(prefix="/devices", tags=["devices"])


@router.get("")
def list_devices(limit: int = 20):
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            rows = device_repository.fetch_all_devices(cur, limit)
    finally:
        conn.close()
    return rows


@router.post("/heartbeat")
def device_heartbeat(hb: DeviceHeartbeat):
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            device_repository.upsert_device(cur, hb.hostname, hb.ip_address, hb.client_version)
    finally:
        conn.close()
    return {"ok": True}
