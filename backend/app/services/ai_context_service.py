"""Shared AI context helpers for PiStation prompts."""

from app.db import get_conn
from app.services import ai_tools_service
from app.utils.title_utils import game_title_from_path


def _format_time(seconds: int) -> str:
    if not seconds or seconds <= 0:
        return "0 minutes"
    if seconds < 60:
        return f"{seconds} seconds"
    if seconds < 3600:
        return f"{seconds // 60} minutes"
    h = seconds // 3600
    m = (seconds % 3600) // 60
    return f"{h} hours {m} minutes"


def _build_context(
    summary: dict,
    top_games: list,
    systems: list,
    recent: list,
    active: list,
    longest: dict | None,
) -> str:
    """Build a natural language context string from gaming data."""
    lines = []

    if summary:
        lines.append("GAMING STATS OVERVIEW:")
        lines.append(f"- Total sessions: {summary.get('total_sessions', 0)}")
        lines.append(f"- Total playtime: {_format_time(summary.get('total_seconds', 0))}")
        lines.append(f"- Unique systems: {summary.get('unique_systems', 0)}")
        if summary.get("first_session"):
            lines.append(f"- First session: {summary['first_session']}")
        if summary.get("last_session"):
            lines.append(f"- Last session: {summary['last_session']}")

    if active:
        lines.append("\nCURRENTLY PLAYING:")
        for session in active:
            title = game_title_from_path(session.get("rom_path", ""))
            lines.append(
                f"- {title} ({session.get('system_name', 'unknown')}) "
                f"on {session.get('pi_hostname', 'unknown')} since {session.get('started_at', '?')}"
            )

    if top_games:
        lines.append("\nTOP GAMES BY PLAYTIME:")
        for index, game in enumerate(top_games, 1):
            title = game_title_from_path(game.get("rom_path", ""))
            lines.append(
                f"  {index}. {title} ({game.get('system_name', 'unknown')}) "
                f"- {_format_time(game.get('total_seconds', 0))}, "
                f"{game.get('session_count', 0)} sessions"
            )

    if systems:
        lines.append("\nPLAYTIME BY SYSTEM:")
        for system in systems:
            lines.append(
                f"  - {system.get('system_name', 'unknown').upper()}: "
                f"{_format_time(system.get('total_seconds', 0))}, "
                f"{system.get('session_count', 0)} sessions"
            )

    if recent:
        lines.append("\nRECENT SESSIONS:")
        for session in recent:
            title = game_title_from_path(session.get("rom_path", ""))
            duration = (
                _format_time(session.get("duration_seconds", 0))
                if session.get("duration_seconds")
                else "in progress"
            )
            lines.append(
                f"  - {title} ({session.get('system_name', 'unknown')}) "
                f"on {session.get('pi_hostname', 'unknown')}, "
                f"{session.get('started_at', '?')}, duration: {duration}"
            )

    if longest:
        title = game_title_from_path(longest.get("rom_path", ""))
        lines.append(
            f"\nLONGEST SESSION EVER: {title} "
            f"({longest.get('system_name', 'unknown')}) "
            f"- {_format_time(longest.get('duration_seconds', 0))}"
        )

    return "\n".join(lines)


def fetch_context() -> str:
    """Query PiStation stats and return a prompt-ready context snapshot."""
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            summary = ai_tools_service.get_gaming_summary(cur)
            top_games = ai_tools_service.get_top_games(cur, 5)
            systems = ai_tools_service.get_system_breakdown(cur)
            recent = ai_tools_service.get_recent_sessions(cur, 5)
            active = ai_tools_service.get_active_sessions(cur)
            longest = ai_tools_service.get_longest_session(cur)
    finally:
        conn.close()

    return _build_context(summary, top_games, systems, recent, active, longest)
