# Full C++ And GBA Port Design

Date: 2026-04-24

## Goal

Port Mythical from the canonical Python/Pygame implementation to a full-parity C++ desktop executable, then build a separate full-parity GBA project from the same portable C++ gameplay core.

Full parity means the port must preserve the complete shipped campaign and systems described in `PROJECT_STATUS.md`: title flow, three acts, six maps, three bosses, player forms, inventory, equipment, hotbar, wallet, quests, crafting, bestiary, reputation, consequences, fast travel, weather state, save/load, stage intros, game over, and final victory.

## Current Context

The current source of truth is the Python/Pygame game at the repository root. Existing GBA-prep infrastructure includes:

- `runtime/fixed_point.py`, `runtime/memory_budget.py`, `runtime/asset_pipeline.py`, and `runtime/gba_compat.py`
- `tools/generate_gba_rom_tables.py` and `tools/generate_gba_assets.py`
- generated C tables and assets under `gba_src/generated/`
- GBA readiness docs and tests

This working tree does not contain a standalone `gba_project/`, despite older docs referencing one. This working tree also is not currently a Git repository, so the design and implementation plan can be written but not committed from this location.

## Chosen Approach

Use one shared portable C++ core with two platform shells:

- `cpp_core/`: portable game simulation and data model used by both targets
- `cpp_port/`: desktop C++ executable, using SDL2 for windowing, input, rendering, and audio
- `gba_project/`: standalone GBA build, using devkitARM/libtonc-style hardware interfaces and generated ROM data

The desktop C++ executable is the proving target. The GBA project should be created only after the shared core has a testable campaign loop and the desktop shell can exercise it. The GBA target then reuses the same core and substitutes hardware-appropriate rendering, input, audio, storage, and asset loading.

## Architecture

### Shared Core

`cpp_core/` owns all saveable and deterministic game behavior:

- state machine transitions
- campaign stage progression
- map registry and map transitions
- player stats, forms, movement, attacks, damage, and death
- enemy, animal, and boss simulation
- inventory, equipment, hotbar, wallet, crafting, and drops
- quests, dialogue routing, reputation, bestiary, consequences, fast travel, and weather state
- save serialization contracts
- fixed-step update loop contracts

The core must not depend on SDL, Pygame, GBA headers, filesystem APIs, hardware registers, or renderer-owned objects.

### Platform Interfaces

The core communicates with targets through explicit interfaces:

- `IInput`: logical buttons and one-frame press/release edges
- `IRenderer`: tile, sprite, text, rectangle, and palette-level drawing commands
- `IAudio`: music and sound-effect commands by stable ID
- `IStorage`: save/load byte payloads
- `IClock`: fixed-step timing boundary for the shell
- `IAssets`: map, sprite, item, enemy, dialogue, and text lookup by stable ID

The core exposes serializable game snapshots. Renderers consume snapshots and draw them; renderers never own gameplay truth.

### Desktop C++ Executable

`cpp_port/` provides:

- CMake project for Windows desktop builds
- SDL2 window, renderer, keyboard/gamepad input, and audio stubs
- virtual handheld-resolution render target scaled to the window
- debug overlay for frame time, current map, entity counts, and current state
- file-backed save storage compatible with the core binary save contract

The desktop renderer may be visually simpler than the Python Pygame renderer at first, but must represent every gameplay state and screen needed for full game completion.

### GBA Project

`gba_project/` provides:

- separate GBA build tree
- Makefile for devkitARM/libtonc-style builds
- `source/`, `include/`, `data/`, and generated asset integration folders
- hardware input mapping to the same logical buttons
- tile/background/sprite renderer implementing the same render command model
- SRAM-compatible save storage
- ROM-table asset source linked from generated data

The GBA build must avoid exceptions, RTTI, filesystem access, dynamic allocation during gameplay, floating point in simulation hot paths, and desktop-only standard-library dependencies.

## Data Flow

1. Python content remains source-of-truth during the port.
2. Existing generators continue to emit `gba_src/generated/*.c` and `*.h`.
3. New generators or adapters emit equivalent C++ core data tables when needed.
4. `cpp_core` loads content from generated tables or compact manifests.
5. `cpp_port` uses the same content and exercises the full game loop.
6. `gba_project` links the same core and ROM data with GBA platform bindings.

## Save Boundary

The shared core owns the canonical portable save format. The format should be binary, versioned, and round-trip tested. Desktop may additionally provide import/export helpers for Python JSON saves, but the GBA target stores the compact binary payload only.

## Testing Strategy

The port begins with tests before production C++ implementation:

- campaign progression and boss routing
- inventory/equipment/hotbar behavior
- save serialization and version validation
- map registry and stage gate behavior
- combat damage and death/checkpoint behavior
- generated data table sanity
- platform-interface fakes for input, storage, assets, audio, and rendering

The desktop executable and GBA project should include build smoke tests. If a GBA toolchain is unavailable locally, the build system must fail with a clear toolchain message and the desktop/core tests remain the required local verification.

## Full-Parity Acceptance Criteria

The work is complete when:

- `cpp_port` builds a Windows executable.
- `cpp_port` can start a new game, continue from save, play through all three acts, defeat all bosses, and reach final victory.
- `cpp_core` has automated tests covering the main gameplay contracts.
- `gba_project` exists as a standalone project with a real GBA build path.
- `gba_project` uses the shared core rather than a separate gameplay rewrite.
- GBA asset/data integration uses generated ROM data rather than runtime file access.
- GBA memory constraints are represented in code and tests.
- docs explain how to build and run both targets.

## Risks

- Full parity is a large rewrite, not a quick mechanical conversion.
- Python rendering code uses Pygame surfaces and procedural drawing heavily; the port must preserve gameplay first and adapt presentation per target.
- The GBA renderer will need hardware-shaped compromises while preserving state and progression parity.
- This workspace is not a Git repository, so normal design-plan-implementation commits cannot be created here.

## Non-Goals

- Preserve pixel-perfect Pygame rendering on GBA.
- Keep Python and C++ implementations forever in feature lockstep after the port becomes authoritative.
- Build a second independent GBA gameplay rewrite.
- Introduce a desktop engine that cannot map cleanly to GBA constraints.
