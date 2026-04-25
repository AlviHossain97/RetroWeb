from fastapi import FastAPI
from pydantic import BaseModel
import pymysql
from datetime import datetime
import re
from pathlib import Path

DB = {
    "host": "127.0.0.1",
    "user": "pistation_app",
    "password": "REDACTED",  # captured value redacted before commit — see ./README.md
    "database": "pistation",
    "charset": "utf8mb4",
    "cursorclass": pymysql.cursors.DictCursor,
    "autocommit": True,
}

app = FastAPI(title="PiStation Stats API")


class StartEvent(BaseModel):
    pi_hostname: str
    rom_path: str
    system_name: str | None = None
    emulator: str | None = None
    core: str | None = None
    started_at: datetime


class EndEvent(BaseModel):
    session_id: int
    ended_at: datetime
    duration_seconds: int


def get_conn():
    return pymysql.connect(**DB)


def normalize_fields(rom_path: str, system_name: str | None, emulator: str | None, core: str | None):
    cmd = (rom_path or "").strip()
    rom = cmd

    m = re.search(r'(")?(/home/pi/RetroPie/roms/[^"]+)\1', cmd)
    if m:
        rom = m.group(2)

    if not core:
        m = re.search(r'-L\s+(\S+)', cmd)
        if m:
            so = m.group(1)
            base = so.split("/")[-1]
            core = base.replace("_libretro.so", "")

    if not system_name and rom:
        try:
            parts = Path(rom).parts
            i = parts.index("roms")
            if i + 1 < len(parts):
                system_name = parts[i + 1]
        except ValueError:
            pass

    if not emulator and "retroarch" in cmd:
        emulator = "retroarch"

    return rom, system_name, emulator, core


@app.get("/health")
def health():
    return {"ok": True}


@app.get("/version")
def version():
    return {"api": "pistation", "version": "reliable_v2"}


@app.post("/session/start")
def session_start(ev: StartEvent):
    rom, system_name, emulator, core = normalize_fields(
        ev.rom_path, ev.system_name, ev.emulator, ev.core
    )

    conn = get_conn()
    with conn.cursor() as cur:
        # Close any stale open sessions for this Pi before starting a new one
        cur.execute(
            """
            UPDATE sessions
            SET ended_at = %s,
                duration_seconds = GREATEST(TIMESTAMPDIFF(SECOND, started_at, %s), 0)
            WHERE pi_hostname = %s
              AND ended_at IS NULL
            """,
            (ev.started_at, ev.started_at, ev.pi_hostname),
        )

        cur.execute(
            """
            INSERT INTO sessions
            (pi_hostname, rom_path, system_name, emulator, core, started_at)
            VALUES (%s,%s,%s,%s,%s,%s)
            """,
            (ev.pi_hostname, rom, system_name, emulator, core, ev.started_at),
        )
        session_id = cur.lastrowid

    conn.close()
    return {"session_id": session_id}


@app.post("/session/end")
def session_end(ev: EndEvent):
    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE sessions
            SET ended_at = %s,
                duration_seconds = %s
            WHERE id = %s
            """,
            (ev.ended_at, ev.duration_seconds, ev.session_id),
        )
    conn.close()
    return {"ok": True}


@app.get("/stats/recent")
def recent_sessions(limit: int = 20):
    conn = get_conn()
    with conn.cursor() as cur:
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
        rows = cur.fetchall()
    conn.close()
    return rows


@app.get("/stats/active")
def active_sessions(limit: int = 10):
    conn = get_conn()
    with conn.cursor() as cur:
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
        rows = cur.fetchall()
    conn.close()
    return rows


@app.get("/stats/top")
def top_games(limit: int = 10):
    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT rom_path,
                   system_name,
                   emulator,
                   core,
                   SUM(COALESCE(duration_seconds,0)) AS total_seconds,
                   MAX(started_at) AS last_played
            FROM sessions
            GROUP BY rom_path, system_name, emulator, core
            ORDER BY total_seconds DESC
            LIMIT %s
            """,
            (limit,),
        )
        rows = cur.fetchall()
    conn.close()
    return rows
