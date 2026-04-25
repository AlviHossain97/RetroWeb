# Mythical GBA Port

This folder now follows the same separation model that works in `Red Racer`:

- the desktop Python game stays at the repo root
- the handheld port lives in its own `gba_project/`
- assets and map data are generated from the original game instead of being rewritten by hand

That means the port keeps Mythical's existing look and feel by reusing:

- the procedural tile rendering from [tilemap.py](/c:/Users/alvi9/MyWork/Mythical/tilemap.py)
- the compiled desktop player sprites from [assets/compiled/player](/c:/Users/alvi9/MyWork/Mythical/assets/compiled/player)
- the authored world data from [maps](/c:/Users/alvi9/MyWork/Mythical/maps)

## Current Slice

The standalone GBA build now includes the full authored campaign loop:

- title, help, inventory, stage-clear, game-over, and victory states
- full-map exploration across all six authored maps
- scrolling camera and scaled desktop player sprite animation
- collision, exits, and campaign-stage gating from the original Python map data
- NPC dialogue, sign reading, chest opening, ground pickups, and lore pickups
- quest progression driven by the original trigger tables
- native enemy and boss combat with stage progression through all three acts
- inventory, equipment, consumable usage, boss loot, and SRAM save / continue support

## Why This Matches Red Racer Better

The earlier Mythical GBA work mostly lived as runtime prep inside the Python codebase. `Red Racer` works because it has a dedicated port implementation that consumes shared assets but is not tangled into the desktop runtime.

This folder makes Mythical behave the same way:

- desktop code remains the canonical Python version
- GBA code becomes a real standalone target
- the same authored assets drive both builds

## Build Flow

1. Generate the standalone asset and content tables:

```bash
py -3 convert_assets.py
py -3 convert_content.py
```

2. Build the ROM with devkitARM:

```bash
make build
```

## Files

- [main.c](/c:/Users/alvi9/MyWork/Mythical/gba_project/main.c): standalone GBA campaign runtime
- [gba.h](/c:/Users/alvi9/MyWork/Mythical/gba_project/gba.h): hardware helpers
- [convert_assets.py](/c:/Users/alvi9/MyWork/Mythical/gba_project/convert_assets.py): Python art -> C tables
- [convert_content.py](/c:/Users/alvi9/MyWork/Mythical/gba_project/convert_content.py): Python maps + gameplay content -> C tables
- [docs/PROJECT_STATUS.md](/c:/Users/alvi9/MyWork/Mythical/gba_project/docs/PROJECT_STATUS.md): current project snapshot and verification status
- [docs/PORT_PARITY.md](/c:/Users/alvi9/MyWork/Mythical/gba_project/docs/PORT_PARITY.md): parity tracker

## Notes

- The port intentionally scales 32px desktop tiles down to 16px on GBA to preserve the original field of view more closely.
- The GBA runtime is still a dedicated handheld implementation rather than a byte-for-byte rewrite of the desktop Python simulation, but it now consumes the same authored story, map, item, enemy, and quest data.
