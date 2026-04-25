# Mythical - Desktop Project Status

Last updated: April 15, 2026

## Status

`Production-playable`

The desktop Pygame game at the repo root remains the canonical version of Mythical. It is no longer a small prototype; it is a multi-act action RPG with a complete authored campaign loop, layered meta systems, and a separate standalone GBA port living under [gba_project](/c:/Users/alvi9/MyWork/Mythical/gba_project).

## Snapshot

- Campaign acts: `3`
- Maps in the live registry: `6`
- Bosses in the campaign arc: `3`
- Main quest chains: `3`
- Player forms: `3`
- Desktop save format: `v5`
- Automated tests: `242 passing`

The implemented high-level loop is:

```text
Title
-> Act I: Village + Dungeon
-> Dark Golem
-> Act II intro
-> Haunted Ruins
-> Gravewarden
-> Act III intro
-> Mythic Sanctum
-> Mythic Sovereign
-> Final Victory
```

## Acts And Maps

| Act | Maps | Boss | Player form |
| --- | --- | --- | --- |
| Act I | `village`, `dungeon` | `dark_golem` | `base` |
| Act II | `ruins_approach`, `ruins_depths` | `gravewarden` | `hero` |
| Act III | `sanctum_halls`, `throne_room` | `mythic_sovereign` | `mythic` |

## What Is Live In The Desktop Game

### Runtime Flow

- `main.py` wires the live state machine, including title, gameplay, pause, inventory, instructions, skill screen, crafting screen, stage intro, bestiary, game over, and victory.
- `campaign.py` tracks world progression separately from local quest stages.
- `states/gameplay.py` routes boss defeats into the full three-act flow:
  - Stage 1 boss defeat unlocks Act II and prepares `stage_intro`
  - Stage 2 boss defeat unlocks Act III and prepares `stage_intro`
  - Stage 3 boss defeat reaches the final `victory` state
- `save_manager.py` persists campaign state alongside the older gameplay systems.

### Core Game Systems

- Fixed-step gameplay loop, state machine, input abstraction, tilemap rendering, map transitions, combat, AI, death flow, and save/load are all present and connected.
- All six maps are registered and loadable.
- Stage gating is live in gameplay:
  - entering `dungeon` requires the Forest Key
  - entering `ruins_approach` requires `world_stage >= 2`
  - entering `sanctum_halls` requires `world_stage >= 3`
- Player form progression is implemented through `player_forms.py`, with Hero and Mythic forms providing real visual and stat changes.

### Content Layer

- Content registries exist for all three acts:
  - base content in `content_registry.py`
  - Act II content in `content/stage2_content.py`
  - Act III content in `content/stage3_content.py`
- Those registries include NPCs, chests, ground items, enemy spawns, bosses, lore, environmental definitions, fast-travel hints, and BGM mappings.
- Map data exists for all regions in `maps/village.py`, `maps/dungeon.py`, `maps/ruins.py`, and `maps/sanctum.py`.

### Inventory, Progression, And Meta Systems

- The inventory model is now beyond the original simple key-item bag:
  - grid inventory
  - equipment slots
  - hotbar
- The inventory overlay supports drag/drop movement, equip and unequip flows, item details, hotbar awareness, crafting access, and auto-sort behavior.
- `wallet.py` separates coin currency from item storage.
- Gameplay uses the active hotbar slot for live weapon and consumable behavior.
- XP, leveling, skill points, bestiary tracking, reputation, campaign progression, and save-backed progression systems are active.
- The bestiary has a dedicated screen and discovery progression, including combat payoff for full unlocks.
- Consequence and reputation systems are present, persisted, and covered by tests, though authored reactivity is still lighter than the core combat/campaign layer.

### World And Presentation Systems

- Wildlife is active through `animal.py` and `animal_spawner.py`.
- Environmental interactions exist through `environmental.py`.
- Weather, lighting, post-processing, and fast travel are present in runtime and persisted in save data.
- Small-viewport and portability-aware rendering paths now exist across major UI screens and shared render systems, which keeps the desktop build friendlier to handheld-sized layout assumptions without replacing the desktop presentation.

### Persistence

Desktop save data currently stores:

- player position, HP, facing, difficulty
- inventory, equipment, hotbar, crafting bag, and wallet state
- quest stages and campaign progression
- opened chests and collected ground items
- defeated enemies, bosses, and dynamic drops
- progression and allocated skills
- reputation, bestiary, and consequence state
- fast-travel unlocks
- weather state
- killed animals
- player form and world stage progression

## Desktop / GBA Relationship

The repository now has two clear tracks:

- repo root: canonical desktop Pygame game
- [gba_project](/c:/Users/alvi9/MyWork/Mythical/gba_project): standalone handheld implementation

The older GBA-prep modules in `runtime/` and related tests still exist as useful portability and validation tooling, but the actual handheld game is no longer just a theoretical compatibility layer inside the Python build. The GBA target now has its own generated assets, runtime, and ROM build path.

## Verification

Verified on April 15, 2026:

- `py -3 -m pytest -q`
- `py -3 -m pytest --collect-only -q`

Results:

- `242 passed` in the full suite
- `242 collected` across the current test set

### Test Split

- `tests/test_campaign.py`: `57`
- `tests/test_regressions.py`: `98`
- `tests/test_drift_fixes.py`: `44`
- `tests/test_gba_runtime.py`: `43`

## Strongly Implemented And Coherent

- Three-act campaign progression is implemented, saved, and tested.
- Six maps are registered and loadable.
- Three bosses are implemented with stage-aware progression.
- Stage intro and victory flow support intermediate and final act outcomes.
- Inventory, wallet, progression, bestiary, reputation, consequence state, and campaign progress are persisted.
- Title-screen continue flow is real.
- Pause menu navigation into inventory and bestiary is real.
- Portability and handheld-sized layout regressions are covered by tests rather than left to guesswork.

## Current Desktop Risks / Limitations

These are no longer foundation problems, but they are the main areas where the desktop project still has room to deepen:

- `states/gameplay.py` is still the main orchestration hotspot and carries a lot of runtime responsibility.
- The system layer is broader than the authored content payoff in some areas, especially for consequence, reputation, and lore reactivity.
- Real-hardware-feeling balance and pacing can still improve through more playtesting even though the campaign structure is complete.
- Some presentation layers are still partially procedural or placeholder-heavy compared with the amount of gameplay logic now in place.

## Recommended Next Priorities

- Continue moving orchestration pressure out of `states/gameplay.py`.
- Deepen authored payoff for reputation, consequence, lore, and side-content systems.
- Replace more placeholder or procedural presentation with final authored assets over time.
- Keep desktop and `gba_project` behavior aligned at the content level while allowing each runtime to stay platform-appropriate.

## Related Docs

- [gba_project/docs/PROJECT_STATUS.md](/c:/Users/alvi9/MyWork/Mythical/gba_project/docs/PROJECT_STATUS.md)
- [GBA_PORT_SUMMARY.md](/c:/Users/alvi9/MyWork/Mythical/GBA_PORT_SUMMARY.md)
- [GBA_PORT_READINESS.md](/c:/Users/alvi9/MyWork/Mythical/GBA_PORT_READINESS.md)
