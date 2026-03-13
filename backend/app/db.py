"""
Database connection pool using DBUtils + PyMySQL.

Replaces the per-request get_conn() pattern with a pooled connection manager.
"""

import pymysql
from dbutils.pooled_db import PooledDB
from app.config import get_settings

_pool: PooledDB | None = None


def _create_pool() -> PooledDB:
    """Create and return a new connection pool."""
    settings = get_settings()
    return PooledDB(
        creator=pymysql,
        maxconnections=settings.db_pool_size,
        mincached=1,
        maxcached=settings.db_pool_size,
        blocking=True,
        host=settings.db_host,
        port=settings.db_port,
        user=settings.db_user,
        password=settings.db_password,
        database=settings.db_name,
        charset=settings.db_charset,
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True,
    )


def get_pool() -> PooledDB:
    """Return the global connection pool, creating it if needed."""
    global _pool
    if _pool is None:
        _pool = _create_pool()
    return _pool


def get_conn():
    """Get a pooled database connection."""
    return get_pool().connection()


def close_pool():
    """Close the connection pool on shutdown."""
    global _pool
    if _pool is not None:
        _pool.close()
        _pool = None
