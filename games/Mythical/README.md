# Mythical

A top-down 2D adventure / exploration game for the Game Boy Advance.
The player moves through tile-mapped wilderness biomes populated by
animals and bosses, with combat, exploration, and progression
mechanics. The narrative and creature design are bespoke to this
project.

| Property | Value |
|---|---|
| Platform | Game Boy Advance |
| Runs on | RetroArch `lr-mgba` core (Pi-side) |
| GBA build | C entry point with C++ game-tools pipeline (`gba_project/main.c` + `cpp_core/`) |
| Prototype language | Python (pygame) |
| Shipped ROM | [`gba_project/Mythical_GBA.gba`](gba_project/Mythical_GBA.gba) — 125 KB |
| Status | Built, runnable on hardware |

---

## Folder layout

```
Mythical/
├── README.md                       (this file)
├── CMakeLists.txt                  Top-level CMake (builds cpp_core + cpp_port for desktop)
├── cpp_core/                       Shared simulation logic (engine-agnostic)
│   ├── include/mythical/           Public headers
│   ├── src/                        .cpp implementations
│   ├── tests/                      gtest / catch unit tests
│   └── CMakeLists.txt
├── cpp_port/                       Desktop simulator (renders cpp_core to a window)
│   ├── src/
│   ├── tests/
│   └── CMakeLists.txt
├── gba_project/                    GBA target
│   ├── main.c                      GBA entry point + game loop
│   ├── gba.h                       GBA hardware definitions
│   ├── generated/                  Asset baking output (sprite tiles, palettes, maps)
│   ├── convert_assets.py           Python tool — sprite-sheet → tile/palette
│   ├── convert_content.py          Python tool — game data → embedded C tables
│   ├── Makefile                    devkitARM build
│   ├── Mythical_GBA.gba            Shipped ROM
│   └── README.md                   Build-specific notes
├── docs/                           Design notes, sprint plans, specs
├── image/                          Status screenshots, design boards
└── src/
    ├── python_game/                Original Python prototype (pygame)
    │   ├── states/                 Game-state machine
    │   ├── ai/                     Enemy AI behaviours
    │   ├── content/                Levels, dialogue, item definitions
    │   ├── data/, maps/            Static game data
    │   ├── runtime/                Save / load, input mapping
    │   ├── ui/                     HUD, menus, dialogue boxes
    │   ├── tools/                  Author-side utilities
    │   └── tests/                  pytest suite
    └── cpp_game_tools/             Asset-processing utilities shared between desktop and GBA builds
```

---

## Prototyping pipeline

Mythical follows the same Python-to-GBA-native pattern as the rest of
the corpus, with one extension: a **C++ desktop simulator** intermediate
stage. The full chain is:

```
Python prototype (pygame)        ← gameplay design iteration
        ↓
C++ core + desktop port          ← engine-agnostic logic + a renderer that runs on the laptop
        ↓
GBA target (C with C++ tooling)  ← shipped artefact, runs on the Pi
```

The C++ desktop simulator lets the GBA-bound game logic be unit-tested
on the laptop without round-tripping through hardware on every change.
`cpp_core/` is the engine-agnostic simulation; `cpp_port/` wires it to
a desktop renderer; `gba_project/` provides the GBA-specific renderer
and main loop.

---

## Build

### GBA ROM (the artefact)

```bash
# Install devkitARM (one-off, system-wide)
# https://devkitpro.org/wiki/Getting_Started

cd gba_project
make
```

Output: `Mythical_GBA.gba`.

The asset baking step uses Python (`convert_assets.py`,
`convert_content.py`) to turn source sprite sheets and content data
into the C tables that `gba_project/generated/` contains.

### Desktop simulator (development convenience, not the artefact)

```bash
cmake -B build
cmake --build build
ctest --test-dir build      # runs cpp_core tests
```

### Python prototype

```bash
cd src/python_game
python -m pytest             # design-time tests
python main.py               # play the prototype
```

---

## Asset Attribution

All assets — sprites, code — are project-original. No third-party
content is used.

The sprite sheets in `src/python_game/assets/compiled/` (animal_deer,
boss_1, etc.) and the GBA-build tile data in `gba_project/generated/`
were drawn for this project.

### Audio assets

The shipped GBA build is silent. The Python prototype's
`audio_manager.py` implements procedural audio synthesis (in-memory
`pygame.mixer.Sound` buffers, no audio files on disk) as documented
engineering work but is not ported to the C++ or GBA targets.

This aligns with the corpus-wide silent-audio policy across all
three PiStation original games.

### Code

Project-original. C++ on the desktop simulator, C entry point with
C++ tooling on the GBA target, ported from earlier Python prototype.
