# Red Racer

A top-down endless-runner racing game for the Game Boy Advance.
Dodge oncoming traffic, collect fuel and nitro pickups, time your
overtakes, and survive as long as possible. Difficulty ramps with
distance.

| Property | Value |
|---|---|
| Platform | Game Boy Advance |
| Runs on | RetroArch `lr-mgba` core (Pi-side) |
| GBA build language | C |
| Prototype language | Python (pygame) |
| Shipped ROM | [`assets/gba_game/RedRacer_Phys.gba`](assets/gba_game/RedRacer_Phys.gba) — 193 KB |
| Approximate ROM size | 200 KB |
| Status | Built, runnable on hardware, in active session log |

---

## Folder layout

```
Red Racer/
├── README.md                       (this file)
├── assets/
│   ├── gba_game/
│   │   ├── RedRacer_Phys.gba       Shipped ROM — what the marker plays
│   │   └── ...                     Sprite sheets, palette dumps, audio used by the GBA build
│   └── python_game/
│       └── README.md               Prototype reference assets withheld; see notes below
├── gba_project/
│   ├── main.c                      GBA entry point + game loop
│   ├── gba.h                       GBA hardware definitions (registers, palette, sprite control)
│   ├── assets.h                    Embedded sprite tile / palette data (generated)
│   ├── Makefile                    devkitARM build
│   ├── README.md                   Build-specific notes
│   └── docs/                       Design notes for the GBA port
└── src/
    ├── python_game/                Original Python prototype (pygame)
    │   ├── main.py
    │   ├── cars.py / traffic.py / roads.py / sprites.py
    │   ├── ai_driver.py / modes.py / missions.py
    │   ├── achievements.py / save_system.py / settings.py
    │   ├── systems.py / utils.py / ui.py
    │   └── check_dims.py
    └── gba_game/                   C source mirrored from the prototype design (per-system files)
```

---

## Prototyping pipeline

Red Racer was the first game in the project's
[Python-to-GBA-native pipeline](../README.md#the-python-to-gba-native-prototyping-pattern).

The Python prototype in [`src/python_game/`](src/python_game/) explored
gameplay design with no constraints: lane logic, fuel/nitro/repair
pickups, AI traffic patterns, mission progression, achievements, save
files. Once the design was locked, the gameplay was rewritten as
GBA-native C in [`gba_project/main.c`](gba_project/main.c) under the
GBA's hard constraints (240×160 framebuffer, no FPU, no dynamic
allocation in hot paths, fixed-point math, sprite-tile memory layout).

The two implementations share **no source**. What carries across is
the design.

---

## Build

The shipped `.gba` ROM is committed and is what the Pi actually loads;
rebuilding is optional.

```bash
# Install devkitARM (one-off, system-wide)
# https://devkitpro.org/wiki/Getting_Started

cd gba_project
make
```

Output: a `RedRacer.gba` in `gba_project/`. Copy or symlink it to the
ROM directory the Pi's EmulationStation watches.

---

## Asset attribution

This is where Red Racer's situation is most delicate and is treated
honestly here rather than waved away.

### GBA-build assets (`assets/gba_game/`)

Sprite sheets and palettes baked into `assets.h` are embedded directly
in the ROM via the build pipeline. **TODO: enumerate the source of each
sprite sheet and audio sample, with a per-asset licence line.** The
project author should fill in the table below before submission:

| Asset | File(s) | Source | Licence |
|---|---|---|---|
| Player car | *e.g.* `assets/gba_game/player.bmp` | *e.g.* original pixel art by project author | *e.g.* original work — all rights retained |
| Traffic cars | …  | … | … |
| Road / background | … | … | … |
| Pickups (fuel, nitro, repair) | … | … | … |
| Audio (engine, crash, pickup, BGM) | … | … | … |

If any sprite sheet or audio sample was sourced from
**Kenney.nl** (CC0), **OpenGameArt** (CC0 / CC-BY / GPL — varies),
**itch.io** (per-author), or another source, the relevant licence
text or attribution line must be added to this table.

### Python-prototype assets (`assets/python_game/`)

The original Python prototype used third-party reference imagery and
audio (branded car PNGs, manufacturer-named sprites, ripped soundtrack
audio). **Those assets are not part of the project's IP and have been
removed from the repository.** A placeholder
[`assets/python_game/README.md`](assets/python_game/README.md) explains
the situation in-place; the original files are kept only on the
development machine in the build cache and are not redistributed.

The prototype's Python source code references the original asset
filenames; running the Python prototype against the current repository
state will hit `FileNotFoundError`. The Python sources are committed
as a record of the prototyping pipeline (the pygame architecture, AI
driver logic, mission system) — they are not a runnable artefact in
this snapshot. The runnable artefact for Red Racer is the GBA ROM.
