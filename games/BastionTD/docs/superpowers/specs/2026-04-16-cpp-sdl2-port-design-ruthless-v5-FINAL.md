# BastionTD C++ SDL2 Port — Ruthless Revised Design Spec (Final Hardened v5)

## Third Ruthless Review Pass — Final Structural Hardening

This is the final addendum. After this, the spec is complete. Further additions without implementation are spec-hoarding, not engineering.

---

### 10. Explicit Simulation Tick Order

The v4 correctly identifies this as critical. The ordering is almost right but has two gaps: healer pulse resolution is missing, and economy/bonus resolution is lumped vaguely into "deaths / leaks / rewards" without specifying order of operations.

#### Canonical Tick Order

```
 1. Process deferred spawns (from overflow queue)
 2. Spawn new enemies due this tick (wave roster → pool)
 3. Tick enemy status effects (decrement durations, apply burn damage, apply slow)
 4. Resolve healer pulses (heal allies in range, respecting max HP cap)
 5. Update enemy movement (apply speed × slow modifier × SIM_DT along cached path)
 6. Check enemy leaks (enemy path progress >= 1.0 → deduct lives, deactivate, emit event)
 7. Check defeat condition (lives <= 0 → transition to DefeatPending)
 8. Acquire/refresh tower targets (closest-to-base by path progress, tie-break rules)
 9. Fire ready towers (cooldown expired + valid target → spawn projectile, emit event)
10. Update projectile movement (advance position toward target/destination)
11. Resolve projectile hits (collision check, apply damage/splash/chain/effects)
12. Resolve enemy deaths (HP <= 0 → award gold, deactivate, emit event)
13. Check wave completion (all roster spawned + all enemies dead/leaked → WaveCleanup)
14. Award perfect wave bonus (if no leaks this wave, +25g, emit event)
15. Advance phase state machine (countdown timers, cleanup timers, pending timers)
16. Flush event log write head (mark end-of-tick boundary for consumers)
```

#### Rules
- This order is canonical. Changing it changes balance. Document any reordering in a commit message with justification.
- Steps 6-7 (leak check before towers fire) means enemies that reach the base on the same tick they would have been killed are counted as leaks. This is intentional — it rewards placing towers earlier on the path rather than relying on last-second kills.
- Step 12 happens after all projectile resolution in the same tick, meaning an enemy can be hit by multiple projectiles in one tick and die from cumulative damage. This is correct and expected.
- Healer pulse (step 4) happens before movement (step 5) and before combat (steps 8-12). This means healing applies to the formation as it existed at tick start, not after repositioning or damage. This is the least surprising behavior.

---

### 11. Floating-Point Discipline

The v4 says "may use float initially" and "mark with comments." That is discipline-by-hope. Comments don't enforce anything and will be ignored within two weeks. Here is what actually works:

#### Strategy: float now, constrained for migration

The SDL2 build uses `float` for all simulation math. This is the pragmatic choice — the game needs to ship on desktop first.

#### Concrete constraints
1. **All simulation math routes through `core/math.h` helper functions.** No raw `+`, `-`, `*`, `/` on floats in gameplay code. Use `sim_mul(a, b)`, `sim_div(a, b)`, etc. These are trivial inline wrappers around float today. When the GBA port happens, you replace the implementations with fixed-point and nothing else changes.

```cpp
// core/math.h — today (SDL2 build)
inline float sim_mul(float a, float b) { return a * b; }
inline float sim_div(float a, float b) { return a / b; }
inline int   sim_to_int(float a)       { return static_cast<int>(a); }

// core/math.h — future (GBA build)
// Replace with Q16.16 or Q8.8 fixed-point equivalents
```

2. **Never compare floats with `==`.** Use `sim_approx_eq(a, b, epsilon)` with a defined epsilon constant in `config.h`. The main spec already implies this but it was never stated explicitly.

3. **Simulation coordinates use tile units (float), not pixel units (int).** Pixel conversion happens only in the render snapshot builder. This is already in the main spec but repeated here because violating it is the #1 way float precision issues leak into gameplay.

4. **No `double` anywhere in `core/`.** Fixed-point migration from `float` is straightforward. Migration from `double` is painful because the precision expectations are different.

#### What this replaces
Delete the `// FIXED_POINT_PORT_NOTE` comment approach from v4. If the migration boundary is in the code (math.h wrappers), comments add nothing. If the migration boundary is NOT in the code, comments won't save you.

