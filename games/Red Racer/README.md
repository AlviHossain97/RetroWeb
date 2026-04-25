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

## Asset Attribution

### Visual assets

The 14 car sprite sets baked into [`gba_project/assets.h`](gba_project/assets.h)
(`car_<name>_normal/left/right`, 192 × `u16` each, 16×24 at 8bpp) are
sourced from **TMD Studios** — [Cars](https://tmd-studios.itch.io/cars)
on itch.io.

**Licence**, per the creator's stated terms:

> "Feel free to use them in any of your projects (with or without
> modifications). I just ask that you link to my website
> tmdstudios.wordpress.com"
> — TMD Studios

Credit links:

- **Asset page**: <https://tmd-studios.itch.io/cars>
- **Creator website** (linked per licence): <https://tmdstudios.wordpress.com>

The sprites are used as-supplied without modification; the
build pipeline (`src/gba_game/convert_assets.py` →
`src/gba_game/dump_c.py`) only re-encodes them into 8bpp paletted
GBA tile format and bakes them as C arrays into `assets.h`.

### Car names

The display names and identifier symbols for the 14 cars in the C
source are project-original (Felucia, Suprex, Aurion, Corveda, Lotrix,
P11, Astor, Merren, Vyrex, Lumbra, Marlon, Zondra, CXR, Vexa).
They are deliberately not real-world car brands — to avoid any
trademark question independent of the visual asset licence — see
[`ASSET_NOTICE.md`](ASSET_NOTICE.md).

### Audio

The shipped GBA build is silent. The Python prototype's audio plumbing
(via `pygame.mixer`) remains in `src/python_game/main.py` as documented
engineering work but its source media files were removed during the IP
cleanup pass — see [`ASSET_NOTICE.md`](ASSET_NOTICE.md). This aligns
with the corpus-wide silent-audio policy across all three PiStation
original games.

### Code

Project-original. C, GBA-native, ported from an earlier Python
(pygame) prototype. The two implementations share no source — only
the gameplay design carries across.

The Python prototype's source is committed as a record of the
prototyping pipeline (gameplay design iteration in
`src/python_game/`); running it directly against the current
repository state will hit `FileNotFoundError` because the prototype's
reference media are not distributed. The runnable artefact for Red
Racer is the GBA ROM.
