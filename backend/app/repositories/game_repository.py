"""
Repository for game-related database queries.
"""


def fetch_all_games(cur, limit=50):
    cur.execute("""
        SELECT rom_path, system_name,
               SUM(COALESCE(duration_seconds,0)) AS total_seconds,
               MAX(started_at) AS last_played,
               COUNT(*) AS session_count
        FROM sessions
        GROUP BY rom_path, system_name
        ORDER BY last_played DESC
        LIMIT %s
    """, (limit,))
    return cur.fetchall()


def fetch_game_detail(cur, rom_path: str):
    cur.execute("""
        SELECT rom_path, system_name, emulator, core,
               SUM(COALESCE(duration_seconds,0)) AS total_seconds,
               MAX(started_at) AS last_played,
               MIN(started_at) AS first_played,
               COUNT(*) AS session_count
        FROM sessions
        WHERE rom_path = %s
        GROUP BY rom_path, system_name, emulator, core
    """, (rom_path,))
    return cur.fetchone()