---

### 12. Versioned Balance Hashing

The v4 is directionally right but doesn't specify how the hash is computed.

#### Hash computation
- At build time, the same `gen_balance.py` script that produces `balance_data.h` also produces a `balance_hash.h` containing a single `constexpr uint32_t BALANCE_HASH = 0xABCD1234;`
- The hash is computed as CRC32 over the raw bytes of `balance.toml` concatenated with the string representation of `SIM_DT` and the build version string.
- CRC32 is sufficient. This is not cryptographic — it is a quick mismatch detector for replay validation.

#### Replay compatibility rule
- Replay header stores `BALANCE_HASH`.
- On playback, if stored hash ≠ current hash, refuse playback with message: "Replay incompatible: balance data has changed since recording."
- Do not attempt partial compatibility. Balance changes invalidate all prior replays. This is correct and simple.

---

### 13. Unit Test Matrix (Hardened)

The v4 list is a good start but has gaps. Here is the complete required set, organized by system.

#### Pathfinding
- BFS returns shortest path on a known 5×5 grid
- BFS returns failure on a grid with no valid path
- Path does not traverse blocked tiles
- Multi-spawn: both spawns have valid paths

#### Map Generation
- 100 seeds all produce reachable maps
- Base is on right edge
- Spawn(s) are on left edge
- No path tile overlaps with blocker tiles
- Retry budget: generator with an intentionally broken config hits retry limit and falls back

#### Combat
- Armor formula: `max(1, raw - armor)` for direct hits
- Armor formula: burn bypasses armor, no minimum floor
- Burn stacking: 3 stacks max, 4th refreshes oldest
- Slow: strongest-wins, duration refreshes on reapply
- Chain lightning: never hits same enemy twice, respects bounce radius
- Splash: 50% to secondaries, no recursive splash
- Minimum 1 damage on direct hit ensures every tower can chip titans

#### Economy
- Kill gold matches canonical enemy table
- Sell refund = `floor(total_invested * 0.5)`
- Perfect wave bonus: +25g when zero leaks, 0g when any leaks
- Fleet upgrade cost = `ceil(sum_of_missing_upgrades * 1.10)`
- Starting gold = 200, starting lives = 20

#### Wave System
- Wave composition matches canonical table for all 20 waves
- Spawn interleaving is deterministic from seed
- Boss waves (5, 10, 15, 20) contain correct titan count

