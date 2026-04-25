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
| [`RetroWeb.sh.retropiemenu`](RetroWeb.sh.retropiemenu) | `/home/pi/RetroPie/retropiemenu/RetroWeb.sh` | The dashboard launcher. Resolves the laptop's hostname, then `xinit` + `matchbox-window-manager` + `moonlight-qt` at 720p30 / 8 Mbps / H.264 / software-decoded. Sunshine app name on the laptop is `"PiStation"`. **Note:** lives in `retropiemenu/`, not under an EmulationStation `roms/` system entry. |
| [`fstab.full`](fstab.full) | `/etc/fstab` | The Pi's full fstab. **Contains no CIFS/SMB mount line** — see "Findings" below. |
| [`es_systems.cfg.system`](es_systems.cfg.system) | `/etc/emulationstation/es_systems.cfg` | The EmulationStation system definitions. The Pi has **no `/opt/retropie/configs/all/emulationstation/es_systems.cfg` overlay**, so this file is the source of truth for which systems appear in the carousel. |
| [`rom-launch-scripts.txt`](rom-launch-scripts.txt) | `~/RetroPie/roms/*/+Start *.sh` and `~/RetroPie/roms/jellyfin/Jellyfin.sh` | All ES launcher shell scripts found on the Pi. Most are RetroPie's standard "ports" launchers (Amiga, ZX Spectrum, DOSBox, ScummVM, Reicast). The notable custom one is `Jellyfin.sh`. |

## Findings — Pi reality vs. project documentation

These were uncovered while capturing and are **not yet reflected in the
parent `pi/README.md` or the top-level `README.md`**:

1. **No CIFS / Samba mount.** `/etc/fstab` contains only the standard Pi defaults (`/`, `/boot`, `proc`); `mount` shows no CIFS/SMB filesystems active; no systemd `.mount` units, autofs, rc.local, or shell-rc fragments mount one. The shipped GBA homebrew lives on the Pi's local SD card at `/home/pi/RetroPie/roms/gba/RedRacer_Phys.gba`. The "centralised storage on the laptop's Samba share" architecture described in the docs is not currently deployed.
2. **Only Red Racer is on the Pi.** `find` for "Mythical" and "Bastion" returned nothing under `~/RetroPie/roms/`. The other two GBA homebrew titles in the corpus are built but not yet copied across.
3. **Loop 2 is Jellyfin-as-ES-system, not Kodi-as-ES-system.** EmulationStation's system entry is `<name>jellyfin</name>` with `path=/home/pi/RetroPie/roms/jellyfin`. The launcher (`Jellyfin.sh`) switches to TTY8, runs `xinit` + `openbox`, and **then** runs Kodi-standalone (which has the Jellyfin-for-Kodi add-on configured) or falls back to a Chromium kiosk pointing at `http://192.168.1.190:8096`. Kodi is the *renderer*, not the ES system entry.
4. **Loop 3 is launched from the RetroPie system menu, not the games carousel.** The dashboard launcher (`RetroWeb.sh`) lives in `~/RetroPie/retropiemenu/`, accessed via the RetroPie menu inside ES. There is no `roms/dashboard/` ES system entry.
5. **The Moonlight binary in use is `moonlight-qt`, not `moonlight-embedded`.** Different package, different command-line interface.
6. **Endpoint paths.** The runcommand session ingest is `POST /session/start` and `POST /session/end` (both POSTs), not `POST /api/v1/sessions` and `PATCH /api/v1/sessions/{id}` as documented in the parent `pi/README.md`. The state file is JSON in `/tmp/pistation_session.json`, not the plaintext `/tmp/pistation_session_id` described.

These divergences need to be reconciled before submission — either by
deploying the missing pieces on the Pi or by correcting the
documentation. See the project root for the active docs that need
revising.
