#!/bin/bash
# PiStation Loop 2 launcher — Jellyfin via Kodi (kodi-standalone).
#
# Architectural simplification 2026-04-25: previous versions wrapped
# Kodi inside an xinit + openbox X session on a separate VT, which
# created a race on exit (X teardown + VT switch + ES resume) that
# occasionally hung the Pi. /usr/bin/kodi-standalone is the distro's
# official session-manager wrapper — it owns the VT/framebuffer
# lifecycle natively and exits cleanly when Kodi exits. We just
# splash + invoke + backstop-cleanup.
#
# Persistent log at /home/pi/pistation-jellyfin.log (survives reboots,
# unlike /tmp).

set -uo pipefail
LOGFILE=/home/pi/pistation-jellyfin.log
log() { printf '%s %s\n' "$(date '+%F %T')" "$*" >> "$LOGFILE"; }
log "==== launch (pid=$$) ===="

# Splash
SPLASH_MP4=/home/pi/RetroPie/splashscreens/jellyfin.mp4
if [ -f "$SPLASH_MP4" ] && command -v omxplayer >/dev/null 2>&1; then
  log "splash start"
  omxplayer --no-osd --aspect-mode fill "$SPLASH_MP4" >/dev/null 2>&1 &
  SPLASH_PID=$!
  sleep 3
  kill "$SPLASH_PID" 2>/dev/null || true
  pkill -f omxplayer 2>/dev/null || true
  log "splash end"
fi

KODI_BIN=$(command -v kodi-standalone || command -v kodi || true)
if [ -z "$KODI_BIN" ]; then
  log "no kodi binary on PATH"
  exit 1
fi
log "invoking $KODI_BIN"

# Run Kodi. kodi-standalone handles its own VT/framebuffer/teardown.
"$KODI_BIN" >> "$LOGFILE" 2>&1
RC=$?
log "kodi exited rc=$RC"

# Backstop — kill any stragglers (Kodi child threads, helper procs)
for p in kodi.bin kodi kodi-standalone; do
  if pgrep -x "$p" >/dev/null 2>&1; then
    log "backstop pkill -KILL $p"
    pkill -KILL -x "$p" 2>/dev/null || true
  fi
done

# ES suspends itself when launching a system entry; resume it explicitly
ES_PID=$(pgrep -x emulationstation 2>/dev/null | head -1)
if [ -n "$ES_PID" ]; then
  log "SIGCONT to emulationstation pid=$ES_PID"
  kill -CONT "$ES_PID" 2>/dev/null || true
fi

# Make sure we're on the ES VT
sudo chvt 1 2>/dev/null || true

log "done rc=$RC"
exit 0
