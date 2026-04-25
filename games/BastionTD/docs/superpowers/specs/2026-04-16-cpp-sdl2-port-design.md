# BastionTD C++ SDL2 Port — Ruthless Revised Design Spec

## Executive Verdict

The original spec has a strong direction but is not implementation-safe yet. Its biggest weaknesses are:

1. **Fake portability risk**: the HAL is underspecified and only covers draw/input/audio calls, not the asset, time, save, or debug seams that actually break portability.
2. **Simulation instability risk**: fast forward is currently specified as `delta_time * speed_factor`, which is the classic way to create non-deterministic combat, projectile tunneling, cooldown drift, and platform mismatch.
3. **Balance ambiguity**: several combat rules are vague enough that different implementations will produce materially different difficulty curves.
4. **Missing production rules**: there is no explicit save format, no asset manifest contract, no fixed-step update rule, no targeting priority rules, no map validation contract, and no acceptance criteria.
5. **GBA portability optimism**: the spec says “future GBA/Butano portability” but does not constrain memory, allocations, sprite batching, or text/asset handling tightly enough to make that credible.

This revised spec hardens those weak points and adds explicit engineering constraints so the SDL2 port does not become a dead-end rewrite.

---

## Product Goal

Port the existing Python/Pygame BastionTD tower defense game to C++17 with SDL2 while preserving the current full run loop from title screen to victory/defeat, including menu flow, randomized maps, tower build/upgrade/sell, wave progression, pause, fast forward, end screens, saved run stats, and the 20-wave structure already present in the project. fileciteturn3file4L3-L8 fileciteturn3file5L12-L23

The port must also introduce or formalize the following:
- stable fast forward
- fleet upgrades
- titan damage fix
- character sprite remapping
- explicit 20-wave balance table
- architecture boundaries that keep core logic portable for later GBA/Butano work

---

## Non-Negotiable Engineering Rules

1. **Core simulation must run in a fixed timestep.**
   - Use `SIM_DT = 1.0 / 60.0`.
   - Never multiply gameplay dt directly by 2x or 3x. Run multiple fixed simulation ticks per rendered frame instead.
   - Fast forward means 1, 2, or 3 simulation steps per render frame budget, not inflated dt.

2. **Core logic must be deterministic from a seed.**
   - Given the same RNG seed and the same input sequence, wave outcomes must match across runs.
   - Random map generation, enemy spawn intervals, and decorative placement must all use a single explicit RNG stream.

3. **`core/` must remain platform-clean.**
   - No SDL headers.
   - No filesystem APIs.
   - No wall-clock reads.
   - No dynamic asset lookup by path.
   - No heap churn inside hot loops unless justified and measured.

4. **All asset references must be symbolic IDs, not file paths.**
   - Asset loading belongs to the platform/application layer.
   - Core requests `SpriteId::ArrowTowerBase`, not `assets/towers/arrow.png`.

5. **Portability claims must be enforced by constraints.**
   - Assume later GBA-like limits during design: low sprite count, low text complexity, no runtime font rasterization, low allocation pressure, fixed tile grid, fixed virtual resolution.

---

## Revised Architecture

### Top-Level Layout

```text
src/
├── app/
│   ├── app.h/cpp                 # app bootstrap, main loop, state switching
│   ├── asset_catalog.h/cpp       # maps symbolic IDs to loaded SDL resources
│   ├── save_service.h/cpp        # platform-side save/load bridge
│   └── telemetry.h/cpp           # optional perf/debug counters
├── hal/
│   ├── hal.h                     # interfaces only
│   ├── sdl2_renderer.h/cpp
│   ├── sdl2_input.h/cpp
│   ├── sdl2_audio.h/cpp
│   ├── sdl2_clock.h/cpp
│   └── sdl2_storage.h/cpp
├── core/
│   ├── types.h
│   ├── ids.h                     # enums for towers, enemies, sprites, sounds, states
│   ├── config.h
│   ├── rng.h
│   ├── fixed.h                   # fixed-point helpers if needed for portability
│   ├── math.h
│   ├── grid.h/cpp
│   ├── map_generator.h/cpp
│   ├── pathfinding.h/cpp
│   ├── combat_rules.h/cpp
│   ├── tower.h/cpp
│   ├── enemy.h/cpp
│   ├── projectile.h/cpp
│   ├── effect.h/cpp
│   ├── wave_manager.h/cpp
│   ├── economy.h/cpp
│   ├── save_data.h
│   ├── game_session.h/cpp
│   └── game_renderer_model.h/cpp # render-ready snapshot structs, no SDL
├── states/
│   ├── state.h
│   ├── title_state.h/cpp
│   ├── instructions_state.h/cpp
│   ├── settings_state.h/cpp
│   ├── gameplay_state.h/cpp
│   ├── pause_state.h/cpp
│   ├── game_over_state.h/cpp
│   └── victory_state.h/cpp
└── main.cpp
```

