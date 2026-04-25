#!/usr/bin/env bash
# setup-cifs-mount-pi.sh
#
# Runs on the Pi (the CIFS client). The assistant deploys this via
# SSH after setup-samba-laptop.sh has succeeded on the laptop.
# Idempotent — safe to re-run.
#
# Mounts the laptop's [pistation] share read-only at /mnt/laptop and
# updates EmulationStation's GBA system path to point at it.

set -euo pipefail

LAPTOP_HOST="${LAPTOP_HOST:-alvi-OMEN-Laptop-15-en1xxx.local}"
SHARE_NAME="${SHARE_NAME:-pistation}"
MOUNTPOINT="${MOUNTPOINT:-/mnt/laptop}"
ES_OVERLAY="/opt/retropie/configs/all/emulationstation/es_systems.cfg"

echo "[1/5] ensuring cifs-utils is installed"
if ! dpkg -l cifs-utils 2>/dev/null | grep -q '^ii'; then
  sudo apt-get update
  sudo apt-get install -y cifs-utils
else
  echo "  cifs-utils already installed"
fi

echo "[2/5] preparing $MOUNTPOINT"
sudo mkdir -p "$MOUNTPOINT"

echo "[3/5] adding fstab line for //${LAPTOP_HOST}/${SHARE_NAME}"
FSTAB_LINE="//${LAPTOP_HOST}/${SHARE_NAME} ${MOUNTPOINT} cifs guest,ro,uid=pi,gid=pi,iocharset=utf8,vers=3.0,_netdev,nofail,x-systemd.automount 0 0"
if grep -qF "//${LAPTOP_HOST}/${SHARE_NAME}" /etc/fstab; then
  echo "  fstab already has a line for this share — leaving as-is"
else
  echo "$FSTAB_LINE" | sudo tee -a /etc/fstab >/dev/null
  echo "  appended"
fi

echo "[4/5] mounting (or remounting)"
sudo systemctl daemon-reload
if mountpoint -q "$MOUNTPOINT"; then
  sudo umount "$MOUNTPOINT" 2>/dev/null || true
fi
sudo mount -a
mountpoint -q "$MOUNTPOINT" && {
  echo "  $MOUNTPOINT mounted; contents:"
  ls -la "$MOUNTPOINT" 2>&1 | head -10 | sed 's/^/    /'
} || {
  echo "  WARN: mount did not succeed; check 'dmesg | tail' on the Pi" >&2
  exit 1
}

echo "[5/5] pointing EmulationStation's GBA system at the share"
if [ -f "$ES_OVERLAY" ]; then
  sudo sed -i \
    -e 's|<path>/home/pi/RetroPie/roms/gba</path>|<path>'"$MOUNTPOINT"'/games/gba</path>|g' \
    "$ES_OVERLAY"
  if grep -q "<path>${MOUNTPOINT}/games/gba</path>" "$ES_OVERLAY"; then
    echo "  GBA path now points at ${MOUNTPOINT}/games/gba"
  else
    echo "  WARN: GBA <path> tag not updated; inspect $ES_OVERLAY manually" >&2
  fi
else
  echo "  $ES_OVERLAY missing; cannot update GBA path" >&2
fi

echo
echo "[done] CIFS mount is live. Restart EmulationStation"
echo "       (Quit ES from the Start menu) to pick up the new GBA path."
