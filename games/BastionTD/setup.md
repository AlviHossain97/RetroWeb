# BastionTD — build setup

The shipped artefact is the GBA ROM at
`src_cpp/gba_project/BastionTD.gba` (and `BastionTD_fixed.gba`).
RetroArch's `lr-mgba` core loads it directly; you do not need to rebuild
to run it on the Pi.

If you want to rebuild from source, the build dependencies are not
checked into this repository. They are large (~1.4 GB of toolchain and
third-party binaries) and do not constitute project IP. You will need:

| Dep | Purpose | Where to get it |
|---|---|---|
| **devkitARM** | ARM cross-compiler for the GBA target | https://devkitpro.org/wiki/Getting_Started |
| **Butano** | GBA C++23 engine (header-only + tools) | https://github.com/GValiente/butano |
| **CMake ≥ 3.16** | Desktop simulator build | apt / brew / installer |
| **SDL2** | Desktop simulator runtime | apt / brew / installer |
| **Python 3** | Asset baking script (`scripts/bake_sprites.py`) | system |

## Expected layout

The build files reference these paths relative to `src_cpp/`:

```
src_cpp/tools/butano/        # Butano engine clone
src_cpp/third_party/SDL2/    # SDL2 development libs (desktop build only)
```

Either clone Butano into `src_cpp/tools/butano/` and place SDL2 dev libs
under `src_cpp/third_party/SDL2/`, or symlink them in from a shared
location.

On the original development machine these live in
`~/PiStation-build-cache/BastionTD/src_cpp/{tools,third_party}/` and are
symlinked back when building.

## Build

GBA ROM (the actual artefact):
```
cd src_cpp/gba_project
make
```
Output: `BastionTD.gba`.

Desktop simulator (development convenience, not the artefact):
```
cd src_cpp
cmake -B build
cmake --build build
```

## What's in this folder

- `src_cpp/` — game source (core simulation, GBA renderer, desktop renderer)
- `src_cpp/gba_project/{src,graphics,audio,Makefile}` — Butano-side build inputs
- `src_cpp/gba_project/*.gba` — built ROMs (committed for marker convenience)
- `src_python/` — original Python prototype that drove the gameplay design
- `assets/` — source-of-truth sprite and audio assets
- `docs/` — design notes
