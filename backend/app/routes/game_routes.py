"""
Game-related API routes.
"""

from fastapi import APIRouter
from app.db import get_conn
from app.repositories import game_repository
from app.utils.title_utils import game_title_from_path

router = APIRouter(prefix="/games", tags=["games"])


@router.get("")
def list_games(limit: int = 50):
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            rows = game_repository.fetch_all_games(cur, limit)
    finally:
        conn.close()
    for row in rows:
        row['title'] = game_title_from_path(row.get('rom_path', ''))
    return rows
