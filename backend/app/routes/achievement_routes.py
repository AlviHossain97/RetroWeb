"""
Achievement-related API routes.
"""

from fastapi import APIRouter
from app.db import get_conn
from app.repositories import achievement_repository

router = APIRouter(prefix="/achievements", tags=["achievements"])


@router.get("")
def list_achievements():
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            rows = achievement_repository.fetch_all_achievements(cur)
    finally:
        conn.close()
    return rows


@router.get("/unlocked")
def unlocked_achievements():
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            rows = achievement_repository.fetch_unlocked_achievements(cur)
    finally:
        conn.close()
    return rows
