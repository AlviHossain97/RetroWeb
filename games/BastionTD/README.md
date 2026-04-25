# Bastion Tower Defence

*Tower defence game for the Game Boy Advance. Built using the Butano
framework on devkitARM.*

**Visual assets**: [Tiny Tower Defense Assets](https://ilustramundogames.itch.io/tiny-tower-defense-assets)
by **pixel.iwao** (ilustramundogames). Free for personal and commercial
use with creator credit — per the creator's confirmed reply on the
asset's itch.io page.

---

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

## Asset Attribution

### Visual assets

Sourced from itch.io: [Tiny Tower Defense Assets](https://ilustramundogames.itch.io/tiny-tower-defense-assets)
by **pixel.iwao** (ilustramundogames).

**Licence**: Free for personal and commercial use with creator credit
required. The creator confirmed this directly on the asset's itch.io
page in response to a community licence enquiry:

> "Hello! free for personal and commercial use if you add creator
> credits: pixel.iwao"
> — Ilustra Mundo Games, [itch.io community reply](https://ilustramundogames.itch.io/tiny-tower-defense-assets)

Credit is given:

1. At the top of this README
2. In the cross-game [`games/README.md`](../README.md) summary table
3. In the GBA build's credits surface — *credits screen pending
   integration; flagged as a follow-up task*

**Modifications**: assets used as-supplied without modification —
the GBA build references `assets/assets/*.png` and
`assets/extracted/<sprite>/*.png` (the latter being per-sprite tile
extractions auto-generated by the build pipeline from the source
sheets).

### Audio assets

Audio under [`assets/audio/`](assets/audio/) (24 WAV files: BGM,
combat SFX, UI clicks, victory/game-over stings).

**TODO: confirm origin and licence for the audio set before
submission.** If sourced from a CC0 / CC-BY / itch.io pack, attribute
here with source URL and licence; if project-original, replace this
TODO with "Project-original — composed/recorded by the project
author."

### Code

All gameplay logic, wave structure, tower placement, enemy AI,
projectile physics, and HUD code is project-original. C++,
GBA-native (Butano framework on devkitARM), ported from earlier
Python and C++/SDL2 prototypes.
