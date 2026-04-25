# Mythical GBA Project Status

Last updated: April 24, 2026

## Status

`Production-playable`

The handheld port is now a real GBA-native game build rather than a framebuffer prototype. The major architecture work is complete:

- world rendering uses streamed tiled backgrounds
- UI and text use a dedicated tile layer
- actors, pickups, and effects use OBJ sprites
- desktop content still drives the handheld build through the generator pipeline

## Current Outcome

The GBA version is currently in a strong shipping-candidate state for emulator play:

- full authored campaign loop is playable from title screen to victory
- SRAM save and continue are working
- dialogue, HUD, inventory, bosses, quests, and map transitions are all in the standalone runtime
- text and UI were redesigned around the GBA screen instead of desktop assumptions
- the renderer now fits real GBA hardware structure instead of brute-force framebuffer copying

## Architecture Snapshot

### Runtime

- [main.c](/c:/Users/alvi9/MyWork/Mythical/gba_project/main.c): standalone campaign runtime and game state flow
- [gba.h](/c:/Users/alvi9/MyWork/Mythical/gba_project/gba.h): low-level display, DMA, BG, OBJ, and input hardware helpers

### Asset / Content Build

- [convert_assets.py](/c:/Users/alvi9/MyWork/Mythical/gba_project/convert_assets.py): builds paletted BG, UI/font, and OBJ tile data
- [convert_content.py](/c:/Users/alvi9/MyWork/Mythical/gba_project/convert_content.py): converts authored maps, quests, items, enemies, and dialogue into generated tables
- [generated/assets.h](/c:/Users/alvi9/MyWork/Mythical/gba_project/generated/assets.h): generated asset interface used by the runtime
- [generated/maps.h](/c:/Users/alvi9/MyWork/Mythical/gba_project/generated/maps.h): generated map data
- [generated/content.h](/c:/Users/alvi9/MyWork/Mythical/gba_project/generated/content.h): generated gameplay/content data

### Renderer Layout

- `BG0`: streamed ground layer
- `BG1`: streamed decor layer
- `BG2`: fixed HUD / dialogue / menu text layer
- `OBJ`: player, NPCs, enemies, bosses, pickups, slash effect

## Completed Milestones

- Standalone `gba_project/` structure established
- Full campaign traversal ported across all six authored maps
- Combat, enemies, bosses, quest progression, loot, inventory, and SRAM save implemented
- Text readability overhaul completed
- HUD and dialogue layout rebuilt for handheld readability
- Full renderer migration completed from Mode 3 framebuffer logic to Mode 0 tiled BG + OBJ architecture
- Asset pipeline rebuilt to generate hardware-native tile packs and palette data

## Verification

Verified on April 24, 2026:

- `py -3 convert_content.py` — regenerated `generated/maps.{c,h}` and `generated/content.{c,h}`
- `py -3 convert_assets.py` — regenerated `generated/assets.{c,h}`
- `make clean && make build` — clean rebuild through devkitARM
- `py -3 -m pytest -q tests\test_gba_runtime.py`
- `py -3 -m pytest -q`

Results:

- `45 passed` in `tests/test_gba_runtime.py`
- `244 passed` in the full repo test suite
- rebuilt ROM: [Mythical_GBA.gba](/c:/Users/alvi9/MyWork/Mythical/gba_project/Mythical_GBA.gba)
- current ROM size: `121,764` bytes

### Content Count Parity (Python ↔ GBA generated tables)

| Dimension | Python source | `gba_project/generated/` | Match |
| --- | --- | --- | --- |
| Maps | 6 (village, dungeon, ruins_approach, ruins_depths, sanctum_halls, throne_room) | 6 (`MAP_COUNT`) | ✅ |
| Map dimensions | 50×36 / 40×40 / 50×36 / 60×40 / 60×40 / 50×36 | identical | ✅ |
| Items | 48 (`ITEM_DEFS`) | 48 (`GBA_ITEM_COUNT`) | ✅ |
| NPCs | 8 across `NPC_DEFS` + stage2 + stage3 | 8 (`GBA_NPC_COUNT`) | ✅ |
| Chests | 12 (2 per map × 6 maps) | 12 (`GBA_CHEST_COUNT`) | ✅ |
| Ground items | 11 | 11 (`GBA_GROUND_ITEM_COUNT`) | ✅ |
| Lore notes | 9 | 9 (`GBA_LORE_COUNT`) | ✅ |
| Enemy spawns | 39 | 39 (`GBA_ENEMY_SPAWN_COUNT`) | ✅ |
| Enemy types | 12 | 12 (`GBA_ENEMY_TYPE_COUNT`) | ✅ |
| Bosses | 3 (dark_golem, gravewarden, mythic_sovereign) | 3 (`GBA_BOSS_COUNT`) | ✅ |
| Quests | 3 main chains | 3 (`GBA_QUEST_COUNT`) | ✅ |
| Recipes | 14 | 14 (`GBA_RECIPE_COUNT`) | ✅ |
| Waypoints | 6 fast-travel hints | 6 (`GBA_WAYPOINT_COUNT`) | ✅ |
| Animals | 6 types / 33 spawns | 6 / 33 (`GBA_ANIMAL_*`) | ✅ |
| Signs | 7 | 7 (`GBA_SIGN_COUNT`) | ✅ |

## What Is Left

No critical architecture migration work is left open in the GBA target.

Any remaining work is optional polish rather than unfinished backend conversion:

- more art-specific tuning for certain scenes or bosses
- additional handheld flair in menus or transitions
- real-hardware QA beyond emulator validation
- balance and feel iteration after longer play sessions

## Risks / Watch Areas

- The port is validated in mGBA and through automated tests, but real hardware testing is still worth doing for final confidence.
- The shared 256-color palette is working within the current asset set; future art expansion should keep an eye on palette pressure.
- Large future UI additions should stay disciplined so the readable handheld layout does not regress toward desktop-style density.

## Recommended mGBA Setup

The ROM-side fixes are doing the important work now. mGBA tweaks are minor:

- keep frameskip off
- use integer scaling or nearest-neighbor output for the sharpest text
- avoid extra filters or shaders if readability is the priority

## Related Docs

- [README.md](/c:/Users/alvi9/MyWork/Mythical/gba_project/README.md)
- [PORT_PARITY.md](/c:/Users/alvi9/MyWork/Mythical/gba_project/docs/PORT_PARITY.md)
