#!/bin/bash
# ============================================================
# PiStation Dashboard Stream
# Renders the kiosk dashboard on a virtual display and streams
# it to the Pi via UDP using NVENC hardware encoding.
# The laptop's main display is completely untouched.
#
# Usage:
#   PI_IP=192.168.1.100 ./scripts/dashboard-stream.sh
#
# Pi-side playback:
#   mpv udp://0.0.0.0:5004 --no-cache --profile=low-latency --fs --no-osc
# ============================================================

set -euo pipefail

HOST_IP="${HOST_IP:-$(hostname -I | awk '{print $1}')}"
PI_IP="${PI_IP:-}"
DISPLAY_NUM="${DISPLAY_NUM:-99}"
RESOLUTION="${RESOLUTION:-1280x720}"
FPS="${FPS:-15}"
BITRATE="${BITRATE:-2M}"
STREAM_PORT="${STREAM_PORT:-5004}"
DASHBOARD_URL="${DASHBOARD_URL:-http://localhost:8000/dashboard/kiosk}"

if [ -z "$PI_IP" ]; then
  echo "ERROR: PI_IP environment variable is required."
  echo "Usage: PI_IP=192.168.1.100 $0"
  exit 1
fi

XVFB_PID=""
BROWSER_PID=""
FFMPEG_PID=""

cleanup() {
  echo ""
  echo "[DashStream] Shutting down..."
  [ -n "$FFMPEG_PID" ]  && kill "$FFMPEG_PID"  2>/dev/null
  [ -n "$BROWSER_PID" ] && kill "$BROWSER_PID" 2>/dev/null
  [ -n "$XVFB_PID" ]    && kill "$XVFB_PID"    2>/dev/null
  # Clean up lock file
  rm -f "/tmp/.X${DISPLAY_NUM}-lock" 2>/dev/null
  echo "[DashStream] Stopped."
}
trap cleanup SIGINT SIGTERM EXIT

# 1. Start virtual framebuffer
echo "[DashStream] Starting Xvfb on :${DISPLAY_NUM} (${RESOLUTION})..."
Xvfb ":${DISPLAY_NUM}" -screen 0 "${RESOLUTION}x24" -ac +extension GLX &
XVFB_PID=$!
sleep 1

if ! kill -0 "$XVFB_PID" 2>/dev/null; then
  echo "[DashStream] ERROR: Xvfb failed to start. Is display :${DISPLAY_NUM} already in use?"
  exit 1
fi

# 2. Launch browser in kiosk mode on the virtual display
echo "[DashStream] Launching browser on :${DISPLAY_NUM} → ${DASHBOARD_URL}"
DISPLAY=":${DISPLAY_NUM}" brave-browser-stable \
  --kiosk \
  --no-first-run \
  --disable-infobars \
  --disable-session-crashed-bubble \
  --disable-translate \
  --noerrdialogs \
  --disable-extensions \
  --disable-background-networking \
  --disable-sync \
  --user-data-dir="/tmp/pistation-stream-profile" \
  "$DASHBOARD_URL" &
BROWSER_PID=$!
sleep 3

# 3. Capture virtual display and stream via UDP with NVENC
echo "[DashStream] Starting NVENC capture → udp://${PI_IP}:${STREAM_PORT}"
ffmpeg -loglevel warning \
  -f x11grab -framerate "${FPS}" -video_size "${RESOLUTION}" -i ":${DISPLAY_NUM}.0" \
  -c:v h264_nvenc -preset ll -tune ll \
  -b:v "${BITRATE}" -maxrate "${BITRATE}" -bufsize "${BITRATE}" \
  -g "$((FPS * 2))" -bf 0 \
  -f mpegts "udp://${PI_IP}:${STREAM_PORT}" &
FFMPEG_PID=$!

echo ""
echo "  ┌──────────────────────────────────────────────┐"
echo "  │         PiStation Dashboard Stream            │"
echo "  ├──────────────────────────────────────────────┤"
echo "  │  Host IP   : ${HOST_IP}"
echo "  │  Virtual    : :${DISPLAY_NUM} (${RESOLUTION} @ ${FPS}fps)"
echo "  │  Encoder    : h264_nvenc @ ${BITRATE}"
echo "  │  Stream     : udp://${PI_IP}:${STREAM_PORT}"
echo "  ├──────────────────────────────────────────────┤"
echo "  │  Pi command:                                  │"
echo "  │  mpv udp://0.0.0.0:${STREAM_PORT} --no-cache \\"
echo "  │      --profile=low-latency --fs --no-osc      │"
echo "  ├──────────────────────────────────────────────┤"
echo "  │  Press Ctrl+C to stop.                        │"
echo "  └──────────────────────────────────────────────┘"
echo ""

wait
