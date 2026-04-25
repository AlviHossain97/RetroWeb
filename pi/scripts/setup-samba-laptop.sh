#!/usr/bin/env bash
# setup-samba-laptop.sh
#
# Run this on the laptop (the Samba host), with sudo:
#   sudo bash pi/scripts/setup-samba-laptop.sh
#
# Configures Samba to expose ~/PiStation-share read-only over the LAN
# so the Pi can mount it as /mnt/laptop. Idempotent — safe to re-run.
#
# Companion script: pi/scripts/setup-cifs-mount-pi.sh runs on the Pi
# after this has succeeded.

set -euo pipefail

[ "$(id -u)" -eq 0 ] || { echo "Run with sudo:  sudo bash $0" >&2; exit 1; }

LAPTOP_USER="${SUDO_USER:-alvi}"
LAPTOP_HOME=$(getent passwd "$LAPTOP_USER" | cut -d: -f6)
[ -d "$LAPTOP_HOME" ] || { echo "Could not resolve home for $LAPTOP_USER" >&2; exit 1; }

SHARE_DIR="${LAPTOP_HOME}/PiStation-share"
GAMES_DIR="${SHARE_DIR}/games/gba"
REPO_ROOT="${LAPTOP_HOME}/PiStation/PiStation"
SMB_CONF="/etc/samba/smb.conf"
TS=$(date +%Y%m%d-%H%M%S)
SMB_BACKUP="/etc/samba/smb.conf.bak.${TS}"

echo "[1/6] ensuring samba is installed"
if ! dpkg -l samba 2>/dev/null | grep -q '^ii'; then
  apt-get update
  apt-get install -y samba
else
  echo "  samba already installed"
fi

echo "[2/6] preparing share directory at $SHARE_DIR"
mkdir -p "$GAMES_DIR"
chown -R "$LAPTOP_USER:$LAPTOP_USER" "$SHARE_DIR"

echo "[3/6] copying ROMs from $REPO_ROOT"
ROMS=(
  "$REPO_ROOT/games/Red Racer/assets/gba_game/RedRacer_Phys.gba"
  "$REPO_ROOT/games/Mythical/gba_project/Mythical_GBA.gba"
  "$REPO_ROOT/games/BastionTD/src_cpp/gba_project/BastionTD.gba"
  "$REPO_ROOT/games/BastionTD/src_cpp/gba_project/BastionTD_fixed.gba"
)
for src in "${ROMS[@]}"; do
  if [ -f "$src" ]; then
    cp -v "$src" "$GAMES_DIR/"
  else
    echo "  skip (missing): $src"
  fi
done
chown -R "$LAPTOP_USER:$LAPTOP_USER" "$SHARE_DIR"

echo "[4/6] patching $SMB_CONF (adds [pistation] share if absent)"
if grep -q '^\[pistation\]' "$SMB_CONF" 2>/dev/null; then
  echo "  [pistation] block already present — leaving as-is"
else
  cp -v "$SMB_CONF" "$SMB_BACKUP"
  cat >> "$SMB_CONF" <<EOF

# Added by PiStation setup-samba-laptop.sh on ${TS}
[pistation]
   comment = PiStation game ROMs (read-only)
   path = ${SHARE_DIR}
   browseable = yes
   read only = yes
   guest ok = yes
   force user = ${LAPTOP_USER}
   create mask = 0644
   directory mask = 0755
EOF
  echo "  added [pistation] share definition"
fi

echo "[5/6] restarting smbd"
if systemctl is-active --quiet smbd; then
  systemctl restart smbd
else
  systemctl start smbd
fi
systemctl is-active smbd && echo "  smbd active"

echo "[6/6] sanity check (smbclient guest list)"
if command -v smbclient >/dev/null 2>&1; then
  smbclient -N -L //127.0.0.1 2>&1 | grep -E 'pistation|Sharename' || true
  echo "---"
  smbclient -N //127.0.0.1/pistation -c 'ls games/gba' 2>&1 || true
else
  echo "  smbclient not installed; skipping verification"
fi

echo
echo "[done] Samba is up. Tell the assistant 'samba up' and it will"
echo "       configure the Pi-side CIFS mount via SSH."