### Ruthless correction to the original HAL

The original HAL only exposes drawing, input, and audio. That is not enough. A thin HAL that ignores time and storage is not a portable boundary; it is a rendering wrapper. The original design says the architecture uses a thin HAL for future GBA/Butano portability, but only specifies renderer/input/audio interfaces and keeps SDL out of `core/`. fileciteturn3file1L5-L37 That is a good start, but not enough.

### HAL Interfaces

#### `IRenderer`
- `begin_frame()`
- `draw_sprite(SpriteDrawCmd cmd)`
- `draw_rect(RectDrawCmd cmd)`
- `draw_text(TextDrawCmd cmd)`
- `end_frame()`

#### `IInput`
- `poll()`
- `pressed(Action a)`
- `held(Action a)`
- `released(Action a)`

#### `IAudio`
- `play_sfx(SfxId id)`
- `play_bgm(BgmId id, bool loop)`
- `stop_bgm()`
- `set_sfx_enabled(bool)`
- `set_bgm_enabled(bool)`

#### `IClock`
- `frame_delta_seconds()`
- `frame_counter()`

#### `IStorage`
- `save_bytes(slot, data)`
- `load_bytes(slot)`
- `exists(slot)`

### Additional rule

`core/` can produce render commands and consume abstract actions and save payloads, but it must never know how files, textures, or audio are implemented.

---

## Main Loop Contract

### Fixed-Step Loop

```cpp
accumulator += real_frame_dt;
while (accumulator >= SIM_DT) {
    poll_input_once_for_frame();
    run_simulation_step(SIM_DT);
    accumulator -= SIM_DT;
}
render(interpolation_alpha);
```

### Fast Forward Contract

The original spec says fast forward should multiply `delta_time` by a speed factor and scale all systems with that dt. fileciteturn3file3L29-L35 That is a bug factory.

Replace it with:
- 1x = run 1 sim step per update budget
- 2x = run 2 sim steps per update budget
- 3x = run 3 sim steps per update budget
- clamp max steps per frame to avoid spiral-of-death
- if rendering falls behind, simulation remains stable and visual frame rate may drop rather than corrupt gameplay

### Why this matters

If you scale dt directly:
- projectiles can skip collision
- DoT and cooldown timers drift
- heal/slow durations become inconsistent
- balance differs between desktop and later handheld targets

---

## State Machine

The project status file already confirms title, instructions, settings, pause, game over, and victory flow exist and are part of the product. fileciteturn3file5L12-L23 The original port spec omits `instructions_state` and `settings_state` from the file tree despite mentioning them in the title menu. fileciteturn3file1L25-L31 fileciteturn3file3L75-L81 That is sloppy and should be fixed.

### Required states
- Title
- Instructions
- Settings
- Gameplay
- Pause
- GameOver
- Victory

### State responsibilities
- **Title**: new game, instructions, settings, quit
- **Instructions**: controls, enemy roster, tower roles, phase loop
- **Settings**: visual mode, sound effects, music, performance counter, defaults restore
- **Gameplay**: build phase, wave phase, HUD, map, towers, enemies, economy, boss bar
- **Pause**: resume, restart run, quit to title
- **GameOver**: summary stats, retry, title
- **Victory**: summary stats, retry, title

---

## Save Data Contract

The project currently saves best wave reached, highest gold-earned score, and total runs played. fileciteturn3file5L8-L11 The original port spec mentions none of the serialization details. That is a hole.

### `SaveData`
```cpp
struct SaveData {
    uint32_t version;
    uint32_t best_wave_reached;
    uint32_t highest_gold_earned;
    uint32_t total_runs_played;
    uint32_t checksum;
};
```

### Rules
- Include a version field for forward compatibility.
- Include a checksum or simple validation guard.
- Corrupt save must fall back safely to defaults.
- Save only on run end or settings change, not every frame.

---

## Core Gameplay Data Model

### Grid and Coordinates
- Virtual screen: `240x160`
- Tile size: `8x8`
- Grid: `30x16`
- HUD rows: `0-1`
- Playfield rows: `2-13`
- Tray rows: `14-15`

