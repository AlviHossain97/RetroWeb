# Bastion Tower Defence

A grid-based tower defence for the Game Boy Advance. Place towers on a
tile map; waves of enemies path-find from spawn points to the player's
base. Resource economy, multiple tower types and upgrades, escalating
wave difficulty including boss waves.

| Property | Value |
|---|---|
| Platform | Game Boy Advance |
| Runs on | RetroArch `lr-mgba` core (Pi-side) |
| GBA build engine | [Butano](https://github.com/GValiente/butano) (C++23 GBA engine) |
| Prototype language | Python + SDL2 (initial), then C++ + SDL2 (mid-stage) |
| Shipped ROMs | [`src_cpp/gba_project/BastionTD.gba`](src_cpp/gba_project/BastionTD.gba) — 506 KB · [`src_cpp/gba_project/BastionTD_fixed.gba`](src_cpp/gba_project/BastionTD_fixed.gba) — 202 KB (release) |
| Status | Built, runnable on hardware |

---

## Folder layout

```
BastionTD/
├── README.md                       (this file)
├── setup.md                        Build setup — toolchain + third-party deps
├── assets/
│   ├── assets/                     Source-of-truth sprite sheets (PNG)
│   ├── audio/                      Source-of-truth audio (WAV)
│   └── extracted/                  Per-sprite extracted tiles (build-pipeline output)
├── docs/                           Design notes, sprint plans, specs
├── src_cpp/                        C++ implementation (desktop simulator + GBA target)
│   ├── CMakeLists.txt              Desktop simulator build (SDL2)
│   ├── main.cpp                    Desktop entry point
│   ├── core/                       Engine-agnostic simulation
│   │   ├── grid.cpp / pathfinding.cpp
│   │   ├── economy.cpp / wave_manager.cpp
│   │   ├── enemy.cpp / tower.cpp / projectile.cpp
│   │   ├── map_generator.cpp / save_manager.cpp
│   │   └── effects.cpp / game.cpp
│   ├── states/                     Game-state machine (menu, build, combat, game-over, …)
│   ├── hal/                        Hardware-abstraction layer (desktop ↔ GBA)
│   ├── tests/                      Unit tests for the simulation core
│   └── gba_project/                GBA target — Butano build
│       ├── Makefile                Butano build entry point
│       ├── src/                    GBA renderer + SRAM-backed save manager
│       ├── include/
│       ├── graphics/               Butano-format graphics
│       ├── audio/, dmg_audio/      Butano-format audio
│       ├── tools/convert_assets.py
│       ├── BastionTD.gba           Shipped ROM (debug build)
│       └── BastionTD_fixed.gba     Shipped ROM (release / "fixed" build)
└── src_python/                     Original Python prototype (pygame)
    ├── main.py
    ├── grid.py / pathfinding.py
    ├── economy.py / wave_manager.py
    ├── enemy.py / tower.py / projectile.py
    ├── map_generator.py / save_manager.py / effects.py
    ├── asset_manager.py / audio_manager.py
    ├── input_handler.py / hud.py
    ├── states/                     Game-state machine (mirrors src_cpp/states/)
    └── scripts/                    Author-side utilities
```

---

## Prototyping pipeline

Bastion is the most fully-developed of the three games in terms of
prototyping stages:

```
Python prototype (pygame)            ← gameplay design iteration
        ↓
C++ desktop simulator (SDL2)         ← cross-platform port to validate the design under typed code
        ↓
GBA target (Butano, C++23)           ← shipped artefact, runs on the Pi
```

The Python and C++ implementations are deliberately structurally
parallel: `src_python/grid.py` ↔ `src_cpp/core/grid.cpp`,
`src_python/pathfinding.py` ↔ `src_cpp/core/pathfinding.cpp`, and so
on. This made the Python → C++ rewrite a directed translation rather
than a redesign.

The Butano-based GBA build sits on top of `src_cpp/core/` via the
hardware-abstraction layer in `src_cpp/hal/`: the simulation core is
identical between desktop and GBA, and only the renderer and input
plumbing differ.

---

## Build

See [setup.md](setup.md) for the full build prerequisites — Bastion
has the most involved toolchain of the three games (Butano + devkitARM
+ CMake + SDL2 + a Python asset-baking step).

### GBA ROM (the artefact)

```bash
cd src_cpp/gba_project
make
```

Output: `BastionTD.gba`.

### Desktop simulator (development convenience, not the artefact)

```bash
cd src_cpp
cmake -B build
cmake --build build
ctest --test-dir build      # runs core unit tests (combat, economy, pathfinding)
```

The simulator is a development tool: it lets the same C++ simulation
code run on the laptop with SDL2 graphics so design changes can be
unit-tested without round-tripping through GBA hardware.

### Python prototype

```bash
cd src_python
python main.py
```

---

## Asset attribution

Bastion's assets are a **mix of project-original and licensed
open-source** material. The marker can verify each asset's provenance
in the table below.

**TODO: the project author should fill in the table below before submission**
with the licence and source for every non-original asset. The structure
below is the audit trail the marker expects to see.

### Sprites (`assets/assets/*.png`)

| File | Origin | Source / URL | Licence |
|---|---|---|---|
| `characters.png` | *e.g.* original pixel art | — | original work |
| `mock.png` | *e.g.* placeholder / test asset | — | original work |
| `props.png` | *e.g.* derived from Kenney.nl Tower Defence Top Down pack | https://kenney.nl/assets/tower-defense-top-down | CC0 |
| `tileset1.png` | … | … | … |
| `towers.png` | … | … | … |
| `ui.png` | … | … | … |

### Audio (`assets/audio/*.wav`)

| File | Origin | Source / URL | Licence |
|---|---|---|---|
| `bgm_title.wav` | … | … | … |
| `bgm_build.wav` | … | … | … |
| `bgm_wave.wav` | … | … | … |
| `bgm_boss.wav` | … | … | … |
| `shoot.wav`, `hit.wav`, `place.wav`, `sell.wav`, `upgrade.wav` | … | … | … |
| `enemy_death.wav`, `boss_spawn.wav`, `base_hit.wav` | … | … | … |
| `victory.wav`, `game_over.wav`, `wave_start.wav`, `wave_clear.wav`, `menu_move.wav`, `menu_select.wav` | … | … | … |

### Open-source asset bundles likely used

If the project pulled from any of these, attribution lines must
explicitly say so:

- **Kenney.nl** assets — CC0; attribution appreciated but not required by the licence
- **OpenGameArt** assets — varies (CC0, CC-BY, GPL); attribution required for non-CC0
- **Freesound.org** clips — varies per upload; attribution required for CC-BY

Any asset that does not have a clear, attributable licence must be
removed and replaced before submission.
