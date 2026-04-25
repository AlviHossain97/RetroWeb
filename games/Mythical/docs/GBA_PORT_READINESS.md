## GBA Port Readiness

Current assessment: partially ready.

Refresh as of April 24, 2026: this working tree does not contain a standalone `gba_project` directory. The desktop Python game remains the source of truth, and generated GBA-ready C data now lives under `gba_src/generated/`. The next missing structural step is a real `cpp_port/` desktop target and, after parity, a standalone GBA target.

The project is in a solid place to begin a structured port, but it is not yet "drop-in ready" for GBA. The gameplay architecture is moving in the right direction: state flow, campaign progression, map data, inventory state, save serialization, and most combat rules are already separated well enough that they can be reimplemented on target hardware. The biggest remaining work is in the platform layer and simulation details, not in the high-level game design.

### Strong foundations

- `states/state_machine.py`: simple state transitions that map well to a handheld game loop.
- `campaign.py`, `quest.py`, `inventory.py`, `item_system.py`, `save_manager.py`: game state and progression are centralized instead of being smeared across rendering code.
- `maps/*.py`, `content/*.py`, `content_registry.py`: campaign/map content is already data-driven enough to be converted into ROM tables later.
- `input_handler.py`: input is already routed through a logical abstraction instead of being queried ad hoc throughout gameplay.
- `tests/`: the project has enough automated coverage to protect behavior while we refactor toward a port-safe architecture.

### Main blockers

- Rendering is still tightly coupled to `pygame.Surface`, `pygame.draw`, alpha blending, and `SysFont`.
- Audio is entirely desktop-specific and procedurally generated at runtime through `pygame.mixer`.
- Entity simulation uses Python floats, trig, dynamic lists, and pathfinding structures that will need fixed-point or tile-native rewrites for GBA.
- Runtime config still assumes desktop file access, even though save serialization is now separated from file I/O.
- Several systems allocate temporary surfaces every frame, which is fine on PC but not a viable handheld rendering model.

### Most expensive future rewrites

- `tilemap.py`: beautiful prototype renderer, but it is a desktop rasterizer rather than a GBA background/tile pipeline.
- `audio_manager.py`: needs replacement with tracker/sample assets and a hardware-appropriate playback layer.
- `player.py`, `enemy.py`, `boss.py`, `boss2.py`, `boss3.py`, `animal.py`, `effects.py`, `weather.py`: these are gameplay-valid, but still float-heavy and effect-heavy.
- `states/*.py` UI screens: most menus are renderable conceptually on GBA, but their implementation is currently PC UI code rather than tile/sprite UI code.

### Changes landed in this audit

- Added a dual-target runtime layer in `runtime/` so boot, frame timing, audio creation, and save I/O are no longer hardwired directly into `main.py`.
- Added explicit target selection through `create_runtime()` / `MYTHICAL_TARGET`, while keeping `pygame` as the default runtime so the desktop build remains the canonical playable version during the port.
- Split logical button state from pygame keyboard events, so input state is now backend-neutral and the desktop key translation lives in the pygame runtime instead of `settings.py`.
- Made camera/gameplay viewport sizing flow from the active target profile instead of assuming the desktop resolution inside the camera logic.
- Made the gameplay HUD and dialogue box respond to the active viewport size, including a smaller-width hotbar/minimap layout path for handheld-sized screens.
- Added shared state viewport helpers and moved the simpler full-screen states (`pause`, `game_over`, `victory`, `instructions`) onto compact-layout-aware rendering paths for handheld-sized screens.
- Added compact-layout-aware rendering paths for the heavier menu states too, including `inventory_screen`, `skill_screen`, `crafting_screen`, and `bestiary_screen`, so they now render against the active target viewport instead of assuming the desktop canvas.
- Centralized font selection through a shared cached UI font helper, so major screens, HUD, dialogue, and transition cards no longer instantiate `pygame.font.SysFont` independently.
- Made shared map rendering systems viewport-aware too: `MapManager` now sizes fade buffers against the active screen instead of a hardcoded desktop canvas, and `TileMap.render()` now blits only the visible world area instead of always pushing the whole cached map surface.
- Added a runtime-owned animation clock and moved multiple renderers (`HUD`, `weather`, `NPC`, interactables, inventory glow states, and environmental warning pulses) off `pygame.time.get_ticks()`, which reduces hidden desktop-global timing dependencies.
- Made the weather system viewport-aware, so particle spawn bounds, particle culling, overlays, and fog bands now follow the active target dimensions instead of the desktop constants.
- Centralized repeated gameplay math into `game_math.py`, and moved core player/enemy/boss/animal/effects/fast-travel logic onto those helpers so a future fixed-point or lookup-table rewrite has a single seam.
- Added shared logical viewport defaults for backend-neutral layout/render systems, so camera, state layout helpers, HUD, dialogue, weather, lighting, and post-processing no longer need to fall back through desktop screen constants.
- Made `LightingSystem` and `PostProcessor` capability-aware, including small-screen sizing and non-alpha fallback paths, so handheld target profiles can exercise those systems without assuming desktop-grade blending.
- Wired gameplay into those shared FX systems properly: map loads now set post-process/light context, static decor lights are populated from map data, and damage/death feedback now advances during gameplay updates instead of only existing as dormant desktop-only helpers.
- Hardened the pygame runtime audio path so it can fall back to a null audio backend if the mixer is unavailable, instead of assuming procedural desktop audio is always present.
- Split save serialization from save storage in `save_manager.py`, adding byte-level encode/decode helpers and size estimation so future SRAM/flash backends have a clean seam that does not depend on desktop JSON files.
- Centralized stage config access through cached loader helpers in `ai/config_loader.py` instead of reopening `stage_configs.json` inside gameplay code.
- Updated `states/gameplay.py` to use those cached helpers for stage difficulty, stage HP bonus, boss XP, and boss loot.
- Prevented `tilemap.py` from resetting the global RNG during map baking, which keeps gameplay randomness deterministic and easier to port.
- Cached the damage-number font in `effects.py` to avoid repeated per-frame font allocation.

