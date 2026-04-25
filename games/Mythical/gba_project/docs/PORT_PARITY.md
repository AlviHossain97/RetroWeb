# Mythical Python -> GBA Parity

This tracks the standalone `gba_project/` port against the desktop Python game.

| Python Feature | GBA Equivalent | Status | Notes |
| --- | --- | --- | --- |
| Title screen | Native GBA title state | `Done` | Dedicated title screen in `main.c` |
| Player walk sprites | Scaled compiled sprite frames | `Done` | Reuses desktop compiled player art |
| Procedural tile art | Generated 16px handheld tile textures | `Done` | Derived from the same `tilemap.py` rendering logic |
| Decoration layer | Generated decor textures | `Done` | Trees, houses, props preserved through asset conversion |
| Camera scrolling | Pixel camera clamp | `Done` | Follows player across authored maps |
| Map collisions | Bit-packed collision tables | `Done` | Imported from original Python map data |
| Map transitions | Exit tables | `Done` | All authored world-map exits compile into the GBA build |
| Six-map world traversal | Standalone world tour | `Done` | `village` through `throne_room` included |
| Combat | Native action combat loop | `Done` | Melee player combat plus enemy and boss attack states now run in `main.c` |
| Enemies and bosses | GBA entity sets | `Done` | All authored enemy spawns and three stage bosses are generated into the port |
| NPC dialogue | Native dialogue boxes | `Done` | Dialogue pages are generated from the Python content registries |
| Inventory / equipment | GBA menu states | `Done` | Inventory, equip, consumable use, and boss loot are available from the handheld menu |
| Save data | SRAM format | `Done` | Native SRAM save and title-screen continue flow are implemented |

## Port Rules

The port now follows the same rules that made `Red Racer` feel faithful:

1. Keep the desktop game untouched.
2. Build a separate hardware implementation in C.
3. Reuse the original art and content pipelines wherever possible.
4. Preserve the desktop game's composition and field of view before adding new handheld-specific embellishment.

## Current Focus

The current handheld build now covers the core authored campaign loop:

- keep the same procedural world art and authored maps
- keep the same player sprite identity and overall field of view
- drive quests, NPCs, items, enemies, and bosses from the Python source tables
- preserve the dedicated-port separation model that worked in `Red Racer`

Further polish can still deepen parity, but the port is no longer just a traversal slice.