#### Save/Load
- Valid save round-trips correctly
- Corrupted checksum → fallback to defaults
- Version mismatch → migration or reset (see #17)
- Missing save file → defaults, no crash

#### Pools
- Enemy pool at capacity: spawn defers to queue
- Spawn queue at capacity: excess permanently dropped
- Projectile pool at capacity: shot silently skipped
- Effect pool at capacity: cosmetic FX dropped, status visuals unaffected

#### Replay
- Same seed + same inputs → identical frame-by-frame state
- Hash mismatch → playback refused

---

### 14. Integration Test Matrix (Hardened)

The v4 mentions "autoplay" without defining what it means. Autoplay is a scripted bot, not random inputs.

#### Autoplay bot definition
A minimal bot that:
1. Waits in build phase
2. Places the cheapest affordable tower on the first valid buildable tile (scanning left-to-right, top-to-bottom)
3. Starts wave
4. Repeats

This is not a smart strategy. It does not need to be. Its purpose is to exercise the full game loop under deterministic conditions.

#### Required integration tests

| Test | Method | Pass Condition |
|------|--------|----------------|
| Full autoplay run | Autoplay bot, seed 12345 | Reaches wave 20 or game over without crash/hang, final state matches recorded baseline |
| Fast-forward parity | Autoplay at 1x, 2x, 3x on seed 12345 | Identical tick-by-tick simulation state at all speeds |
| Map stress | Generate 1000 maps from sequential seeds | All produce valid paths, zero retry-limit fallbacks |
| Peak pool stress | Manually craft wave 20 scenario with max enemies + max towers firing | Zero pool overflow, frame time < 2ms |
| Save lifecycle | Save on run end → restart → load | Loaded values match saved values |
| State transition soak | Script: start game → pause → resume → pause → quit to title → new game → win/lose, 50 iterations | Zero crashes, zero leaked state |
| Telemetry output | Autoplay run, debug build | CSV file produced, parseable, row count = wave count + 1 |

---

### 15. Debug Cheat Harness (Hardened)

The v4 lists commands but doesn't specify the interface.

#### Interface
- Debug commands are triggered by keyboard shortcuts, **not** a text console. A console requires text input parsing, which is complexity this project does not need.
- All debug shortcuts use `Ctrl+Shift+<key>` to avoid collision with gameplay inputs.
- Debug shortcuts are compiled out in release builds via `#ifdef BASTION_DEBUG`.

#### Command table

| Shortcut | Command | Behavior |
|----------|---------|----------|
| Ctrl+Shift+W | Skip to wave N | Prompts N via cycling (press repeatedly to increment, confirm to jump) |
| Ctrl+Shift+G | Add 500 gold | Instant |
| Ctrl+Shift+K | Kill all enemies | Instant, awards gold, emits events |
| Ctrl+Shift+T | Force titan spawn | Spawns one titan at first spawn point |
| Ctrl+Shift+I | Toggle invincibility | Lives cannot decrease |
| Ctrl+Shift+B | Toggle infinite build | Can place/upgrade without gold cost |
| Ctrl+Shift+M | Regenerate map | New seed, regenerate, restart run |
| Ctrl+Shift+S | Step one tick | Only works when paused. Advances simulation by exactly one tick. Essential for debugging targeting and collision. |
| Ctrl+Shift+H | Halve speed | 0.5x (run one sim tick every 2 render frames). Useful for watching projectile behavior. |

#### The one the v4 missed: frame stepping
Single-tick stepping while paused is the most valuable debug tool in any real-time simulation. Without it, you cannot observe what happens at tick granularity, and you will waste hours adding print statements to debug targeting or collision edge cases.

---

### 16. Asset Validation Rules (Hardened)

The v4 lists checks but doesn't specify when they run or what the fallbacks look like.

#### When validation runs
- **Build time** (in `gen_balance.py` or a separate `validate_assets.py`): checks atlas ID uniqueness, tile dimensions, palette compliance. Build fails on error.
- **Runtime load** (in `AssetCatalog::load()`): checks that every `SpriteId` enum value has a corresponding loaded texture region. Missing → magenta fallback. Duplicate → assert in debug, silent in release.

#### Magenta fallback specification
- A single 8×8 magenta (`#FF00FF`) tile, pre-baked into the binary as a constexpr array (not loaded from disk).
- Any missing sprite renders as this tile. It is visually unmissable, which is the point.
- Missing SFX → silent stub (function returns immediately). Missing BGM → silent stub with a one-time debug log warning.

#### Why palette compliance matters now
The main spec says "palette-friendly art style remains mandatory." But without a validation check, non-compliant art will slip in during development and create a painful batch-conversion problem when the GBA port starts. Check at build time: every PNG in the asset directory must use ≤ 16 colors from the defined palette. Warn on violation, fail on flag `--strict-palette`.

---

### 17. Save Migration Rules (Hardened)

The v4 says "transform forward" without defining how. Here is the concrete policy.

#### Migration strategy: version-gated field addition

```cpp
// Save versions and their fields:
// v1: best_wave_reached, highest_gold_earned, total_runs_played
// v2 (hypothetical): + total_enemies_killed, + best_seed
// v3 (hypothetical): + difficulty_mode

SaveData migrate(const uint8_t* raw, uint32_t version) {
    SaveData out = SaveData::defaults();
    if (version >= 1) {
        out.best_wave_reached   = read_u32(raw, offset_v1_wave);
        out.highest_gold_earned = read_u32(raw, offset_v1_gold);
        out.total_runs_played   = read_u32(raw, offset_v1_runs);
    }
    if (version >= 2) {
        out.total_enemies_killed = read_u32(raw, offset_v2_kills);
        out.best_seed            = read_u32(raw, offset_v2_seed);
    }
    // Fields not present in older versions keep their defaults
    return out;
}
```

#### Rules
- New fields are always appended. Never reorder or remove existing fields.
- Every new field has a sensible default (zero, or the neutral value for its type).
- If the version number is higher than the current build knows about (downgrade scenario), reset to defaults and log a warning.
- If the checksum fails, reset to defaults. Do not attempt to salvage partially corrupt data.
- Maximum save size: 256 bytes. This leaves room for ~50 future uint32 fields, which is more than this game will ever need. Hard-cap it so the IStorage implementation knows the upper bound.

---

### 18. Definition of Done Gate (Hardened)

The v4 is right that "coded ≠ done." But "telemetry verified" and "replay deterministic" need concrete pass/fail criteria, not vibes.

#### Feature completion checklist

A feature is complete when ALL of the following are true:

| Gate | Pass Criteria |
|------|---------------|
| Implemented | Feature works as described in this spec in a manual playthrough |
| Unit tested | All relevant unit tests from section #13 pass |
| Integration tested | Autoplay bot completes a full run without regression |
| Determinism verified | Fast-forward parity test passes (1x vs 3x, same seed → same state) |
| Performance verified | No test exceeds frame budget (sim tick < 2ms, render < 4ms) |
| Pool safety verified | Zero pool overflow events during peak-load integration test |
| Spec reviewed | Feature matches the canonical spec section. Deviations are documented and justified in a commit message |

#### When to skip gates
Never. If a gate is too expensive to run for a given change, the gate is broken (fix the test infrastructure), not optional.

---

### 19. Application Startup and Shutdown Contract

This was missing from every previous pass. Without it, the game will have undefined initialization order and resource leaks.

#### Startup sequence

```
1. Initialize SDL2, SDL2_mixer, SDL2_image
2. Create window + renderer (virtual 240×160, integer-scaled to display)
3. Load AssetCatalog (all sprites, SFX, BGM loaded here, validated here)
4. Load or create SaveData via IStorage
5. Initialize AudioManager (set volumes from SaveData/settings)
6. Create App state machine, enter TitleState
7. Begin main loop
```

#### Rules
- All asset loading happens in step 3, before the main loop starts. No lazy loading during gameplay. This is both simpler and GBA-compatible (GBA loads from ROM, not filesystem).
- If any SDL init fails, print error to stderr and exit with non-zero code. No partial initialization.
- If AssetCatalog detects missing assets, log warnings and substitute magenta fallbacks (section #16), but do NOT abort. The game must be runnable with placeholder art during development.

#### Shutdown sequence

```
1. Save current settings/stats via IStorage (if dirty)
2. Destroy App state machine (calls current state's exit())
3. Free AssetCatalog (textures, audio chunks, music)
4. Quit SDL2_mixer, SDL2_image, SDL2
5. Exit
```

#### Rules
- Shutdown must not crash if called from any state (including mid-wave, mid-transition, or error recovery).
- Resource release order is reverse of acquisition order. SDL_Quit is always last.
- On Windows, ensure the console window (if present) stays open long enough to read error output. Use `SDL_ShowSimpleMessageBox` for fatal errors.

---

### 20. Render Interpolation Contract

The main spec's loop shows `render(interpolation_alpha)` but never defines what gets interpolated. Without this, either rendering stutters at non-exact frame boundaries or the interpolation is implemented inconsistently.

#### What gets interpolated
- **Enemy positions**: lerp between previous tick position and current tick position using alpha. This eliminates visual stutter when render rate and sim rate don't align perfectly.
- **Projectile positions**: same lerp.

#### What does NOT get interpolated
- Tower positions (they don't move)
- HUD values (discrete integers, no lerping)
- Tile grid (static per map)
- Status effect visuals (binary on/off per tick, no blending)
- Cursor position (tile-snapped, discrete)

#### Implementation
```cpp
Vec2 render_pos(const Vec2& prev, const Vec2& curr, float alpha) {
    return { prev.x + (curr.x - prev.x) * alpha,
             prev.y + (curr.y - prev.y) * alpha };
}
```

#### Rules
- Every moving entity must store both `prev_pos` and `pos`. `prev_pos` is copied from `pos` at the START of each simulation tick, before movement updates.
- Alpha is computed as `accumulator / SIM_DT` after the simulation loop exits.
- If fast-forwarding (multiple sim ticks per frame), only the last tick's prev/curr pair is used for interpolation. Intermediate ticks are not rendered.

---

### 21. Audio Threading Acknowledgment

The main spec declares "single-threaded execution model" (Rule 7). SDL2_mixer's audio callback runs on a separate thread. These two statements need to be reconciled, not ignored.

#### The reconciliation
- `core/` is single-threaded. This is true and unchanged.
- SDL2_mixer's internal mixing thread is managed entirely by SDL. The app layer calls `Mix_PlayChannel()` and `Mix_PlayMusic()` from the main thread. SDL_mixer handles the rest.
- **The app layer must never call SDL_mixer functions from inside `core/` tick logic.** Audio calls happen after the tick, when draining the event log. This is already specified in the event system (v3 section #3) but the threading implication was never stated.
- No mutexes, no atomics, no shared state between the main thread and the audio callback. SDL_mixer's API is designed to be called from one thread. Do not get creative.

---

## What Was Wrong With The v4

1. **Section 11 (float discipline) was discipline-by-comment.** `// FIXED_POINT_PORT_NOTE` is grep-able but not enforceable. Replaced with `core/math.h` wrapper functions that ARE the migration boundary. When the GBA port happens, you change the implementations in one file.

2. **Section 13-14 (tests) were lists without pass/fail criteria.** A test that says "BFS returns shortest path" is not runnable until you define the input grid and expected output. Now the unit tests specify what's being tested and the integration tests specify concrete seeds, methods, and pass conditions.

3. **Section 15 (debug cheats) had no interface spec.** "Skip to wave N" means nothing without knowing how N is selected. Now keyboard-shortcut driven with Ctrl+Shift prefix to avoid gameplay collision. Added the most important missing debug tool: single-tick stepping while paused.

4. **Section 16 (asset validation) was split across build-time and runtime without saying which checks happen where.** Now explicit. Also added the magenta fallback as a constexpr baked into the binary, not loaded from disk.

5. **Section 17 (save migration) was "transform forward" with zero implementation guidance.** Now a concrete version-gated field-addition pattern with code example and a 256-byte hard cap.

6. **Section 18 (definition of done) had subjective gates.** "Telemetry verified" is not a pass/fail criterion. Now every gate has a concrete pass condition.

7. **Missing: startup/shutdown sequence (#19).** The entire application lifecycle was unspecified. Initialization order, error handling, resource cleanup — none of it existed.

8. **Missing: render interpolation (#20).** The main loop uses `interpolation_alpha` but nothing defined what gets interpolated. Without this, enemy movement visually stutters.

9. **Missing: audio threading acknowledgment (#21).** The spec says "single-threaded" while depending on SDL2_mixer, which runs a callback on a separate thread. That contradiction needed explicit reconciliation.

---

## Spec Completeness Declaration

This spec now covers:

| Layer | Status |
|-------|--------|
| Product goal | Defined |
| Engineering constraints (8 rules) | Defined |
| Architecture + file tree | Defined |
| HAL interfaces (5) + enforcement | Defined |
| Main loop + fixed timestep | Defined |
| Fast forward contract | Defined |
| Game state machine + transitions | Defined |
| Gameplay phase state machine + transitions | Defined |
| Save data contract + migration | Defined |
| Grid, HUD, tray layout | Defined |
| Cursor and selection UX | Defined |
| Map generation + validation + retry | Defined |
| Pathfinding algorithm | Defined |
| Multi-spawn distribution | Defined |
| Tower stats, targeting, cadence | Defined |
| Enemy stats, armor, healing | Defined |
| Status effects (slow, burn, chain, splash) | Defined |
| Wave table with computed gold | Defined |
| Spawn pacing + interleaving | Defined |
| Fleet upgrade system + UI flow | Defined |
| Economy rules | Defined |
| Input mapping | Defined |
| Rendering rules + sprite budget + draw order | Defined |
| Render model snapshot struct | Defined |
| Render interpolation | Defined |
| Asset pipeline + validation | Defined |
| Audio rules + threading | Defined |
| Simulation tick order | Defined |
| Simulation authority + event log | Defined |
| Float discipline + migration path | Defined |
| Data-driven balance (generated headers) | Defined |
| Replay recording + version hashing | Defined |
| Difficulty scaling hook | Defined |
| Memory management (pools, caps) | Defined |
| Pool overflow policy | Defined |
| Performance budget | Defined |
| Debug overlay + cheats | Defined |
| Balancing telemetry | Defined |
| Unit test matrix | Defined |
| Integration test matrix | Defined |
| Definition of done gate | Defined |
| Startup + shutdown sequence | Defined |
| Build system (CMake) | Defined |
| Acceptance criteria (15 items) | Defined |

**There is nothing left to spec.** If you find yourself adding more sections, you are procrastinating on implementation. The next action is writing code, not writing more spec.

---

## Final Brutal Warning (Unchanged — Because It Was Right)

Your biggest remaining risk is no longer under-specification.

Your biggest remaining risk is: **ignoring your own spec during implementation.**

A great spec with sloppy implementation discipline still produces garbage.

Start building.

---

(Previous spec content retained below in implementation branch.)
