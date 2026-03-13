"""
Dashboard service — assembles all data needed for dashboard rendering.
"""

from app.db import get_conn
from app.repositories import session_repository, stats_repository
from app.models.view_models import DashboardContext


def get_dashboard_context() -> DashboardContext:
    """Fetch all dashboard data in a single connection and return a DashboardContext."""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            active = session_repository.fetch_active_session(cur, limit=1)
            recent = session_repository.fetch_recent_sessions(cur, limit=8)
            top = session_repository.fetch_top_games(cur, limit=6)
            summary = stats_repository.fetch_summary_stats(cur)
            fav_system = stats_repository.fetch_favourite_system(cur)
    finally:
        conn.close()

    return DashboardContext(
        active_session=active,
        recent_sessions=recent,
        top_games=top,
        total_sessions=summary["total_sessions"] or 0,
        total_seconds=summary["total_seconds"] or 0,
        fav_system_name=fav_system["system_name"] if fav_system else "N/A",
    )