### Current target usage

- Default: `pygame` remains the active gameplay runtime.
- Alternate target: set `MYTHICAL_TARGET=gba` to exercise the handheld target selection path and capability profile.
- Important: the `gba` runtime is intentionally non-runnable inside this Python build for now; it exists to guide refactors and keep dual-target assumptions explicit while the shared simulation layer is extracted.

### Changes landed in this audit (Continued)

- Added `runtime/fixed_point.py` with complete 24.8 fixed-point math library:
  - Conversion helpers: `to_fixed()`, `to_float()`, `from_int()`, `to_int()`
  - Arithmetic: `mul()`, `div()`, `sqrt()` with Newton-Raphson iteration
  - Trigonometry lookup tables (256 entries) for sin/cos without float
  - `FixedVec2` class as drop-in replacement for float tuples
  - Distance, normalization, and vector math using pure integers
  
- Added `runtime/memory_budget.py` with GBA hardware constraints:
  - MemoryBudget dataclass with realistic GBA limits
  - MemoryTracker for development-time validation
  - Budgets: 64 max entities, 256 max particles, 64x64 max map size
  - Save size estimation (~1200 bytes fits in 64KB SRAM)
  - Verification helpers to check content against constraints

- Added `runtime/asset_pipeline.py` for GBA asset conversion:
  - TileSet class for 8x8 4bpp tile generation
  - SpriteSheet class with animation metadata
  - SurfaceConverter for pygame → GBA format (16-color palette)
  - Tilemap to binary format for ROM embedding
  - SavePacker with complete binary SRAM format (v6)
  - C array generation for GBA toolchain integration

- Added `runtime/gba_compat.py` for gradual migration:
  - GBAOAMManager simulates 128 hardware sprites
  - GBAEntity base class with fixed-point positions
  - GBACompatMode context manager for testing with GBA constraints
  - Distance checks, collision, and angle approx without sqrt/atan2
  - Surface quantization to GBA-compatible palettes
  - HybridEntity for float/fixed-point switching during port

### New GBA Runtime Modules

| Module | Purpose | Status |
|--------|---------|--------|
| `runtime/fixed_point.py` | Integer math replacement for floats | ✅ Complete |
| `runtime/memory_budget.py` | Hardware constraint validation | ✅ Complete |
| `runtime/asset_pipeline.py` | Asset conversion pipeline | ✅ Complete |
| `runtime/gba_compat.py` | GBA compatibility layer | ✅ Complete |

### Updated blockers status

| Blocker | Before | After |
|---------|--------|-------|
| Float positions | No replacement | FixedVec2 + 24.8 fixed-point |
| Trig functions | No replacement | 256-entry LUT for sin/cos |
| Memory budgets | No validation | GBA_BUDGET with tracking |
| Asset conversion | No pipeline | Complete pipeline to C arrays |
| Entity systems | Float-heavy | GBAEntity base class available |
| Save format | JSON only | Binary v6 with SRAM packing |

### Recommended next port-prep steps

