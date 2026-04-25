# PiStation — Pi Component

> **Context.** This README covers the **Pi side** of PiStation. The
> system as a whole is a two-host architecture; see the
> [top-level README](../README.md) for the system overview and the
> [laptop component](../laptop/README.md) for the analytics backend,
> dashboard, and local AI services.

The Raspberry Pi 3 is the **physical interaction surface** — it is
plugged into the TV via HDMI, takes input from a USB controller
(8BitDo SN30 Pro), and runs three things:

1. **Native retro emulation** via RetroPie / EmulationStation / RetroArch
2. **Kodi** with the Jellyfin-for-Kodi add-on for media playback
3. **Moonlight** as a thin client receiving the streamed dashboard from
   the laptop's Sunshine

The Pi 3 was deliberately chosen for the role it can do well: native
emulation for older systems and HEVC/H.264 video decode. Anything
GPU-bound (the React 19 dashboard, AI inference, video transcoding)
runs on the laptop and is delivered to the Pi as decoded video.

---

## Table of Contents

- [Hardware](#hardware)
- [Software stack](#software-stack)
- [Loop 1 — Native gaming](#loop-1--native-gaming)
- [Loop 2 — Media via Jellyfin (Kodi-renderer or Chromium-fallback)](#loop-2--media-via-jellyfin-kodi-renderer-or-chromium-fallback)
- [Loop 3 — Dashboard via Moonlight](#loop-3--dashboard-via-moonlight)
- [Setup](#setup)
- [Pi-side scripts](#pi-side-scripts)
- [Troubleshooting](#troubleshooting)

---

## Hardware

| Item | Spec |
|---|---|
| Board | Raspberry Pi 3 Model B (BCM2837, quad-core ARM Cortex-A53 @ 1.2 GHz, VideoCore IV GPU) |
| Memory | 1 GB LPDDR2 |
| Storage | 32 GB microSD (RetroPie image + Kodi cache; ROMs and media stream from the laptop's Samba share) |
| Display | TV via HDMI |
| Input | 8BitDo SN30 Pro USB controller; USB keyboard for setup |
| Network | Wired Ethernet preferred for Sunshine streaming; 5 GHz Wi-Fi acceptable |

The Pi 3 cannot decode 4K video and does not have NVENC. Sunshine on
the laptop encodes at 1080p with H.264 / HEVC at a bitrate the Pi 3
can decode in real time.

---

## Software stack

| Component | Version | Role |
|---|---|---|
| **RetroPie** | 4.8+ on Raspbian/Raspberry Pi OS | Pre-configured retro-gaming image |
| **EmulationStation** | RetroPie default | TV-friendly carousel launcher |
| **RetroArch** | with libretro core ecosystem | Multi-emulator frontend |
| **lr-mgba** | latest | GBA core; runs the three original homebrew titles |
| **lr-snes9x**, **lr-fceumm**, **lr-genesis-plus-gx** | latest | Other systems registered in EmulationStation (used during testing with the open-source GBA test ROM in Nov 2025) |
| **Kodi** | 19.x (Matrix) or later | Media player |
| **Jellyfin for Kodi** | latest | Add-on that connects Kodi to the laptop's Jellyfin server |
| **Moonlight Embedded** | latest | Sunshine/GeForce-Experience-compatible streaming client |
| **cifs-utils** | system | CIFS mount of the laptop's Samba share |

---

## Loop 1 — Native gaming

The Pi runs RetroArch natively. The three original GBA homebrew titles
(Red Racer, Mythical, Bastion Tower Defence — see [../games/](../games/README.md))
are loaded by EmulationStation through the GBA system entry, which is
configured to use `lr-mgba`.

### ROM storage

ROMs do not live on the Pi's SD card. They live on the laptop's Samba
share and are mounted on the Pi at `/mnt/laptop` via CIFS, with
EmulationStation's GBA system pointed at `/mnt/laptop/games/.../*.gba`.

This is a deliberate centralisation choice: one filesystem of
truth (the laptop), backed up alongside everything else, accessible
from any LAN host. The Pi's SD card stays small and replaceable.

### Session capture (runcommand hooks)

RetroPie's `runcommand` system fires shell hooks before and after every
emulator launch:

- **`/opt/retropie/configs/all/runcommand-onstart.sh`** runs *before* RetroArch starts.
  It POSTs to the laptop's FastAPI:

  Both hooks shell out to `/home/pi/pistation/session_logger.py`
  ([captured](scripts/session_logger.py)) which does the actual POST.

  ```
  POST http://alvi-OMEN-Laptop-15-en1xxx.local:8000/session/start
  Content-Type: application/json

  {
    "pi_hostname": "retropie",
    "rom_path": "/home/pi/RetroPie/roms/gba/BastionTD.gba",
    "system_name": "gba",
    "emulator": "retroarch",
    "core": "mgba",
    "started_at": "2026-04-25T16:48:33+00:00"
  }
  ```

  The endpoint inserts a row into the `sessions` table (see
  `backend/app/pistation.sql`) and returns `{session_id: <int>}`.
  `session_logger.py` then writes the assigned `session_id` and the
  start timestamp as JSON to `/tmp/pistation_session.json`, where the
  end hook will pick it up.

- **`/opt/retropie/configs/all/runcommand-onend.sh`** runs *after* RetroArch exits.
  It reads `/tmp/pistation_session.json` and POSTs:

  ```
  POST http://alvi-OMEN-Laptop-15-en1xxx.local:8000/session/end
  Content-Type: application/json

  { "session_id": 42, "ended_at": "2026-04-25T17:00:33+00:00", "duration_seconds": 720 }
  ```

`session_logger.py` also has a stale-session safeguard: on `start`,
if a previous session-state file exists (because `onend` was missed
— e.g. the Pi was power-cycled mid-game), it auto-closes the orphan
before opening the new one. This prevents permanently-open sessions
in the analytics view.

The hooks themselves live on the Pi's filesystem; copies are kept in
[pi/scripts/](scripts/) so the marker can read them — see
[pi/scripts/README.md](scripts/README.md) for the full inventory and
deployment status.

---

## Loop 2 — Media via Jellyfin (Kodi-renderer or Chromium-fallback)

**Jellyfin** is registered as an EmulationStation system entry (not Kodi).
Selecting it from the carousel runs `/home/pi/RetroPie/roms/jellyfin/Jellyfin.sh`,
which does the actual rendering through Kodi (preferred) or a
Chromium kiosk (fallback). Kodi is the *renderer*; Jellyfin is the
ES-visible *system*.

### EmulationStation system entry

From [`pi/scripts/es_systems.cfg.system`](scripts/es_systems.cfg.system):

```xml
<system>
  <name>jellyfin</name>
  <fullname>Jellyfin</fullname>
  <path>/home/pi/RetroPie/roms/jellyfin</path>
  <extension>.sh .SH</extension>
  <command>%ROM%</command>
  <platform>jellyfin</platform>
  <theme>ports</theme>
</system>
```

### Launcher behaviour ([Jellyfin.sh](scripts/Jellyfin.sh))

1. Plays a 3-second MP4 splash (`/home/pi/RetroPie/splashscreens/jellyfin.mp4`) via `omxplayer` — Pi 3's stock hardware video decoder.
2. Forks a fresh X server on TTY8 via `sudo openvt -c 8 -s -w -- xinit ...` so EmulationStation on TTY1 stays untouched.
3. Inside that X session: `openbox-session` window manager + `kodi-standalone` (or, if Kodi isn't installed, `chromium-browser --kiosk` pointing at `http://192.168.1.190:8096`).
4. On exit (whether clean Kodi quit, Ctrl+C, or kill) a `cleanup` trap fires `EXIT/INT/TERM/HUP`: kills Kodi/openbox/X aggressively, deallocates VT8, `chvt`s back to TTY1, and sends `SIGCONT` to EmulationStation in case it was paused. This trap was added 2026-04-25 to fix a regression where exiting Kodi sometimes left the Pi stuck and required a power-cycle.

Inside Kodi, the **Jellyfin for Kodi** add-on is configured to connect
to the Jellyfin server on the laptop (`http://192.168.1.190:8096`).
Library scanning and any transcoding happen on the laptop's GPU; the
Pi's only job is HEVC / H.264 decode for the playback stream.

If Kodi is unavailable, the same launcher falls back to a Chromium
kiosk pointing directly at Jellyfin's web UI. Less polished than Kodi
but keeps Loop 2 working without the add-on stack.

---

## Loop 3 — Dashboard via Moonlight

`moonlight-qt` on the Pi is paired with the Sunshine instance on the
laptop (Sunshine app name: `PiStation`). The launcher script resolves
the laptop's hostname, then `xinit` + `matchbox-window-manager` +
`moonlight-qt` at **720p / 30 fps / 8 Mbps / H.264 / software-decoded**.
Software decode, not hardware: the Pi 3's hardware H.264 path is
unstable on RetroPie 4.8's older kernel, and software decode at
720p30 keeps a steady frame rate within thermal/CPU envelope.

```
Pi                                   Laptop
┌─────────────────┐                  ┌──────────────────────┐
│ moonlight-qt    │ ◀─── video ──────│ Sunshine NVENC       │
│ software H.264  │                  │ captures Chromium    │
│ decoder         │ ──── input ─────▶│ (the dashboard PWA)  │
└─────────────────┘                  └──────────────────────┘
```

The laptop's RTX 3070 NVENC encodes in ~5 ms per frame. End-to-end
Pi-perceived latency on wired Ethernet is well within a frame at
60 Hz on the laptop side; Moonlight on the Pi caps display refresh at
30 Hz to match the encode setting.

The user controls the dashboard with the same 8BitDo controller used
for retro gaming — Moonlight forwards button events to Sunshine, which
delivers them to Chromium as gamepad inputs that the React PWA reads
through the standard Gamepad API.

### Launch path

The dashboard is reached through the **RetroPie system menu** inside
EmulationStation: select the RetroPie system in the carousel, then
the `RetroWeb` entry. That runs
[`~/RetroPie/retropiemenu/RetroWeb.sh`](scripts/RetroWeb.sh.retropiemenu),
which spawns moonlight-qt in an X session as described above. Keeping
the launcher in `retropiemenu/` rather than in a games-carousel
system entry avoids polluting the carousel with a non-game and
matches how RetroPie's own utilities (audio settings, Wi-Fi config,
file manager) are surfaced.

---

## Setup

These steps assume a clean Pi and a laptop already running the laptop
component (see [../laptop/README.md](../laptop/README.md)).

### 1. RetroPie image

Flash the RetroPie SD-image for Pi 3 (Raspberry Pi Imager → Other
specific-purpose OS → Emulation and game OS → RetroPie). Boot, complete
the controller-config wizard, set hostname to `retropie` (or whatever
you point `runcommand-onstart.sh` at).

### 2. CIFS mount of the laptop's Samba share

Two idempotent setup scripts in [`pi/scripts/`](scripts/) handle this:

```bash
# On the laptop (Samba host) — installs samba, creates ~/PiStation-share/,
# copies the four GBA ROMs in, adds a [pistation] share to smb.conf,
# restarts smbd:
sudo bash pi/scripts/setup-samba-laptop.sh

# On the Pi (CIFS client) — installs cifs-utils (already present on
# this Pi), prepares /mnt/laptop, adds an fstab line, mounts the share,
# and updates EmulationStation's GBA <path> tag to point at the mount:
bash pi/scripts/setup-cifs-mount-pi.sh
```

The share is exposed read-only and guest-readable; the LAN is
trusted. After the Pi-side script finishes, EmulationStation needs to
restart (Quit from the Start menu) to pick up the new GBA path.

### 3. Runcommand hooks + session_logger

```bash
sudo cp pi/scripts/runcommand-onstart.sh /opt/retropie/configs/all/
sudo cp pi/scripts/runcommand-onend.sh   /opt/retropie/configs/all/
sudo chmod +x /opt/retropie/configs/all/runcommand-on{start,end}.sh

mkdir -p ~/pistation
cp pi/scripts/session_logger.py ~/pistation/session_logger.py
chmod +x ~/pistation/session_logger.py
# Edit the API_BASE constant at the top to match your laptop's
# reachable hostname or IP.
```

The hooks call `session_logger.py`, which POSTs to
`/session/start` and `/session/end` on the laptop's FastAPI and
persists session state in `/tmp/pistation_session.json`. Hook stdout
goes to `/tmp/pistation_hook.log` for debugging.

### 4. Loop 2 launcher (Jellyfin → Kodi/Chromium)

Kodi is the renderer; Jellyfin is the EmulationStation system entry.
The system is already in `/etc/emulationstation/es_systems.cfg` on
the stock RetroPie image. Drop the launcher in:

```bash
sudo apt install kodi xinit openbox dbus-x11 chromium-browser omxplayer
mkdir -p ~/RetroPie/roms/jellyfin
cp pi/scripts/Jellyfin.sh ~/RetroPie/roms/jellyfin/Jellyfin.sh
chmod +x ~/RetroPie/roms/jellyfin/Jellyfin.sh
```

Reboot or restart EmulationStation, pick Jellyfin from the carousel,
sign in to the Jellyfin server inside Kodi (Add-ons → Jellyfin for Kodi).

### 5. Loop 3 launcher (Dashboard via Moonlight)

```bash
sudo apt install moonlight-qt matchbox-window-manager
# Pair against the laptop's Sunshine (this prints a PIN to enter
# in Sunshine's web UI):
moonlight pair <laptop-hostname>

# Drop the launcher into the RetroPie system menu:
cp pi/scripts/RetroWeb.sh.retropiemenu ~/RetroPie/retropiemenu/RetroWeb.sh
chmod +x ~/RetroPie/retropiemenu/RetroWeb.sh
```

Edit the `HOSTNAME_TARGET` constant at the top of `RetroWeb.sh` to
match your laptop's hostname before launching. Inside ES, select the
RetroPie system in the carousel, then `RetroWeb` from the menu.

---

## Pi-side scripts

The shell scripts and Python modules that implement the Pi side of
the integration live on the Pi's filesystem at the OS-defined
locations. For marker visibility, full copies are kept in
[`scripts/`](scripts/) — see [`scripts/README.md`](scripts/README.md)
for the inventory and current deployment status.

---

## Troubleshooting

<details>
<summary><b>🎮 Sessions aren't appearing in the dashboard after I exit a game</b></summary>

The runcommand hooks may not be wired up.

1. Confirm the hooks are executable: `ls -l /opt/retropie/configs/all/runcommand-on*.sh`
2. Tail the hook log: `tail -f /tmp/pistation_hook.log` while you exit a game — the hook stdout/stderr is captured here.
3. Tail the logger debug log: `tail -f /tmp/pistation_logger_debug.log` — `session_logger.py` writes its own structured trace there, including the actual POST payloads and HTTP responses.
4. Manually probe the laptop endpoint: `curl http://<laptop-host>:8000/health`. If that fails the laptop's FastAPI is down or unreachable.
5. Inspect the state file: `cat /tmp/pistation_session.json` — should be valid JSON with a numeric `session_id`.

</details>

<details>
<summary><b>📂 /mnt/laptop is empty or refuses to mount</b></summary>

1. Laptop's Samba is down: `sudo systemctl status smbd` on the laptop.
2. Laptop hostname (e.g. `alvi-OMEN-Laptop-15-en1xxx.local`) doesn't resolve from the Pi: try the IP. If the IP works, install `avahi-daemon` on both ends or check `nss-mdns` is in the Pi's `/etc/nsswitch.conf` `hosts` line.
3. Share name mismatch: the fstab line must reference `//<laptop-host>/pistation`, matching the `[pistation]` block in the laptop's `/etc/samba/smb.conf`.
4. Protocol version mismatch: Pi 3 with old kernels sometimes needs `vers=2.0` instead of `3.0` in fstab.
5. The setup expects guest read-only access; if the laptop's smb.conf has `map to guest = bad user` configured, ensure `guest ok = yes` is set on the share.

</details>

<details>
<summary><b>🎬 Exiting Kodi from Jellyfin leaves the Pi stuck (have to power-cycle)</b></summary>

This was the old `Jellyfin.sh`'s bug — fixed 2026-04-25 with a
comprehensive cleanup trap. If you still see it after the new
[`Jellyfin.sh`](scripts/Jellyfin.sh) is in place:

1. Confirm the new script is the one running — its first lines should
   contain `"clean-exit version"` and a `cleanup()` function. If it's
   the old one, the backup is at `~/RetroPie/roms/jellyfin/Jellyfin.sh.bak-*`.
2. Tail the launcher log while exiting: `tail -f /tmp/jellyfin.log`.
   You should see `cleanup trapped`, then `cleanup done`. If the trap
   never fires, the script crashed early (see the log for which line).
3. Manually verify the trap's individual steps by running them from
   an SSH shell while in a stuck state: `sudo chvt 1` should bring ES
   back. If it doesn't, X is still holding the framebuffer; run
   `sudo pkill -KILL -x X Xorg xinit` then `sudo deallocvt 8`.

</details>

<details>
<summary><b>📺 Kodi launches but the Jellyfin add-on can't connect</b></summary>

1. Confirm Jellyfin is running on the laptop: `curl http://laptop.local:8096/System/Info/Public`.
2. Check the Pi can reach it: `curl http://laptop.local:8096/...` from the Pi shell.
3. The Jellyfin-for-Kodi add-on logs to `~/.kodi/temp/kodi.log` on the Pi.

</details>

<details>
<summary><b>🖥️ Moonlight connects but the dashboard is laggy or stutters</b></summary>

See the matching section in
[../laptop/README.md#troubleshooting](../laptop/README.md#troubleshooting) —
the symptoms manifest on the Pi but the fixes are mostly on the laptop
(NVENC encoder, bitrate, network).

The Pi-specific check: the deployed `RetroWeb.sh` already runs at
720p30 / 8 Mbps / H.264 / **software-decoded** — these are
conservative settings tuned for the Pi 3. If you raise resolution or
bitrate beyond this, the Pi 3 will drop frames; switch to hardware
decode by replacing `--video-decoder software` in `RetroWeb.sh` only
if you've confirmed the kernel's `bcm2835_v4l2` decoder is stable on
your image.

</details>

<details>
<summary><b>🔥 Pi 3 thermally throttles during long Sunshine sessions</b></summary>

The BCM2837 throttles at 80 °C. A passive heatsink is sufficient for
emulation but Moonlight's continuous H.264/HEVC decode can push it
over with no airflow. Add a fan or drop Moonlight to 720p60 if a fan
is not an option.

</details>
