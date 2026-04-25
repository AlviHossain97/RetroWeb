#!/usr/bin/env python3
import os
import sys
import json
import time
import socket
import re
from datetime import datetime, timezone
import urllib.request
import urllib.error

API_BASE = "http://alvi-OMEN-Laptop-15-en1xxx.local:8000"
STATE_FILE = "/tmp/pistation_session.json"
DEBUG_LOG = "/tmp/pistation_logger_debug.log"


def iso_now():
    return datetime.now(timezone.utc).isoformat()


def dbg(msg):
    try:
        with open(DEBUG_LOG, "a") as f:
            f.write("{} {}\n".format(iso_now(), msg))
    except Exception:
        pass


def post(path, payload):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        API_BASE + path,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=5) as resp:
        body = resp.read().decode("utf-8") or "{}"
        return json.loads(body)


def parse_runcommand(argv):
    """
    RetroPie runcommand args on your setup:
      argv[0] = system
      argv[1] = emulator
      argv[2] = rom path
      argv[3:] = full command line
    """
    system = argv[0] if len(argv) > 0 else ""
    emulator = argv[1] if len(argv) > 1 else ""
    rom_path = argv[2] if len(argv) > 2 else ""
    cmdline = " ".join(argv[3:]) if len(argv) > 3 else ""

    core = ""
    m = re.search(r"-L\s+(\S+)", cmdline)
    if m:
        so_path = m.group(1)
        base = os.path.basename(so_path)
        core = base.replace("_libretro.so", "")

    if not rom_path and cmdline:
        m = re.search(r'(")?(/home/pi/RetroPie/roms/[^"]+)\1', cmdline)
        if m:
            rom_path = m.group(2)

    return system, emulator, rom_path, core, cmdline


def close_existing_local_session():
    """
    If a previous session state file exists, try to close it before starting a new one.
    This prevents duplicate open sessions when onend was missed.
    """
    if not os.path.exists(STATE_FILE):
        return

    dbg("Found existing state file, attempting to close stale session first")

    try:
        with open(STATE_FILE, "r") as f:
            st = json.load(f)
    except Exception as e:
        dbg("ERROR reading stale state file: {}".format(repr(e)))
        try:
            os.remove(STATE_FILE)
            dbg("Removed unreadable stale state file")
        except Exception as e2:
            dbg("ERROR removing unreadable stale state file: {}".format(repr(e2)))
        return

    ended = iso_now()
    try:
        started_ts = datetime.fromisoformat(st["started_at"].replace("Z", "+00:00")).timestamp()
    except Exception:
        started_ts = time.time()

    duration = max(0, int(time.time() - started_ts))
    payload = {
        "session_id": int(st["session_id"]),
        "ended_at": ended,
        "duration_seconds": duration,
    }

    try:
        dbg("POST /session/end for stale local session payload={}".format(payload))
        res = post("/session/end", payload)
        dbg("RESP /session/end stale {}".format(res))
    except Exception as e:
        dbg("ERROR closing stale local session: {}".format(repr(e)))

    try:
        os.remove(STATE_FILE)
        dbg("Removed stale state file")
    except Exception as e:
        dbg("ERROR removing stale state file: {}".format(repr(e)))


def main():
    mode = os.environ.get("PISTATION_MODE", "").strip()
    host = socket.gethostname()
    argv = sys.argv[1:]

    dbg("BEGIN mode={} host={} argv={}".format(mode, host, argv))

    system, emulator, rom_path, core, cmdline = parse_runcommand(argv)
    dbg("PARSED system={} emulator={} rom_path={} core={}".format(system, emulator, rom_path, core))

    if mode == "start":
        close_existing_local_session()

        started = iso_now()
        payload = {
            "pi_hostname": host,
            "rom_path": rom_path,
            "system_name": system or None,
            "emulator": emulator or None,
            "core": core or None,
            "started_at": started,
        }

        dbg("POST /session/start payload={}".format(payload))
        try:
            res = post("/session/start", payload)
            dbg("RESP /session/start {}".format(res))
        except urllib.error.HTTPError as e:
            try:
                body = e.read().decode("utf-8", "ignore")
            except Exception:
                body = ""
            dbg("HTTPError start code={} body={}".format(getattr(e, "code", None), body))
            return
        except Exception as e:
            dbg("ERROR start exception={}".format(repr(e)))
            return

        try:
            with open(STATE_FILE, "w") as f:
                json.dump({"session_id": int(res["session_id"]), "started_at": started}, f)
            dbg("WROTE {}".format(STATE_FILE))
        except Exception as e:
            dbg("ERROR writing state file: {}".format(repr(e)))

        return

    if mode == "end":
        try:
            with open(STATE_FILE, "r") as f:
                st = json.load(f)
        except IOError:
            dbg("END: no state file {} (nothing to close)".format(STATE_FILE))
            return
        except Exception as e:
            dbg("ERROR reading state file: {}".format(repr(e)))
            return

        ended = iso_now()
        try:
            started_ts = datetime.fromisoformat(st["started_at"].replace("Z", "+00:00")).timestamp()
        except Exception:
            started_ts = time.time()

        duration = max(0, int(time.time() - started_ts))
        payload = {
            "session_id": int(st["session_id"]),
            "ended_at": ended,
            "duration_seconds": duration,
        }

        dbg("POST /session/end payload={}".format(payload))
        try:
            res = post("/session/end", payload)
            dbg("RESP /session/end {}".format(res))
        except urllib.error.HTTPError as e:
            try:
                body = e.read().decode("utf-8", "ignore")
            except Exception:
                body = ""
            dbg("HTTPError end code={} body={}".format(getattr(e, "code", None), body))
            return
        except Exception as e:
            dbg("ERROR end exception={}".format(repr(e)))
            return

        try:
            os.remove(STATE_FILE)
            dbg("REMOVED {}".format(STATE_FILE))
        except Exception as e:
            dbg("ERROR removing state file: {}".format(repr(e)))

        return

    dbg("No valid PISTATION_MODE set; exiting without action.")


if __name__ == "__main__":
    main()
