"""
System-related API routes.
"""

from fastapi import APIRouter
from app.db import get_conn
from app.repositories import system_repository

router = APIRouter(prefix="/systems", tags=["systems"])


@router.get("")
def list_systems(limit: int = 20):
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            rows = system_repository.fetch_system_stats(cur, limit)
    finally:
        conn.close()
    return rows
