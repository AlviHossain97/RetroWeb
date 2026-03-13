"""
Session repository — all SQL queries related to gaming sessions.
"""

from datetime import datetime


def close_stale_sessions(cur, pi_hostname: str, started_at: datetime) -> int:
    """Close any open sessions for the given device.

    Sets ended_at and calculates duration for sessions that were never
    properly closed (e.g. due to crashes or missed end hooks).

    Returns the number of rows affected.
    """
    cur.execute(
        """
        UPDATE sessions
        SET ended_at = %s,
            duration_seconds = GREATEST(TIMESTAMPDIFF(SECOND, started_at, %s), 0)
        WHERE pi_hostname = %s
          AND ended_at IS NULL
        """,
        (started_at, started_at, pi_hostname),
    )
    return cur.rowcount


def insert_session(
    cur,
    pi_hostname: str,
    rom_path: str,
    system_name: str | None,
    emulator: str | None,
    core: str | None,
    started_at: datetime,
) -> int:
    """Insert a new session row and return its ID."""
    cur.execute(
        """
        INSERT INTO sessions
        (pi_hostname, rom_path, system_name, emulator, core, started_at)
        VALUES (%s,%s,%s,%s,%s,%s)
        """,
        (pi_hostname, rom_path, system_name, emulator, core, started_at),
    )
    return cur.lastrowid


def update_session_end(cur, session_id: int, ended_at: datetime, duration_seconds: int):
    """Mark a session as ended with its final duration."""
    cur.execute(
        """
        UPDATE sessions
        SET ended_at = %s,
            duration_seconds = %s
        WHERE id = %s
        """,
        (ended_at, duration_seconds, session_id),
    )


def fetch_active_session(cur, limit: int = 1) -> dict | None:
    """Fetch the most recent active (unfinished) session."""
    cur.execute(
        """
        SELECT id, pi_hostname, rom_path, system_name, emulator, core,
               started_at,
               TIMESTAMPDIFF(SECOND, started_at, NOW()) AS live_seconds
        FROM sessions
        WHERE ended_at IS NULL
        ORDER BY started_at DESC
        LIMIT %s
        """,
        (limit,),
    )
    return cur.fetchone()


def fetch_active_sessions(cur, limit: int = 10) -> list[dict]:
    """Fetch all active (unfinished) sessions."""
    cur.execute(
        """
        SELECT id, pi_hostname, rom_path, system_name, emulator, core,
               started_at,
               TIMESTAMPDIFF(SECOND, started_at, NOW()) AS live_seconds
        FROM sessions
        WHERE ended_at IS NULL
        ORDER BY started_at DESC
        LIMIT %s
        """,
        (limit,),
    )
    return cur.fetchall()


def fetch_recent_sessions(cur, limit: int = 20) -> list[dict]:
    """Fetch the most recent sessions ordered by start time."""
    cur.execute(
        """
        SELECT id, pi_hostname, rom_path, system_name, emulator, core,
               started_at, ended_at, duration_seconds
        FROM sessions
        ORDER BY started_at DESC
        LIMIT %s
        """,
        (limit,),
    )
    return cur.fetchall()


def fetch_top_games(cur, limit: int = 10) -> list[dict]:
    """Fetch top games by total playtime."""
    cur.execute(
        """
        SELECT rom_path,
               system_name,
               emulator,
               core,
               SUM(COALESCE(duration_seconds,0)) AS total_seconds,
               MAX(started_at) AS last_played,
               COUNT(*) AS session_count
        FROM sessions
        GROUP BY rom_path, system_name, emulator, core
        ORDER BY total_seconds DESC
        LIMIT %s
        """,
        (limit,),
    )
    return cur.fetchall()
