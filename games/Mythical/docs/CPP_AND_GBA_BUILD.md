# Mythical — C++ core, C++ desktop port, and GBA port

This doc covers the three native build targets that sit alongside the Python
desktop game. All three share a single game-logic library (`cpp_core/`):

- **cpp_core/** — pure C++17 game-logic library (no platform deps). Campaign,
  inventory, items, maps, tilemap, player, enemies, combat, quests, fixed-point
  math, and binary save/load all live here.
- **cpp_port/** — desktop front-end built on `cpp_core`. ASCII terminal renderer
  with cross-platform keyboard input (conio on Windows, termios on POSIX) and
  file-backed save/load.
- **gba_port/** — Game Boy Advance ROM build using `cpp_core` + libgba. Same
  game logic, rendered to the libgba text console; D-pad + A/B/L/R/START/SELECT.

## Layout

```
cpp_core/
  include/mythical/core/   # public headers (campaign, inventory, items, maps,
                           # player, enemies, combat, quests, save, tilemap,
                           # world, fixed)
  src/                     # implementations
  tests/                   # standalone C++ tests (one binary per file)
  CMakeLists.txt

cpp_port/
  src/main.cpp             # terminal game loop
  src/render.{hpp,cpp}     # ASCII renderer
  src/terminal.{hpp,cpp}   # raw keyboard + screen clear
  src/save_io.{hpp,cpp}    # file-backed save
  tests/test_save_io.cpp
  CMakeLists.txt

gba_port/
  source/main.cpp          # GBA entry + game loop
  source/gba_glue.cpp      # console renderer / key decoder
  source/gba_save.cpp      # SRAM-backed save/load
  include/gba_glue.hpp
  include/gba_save.hpp
  Makefile                 # devkitARM build (produces mythical.gba)
```

## Building the C++ desktop port (cpp_port) + cpp_core tests

Requires a C++17 toolchain and CMake 3.20+. The root `CMakeLists.txt` pulls in
both `cpp_core/` (library + tests) and `cpp_port/` (executable + its test).

```bash
cmake -S . -B build/cpp
cmake --build build/cpp
ctest --test-dir build/cpp --output-on-failure
build/cpp/cpp_port/mythical_cpp         # run the terminal game
```

Controls in the terminal game:

```
wasd         move
f            attack the tile in front of the player
e            use the door under the player
b            defeat current-stage boss (debug fast-path)
i            show inventory
s / l        save / load (mythical_save.bin in cwd)
q            quit
```

## Building the GBA ROM (gba_port)

Requires [devkitPro](https://devkitpro.org/) with the `gba-dev` meta-package
installed. `DEVKITARM` and `DEVKITPRO` must point at your devkitPro install.

```bash
cd gba_port
make DEVKITARM=$DEVKITARM DEVKITPRO=$DEVKITPRO
# produces mythical.elf and mythical.gba alongside the Makefile.
```

Run the resulting `mythical.gba` in mGBA, VisualBoyAdvance, or on real hardware
via a flash cart. GBA controls:

```
D-pad        move
A            attack the tile in front of the player
B            use the door under the player
START        defeat current-stage boss (debug fast-path)
SELECT       show equipped weapon/armor on the status line
L            save to SRAM
R            load from SRAM
```

### Windows / git-bash build notes

The `Makefile` has two knobs that help when invoking devkitPro's bundled make
from a host shell that isn't devkitPro's msys2 (e.g. git-bash):

- `MAKE_CMD=` — absolute path to `make.exe` used for the recursive pass.
- `TMP_DIR=` — writable temp dir for the linker.

Example invocation from git-bash:

```bash
cd gba_port
make \
  DEVKITARM=C:/devkitPro/devkitARM \
  DEVKITPRO=C:/devkitPro \
  MAKE_CMD=C:/devkitPro/msys2/usr/bin/make.exe \
  TMP_DIR=C:/Users/$USER/.mythical_tmp
```

If run from devkitPro's own msys2 shell none of these flags are required; plain
`make` works.

## Sharing code between the desktop port and the GBA port

`cpp_core` is the single source of truth for campaign rules, inventory math,
map metadata, tilemaps, combat, quests, and save/load. Both ports link it
directly. The platform-specific seams are small:

- **Desktop:** `cpp_port/src/terminal.cpp` for I/O, `cpp_port/src/save_io.cpp`
  for file-backed persistence, `cpp_port/src/render.cpp` for ASCII framing.
- **GBA:** `gba_port/source/gba_glue.cpp` for libgba text-console rendering,
  `gba_port/source/gba_save.cpp` for SRAM persistence.

The binary save format (`mythical::pack_save` / `mythical::unpack_save`) is
identical on both platforms, so desktop `.bin` saves can be round-tripped
through GBA SRAM and vice versa.
