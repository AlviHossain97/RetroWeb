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
- [Loop 2 — Media via Kodi + Jellyfin](#loop-2--media-via-kodi--jellyfin)
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

  ```
  POST http://laptop.local:8000/api/v1/sessions
  Content-Type: application/json

  {
    "rom_path": "/mnt/laptop/games/BastionTD/.../BastionTD.gba",
    "system": "gba",
    "emulator": "retroarch",
    "core": "mgba",
    "pi_hostname": "retropie",
    "started_at": "2026-04-25T16:48:33Z"
  }
  ```

  The endpoint inserts a row into the `sessions` table (see
  `backend/app/pistation.sql`) and returns the new `session_id`,
  which the hook stashes in `/tmp/pistation_session_id`.

- **`/opt/retropie/configs/all/runcommand-onend.sh`** runs *after* RetroArch exits.
  It reads the stashed `session_id` and PATCHes:

  ```
  PATCH http://laptop.local:8000/api/v1/sessions/{id}
  Content-Type: application/json

  { "ended_at": "2026-04-25T17:00:33Z", "duration_seconds": 720 }
  ```

The hooks themselves live on the Pi's filesystem and are reproduced
in [pi/scripts/](scripts/) for marker visibility — see
[pi/scripts/README.md](scripts/README.md) for what is expected to be
in there.

---

## Loop 2 — Media via Kodi + Jellyfin

Kodi is registered as an EmulationStation **system** (not a port), so
it appears in the same carousel as GBA, SNES, etc. Picking it launches
Kodi fullscreen.

### EmulationStation system entry

The relevant section of `/etc/emulationstation/es_systems.cfg` (or the
overlay in `/opt/retropie/configs/all/emulationstation/es_systems.cfg`):

```xml
<system>
  <name>kodi</name>
  <fullname>Kodi Media Centre</fullname>
  <path>/home/pi/RetroPie/roms/kodi</path>
  <extension>.sh</extension>
  <command>kodi-standalone</command>
  <platform>kodi</platform>
  <theme>kodi</theme>
</system>
```

A placeholder `.sh` file under `roms/kodi/` provides the launcher
target so EmulationStation thinks Kodi is "a game it can launch".

### Jellyfin connection

Inside Kodi:

1. **Add-ons → Install from repository → Jellyfin for Kodi**
2. Sign in to the Jellyfin server running on the laptop (default `http://laptop.local:8096`)
3. Pick the libraries to sync; the add-on writes Kodi-native metadata
   so the Pi's library browser is fast even though the actual files are
   on the laptop.

Streaming and any transcoding happen on the laptop's GPU. The Pi's
job is HEVC / H.264 hardware decode, which the BCM2837 handles fine
at 1080p.

---

## Loop 3 — Dashboard via Moonlight

Moonlight Embedded on the Pi is paired with the Sunshine instance
running on the laptop. A "Dashboard" launcher (also exposed as an ES
system entry) starts Moonlight, which connects to Sunshine and
displays the laptop's fullscreen Chromium window — the React 19 PWA —
on the TV.

```
Pi                          Laptop
┌──────────────┐           ┌──────────────────────┐
│ Moonlight    │ ◀─ video ─│ Sunshine NVENC       │
│ (decode)     │           │ captures Chromium    │
│              │ ── input ▶│ (the dashboard PWA)  │
└──────────────┘           └──────────────────────┘
```

Latency end-to-end is dominated by encode + network; the laptop's
RTX 3070 NVENC encodes in ~5 ms per frame. On wired Ethernet the
total Pi-perceived latency is below one frame at 60 Hz.

The user controls the dashboard with the same 8BitDo controller used
for retro gaming — Moonlight forwards button events to Sunshine, which
delivers them to Chromium as gamepad inputs that the React PWA reads
through the standard Gamepad API.

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

On the laptop, share `/path/to/games` and `/path/to/media` via Samba
(`/etc/samba/smb.conf`). On the Pi:

```bash
sudo apt install cifs-utils
sudo mkdir -p /mnt/laptop
echo "//laptop.local/games /mnt/laptop cifs credentials=/etc/samba/creds,uid=pi,gid=pi,iocharset=utf8,vers=3.0 0 0" | sudo tee -a /etc/fstab
sudo mount -a
ls /mnt/laptop   # should list the laptop's shared games + media
```

### 3. Point EmulationStation's GBA system at the share

Edit the GBA `path` in `/opt/retropie/configs/all/emulationstation/es_systems.cfg`:

```xml
<path>/mnt/laptop/games</path>
```

(Or symlink `~/RetroPie/roms/gba` to `/mnt/laptop/games/...` if you
want the rest of the RetroPie default layout intact.)

### 4. Drop the runcommand hooks in place

Copy `pi/scripts/runcommand-onstart.sh` and
`pi/scripts/runcommand-onend.sh` from this repo to
`/opt/retropie/configs/all/` on the Pi. Make them executable
(`chmod +x`). Edit the `LAPTOP_URL` variable at the top to match your
laptop's reachable address.

### 5. Kodi + Jellyfin

```bash
sudo apt install kodi
mkdir -p ~/RetroPie/roms/kodi
echo "kodi-standalone" > ~/RetroPie/roms/kodi/launch.sh
chmod +x ~/RetroPie/roms/kodi/launch.sh
```

Reboot, pick Kodi from the ES carousel, install **Jellyfin for Kodi**
from the Kodi add-on repository, and sign in to the laptop's Jellyfin
server.

### 6. Moonlight + Sunshine pairing

Install Moonlight Embedded on the Pi (`sudo apt install moonlight-embedded`).
Pair against the laptop's Sunshine (`moonlight pair laptop.local`,
enter the PIN shown in Sunshine's web UI on the laptop).

Add a Dashboard launcher under EmulationStation:

```bash
mkdir -p ~/RetroPie/roms/dashboard
cat > ~/RetroPie/roms/dashboard/launch.sh <<'EOF'
#!/usr/bin/env bash
moonlight stream laptop.local Desktop
EOF
chmod +x ~/RetroPie/roms/dashboard/launch.sh
```

Add a `dashboard` system entry to `es_systems.cfg` mirroring the Kodi
one above. Reboot ES.

---

## Pi-side scripts

The shell scripts that implement the Pi side of the integration live on
the Pi's filesystem at the OS-defined locations
(`/opt/retropie/configs/all/`, `/etc/fstab`, `/etc/samba/`). For marker
visibility, copies are kept in [scripts/](scripts/):

- `runcommand-onstart.sh` — POSTs session start to FastAPI
- `runcommand-onend.sh` — PATCHes session end to FastAPI
- `es_systems.cfg.fragment` — the Kodi + dashboard ES system entries
- `fstab.fragment` — the CIFS mount line
- `smb.conf.laptop-side` — the laptop's Samba share definition (lives on the laptop, kept here for completeness)

See [scripts/README.md](scripts/README.md) for status of which scripts
have been captured into the repo.

---

## Troubleshooting

<details>
<summary><b>🎮 Sessions aren't appearing in the dashboard after I exit a game</b></summary>

The runcommand hooks may not be wired up.

1. Confirm the hooks are executable: `ls -l /opt/retropie/configs/all/runcommand-on*.sh`
2. Manually POST to the laptop to confirm the endpoint is reachable:
   `curl -X POST http://laptop.local:8000/api/v1/sessions/health`
3. Check `journalctl -u retropie-runcommand` (RetroPie logs hook output here on most installs).
4. Run a game from the command line with verbose output:
   `runcommand 0 _SYS_ gba "/mnt/laptop/games/.../RedRacer_Phys.gba" 2>&1 | tee /tmp/rc.log`

</details>

<details>
<summary><b>📂 /mnt/laptop is empty or refuses to mount</b></summary>

1. Laptop's Samba is down: `sudo systemctl status smbd` on the laptop.
2. Hostname `laptop.local` doesn't resolve: try the IP. If it works
   with the IP, install `avahi-daemon` on both ends.
3. Credentials wrong: check `/etc/samba/creds` on the Pi (`username=...`
   and `password=...` lines).
4. Protocol version mismatch: Pi 3 with old kernels sometimes needs
   `vers=2.0` instead of `3.0` in fstab.

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

The Pi-specific check: drop bitrate in Moonlight Embedded settings.
On Pi 3, start at 10 Mbit/s 1080p30 and raise from there.

</details>

<details>
<summary><b>🔥 Pi 3 thermally throttles during long Sunshine sessions</b></summary>

The BCM2837 throttles at 80 °C. A passive heatsink is sufficient for
emulation but Moonlight's continuous H.264/HEVC decode can push it
over with no airflow. Add a fan or drop Moonlight to 720p60 if a fan
is not an option.

</details>
