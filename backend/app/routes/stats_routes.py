"""
Stats routes — GET /stats/recent, /stats/active, /stats/top.
"""

from fastapi import APIRouter
from app.db import get_conn
from app.repositories import session_repository

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("/recent")
def recent_sessions(limit: int = 20):
    """Return the most recent sessions."""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            rows = session_repository.fetch_recent_sessions(cur, limit)
    finally:
        conn.close()
    return rows


@router.get("/active")
def active_sessions(limit: int = 10):
    """Return currently active (unfinished) sessions."""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            rows = session_repository.fetch_active_sessions(cur, limit)
    finally:
        conn.close()
    return rows


@router.get("/top")
def top_games(limit: int = 10):
    """Return the most-played games by total playtime."""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            rows = session_repository.fetch_top_games(cur, limit)
    finally:
        conn.close()
    return rows