### Coordinate rule
- Simulation uses tile coordinates and sub-tile fixed-point or integer world units.
- Rendering converts simulation coordinates to pixels.
- Do not mix “tiles” and “pixels” casually in combat code.

---

## Map Generation Contract

The project status file says each battlefield is randomized and every spawn route is validated so the base is always reachable. fileciteturn3file4L12-L19 The original port spec mentions `map_generator` and path validation in spirit, but does not define failure rules, spawn counts, or placement constraints. fileciteturn3file4L41-L48

### Required guarantees
1. Base is on the right side.
2. One or two spawn points are on the left side.
3. Every spawn has at least one valid path to base.
4. Towers cannot be placed on:
   - path tiles
   - spawn tiles
   - base tile
   - decorative blockers
   - HUD/tray rows
5. Tower placement during gameplay must not invalidate path reachability.
   - If dynamic blocking is allowed, path must be revalidated before confirming placement.
   - If dynamic blocking is not allowed, path tiles are simply non-buildable.

### Recommendation
For this project, **do not allow path-blocking tower placement**. It increases complexity, breaks balance assumptions, and is unnecessary for a compact retro TD.

---

## Tower System

The original tower roster and three-level structure align with the current project state. fileciteturn3file4L28-L35 The numeric table is mostly usable, but the spec is missing targeting priority, attack cadence semantics, and how effects stack.

### Canonical tower stats

| Tower | Char | Cost | Lv1 Dmg | Lv2 Dmg | Lv3 Dmg | Cooldown | Range | Special |
|-------|------|------|---------|---------|---------|----------|-------|---------|
| Arrow | char_2 | 50g | 1 | 3 | 5 | 0.6s | 3.5 tiles | single target |
| Cannon | char_3 | 100g | 3 | 6 | 10 | 1.5s | 2.5 tiles | splash 1.2 tiles, splash deals 50% |
| Ice | char_2 | 75g | 0.5 | 1 | 2 | 0.8s | 3.0 tiles | applies slow |
| Lightning | char_4 | 150g | 2 | 4 | 7 | 1.0s | 4.0 tiles | chain hits |
| Flame | char_3 | 125g | 1 | 2 | 3 | 0.2s | 2.0 tiles | applies burn |

Source values preserved from the original spec. fileciteturn3file1L41-L49

### Upgrade costs

| Tower | Lv1→2 | Lv2→3 |
|-------|-------|-------|
| Arrow | 30g | 50g |
| Cannon | 60g | 90g |
| Ice | 45g | 70g |
| Lightning | 90g | 130g |
| Flame | 75g | 110g |

Sell value = 50% of total invested, rounded down. Preserve this from current design. fileciteturn3file6L1-L7

### Required targeting rule
Every tower must use one explicit targeting mode. Default mode:
1. enemy closest to base by path progress
2. tie-break by lowest remaining path distance
3. tie-break by earliest spawn sequence

Do **not** leave this implicit. “Targeted enemy” is mentioned in rendering notes, but target selection is not actually defined in the original spec. fileciteturn3file6L1-L7

### Required cadence rule
- Cooldown counts down in fixed ticks.
- A tower acquires or refreshes target when ready to fire.
- If target leaves range before shot spawn, tower retargets once; otherwise shot is skipped.

### Required projectile rule
- Arrow, Cannon, Ice, and Flame use explicit projectiles.
- Lightning may use instant chain resolution without a traveling projectile.
- Projectile collision must be step-safe under fast forward.

### Character-on-tower rendering
Preserve the flavor feature from the original spec:
- character sprite drawn over tower base
- sprite horizontally flips toward current target
- fire bob animation up 2 px for 100 ms on shot
- mapping: `char_2` arrow/ice, `char_3` cannon/flame, `char_4` lightning fileciteturn3file6L1-L7

This is a good visual idea. Keep it. Just do not let this bleed into gameplay classes.

---

## Enemy System

The current enemy roster also matches project status. fileciteturn3file5L1-L7 The original numeric table is acceptable as a first pass. fileciteturn3file6L8-L20 But “speed”, “armor”, and “heal” need exact semantics.

### Canonical enemy stats

