# Red Racer Ultimate Edition — GBA

> **A complete port of the Python/Pygame "Ultimate Red Racer" desktop game to the Nintendo Game Boy Advance, written in bare-metal C targeting the ARM7TDMI processor.**

---

## Table of Contents

1. [Origin — The Python Pygame Game](#origin--the-python-pygame-game)
2. [Why Port to GBA?](#why-port-to-gba)
3. [Porting Process](#porting-process)
4. [Technical Architecture](#technical-architecture)
5. [Game States & Flow](#game-states--flow)
6. [Game Modes](#game-modes)
7. [Rendering — GBA Mode 4](#rendering--gba-mode-4)
8. [Asset Pipeline](#asset-pipeline)
9. [Physics & Car Handling](#physics--car-handling)
10. [Scoring & Combo System](#scoring--combo-system)
11. [Traffic AI & Entity System](#traffic-ai--entity-system)
12. [Collectibles & Items](#collectibles--items)
13. [Save System (SRAM)](#save-system-sram)
14. [Input Handling](#input-handling)
15. [Particle Effects](#particle-effects)
16. [Road System](#road-system)
17. [Car Roster](#car-roster)
18. [Build System](#build-system)
19. [File Structure](#file-structure)
20. [Feature Parity Status](#feature-parity-status)

---

## Origin — The Python Pygame Game

Red Racer was originally developed as a full-featured desktop racing game using **Python 3** and the **Pygame** library. The original version (`main.py`, `settings.py`, `sprites.py`, `systems.py`, `ui.py`, `ai_driver.py`) ran at 800×600 resolution on PC and featured:

- **14 selectable supercars** (Ferrari, Lamborghini, McLaren, Audi, Mercedes, Corvette, Bugatti Veyron, Koenigsegg CCX, Toyota Supra, Aston Martin, Lotus, Porsche 911, Dodge Viper, Pagani Zonda), each with unique real-world-inspired specs (BHP, torque, 0-60 time, top speed, engine type, drivetrain).
- **4 distinct road environments** — City Express, Industrial Route, Coastal Run, and Night Circuit — each with different traffic densities, grip levels, lane widths, and risk multipliers.
- A **full menu system** with Start, Editor (car/road/driver selection), Difficulty toggle (Normal/Hard/Easy), Settings, Instructions, Game Mode selector, and Quit.
- A sophisticated **risk scoring system** with near-miss detection, combo meters, wrong-lane bonuses, and multiplier chains.
- A **boost system** that charged from risky driving and discharged as a speed multiplier.
- A **progression system** with XP, levels, car unlocks, upgrades, and cosmetic palette unlocks, persisted to JSON files.
- An **AI driver mode** powered by a local LLM (Ollama/Llama 3.2 Vision) that could play the game autonomously using vision-based inference.
- **Multiple game modes**: Classic Endless, High-Risk, Time Attack, Hardcore (1 life), Daily Run (deterministic seed), and Zen Mode.
- **Visual effects** including particle exhaust trails, screen shake, speed lines, hit-stop on collision, and crash slow-motion.
- **Audio** with menu music (Hans Zimmer F1 theme) and in-game engine sounds.
- A full **JSON-based configuration system** (`game_config.json`) for toggling every gameplay feature independently.

The Pygame version used object-oriented design with classes like `Player`, `Enemy`, `Coin`, `FuelCan`, `NitroBottle`, `RepairKit`, and `Particle` inheriting from a common `Entity` base class. UI was handled by a `Button` class, and gameplay systems like `RiskScoringSystem`, `BoostSystem`, and `ProgressionSystem` were modular classes in `systems.py`.

---

## Why Port to GBA?

The GBA port transforms an 800×600 desktop game into a 240×160 handheld experience running on hardware from 2001. This required rethinking every system from the ground up:

- **No operating system** — the game runs bare-metal on the ARM7TDMI CPU at 16.78 MHz.
- **No floating-point unit** — all physics calculations use software floating-point emulation via GCC.
- **96 KB of VRAM** — the entire display buffer must fit here, using a paletted 8-bit mode instead of true-color.
- **256 KB of ROM** — all code and assets must fit within this space.
- **No filesystem** — assets are compiled directly into the ROM as C arrays.
- **64 KB of SRAM** — the only persistent storage, used for save data.
- **No audio hardware abstraction** — the GBA's DirectSound channels would require raw PCM mixing (not yet implemented).

---

## Porting Process

### From Python Objects to C Structs

The Pygame version's class hierarchy (`Entity` → `Player`/`Enemy`/`Coin`/etc.) was flattened into a single C `Entity` struct with a `type` field (0=Enemy, 1=Coin, 2=Fuel, 3=Repair, 4=Nitro) and a fixed-size pool of 12 entities (`MAX_ENTITIES`). Instead of Pygame's `sprite.Group` for update/draw, the GBA version uses simple array iteration.

### From Pygame Surfaces to Mode 4 Blitting

Pygame's `Surface.blit()` with per-pixel alpha was replaced with manual pixel-pair writes to GBA VRAM. Since Mode 4 packs two 8-bit palette indices into each 16-bit halfword, every pixel operation requires masking and shifting to avoid corrupting the adjacent pixel.

### From 800×600 to 240×160

All coordinates, sprite sizes, and UI layouts were rescaled. Player cars went from 50×100 pixels to 16×24 pixels. Road boundaries went from 130–670 (540px playable) to 40–200 (160px playable). The HUD was redesigned to fit the tiny screen using an 8×8 bitmap font.

### From Pygame Fonts to Bitmap Glyphs

The `convert_assets.py` script renders each character (A–Z, 0–9, colon, space) using Pygame's default font at 20px, scales it to 8×8, quantizes it to the game's 256-color palette, and packs it as a Mode 4 lookup table indexed by ASCII code.

### From JSON Config to Compile-Time Constants

The original's `game_config.json` feature-flag system was replaced with `#define` constants. Toggles like `ENABLE_DEBUG_OVERLAY` and `ENABLE_PARTICLES` are now compile-time switches.

---

## Technical Architecture

The entire game lives in a single `main.c` file (approximately 2,100 lines) plus supporting headers:

| File | Purpose |
|:---|:---|
| `main.c` | All game logic, rendering, state management, physics, AI, save/load |
| `gba.h` | Hardware register definitions, memory map, type aliases, VBlank/page-flip helpers |
| `assets.h` | Auto-generated — palette, car sprites (normal/left/right tilt), road bitmaps, item sprites, font glyphs (8×8) |
| `convert_assets.py` | Python script that automatically discovers PNG assets and converts them into `assets.h` using Pygame for image loading and quantization |
| `Makefile` | devkitARM build configuration |

### Memory Map Usage

| Region | Address | Size | Usage |
|:---|:---|:---|:---|
| VRAM | `0x06000000` | 96 KB | Two 240×160 framebuffers (Mode 4 double-buffering) |
| Palette RAM | `0x05000000` | 512 B | 256-color palette (15-bit BGR) |
| SRAM | `0x0E000000` | 64 KB | Save data (high score, progression, settings) |
| ROM | `0x08000000` | ~196 KB | Code + all asset data |

---

## Game States & Flow

The game is driven by a finite state machine with 8 primary states:

```
                    ┌──────────────┐
                    │  STATE_MENU  │ ◄─────────────────────────────────────┐
                    └──────┬───────┘                                       │
           ┌───────────────┼───────────────┬────────────────┐              │
           ▼               ▼               ▼                ▼              │
    ┌─────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐     │
    │ STATE_PLAY  │ │ STATE_GARAGE │ │ STATE_ROAD_  │ │ STATE_RECORD │     │
    └──────┬──────┘ └──────┬───────┘ │    SELECT    │ └──────┬───────┘     │
           │               │         └──────┬───────┘        │             │
           ▼               ▼                ▼                ▼             │
    ┌─────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐     │
    │  GAME_OVER  │ │ STATE_INSTR_ │ │  STATE_RUN_  │ │  STATE_MENU  │─────┘
    └──────┬──────┘ │    UCTIONS   │ │   SUMMARY    │ └──────────────┘
           │        └─────┬────────┘ └──────┬───────┘
           ▼              │                 │
     STATE_SUMMARY ◄──────┘─────────────────┘
```

- **STATE_MENU**: Title screen with 5 buttons (Start, Garage, Difficulty, Instructions, Records).
- **STATE_GARAGE**: Replaces the old car selection. Shows a detailed view of cars with stats (Speed, Accel, Handling, Braking, Fuel efficiency) and unlock status.
- **STATE_ROAD_SELECT**: Scrollable road preview showing a high-quality downscaled render of the road bitmap.
- **STATE_RECORDS**: Shows persistent statistics: high score, total runs, total play time, level, per-mode bests, and a history of the 20 most recent runs.
- **STATE_PLAY**: The main gameplay loop — scrolling road, player control, HUD rendering.
- **STATE_RUN_SUMMARY**: Displayed after a race. Shows score, risk points, duration, new high score alerts, and XP progression.
- **STATE_GAMEOVER**: Final crash screen.

---

## Game Modes

The GBA port introduces 5 distinct game modes defined by `ModeRules`:

| Mode | Name | Description |
| :--- | :--- | :--- |
| **CLASS** | Classic Endless | The standard experience. Scoring based on distance + items. |
| **HIGH-** | High Risk | Focuses entirely on Risk Scoring. Distance score disabled. |
| **TIME** | Time Attack | 90-second sprint for the highest score. Deterministic seed. |
| **HARDC** | Hardcore | 1-hit kill. No repair kits. No nitro. Fuel drain disabled. |
| **FUEL** | Fuel Crisis | Start with low fuel, elevated drain rate. |
| **BOOST** | Boost Rush | Rapid boost charging, higher baseline speed. |
| **ENDUR** | Endurance | Fewer item pickups, longer runs required. |
| **DAILY** | Daily Run | Fixed daily seed for the ultimate leaderboard challenge. |
| **ZEN**   | Zen Mode | Infinite fuel. No damage. Focuses on smooth driving. |

---

## Rendering — GBA Mode 4

The game uses **Mode 4** (256-color paletted, 240×160), which is the GBA's bitmap mode with double-buffering support. Each pixel is an 8-bit index into a 256-color palette stored in Palette RAM.

### Double Buffering

Two framebuffers exist in VRAM:
- **Page 0**: `0x06000000` (front or back, depending on `REG_DISPCNT` bit 4)
- **Page 1**: `0x0600A000`

Each frame:
1. `waitForVBlank()` — spin until scanline reaches VBlank (line 160+).
2. Draw the entire frame to the **back buffer** (pointed to by `vid_page`).
3. `flipPage()` — toggle bit 4 in `REG_DISPCNT` and swap which page `vid_page` points to.

### Packed Pixel Operations

Since two pixels share a single `u16` in VRAM, every pixel write must:
1. Calculate the halfword offset: `offset = (y * 240 + x) / 2`
2. Read the existing halfword.
3. Mask out the target byte (low byte for even x, high byte for odd x).
4. OR in the new palette index.

This is encapsulated in `drawRect()`, `fillScreen()`, and the background/sprite blit routines.

### Drawing Primitives

| Function | Description |
|:---|:---|
| `fillScreen(color_idx)` | Fills all 19,200 halfwords with a packed color pair. Loop unrolled ×8 for performance. |
| `drawRect(x, y, w, h, color_idx)` | Pixel-by-pixel filled rectangle with bounds checking. |
| `drawSprite(x, y, sprite_data, w, h)` | Blits a packed sprite with transparency (palette index 0 = transparent). X is forced to even alignment for 16-bit writes. |
| `drawChar(x, y, c)` | Renders a single 8×8 font glyph via the `font_lookup[128]` table. |
| `drawText(x, y, str)` | Renders a string character-by-character, advancing x by 8 pixels per glyph. |
| `drawInt(x, y, val)` | Integer-to-string conversion (manual itoa) then `drawText()`. |
| `drawBackground()` | Scrolling road blit — copies the road bitmap to VRAM with vertical wrap using `scroll_y`. Only draws the road area (pixels 40–200). |

---

## Asset Pipeline

The `convert_assets.py` script bridges the Pygame world and the GBA:

1. **Palette Construction**: Starts with index 0 as transparent (black), indices 1–10 as fixed UI colors (white, red, green, blue, yellow, cyan, purple, gray, dark gray, near-black). Remaining indices are filled dynamically as sprites/roads are processed. If all 256 slots fill, the nearest-color match is used.

2. **Asset Discovery**: The script scans the parent directory for all `.png` files, automatically identifying car sprites (excluding known items, roads, and UI elements). This allows for easy addition of new car models.

3. **Car Processing**: Each car PNG is loaded, scaled to 16×24, and quantized. Three variants are generated:
   - **Normal** (straight ahead)
   - **Left** (rotated +15° for left-steer visual)
   - **Right** (rotated -15° for right-steer visual)

4. **Road Processing**: Each road PNG is loaded and scaled to 240×160 (full GBA screen), then quantized to the shared palette.

5. **Item Processing**: Coin, Fuel, and Repair PNGs are scaled to 12×12 and quantized.

6. **Font Generation**: Pygame's default font renders each character at 20px, scaled to 8×8. White pixels become palette index 1; dark pixels become index 0 (transparent).

7. **Output**: Everything is packed into Mode 4 format (two palette indices per `u16`) and written to `assets.h` as C arrays. The total palette is written as `game_palette[256]` in 15-bit BGR format (`0BBBBBGGGGGRRRRR`).

---

## Physics & Car Handling

The physics system is ported from the Python version's inertia model, with each car having unique stats:

### Car Stats (from `CarStats` struct)

| Property | Description | Effect |
| :--- | :--- | :--- |
| `top_speed` | Maximum MPH | Converted to pixels/frame: `top_speed / 35.0` |
| `accel` | Acceleration rating (0–100) | Forward acceleration per frame: `(accel / 100) × 0.05` |
| `handling` | Handling rating (0–100) | Lateral acceleration multiplier |
| `braking` | Braking strength (0–100) | Deceleration rate when B is held |
| `fuel_eff` | Fuel efficiency (0–100) | How slowly the fuel tank drains |
| `drag` | Air resistance factor | Coasting deceleration rate |
| `grip` | Lateral friction factor | Multiplied with road friction for turn responsiveness |

### Lateral Movement (Steering)

Each frame:
1. If LEFT held: `vel_x -= 0.15 × (handling/100) × (road_friction/100 × grip)`
2. If RIGHT held: `vel_x += ...` (same formula)
3. Apply friction: `vel_x *= 0.90 × grip`
4. Apply velocity: `player_x += (int)vel_x`
5. Clamp to road boundaries: `ROAD_LEFT (40)` to `ROAD_RIGHT - CAR_W (184)`

### Forward Movement

### Forward Movement & Boost

- **A button (Accelerate)**: `speed += (accel/100) × 0.05` capped at `top_speed/35.0`
- **B button (Brake)**: `speed -= (braking/100) × 0.15` floored at 0
- **Coasting**: `speed -= 0.02 × drag` (only if speed > 2.0)
- **Boost System**: Replaces the old nitro mechanic with a two-tier charge system:
  - **Sustain (L Shoulder)**: 1.25x speed multiplier. Drains meter slowly.
  - **Burst (R Shoulder)**: 1.65x speed multiplier. Drains meter rapidly.
- **Boost Charging**: The meter is charged by performing risky maneuvers (near-misses, high-speed overtakes).

### Vertical Position

The player can also move up/down on screen with D-Pad Up/Down at 2 pixels/frame, clamped to screen bounds. This doesn't affect the scroll speed—it's purely positional.

---

## Traffic AI & Entity System

### Entity Pool

A fixed array of 12 `Entity` structs serves as the entire entity system. Entities are spawned into the first available inactive slot and deactivated when they scroll off-screen or are collected.

### Spawn System

Every frame, `spawn_timer` increments. When it exceeds the threshold (60 frames on Normal, 48 on Hard, scaled by road's `spawn_rate_mult`), a dice roll determines what spawns:

| Roll | Entity | Probability |
|:---|:---|:---|
| 0–64 | Enemy Car | 65% |
| 65–83 | Coin | ~30% of remaining |
| 84–95 | Fuel Can | ~15% of remaining |
| 96–99 | Nitro Bottle | ~5% of remaining |
| Special | Repair Kit | 10% on Easy, 3% on Normal |

Entities spawn at the top of the screen (y = -height) at a random x within the road boundaries.

### AI Behaviors (Ported from Python)

Each enemy is assigned a behavior on spawn based on a random roll (more aggressive on Hard difficulty):

| Behavior | Description | Implementation |
|:---|:---|:---|
| **Normal** | Steady speed, stays in lane | `abs_speed = 1.5` |
| **Speeder** | Moves much faster than normal | `abs_speed = 3.5` |
| **Sudden Braker** | Periodically brakes hard | Timer cycles 0–100; brakes at timer > 70 |
| **Weaver** | Swerves left and right | `x += weave_dir × 1.5` per frame, bounces off road edges |
| **Lane Drifter** | Slowly changes lanes | Gradual lateral movement (Normal difficulty only) |
| **Chaos** | Randomly changes behaviors | Aggressive switching between behaviors (Hard mode only) |

---

## Scoring & Combo System

The GBA version features a sophisticated risk scoring system ported from the "Ultimate" Python edition:

### Risk Maneuvers

- **Near-Miss**: Passing an enemy car at high speed with less than 22 pixels of clearance. (+8 Risk Points, +12 Combo)
- **Overtake**: Successfully passing an enemy. (+22 Risk Points, +6 Combo)
- **Thread the Gap**: Passing between two close enemies. (+22 Risk Points, +10 Combo)
- **Wrong Lane**: Driving in the left side (oncoming) of the road builds combo and risk points every 20 frames.

### Multipliers & Combo

- **Combo Meter**: Builds from 0 to 100 through risky play. Decays over time if no maneuvers are performed.
- **Score Multiplier**: Derived from the combo meter:
  - 0-20: **1x**
  - 21-40: **2x**
  - 41-60: **3x**
  - 61-80: **4x**
  - 81-99: **5x**
  - 100: **6x**
- All risk points are multiplied by this factor before being added to the session score.

The relative visual speed of enemies is: `effective_speed - enemy_abs_speed`, with a minimum of 0.5 px/frame to ensure enemies always move downward on screen.

---

## Collectibles & Items

| Item | Sprite | Size | Effect |
|:---|:---|:---|:---|
| **Coin** | `spr_coin` | 12×12 | +50 score × road risk factor |
| **Fuel Can** | `spr_fuel` | 12×12 | +20 fuel (capped at 100) |
| **Repair Kit** | `spr_repair` | 12×12 | +15 HP (Easy/Normal only, capped at 100) |
| **Nitro Bottle** | — | 12×12 | Activates 1.4× speed boost for ~3.3 seconds |

### Nitro Ramming

While nitro is active (`nitro_boost > 1.2`), colliding with an enemy **destroys the enemy** and awards +100 score instead of dealing damage. Particle effects spawn at the collision point.

---

## Save System (SRAM)

The GBA cartridge has 64 KB of battery-backed SRAM at `0x0E000000`. The game uses a `SaveData` struct:

```c
typedef struct {
  u32 magic;           // "RRGR" (0x52524752) — validates save data
  u32 version;         // Schema version (currently 3)
  u32 high_score;
  u32 total_runs;
  u32 total_playtime_frames;
  u16 level;
  u32 xp;
  u16 cars_unlocked;   // Bitmask of 16 cars
  u32 per_car_best[14];
  u32 per_mode_best[5];
  RunRecord recent_runs[20];
  u8  recent_run_head;
} SaveData;
```

### Save/Load Flow

- **On boot**: `load_game()` reads SRAM byte-by-byte. If the magic number or checksum doesn't match, defaults are initialized and written back.
- **On game over**: If the current score exceeds the stored high score, the new high score is saved immediately via `save_game()`.
- SRAM writes are byte-by-byte because the GBA's SRAM bus is 8-bit only.

---

## Input Handling

The GBA's input register (`REG_KEYINPUT` at `0x04000130`) is **active-low** — bits are 0 when pressed. The game maintains an `InputState` struct updated every frame:

```c
u16 keys_curr = ~REG_KEYINPUT & 0x03FF;  // Invert + mask 10 buttons
input.pressed  = keys_curr & ~input.held; // Just pressed this frame
input.released = input.held & ~keys_curr; // Just released this frame
input.held     = keys_curr;               // Currently held
```

### Control Mapping

| GBA Button | Action |
|:---|:---|
| D-Pad Left/Right | Steer (lateral acceleration) |
| D-Pad Up/Down | Move player car vertically |
| A | Accelerate (increase scroll speed) |
| B | Brake (decrease scroll speed) / Cancel in menus |
| Start | Select in menus / Return to menu from game over |
| L/R | Cycle roads in road select screen |

---

## Particle Effects

When `ENABLE_PARTICLES` is defined (compile-time toggle), the game renders simple 1-pixel exhaust particles:

- **Pool**: 20 particles max.
- **Spawn**: At the player's exhaust (bottom-center of car sprite) with 20% probability per frame, and at enemy exhausts with 5% probability.
- **Nitro exhaust**: Spawns particles every frame while nitro is active.
- **Movement**: Random velocity (vx: -0.5 to 0.5, vy: 1.0 to 3.0 downward). Lifetime: 10–25 frames.
- **Rendering**: Single white pixel plotted in Mode 4 (palette index 1).

---

## Road System

Four roads are available, each with different gameplay characteristics:

| Road | Name | Friction | Traffic | Risk Factor | Spawn Rate |
|:---|:---|:---|:---|:---|:---|
| Road 1 | City Express | 100 | 50 | ×1.0 | 1.0× |
| Road 2 | Industrial | 95 | 75 | ×1.5 | 0.84× (faster) |
| Road 3 | Coastal Run | 102 | 60 | ×1.2 | 0.94× |
| Road 4 | Night Circuit | 90 | 90 | ×2.5 | 0.88× (fastest) |

The road bitmap is 240×160 pixels and scrolls vertically by incrementing a `scroll_y` counter. The `drawBackground()` function copies road pixel data from ROM to VRAM with vertical wrapping at the 160-pixel boundary. Only the road area (x: 40–200) is drawn; the rest of the screen remains black.

---

## Car Roster

All 14 cars are ported from the Python version with balanced stats for the GBA's physics model:

| Car | Top Speed | Accel | Handling | Drag | Grip |
|:---|:---|:---|:---|:---|:---|
| Ferrari | 211 | 95 | 90 | 0.95 | 1.05 |
| Lambo | 211 | 94 | 92 | 0.94 | 1.08 |
| McLaren | 208 | 93 | 88 | 0.93 | 1.02 |
| Audi | 205 | 88 | 95 | 0.96 | 1.06 |
| Mercedes | 202 | 90 | 85 | 0.97 | 1.00 |
| Corvette | 194 | 85 | 82 | 0.98 | 0.98 |
| Veyron | 253 | 98 | 75 | 0.90 | 1.10 |
| CCX | 245 | 92 | 78 | 0.92 | 0.95 |
| Supra | 155 | 60 | 80 | 1.05 | 0.95 |
| Aston | 211 | 89 | 85 | 0.96 | 1.02 |
| Lotus | 180 | 75 | 98 | 0.99 | 1.15 |
| 911 | 205 | 96 | 96 | 0.95 | 1.12 |
| Viper | 206 | 88 | 70 | 0.98 | 0.92 |
| Zonda | 217 | 91 | 89 | 0.94 | 1.04 |

Each car has three sprite variants (normal, left-tilt, right-tilt) generated by the asset pipeline. The displayed sprite changes based on the player's lateral velocity (`vel_x`).

---

## Build System

The project builds with **devkitARM** (devkitPro), the standard open-source GBA toolchain:

```bash
# Build the ROM
make

# Clean build artifacts
make clean
```

### Toolchain

| Tool | Purpose |
|:---|:---|
| `arm-none-eabi-gcc` | C compiler (Thumb interworking, -O2 optimization) |
| `arm-none-eabi-objcopy` | Converts ELF → raw GBA binary |
| `gbafix` | Patches the GBA ROM header for hardware/emulator compatibility |

### Compiler Flags

- `-mthumb-interwork -mthumb` — Generates Thumb (16-bit) code for smaller ROM size and better cache usage.
- `-O2` — Optimization level 2 for speed.
- `-Wall` — All warnings enabled.
- `-fno-strict-aliasing` — Necessary for safe type-punning in VRAM/register access.
- `-specs=gba.specs` — Links against GBA-specific runtime (crt0, memory map).

### Asset Regeneration

To regenerate `assets.h` after modifying any PNG sprites or road images:

```bash
cd gba_project
python convert_assets.py
make clean && make
```

---

## File Structure

```
Testing/
├── main.py                  # Original Python Pygame game
├── settings.py              # Python game constants
├── sprites.py               # Python entity classes
├── systems.py               # Python scoring/boost/progression systems
├── ui.py                    # Python button UI class
├── ai_driver.py             # Python LLM-powered AI driver
├── game_config.json         # Python feature toggle config
├── *.png                    # Shared sprite/road assets
├── *.mp3                    # Audio files (Python only)
│
└── gba_project/
    ├── main.c               # Entire GBA game (~1,493 lines)
    ├── gba.h                # GBA hardware definitions
    ├── assets.h             # Auto-generated asset data
    ├── convert_assets.py    # PNG → C header converter
    ├── Makefile             # devkitARM build config
    ├── RedRacer_Phys.gba    # Compiled ROM (~196 KB)
    ├── RedRacer_Phys.sav    # Emulator save file
    └── docs/
        └── PORT_PARITY.md   # Feature parity tracking
```

---

## Feature Parity Status

### ✅ Fully Ported
- Core gameplay loop (steering, acceleration, braking, scrolling)
- Physics-based car handling with per-car stats (drag, grip, handling, top speed, braking, fuel efficiency)
- Fuel system with drain and refueling
- Health/damage system (Easy mode only)
- 14-car roster with 3 sprite variants each
- 4 road environments with unique gameplay properties and visual previews
- 6 enemy AI behaviors (Normal, Speeder, Weaver, Sudden Braker, Lane Drifter, Chaos)
- 4 collectible types (Coin, Fuel, Repair, Nitro)
- **Scoring System**: Near-miss, overtakes, combo meter, and multipliers (1x-6x)
- **Boost System**: Sustain (L) and Burst (R) modes charged via risky play
- Full menu system (Garage, Road Select, Records, Instructions, Summary)
- 5 game modes (Classic, High Risk, Time Attack, Hardcore, Zen)
- 3 difficulty levels (Easy, Normal, Hard)
- SRAM persistent save data v3 (high scores, records, history, unlocks)
- Particle exhaust effects and screen shake
- Double-buffered 60 FPS rendering

### ⚠️ Partially Ported
- Font system (basic 8×8 bitmap — no proportional fonts)
- Progression system (Unlocks and XP implemented; cosmetic upgrades pending)

### ❌ Not Yet Ported
- Audio (music and sound effects)
- Speed line visual effects
- AI driver mode (the Python version's LLM-based autopilot)

---

*Red Racer Ultimate Edition GBA — ported from Python/Pygame with love for retro hardware.*
