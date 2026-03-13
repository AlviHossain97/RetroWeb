"""
Stats repository — aggregate/summary SQL queries.
"""


def fetch_summary_stats(cur) -> dict:
    """Fetch total session count and total playtime."""
    cur.execute(
        """
        SELECT
            COUNT(*) AS total_sessions,
            SUM(COALESCE(duration_seconds,0)) AS total_seconds
        FROM sessions
        """
    )
    return cur.fetchone()


def fetch_favourite_system(cur) -> dict | None:
    """Fetch the system with the most total playtime."""
    cur.execute(
        """
        SELECT system_name,
               SUM(COALESCE(duration_seconds,0)) AS total_seconds
        FROM sessions
        WHERE system_name IS NOT NULL
        GROUP BY system_name
        ORDER BY total_seconds DESC
        LIMIT 1
        """
    )
    return cur.fetchone()