| Enemy | Char | Scale | HP | Speed | Armor | Gold | Special |
|-------|------|-------|----|-------|-------|------|---------|
| Goblin | char_0 | 1.0x | 3 | 2.0 tiles/s | 0 | 5g | baseline |
| Wolf | char_1 | 1.0x | 2 | 3.5 tiles/s | 0 | 8g | fast |
| Knight | char_0 | 1.2x | 8 | 1.2 tiles/s | 2 | 15g | armored |
| Healer | char_1 | 1.1x | 4 | 2.0 tiles/s | 0 | 12g | heals allies |
| Swarm | char_1 | 0.7x | 1 | 3.0 tiles/s | 0 | 2g | fodder |
| Titan | char_0 | 2.5x | 50 | 0.8 tiles/s | 3 | 100g | boss, leaks for 5 lives |

Source values preserved from the original spec. fileciteturn3file6L8-L20

### Armor rule
`final_hit_damage = max(minimum_hit_damage, raw_hit_damage - armor)`

### Titan damage fix
Preserve the intended fix from the original design:
1. burn/DoT bypasses armor
2. minimum hit damage is 1 for direct hits fileciteturn3file6L21-L28

### Critical addition: separate direct-hit and DoT minimum rules
- direct hits: minimum 1 damage after armor
- DoT: no minimum tick floor unless explicitly desired

Reason: if DoT both bypasses armor and also inherits a minimum 1 floor, flame becomes absurdly efficient against bosses.

### Healing rule
- healer pulse every `0.5s`
- restores `0.5 HP` per pulse to allies within 2.0 tiles
- cannot overheal above max HP
- does not heal itself unless explicitly stated

The original “1 hp/s” is fine conceptually, but per-frame healing is vague and makes balance dependent on implementation. fileciteturn3file6L29-L33

---

## Status Effects

The original spec says slow is multiplicative, DoT can stack up to 3, and healer effects exist. fileciteturn3file6L29-L33 That is still too vague.

### Slow
- Only the strongest slow applies.
- No multiplicative stacking of multiple slow sources.
- Duration refreshes if a stronger or equal slow is reapplied.

Reason: multiplicative stacking is the fast route to accidental perma-freeze balance nonsense.

### Burn / DoT
- Up to 3 stacks.
- Each stack has its own remaining duration.
- Reapplying burn adds one stack up to cap, then refreshes oldest-expiring stack.
- Tick interval: `0.25s`
- Burn bypasses armor.

### Chain lightning
- Bounce count: 2 / 3 / 4 by level
- Bounce falloff: 70% of previous hit
- Can hit each enemy at most once per shot
- Bounce search radius: 1.75 tiles from previous target

This was partially present in the original tower table but needed exact execution rules. fileciteturn3file1L41-L49

### Cannon splash
- Full damage to primary target
- 50% damage to secondary targets in 1.2 tile radius
- secondary targets do not recursively splash

---

## Wave System

The project already uses 20 waves with bosses on 5, 10, 15, and 20. fileciteturn3file5L8-L11 The original wave table is serviceable, but the “Est. Gold” values appear inconsistent with the listed enemy rewards in at least some cases, which means they are either inaccurate or mixing kill gold and bonus gold without saying so. fileciteturn3file2L6-L27 That is the kind of sloppiness that ruins balancing discussions.

### Fix
Replace “Est. Gold” with explicit fields:
- `Kill Gold`
- `Perfect Bonus Gold`
- `Total Perfect Gold`

Do not carry fuzzy estimate columns in a balancing spec.

### Wave table (composition preserved, gold columns to be recomputed from canonical enemy values)

| Wave | Composition | Boss |
|------|-------------|------|
| 1 | 4 Goblin | No |
| 2 | 6 Goblin | No |
| 3 | 3 Goblin, 3 Wolf | No |
| 4 | 8 Wolf | No |
| 5 | 4 Knight, 1 Titan | Yes |
| 6 | 10 Goblin, 5 Wolf | No |
| 7 | 6 Knight, 2 Healer | No |
| 8 | 15 Swarm, 4 Wolf | No |
| 9 | 6 Knight, 3 Healer, 8 Swarm | No |
| 10 | 8 Knight, 2 Healer, 1 Titan | Yes |
| 11 | 20 Swarm, 4 Knight | No |
| 12 | 6 Knight, 4 Healer, 10 Swarm | No |
| 13 | 8 Knight, 6 Wolf, 4 Healer | No |
| 14 | 30 Swarm, 6 Knight | No |
| 15 | 10 Knight, 4 Healer, 1 Titan | Yes |
| 16 | 8 Knight, 10 Wolf, 20 Swarm | No |
| 17 | 12 Knight, 6 Healer, 15 Swarm | No |
| 18 | 40 Swarm, 8 Knight, 4 Healer | No |
| 19 | 10 Knight, 8 Healer, 10 Wolf, 20 Swarm | No |
| 20 | 12 Knight, 6 Healer, 30 Swarm, 2 Titan | Yes (double titan) |

