"""
Repository for achievement-related database queries.
"""


def fetch_all_achievements(cur):
    cur.execute("SELECT id, code, title, description, icon, category FROM achievements ORDER BY category, code")
    return cur.fetchall()


def fetch_unlocked_achievements(cur):
    cur.execute("""
        SELECT a.code, a.title, a.description, a.icon, a.category, ua.unlocked_at
        FROM user_achievements ua
        JOIN achievements a ON a.id = ua.achievement_id
        ORDER BY ua.unlocked_at DESC
    """)
    return cur.fetchall()
