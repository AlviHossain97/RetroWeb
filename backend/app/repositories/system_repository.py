"""
Repository for system-related database queries.
"""


def fetch_system_stats(cur, limit=20):
    cur.execute("""
        SELECT system_name,
               SUM(COALESCE(duration_seconds,0)) AS total_seconds,
               COUNT(*) AS session_count
        FROM sessions
        WHERE system_name IS NOT NULL
        GROUP BY system_name
        ORDER BY total_seconds DESC
        LIMIT %s
    """, (limit,))
    return cur.fetchall()
