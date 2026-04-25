# Pi-side scripts

The actual scripts in this directory are **expected to be copied off
the Pi** and committed here so that a marker cloning the repository
can read them alongside everything else.

The scripts themselves live on the Pi's filesystem at OS-defined
locations and are *not* deployed from this directory — they are
captured here for review, not for deployment.

## What should live in this directory

| File | Source on the Pi | Purpose |
|---|---|---|
| `runcommand-onstart.sh` | `/opt/retropie/configs/all/runcommand-onstart.sh` | POSTs session-start metadata to the laptop's FastAPI |
| `runcommand-onend.sh` | `/opt/retropie/configs/all/runcommand-onend.sh` | PATCHes session-end (ended_at, duration_seconds) |
| `es_systems.cfg.fragment` | `/opt/retropie/configs/all/emulationstation/es_systems.cfg` | The Kodi + Dashboard `<system>` entries |
| `fstab.fragment` | `/etc/fstab` | The `/mnt/laptop` CIFS mount line |
| `smb.conf.laptop-side` | `/etc/samba/smb.conf` *on the laptop* | The Samba share definition — kept here for completeness |

## How to capture them

From a workstation that can reach the Pi via SSH:

```bash
mkdir -p pi/scripts
scp pi@retropie.local:/opt/retropie/configs/all/runcommand-onstart.sh pi/scripts/
scp pi@retropie.local:/opt/retropie/configs/all/runcommand-onend.sh pi/scripts/
scp pi@retropie.local:/etc/fstab pi/scripts/fstab.fragment
ssh pi@retropie.local 'cat /opt/retropie/configs/all/emulationstation/es_systems.cfg' \
    > pi/scripts/es_systems.cfg.fragment
# laptop-side:
sudo cat /etc/samba/smb.conf | tee pi/scripts/smb.conf.laptop-side
```

After capturing, redact any embedded credentials before committing
(check `fstab.fragment` for `credentials=` paths and the actual
credentials file; check `smb.conf.laptop-side` for `valid users`,
`hosts allow` entries). The scripts as captured may contain the
laptop's actual hostname/IP — that's fine for documentation purposes.
