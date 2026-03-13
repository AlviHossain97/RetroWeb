"""
Repository for device-related database queries.
"""


def upsert_device(cur, hostname: str, ip_address: str | None = None, client_version: str | None = None):
    cur.execute("""
        INSERT INTO devices (hostname, ip_address, client_version, status, last_seen_at)
        VALUES (%s, %s, %s, 'online', NOW())
        ON DUPLICATE KEY UPDATE
            ip_address = COALESCE(VALUES(ip_address), ip_address),
            client_version = COALESCE(VALUES(client_version), client_version),
            status = 'online',
            last_seen_at = NOW()
    """, (hostname, ip_address, client_version))


def fetch_all_devices(cur, limit=20):
    cur.execute("""
        SELECT id, hostname, display_name, ip_address, status,
               last_seen_at, client_version, notes, created_at
        FROM devices
        ORDER BY last_seen_at DESC
        LIMIT %s
    """, (limit,))
    return cur.fetchall()