Composition preserved from the original spec. fileciteturn3file2L6-L27

### Spawn pacing contract
Each wave also needs:
- spawn interval per enemy type or per wave
- optional pre-delay before first spawn
- optional boss-entry delay / audio cue

Without this, identical compositions can feel wildly different.

### Build phase rule
- next wave starts manually
- build phase always runs at 1x
- fast forward resets to 1x when build phase begins, matching existing intent fileciteturn3file3L29-L35

---

## Fleet Upgrade System

The original idea is good but overpriced and slightly awkward. It says fleet upgrades unlock at waves 5, 10, and 15, and cost the sum of individual upgrades multiplied by 1.25. fileciteturn3file2L37-L42 That multiplier makes the feature feel like a convenience tax rather than a strategic system.

### Revised fleet upgrade rule
- unlocks after clearing waves 5, 10, and 15
- available only during build phase
- upgrades all towers of selected type below target tier
- cost = `sum(individual missing upgrade costs) * 1.10`, rounded up
- cannot partially apply; either all eligible towers upgrade or none do

### Why change 1.25 to 1.10
At 1.25 the player is punished for using the feature. That makes it a UX shortcut, not a real mechanic. The fee should be enough to preserve choice, not enough to make the option stupid.

### UI rule
- show current eligible tower count
- show total cost before confirm
- grey out unavailable option if no eligible towers

---

## Economy

The current project starts with 200 gold and 20 lives, pays kill gold, allows selling at 50%, and penalizes titan leaks harder. fileciteturn3file4L17-L25 fileciteturn3file5L1-L11 The original spec also keeps those numbers. fileciteturn3file3L37-L43 Good. Keep them.

### Canonical economy rules
- starting gold: 200
- starting lives: 20
- normal leak: -1 life
- titan leak: -5 lives
- sell refund: floor(50% of total invested)
- perfect wave bonus: +25 gold only if no leaks

### Add this missing rule
- upgrading or selling is only allowed during build phase

This matches the current run structure and avoids panic-click balance exploits. The project status already frames the game around short build phases followed by active defense phases. fileciteturn3file4L3-L8

---

## Input Mapping

The original input map is mostly reasonable. fileciteturn3file3L45-L53 But one detail is weak: binding fleet upgrade to `L+R` on GBA is not ideal because shoulder combos can be awkward and conflict with cycling.

### Revised input map

| Action | Keyboard | GBA |
|--------|----------|-----|
| Move cursor | Arrow keys | D-pad |
| Confirm / Place / Start Wave | Z / Enter | A |
| Cancel / Back / Upgrade / Sell prompt | X | B |
| Cycle tower type left/right | A / S | L / R |
| Fast forward | Tab | Select |
| Pause | Escape | Start |
| Fleet menu open | F | Select + L |
| Fleet confirm | Z | A |

### Why
A single explicit “open fleet menu” action is cleaner than overloading L+R while those same buttons are already used for cycling.

---

## Rendering Rules

The original rendering section is directionally good: 240×160, nearest-neighbor scaling, 8×8 tiles, layered draw order, bitmap font, palette discipline. fileciteturn3file3L55-L74 Keep that.

### Additional rules
- SDL renderer must use integer scaling and nearest sampling.
- All gameplay rendering is authored for the virtual resolution, then scaled.
- No camera movement.
- No subpixel sprite rendering unless intentionally enabled for projectiles/effects.

### Sprite budget correction
The original mentions ~40 active sprites against a GBA OAM limit of ~128. fileciteturn3file3L61-L68 The raw count is not the only issue. What matters is worst-case on-screen object pressure.

### Budget targets
- enemies visible at once: target ≤ 24
- towers visible at once: target ≤ 12
- projectiles/effects visible at once: target ≤ 24 equivalent sprite units
- boss bar and HUD must remain tile-based/UI-based, not sprite-spammed

### Render order
Preserve original order with one addition:
1. terrain
2. blocked/buildable overlay if toggled
3. path overlay
4. tower bases
5. enemies Y-sorted
6. tower characters
7. projectiles
8. particles/effects
9. HUD
10. pause/menu overlays

