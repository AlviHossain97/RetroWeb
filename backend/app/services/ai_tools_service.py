"""Safe AI tools — provides gaming analytics context from MySQL."""


def get_gaming_summary(cur) -> dict:
    """Overall gaming stats."""
    cur.execute("""
        SELECT 
            COUNT(*) AS total_sessions,
            COALESCE(SUM(duration_seconds), 0) AS total_seconds,
            COUNT(DISTINCT system_name) AS unique_systems,
            MIN(started_at) AS first_session,
            MAX(started_at) AS last_session
        FROM sessions
    """)
    return cur.fetchone()


def get_top_games(cur, limit: int = 5) -> list:
    """Most played games by total playtime."""
    cur.execute("""
        SELECT rom_path, system_name,
               SUM(COALESCE(duration_seconds, 0)) AS total_seconds,
               COUNT(*) AS session_count,
               MAX(started_at) AS last_played
        FROM sessions
        GROUP BY rom_path, system_name
        ORDER BY total_seconds DESC
        LIMIT %s
    """, (limit,))
    return cur.fetchall()


def get_system_breakdown(cur) -> list:
    """Playtime breakdown by system."""
    cur.execute("""
        SELECT system_name,
               SUM(COALESCE(duration_seconds, 0)) AS total_seconds,
               COUNT(*) AS session_count
        FROM sessions
        WHERE system_name IS NOT NULL
        GROUP BY system_name
        ORDER BY total_seconds DESC
    """)
    return cur.fetchall()


def get_recent_sessions(cur, limit: int = 5) -> list:
    """Most recent gaming sessions."""
    cur.execute("""
        SELECT rom_path, system_name, pi_hostname,
               started_at, ended_at, duration_seconds
        FROM sessions
        ORDER BY started_at DESC
        LIMIT %s
    """, (limit,))
    return cur.fetchall()


def get_active_sessions(cur) -> list:
    """Currently active sessions."""
    cur.execute("""
        SELECT rom_path, system_name, pi_hostname, started_at
        FROM sessions
        WHERE ended_at IS NULL
    """)
    return cur.fetchall()


def get_longest_session(cur) -> dict | None:
    """Single longest gaming session ever."""
    cur.execute("""
        SELECT rom_path, system_name, duration_seconds, started_at
        FROM sessions
        WHERE duration_seconds IS NOT NULL
        ORDER BY duration_seconds DESC
        LIMIT 1
    """)
    return cur.fetchone()


def search_games(cur, query: str) -> list:
    """Search sessions by ROM path containing query."""
    cur.execute("""
        SELECT rom_path, system_name,
               SUM(COALESCE(duration_seconds, 0)) AS total_seconds,
               COUNT(*) AS session_count
        FROM sessions
        WHERE rom_path LIKE %s
        GROUP BY rom_path, system_name
        ORDER BY total_seconds DESC
        LIMIT 10
    """, (f"%{query}%",))
    return cur.fetchall()
