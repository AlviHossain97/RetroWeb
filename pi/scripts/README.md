# Pi-side scripts — captured 2026-04-25

These files were pulled off the Pi (`192.168.1.212`, hostname `retropie`,
RetroPie 4.8 on Raspbian Buster) so the marker can read them alongside
the rest of the artefact. The actual deployed copies live at the OS-defined
locations on the Pi; this directory is a **snapshot**, not a deployment
source.

## Inventory

| File here | Source on Pi | Notes |
|---|---|---|
| [`runcommand-onstart.sh`](runcommand-onstart.sh) | `/opt/retropie/configs/all/runcommand-onstart.sh` | Logs to `/tmp/pistation_hook.log`, then invokes `session_logger.py` with `PISTATION_MODE=start`. |
| [`runcommand-onend.sh`](runcommand-onend.sh) | `/opt/retropie/configs/all/runcommand-onend.sh` | Same shape, with `PISTATION_MODE=end`. |
| [`session_logger.py`](session_logger.py) | `/home/pi/pistation/session_logger.py` | The actual session POST logic. POSTs to `http://alvi-OMEN-Laptop-15-en1xxx.local:8000/session/start` and `/session/end`. State persisted in `/tmp/pistation_session.json`. Includes auto-close logic for stale orphaned sessions. |
| [`pistation_api.py`](pistation_api.py) | `/home/pi/pistation/pistation_api.py` | A separate FastAPI service — appears to be an earlier Pi-local iteration of the session-ingest API (with its own MySQL on the Pi). Superseded in production by the laptop-side `backend/app/routes/session_routes.py`. **Database password redacted** from the captured copy (see line 11). Kept in this snapshot as a record of the earlier architecture. |
| [`Jellyfin.sh`](Jellyfin.sh) | `/home/pi/RetroPie/roms/jellyfin/Jellyfin.sh` | Loop 2 launcher. Splash → `xinit + openbox` on VT8 → Kodi-standalone (or Chromium-kiosk fallback). **Replaced 2026-04-25** with a clean-exit version; cleanup trap on `EXIT/INT/TERM/HUP` kills X / openbox / Kodi, deallocates VT8, switches back to ES on VT1, and sends `SIGCONT` to ES in case it was paused. The previous version sometimes left the Pi stuck and required a power-cycle. |
| [`RetroWeb.sh.retropiemenu`](RetroWeb.sh.retropiemenu) | `/home/pi/RetroPie/retropiemenu/RetroWeb.sh` | Loop 3 launcher in the RetroPie system menu. Resolves the laptop's hostname, then `xinit` + `matchbox-window-manager` + `moonlight-qt` at 720p30 / 8 Mbps / H.264 / software-decoded. Sunshine app name on the laptop is `"PiStation"`. Accessed by selecting the RetroPie system inside ES, then "RetroWeb" from the menu. |
| [`fstab.full`](fstab.full) | `/etc/fstab` | The Pi's full fstab as captured. Contains no CIFS/SMB mount yet — see `setup-cifs-mount-pi.sh` below. |
| [`es_systems.cfg.system`](es_systems.cfg.system) | `/etc/emulationstation/es_systems.cfg` | The pristine system-level EmulationStation system definitions (root-owned, RetroPie default + Jellyfin entry). Snapshot for reference. |
| [`rom-launch-scripts.txt`](rom-launch-scripts.txt) | `~/RetroPie/roms/*/+Start *.sh` and `~/RetroPie/roms/jellyfin/Jellyfin.sh` (pre-replacement) | Concatenation of all launcher shell scripts found on the Pi at capture time. Mostly RetroPie's standard "ports" launchers. |
| [`setup-samba-laptop.sh`](setup-samba-laptop.sh) | n/a — runs on the **laptop** | Idempotent setup script. Installs Samba, creates `~/PiStation-share/games/gba/`, copies the four GBA ROMs into it, appends a `[pistation]` share definition to `/etc/samba/smb.conf`, restarts smbd. Run with `sudo bash pi/scripts/setup-samba-laptop.sh`. |
| [`setup-cifs-mount-pi.sh`](setup-cifs-mount-pi.sh) | n/a — runs on the **Pi** | Companion to the above. Installs cifs-utils (already present on this Pi), prepares `/mnt/laptop`, adds an fstab line, mounts the share, and updates EmulationStation's GBA `<path>` to point at the new mount. The assistant deploys and runs this via SSH after the laptop side is up. |

## Deployment status — as of 2026-04-25

| Component | Status |
|---|---|
| Runcommand hooks (Loop 1) | Operational — POSTing to laptop's `/session/start` and `/session/end`. |
| Three GBA homebrew ROMs (Red Racer, Mythical, BastionTD, BastionTD-fixed) | All four `.gba` files now in `/home/pi/RetroPie/roms/gba/` (they were on the Pi's local SD card at capture time; not yet moved to a Samba mount). |
| Loop 2 launcher (Jellyfin → Kodi/Chromium) | New version with clean-exit cleanup deployed. **Needs user testing** to confirm the power-cycle issue is resolved. |
| Loop 3 launcher (Dashboard / Moonlight) | Reachable from the RetroPie system menu inside EmulationStation as `RetroWeb`. |
| CIFS mount (centralised ROM storage on laptop) | **Pending** — `setup-samba-laptop.sh` needs to be run on the laptop, then `setup-cifs-mount-pi.sh` on the Pi. |
