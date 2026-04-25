#!/bin/bash
# Jellyfin / Kodi launcher (PiStation Loop 2)
# - Splash (omxplayer)
# - Kodi-standalone preferred; Chromium-kiosk fallback
# - Aggressive cleanup so EmulationStation regains the framebuffer
#   cleanly when the user exits Kodi (replaces a previous version
#   that occasionally required a power-cycle).

set -u
LOGFILE=/tmp/jellyfin.log
JELLYFIN_URL="http://192.168.1.190:8096"
SPLASH_MP4=/home/pi/RetroPie/splashscreens/jellyfin.mp4
ES_VT=1
KODI_VT=8

log() { echo "$(date +'%F %T') $*" >> "$LOGFILE"; }
log "==== launch (pid=$$) ===="

cleanup() {
  local rc=$?
  log "cleanup trapped (rc=$rc, pid=$$)"
  for p in kodi.bin kodi kodi-standalone openbox openbox-session matchbox-window-manager; do
    pkill -x "$p" 2>/dev/null
  done
  pkill -f chromium-browser 2>/dev/null
  pkill -f chromium 2>/dev/null
  sleep 0.5
  pkill -KILL -x X     2>/dev/null
  pkill -KILL -x Xorg  2>/dev/null
  pkill -KILL -x xinit 2>/dev/null
  sudo deallocvt "$KODI_VT" 2>/dev/null || true
  sudo chvt "$ES_VT" 2>/dev/null
  local espid
  espid=$(pgrep -x emulationstation 2>/dev/null | head -1)
  [ -n "${espid:-}" ] && kill -CONT "$espid" 2>/dev/null
  log "cleanup done"
}
trap cleanup EXIT INT TERM HUP

if [ -f "$SPLASH_MP4" ] && command -v omxplayer >/dev/null 2>&1; then
  omxplayer --no-osd --aspect-mode fill "$SPLASH_MP4" >/dev/null 2>&1 &
  SPLASH_PID=$!
  sleep 3
  kill "$SPLASH_PID" 2>/dev/null
  pkill -f omxplayer 2>/dev/null
fi

if command -v kodi-standalone >/dev/null 2>&1; then
  KODI_BIN=$(command -v kodi-standalone); RENDERER=kodi
elif command -v kodi >/dev/null 2>&1; then
  KODI_BIN=$(command -v kodi); RENDERER=kodi
elif command -v chromium-browser >/dev/null 2>&1; then
  BROWSER=$(command -v chromium-browser); RENDERER=browser
elif command -v chromium >/dev/null 2>&1; then
  BROWSER=$(command -v chromium); RENDERER=browser
else
  log "Neither Kodi nor Chromium installed; aborting."
  exit 1
fi
log "renderer=$RENDERER"

case "$RENDERER" in
  kodi)
    INNER_CMD="openbox-session & OB_PID=\$!; xset s off; xset -dpms; xset s noblank; \"$KODI_BIN\"; kill \$OB_PID 2>/dev/null; pkill -x openbox 2>/dev/null"
    ;;
  browser)
    INNER_CMD="matchbox-window-manager -use_titlebar no & MB_PID=\$!; xset s off; xset -dpms; xset s noblank; \"$BROWSER\" --kiosk --noerrdialogs --disable-infobars --disable-session-crashed-bubble --autoplay-policy=no-user-gesture-required \"$JELLYFIN_URL\"; kill \$MB_PID 2>/dev/null"
    ;;
esac

log "starting xinit on vt$KODI_VT"
sudo openvt -c "$KODI_VT" -s -w -- \
  xinit /bin/sh -c "$INNER_CMD" -- :0 vt"$KODI_VT" -nolisten tcp \
  >> "$LOGFILE" 2>&1
log "xinit exited rc=$?"
exit 0