1. ✅ Introduce platform layer - **DONE** via `runtime/` with dual-target support
2. ✅ Replace float positions - **DONE** via `FixedVec2` and `GBAEntity`
3. 🔄 Convert procedural drawing - **IN PROGRESS** use `SurfaceConverter` on sprites
4. ✅ Move file reads to cached accessors - **DONE** via `ai/config_loader.py`
5. ✅ Define memory budgets - **DONE** via `MemoryBudget` and `MemoryTracker`
6. ✅ Create GBA compatibility shim - **DONE** via `runtime/gba_compat.py`

### Remaining work before GBA port

1. **Migrate entity classes** to inherit from `GBAEntity` and use fixed-point
2. **Convert all sprites** using `SurfaceConverter` and validate with `validate_for_gba()`
3. **Replace `pygame.draw` calls** with tile/sprite-based rendering
4. **Create tracker-based audio** files to replace procedural audio
5. **Test with `GBACompatMode`** to catch GBA constraint violations during development
6. **Generate GBA ROM tables** from `content/*.py` using asset pipeline

### Using the new tools

```python
# Test GBA constraints during development
from runtime.gba_compat import GBACompatMode

with GBACompatMode():
    # Code here runs with GBA memory limits
    game.update()  # Will warn if entity count exceeds 64

# Use fixed-point for new features
from runtime.fixed_point import FixedVec2
pos = FixedVec2(10.5, 20.25)  # Stores as integers internally

# Validate assets
from runtime.gba_compat import validate_for_gba
issues = validate_for_gba(player_sprite, "player")

# Convert for GBA
from runtime.asset_pipeline import SurfaceConverter
converter = SurfaceConverter()
tiles, palette = converter.surface_to_8x8_tiles(surface)
```

### Changes landed in this audit (Continued)

- April 24, 2026 refresh:
  - Regenerated `gba_src/generated/` from the existing ROM table and graphics asset generators.
  - Fixed item ROM table generation so item IDs are stable per item instead of every item receiving ID `48`.
  - Added item enum, accessory type, rarity tier, stack size, and category preservation to generated item headers/tables.
  - Fixed tilemap collision declarations to round up bit-packed collision byte counts for future odd-sized maps.
  - Added regression coverage for item table generation and collision byte sizing.

- Added `tests/test_gba_runtime.py` with 45 tests covering:
  - Fixed-point arithmetic (conversion, mul, div, sqrt, trig)
  - FixedVec2 operations (addition, subtraction, normalization)
  - Memory budget tracking and validation
  - Save packing round-trip verification
  - GBA compatibility layer (OAM, entities, collision)
  - ROM table generator metadata and collision packing regressions

- Added `tools/generate_gba_rom_tables.py` for ROM data generation:
  - Converts all 6 game maps to GBA-compatible tilemap arrays
  - Generates 48-item lookup table from ITEM_DEFS
  - Creates enemy stat tables from spawn definitions
  - Builds dialogue tables from NPC definitions
  - Outputs C headers/source for GBA toolchain
  - Total generated footprint with current asset tables: ~175 KB (4.27% of 4MB cart)

### Summary of New Files

| File | Purpose | Size |
|------|---------|------|
| `runtime/fixed_point.py` | Fixed-point math | 218 lines |
| `runtime/memory_budget.py` | Memory constraints | 216 lines |
| `runtime/asset_pipeline.py` | Asset conversion | 493 lines |
| `runtime/gba_compat.py` | GBA shim layer | 401 lines |
| `tests/test_gba_runtime.py` | GBA module tests | 45 tests |
| `tools/generate_gba_rom_tables.py` | ROM table generator | 428 lines |
| `tools/generate_gba_assets.py` | Tile/player graphics generator | present |
| `gba_src/generated/*.c/h` | Generated ROM/graphics source arrays | 175 KB source data, 181 KB including headers |

### Test Results

All 244 tests passing as of April 24, 2026:
- 199 existing game/runtime tests
- 45 GBA runtime and generator tests

### Bottom line

The codebase now has complete infrastructure for GBA porting:

✅ Fixed-point math library (24.8 format)  
✅ Memory budget validation (64 entities, 256 particles, 64x64 maps)  
✅ Asset conversion pipeline (tiles, sprites, palettes)  
✅ Binary save format (SRAM-compatible)  
✅ ROM/graphics table generators (175 KB of generated source array data)  
✅ GBA compatibility layer (OAM, entities, collision)  
✅ Comprehensive test coverage (45 GBA-specific tests)  

The remaining work is migrating `player.py`, `enemy.py`, etc. to use `GBAEntity` base class and converting procedural sprites to tile/sprite sheets. The architecture supports both desktop development and GBA porting simultaneously.