---

## Asset Pipeline Contract

This was missing entirely.

### Rules
- all sprites use power-of-two atlas packing where sensible
- sprite IDs are enumerated in code
- no runtime directory scanning
- font is bitmap-only
- sound IDs are symbolic
- palette-friendly art style remains mandatory even in SDL build

### Required asset groups
- terrain tiles
- blocker/decor tiles
- tower bases
- character overlays
- enemy sprites
- projectile sprites
- HUD icons
- title/menu assets
- SFX and BGM manifest

---

## Audio Rules

The original spec names audio interfaces but does not define behavior. fileciteturn3file1L33-L37 Add these rules:
- one looping BGM track at a time
- SFX categories: UI, shot, impact, leak, wave start, boss intro, victory, defeat
- settings menu must independently toggle music and SFX, consistent with current project status fileciteturn3file5L8-L11
- audio calls from core should be event-driven, not direct playback logic scattered everywhere

---

## Debug and Test Hooks

This was absent and is a mistake.

### Required debug toggles
- show FPS / frame time
- show sim tick count
- show path progress on enemies
- show tower ranges
- show buildable/non-buildable tiles
- show current RNG seed

### Test scenarios
1. deterministic replay test from fixed seed
2. titan damage test proving every tower can contribute
3. fast-forward parity test: same outcome at 1x vs 3x from same seed/input
4. path validation test on 1000 generated maps
5. save/load corruption fallback test
6. perfect wave bonus correctness test
7. fleet upgrade cost correctness test

If you do not define tests, this port will drift.

---

## Acceptance Criteria

The port is only “done” when all of the following are true:

1. Full run from title to victory/defeat works with all required menus and settings, matching the current project’s stated flow. fileciteturn3file5L12-L23
2. 20-wave structure, bosses on 5/10/15/20, and save stats are present. fileciteturn3file5L8-L11
3. Fast forward does not alter deterministic outcome relative to 1x under the same seed and inputs.
4. All tower types can damage titans in a practical sense.
5. No tower placement can create an unreachable map state.
6. Core compiles with no SDL includes.
7. Save data persists and survives version check/corruption fallback.
8. Instructions and settings states exist, not just menu stubs.
9. Performance is stable at target content load on desktop.
10. Architecture remains ready for later GBA/Butano migration without rewriting game logic.

---

## Build System

The original CMake stub is fine as a seed, but too bare. fileciteturn3file3L82-L87

### Required build rules
- C++17 minimum
- warnings enabled on all targets
- separate `core`, `hal`, `app`, and executable targets
- debug and release presets
- asset copy step for SDL build

### Suggested CMake skeleton

```cmake
cmake_minimum_required(VERSION 3.16)
project(BastionTD LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

find_package(SDL2 REQUIRED)

add_library(core
    src/core/grid.cpp
    src/core/map_generator.cpp
    src/core/pathfinding.cpp
    src/core/combat_rules.cpp
    src/core/tower.cpp
    src/core/enemy.cpp
    src/core/projectile.cpp
    src/core/effect.cpp
    src/core/wave_manager.cpp
    src/core/economy.cpp
    src/core/game_session.cpp
)

target_include_directories(core PUBLIC src)

add_library(hal
    src/hal/sdl2_renderer.cpp
    src/hal/sdl2_input.cpp
    src/hal/sdl2_audio.cpp
    src/hal/sdl2_clock.cpp
    src/hal/sdl2_storage.cpp
)

target_include_directories(hal PUBLIC src)
target_link_libraries(hal PUBLIC SDL2::SDL2)

add_library(app
    src/app/app.cpp
    src/app/asset_catalog.cpp
    src/app/save_service.cpp
)

target_include_directories(app PUBLIC src)
target_link_libraries(app PUBLIC core hal)

add_executable(BastionTD src/main.cpp)
target_link_libraries(BastionTD PRIVATE app)
```

---

## Final Hard Recommendation

Keep **SDL2 for the desktop port**, but enforce this revised architecture or the project will quietly rot into a one-platform implementation with “portable” comments lying to your face.

The strongest decisions in the original spec were:
- core/platform separation
- fixed virtual resolution
- tile-first rendering discipline
- explicit wave roster
- GBA portability intent

The weakest decisions were:
- dt scaling for fast forward
- vague combat semantics
- incomplete state list
- no save/data contract
- no test/acceptance criteria
- convenience-tax fleet upgrade pricing

Those weaknesses are now patched in this revised version.
