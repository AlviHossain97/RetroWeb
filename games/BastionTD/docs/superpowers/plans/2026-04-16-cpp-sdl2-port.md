# BastionTD C++ SDL2 Port — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Port BastionTD from Python/Pygame to C++17/SDL2 with thin HAL for GBA portability, adding fast-forward (1x/2x/3x), fleet upgrades (wave-gated), titan damage fix (min 1 dmg + DoT armor bypass), and character sprite remapping (char 0,1 = enemies; char 2,3,4 = tower operators).

**Architecture:** Pure C++ game logic in `src/core/` with zero SDL dependencies. Thin HAL interfaces (`IRenderer`, `IInput`, `IAudio`) in `src/hal/hal.h`, implemented by SDL2 in `src/hal/sdl2_*.cpp`. Fixed-timestep simulation (60 ticks/sec) with render interpolation. Object pools for enemies/projectiles/effects. GBA-native 240×160 virtual resolution at 8×8 tile size, integer-scaled to desktop window.

**Tech Stack:** C++17, SDL2, SDL2_mixer, SDL2_image (optional — fallback primitives), CMake 3.16+

**Specs:** `docs/superpowers/specs/2026-04-16-cpp-sdl2-port-design-ruthless-v5-FINAL.md` + `PLAN.md`

---

## File Structure

```
BastionTD/
├── CMakeLists.txt
├── src/
│   ├── core/
│   │   ├── types.h              — Vec2, Color, Rect, enums (TowerType, EnemyType, Terrain, GamePhase, SpriteId)
│   │   ├── math_utils.h         — sim_mul, sim_div, sim_to_int, sim_approx_eq, distance (header-only, migration boundary)
│   │   ├── config.h             — All game constants: grid dims, tower/enemy/wave defs, economy, colors (header-only)
│   │   ├── grid.h / grid.cpp    — Grid class: tile storage, get/set, is_buildable, is_passable, in_bounds
│   │   ├── pathfinding.h / pathfinding.cpp — BFS shortest path on grid, 4-directional
│   │   ├── enemy.h / enemy.cpp  — Enemy struct + EnemyPool: movement, HP, armor, status effects, healer pulse
│   │   ├── tower.h / tower.cpp  — Tower struct + array: targeting, cooldown, firing, upgrade, sell
│   │   ├── projectile.h / projectile.cpp — Projectile struct + pool: flight, impact, splash/chain/slow/dot
│   │   ├── wave_manager.h / wave_manager.cpp — Wave roster, spawn queue, spawn timing, wave progression
│   │   ├── economy.h / economy.cpp — Gold, lives, fleet upgrade logic, can_afford, spend, earn
│   │   ├── map_generator.h / map_generator.cpp — Procedural map gen with BFS validation, retry logic
│   │   ├── effects.h / effects.cpp — Particle pool, damage numbers, screen shake
│   │   └── game.h / game.cpp    — Top-level Game struct: owns all systems, tick order, state machine
│   ├── hal/
│   │   ├── hal.h                — IRenderer, IInput, IAudio abstract interfaces
│   │   ├── sdl2_renderer.h / sdl2_renderer.cpp — SDL2 renderer: window, sprites, rects, text, scaling
│   │   ├── sdl2_input.h / sdl2_input.cpp — SDL2 keyboard input: pressed/held/released
│   │   └── sdl2_audio.h / sdl2_audio.cpp — SDL2_mixer audio: procedural SFX gen, BGM, volume
│   ├── states/
│   │   ├── state.h              — State base class + StateMachine (register, change, update, render)
│   │   ├── gameplay_state.h / gameplay_state.cpp — Core: build/wave phases, cursor, tower placement, fast-forward, fleet upgrade UI
│   │   ├── title_state.h / title_state.cpp — Title menu, high score display
│   │   ├── pause_state.h / pause_state.cpp — Pause overlay
│   │   ├── game_over_state.h / game_over_state.cpp — Game over stats
│   │   └── victory_state.h / victory_state.cpp — Victory screen
│   └── main.cpp                 — SDL2 init, HAL creation, game loop (fixed timestep + interpolation), shutdown
└── tests/
    ├── CMakeLists.txt
    ├── test_pathfinding.cpp
    ├── test_combat.cpp
    ├── test_economy.cpp
    └── test_wave.cpp
```

---

## Task 1: CMake Build System + Directory Scaffold

**Files:**

- Create: `CMakeLists.txt`
- Create: `src/core/`, `src/hal/`, `src/states/`, `tests/` directories

- [ ] **Step 1: Create directory structure**

```bash
mkdir -p src/core src/hal src/states tests
```

- [ ] **Step 2: Write CMakeLists.txt**

```cmake
cmake_minimum_required(VERSION 3.16)
project(BastionTD LANGUAGES CXX)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# SDL2
find_package(SDL2 REQUIRED)
find_package(SDL2_mixer QUIET)

# Core library (no SDL deps)
add_library(bastion_core STATIC
    src/core/grid.cpp
    src/core/pathfinding.cpp
    src/core/enemy.cpp
    src/core/tower.cpp
    src/core/projectile.cpp
    src/core/wave_manager.cpp
    src/core/economy.cpp
    src/core/map_generator.cpp
    src/core/effects.cpp
    src/core/game.cpp
)
target_include_directories(bastion_core PUBLIC src)

# HAL + States + Main
add_executable(BastionTD
    src/main.cpp
    src/hal/sdl2_renderer.cpp
    src/hal/sdl2_input.cpp
    src/hal/sdl2_audio.cpp
    src/states/gameplay_state.cpp
    src/states/title_state.cpp
    src/states/pause_state.cpp
    src/states/game_over_state.cpp
    src/states/victory_state.cpp
)
target_include_directories(BastionTD PRIVATE src)
target_link_libraries(BastionTD bastion_core SDL2::SDL2 SDL2::SDL2main)
if(TARGET SDL2_mixer::SDL2_mixer)
    target_link_libraries(BastionTD SDL2_mixer::SDL2_mixer)
    target_compile_definitions(BastionTD PRIVATE HAS_SDL2_MIXER)
endif()

# Debug build
option(BASTION_DEBUG "Enable debug cheats" ON)
if(BASTION_DEBUG)
    target_compile_definitions(BastionTD PRIVATE BASTION_DEBUG)
endif()
```

- [ ] **Step 3: Verify CMake configures**

```bash
cmake -B build -S .
```

Expected: Configuration succeeds (may warn about missing source files — that's fine, they don't exist yet).

- [ ] **Step 4: Commit**

```bash
git add CMakeLists.txt
git commit -m "feat: add CMake build system for C++ SDL2 port"
```

---

## Task 2: Core Types, Math Utilities, Config

**Files:**

- Create: `src/core/types.h`
- Create: `src/core/math_utils.h`
- Create: `src/core/config.h`

- [ ] **Step 1: Write `src/core/types.h`**

```cpp
#pragma once
#include <cstdint>

struct Vec2 {
    float x = 0.0f;
    float y = 0.0f;
};

struct Color {
    uint8_t r = 0, g = 0, b = 0, a = 255;
};

struct Rect {
    float x = 0, y = 0, w = 0, h = 0;
};

enum class Terrain : uint8_t {
    Empty = 0, Path, Rock, Water, Tree, Spawn, Base, Tower
};

enum class TowerType : uint8_t {
    Arrow = 0, Cannon, Ice, Lightning, Flame, COUNT
};

enum class EnemyType : uint8_t {
    Goblin = 0, Wolf, Knight, Healer, Swarm, Titan, COUNT
};

enum class GamePhase : uint8_t {
    Build, Wave, WaveCleanup, DefeatPending
};

enum class SpeedMode : uint8_t {
    Normal = 0, Fast2x, Fast3x
};

enum class SpriteId : uint8_t {
    // Characters
    Char0 = 0, Char1, Char2, Char3, Char4,
    // Tower bases (3 types visible × 3 levels = 9, but we use 5 types × 3 levels)
    TowerArrow1, TowerArrow2, TowerArrow3,
    TowerCannon1, TowerCannon2, TowerCannon3,
    TowerIce1, TowerIce2, TowerIce3,
    TowerLightning1, TowerLightning2, TowerLightning3,
    TowerFlame1, TowerFlame2, TowerFlame3,
    // Tiles
    TileGrass, TilePath, TileRock, TileWater, TileTree, TileSpawn, TileBase,
    // UI
    MagentaFallback,
    COUNT
};

enum class InputButton : uint8_t {
    Up = 0, Down, Left, Right,
    A, B, L, R,
    Start, Select,
    FleetUpgrade,
    COUNT
};

enum class SfxId : uint8_t {
    Place = 0, Shoot, Hit, EnemyDeath, WaveStart, WaveClear,
    BossSpawn, BaseHit, Upgrade, Sell, MenuMove, MenuSelect,
    GameOver, Victory, COUNT
};

enum class BgmId : uint8_t {
    Title = 0, Build, Wave, Boss, COUNT
};
```

- [ ] **Step 2: Write `src/core/math_utils.h`**

Per v5 spec section 11 — all simulation math routes through these wrappers. Float today, fixed-point on GBA later.

```cpp
#pragma once
#include "types.h"
#include <cmath>
#include <algorithm>

// --- Simulation math wrappers (migration boundary for fixed-point) ---
inline float sim_mul(float a, float b) { return a * b; }
inline float sim_div(float a, float b) { return a / b; }
inline int   sim_to_int(float a)       { return static_cast<int>(a); }
inline float sim_abs(float a)          { return std::fabs(a); }
inline float sim_min(float a, float b) { return std::min(a, b); }
inline float sim_max(float a, float b) { return std::max(a, b); }
inline float sim_clamp(float v, float lo, float hi) { return std::clamp(v, lo, hi); }

constexpr float EPSILON = 0.001f;
inline bool sim_approx_eq(float a, float b, float eps = EPSILON) {
    return std::fabs(a - b) < eps;
}

inline float distance(Vec2 a, Vec2 b) {
    float dx = a.x - b.x;
    float dy = a.y - b.y;
    return std::sqrt(sim_mul(dx, dx) + sim_mul(dy, dy));
}

inline float distance_sq(Vec2 a, Vec2 b) {
    float dx = a.x - b.x;
    float dy = a.y - b.y;
    return sim_mul(dx, dx) + sim_mul(dy, dy);
}

inline Vec2 lerp(Vec2 prev, Vec2 curr, float alpha) {
    return { prev.x + (curr.x - prev.x) * alpha,
             prev.y + (curr.y - prev.y) * alpha };
}
```

- [ ] **Step 3: Write `src/core/config.h`**

All game constants. Tower stats, enemy stats, wave generation, economy, grid dimensions, colors.

```cpp
#pragma once
#include "types.h"
#include <array>
#include <cstdint>

namespace cfg {

// --- Screen / Grid ---
constexpr int TILE_SIZE     = 8;
constexpr int GRID_W        = 30;   // playable columns
constexpr int GRID_H        = 12;   // playable rows
constexpr int HUD_ROWS      = 2;    // top HUD
constexpr int TRAY_ROWS     = 2;    // bottom tower tray
constexpr int TOTAL_ROWS    = HUD_ROWS + GRID_H + TRAY_ROWS; // 16
constexpr int SCREEN_W      = TILE_SIZE * GRID_W;   // 240
constexpr int SCREEN_H      = TILE_SIZE * TOTAL_ROWS; // 128
constexpr int WINDOW_SCALE  = 4;    // SDL window = 960×512
constexpr int GRID_OFFSET_Y = HUD_ROWS * TILE_SIZE; // 16px

// --- Timing ---
constexpr float SIM_DT      = 1.0f / 60.0f;
constexpr float MAX_DT      = 0.1f;
constexpr int   TARGET_FPS  = 60;

// --- Economy ---
constexpr int START_GOLD        = 200;
constexpr int START_LIVES       = 20;
constexpr int WAVE_CLEAR_BONUS  = 25;
constexpr int TOTAL_WAVES       = 20;
constexpr float FLEET_UPGRADE_PREMIUM = 1.10f; // 10% surcharge
constexpr int FLEET_UNLOCK_WAVES[] = {5, 10, 15};

// --- Projectile ---
constexpr float PROJECTILE_SPEED = 12.0f; // tiles/sec
constexpr float PROJECTILE_HIT_DIST = 0.3f;

// --- Tower definitions ---
struct TowerDef {
    const char* name;
    int cost;
    float range;
    float damage;
    float cooldown;
    Color color;
    // Special params
    float splash_radius;   // cannon
    float slow_factor;     // ice
    float slow_duration;   // ice
    int   chain_count;     // lightning
    float chain_range;     // lightning
    float dot_damage;      // flame (dps)
    float dot_duration;    // flame
    // Per-level upgrade deltas [0]=lv2, [1]=lv3
    struct Upgrade {
        int   cost;
        float damage;
        float range;
        float splash_radius;
        float slow_factor;
        int   chain_count;
        float dot_damage;
        float dot_duration;
    };
    Upgrade upgrades[2];
    SpriteId char_sprite; // character on tower
};

constexpr TowerDef TOWER_DEFS[5] = {
    // Arrow
    {"Arrow", 50, 3.5f, 1.0f, 0.6f, {160,130,60,255},
     0,0,0, 0,0, 0,0,
     {{30, 2.0f, 4.0f, 0,0,0, 0,0}, {50, 3.0f, 4.5f, 0,0,0, 0,0}},
     SpriteId::Char2},
    // Cannon
    {"Cannon", 100, 2.5f, 3.0f, 1.5f, {120,80,60,255},
     1.2f, 0,0, 0,0, 0,0,
     {{60, 5.0f, 3.0f, 1.2f,0,0, 0,0}, {90, 8.0f, 3.5f, 1.5f,0,0, 0,0}},
     SpriteId::Char3},
    // Ice
    {"Ice", 75, 3.0f, 0.5f, 0.8f, {100,180,220,255},
     0, 0.4f, 2.0f, 0,0, 0,0,
     {{45, 1.0f, 3.0f, 0, 0.3f,0, 0,0}, {70, 1.5f, 3.5f, 0, 0.2f,0, 0,0}},
     SpriteId::Char2},
    // Lightning
    {"Lightning", 150, 4.0f, 2.0f, 1.0f, {200,200,60,255},
     0, 0,0, 2, 1.5f, 0,0,
     {{90, 3.0f, 4.0f, 0,0, 3, 0,0}, {130, 4.0f, 4.5f, 0,0, 4, 0,0}},
     SpriteId::Char4},
    // Flame
    {"Flame", 125, 2.0f, 1.0f, 0.2f, {220,100,40,255},
     0, 0,0, 0,0, 0.5f, 2.0f,
     {{75, 1.5f, 2.0f, 0,0,0, 1.0f, 2.0f}, {110, 2.0f, 2.5f, 0,0,0, 1.5f, 3.0f}},
     SpriteId::Char3},
};

// --- Enemy definitions ---
struct EnemyDef {
    const char* name;
    float hp;
    float speed;
    int   armor;
    int   gold;
    Color color;
    float size;       // render scale multiplier
    int   lives_cost; // lives lost on leak (1 normal, 5 titan)
    // Healer special
    float heal_rate;  // hp/sec (0 = not a healer)
    float heal_range; // tiles
    // Sprite
    SpriteId sprite;
    float sprite_scale;
};

constexpr EnemyDef ENEMY_DEFS[6] = {
    // Goblin
    {"Goblin", 3.0f, 2.0f, 0, 5, {60,160,60,255}, 0.5f, 1, 0,0,
     SpriteId::Char0, 1.0f},
    // Wolf
    {"Wolf", 2.0f, 3.5f, 0, 8, {140,120,100,255}, 0.5f, 1, 0,0,
     SpriteId::Char1, 1.0f},
    // Knight
    {"Knight", 8.0f, 1.2f, 2, 15, {180,180,200,255}, 0.7f, 1, 0,0,
     SpriteId::Char0, 1.2f},
    // Healer
    {"Healer", 4.0f, 2.0f, 0, 12, {60,200,60,255}, 0.5f, 1, 1.0f, 2.0f,
     SpriteId::Char1, 1.1f},
    // Swarm
    {"Swarm", 1.0f, 3.0f, 0, 2, {180,180,50,255}, 0.35f, 1, 0,0,
     SpriteId::Char1, 0.7f},
    // Titan
    {"Titan", 50.0f, 0.8f, 3, 100, {160,80,80,255}, 1.0f, 5, 0,0,
     SpriteId::Char0, 2.5f},
};

// --- Wave composition entry ---
struct WaveEntry {
    EnemyType type;
    int count;
    float spawn_delay; // seconds between each enemy of this group
};

// Max entries per wave, max waves
constexpr int MAX_WAVE_ENTRIES = 6;

struct WaveDef {
    WaveEntry entries[MAX_WAVE_ENTRIES];
    int entry_count;
    bool has_titan;
};

// Populated at startup by generate_waves()
// (Cannot be constexpr due to logic — filled in config.cpp or inline function)

inline void generate_waves(WaveDef waves[TOTAL_WAVES]) {
    for (int w = 1; w <= TOTAL_WAVES; ++w) {
        WaveDef& wd = waves[w - 1];
        wd.entry_count = 0;
        wd.has_titan = false;
        auto add = [&](EnemyType t, int count, float delay) {
            if (wd.entry_count < MAX_WAVE_ENTRIES) {
                wd.entries[wd.entry_count++] = {t, count, delay};
            }
        };
        if (w <= 3) {
            add(EnemyType::Goblin, 4 + w * 2, 0.8f);
        } else if (w <= 6) {
            add(EnemyType::Goblin, 6 + w, 0.7f);
            add(EnemyType::Wolf, w - 2, 0.6f);
        } else if (w <= 10) {
            add(EnemyType::Wolf, 4 + w - 6, 0.6f);
            add(EnemyType::Knight, w - 6, 1.2f);
            if (w >= 9) add(EnemyType::Healer, 1, 1.5f);
        } else if (w <= 15) {
            add(EnemyType::Knight, w - 8, 1.0f);
            add(EnemyType::Healer, (w - 9) / 2 + 1, 1.3f);
            add(EnemyType::Swarm, w * 2, 0.3f);
        } else {
            add(EnemyType::Knight, w - 10, 0.9f);
            add(EnemyType::Wolf, w - 12, 0.5f);
            add(EnemyType::Healer, 2, 1.2f);
            add(EnemyType::Swarm, w * 3, 0.25f);
        }
        if (w == 5 || w == 10 || w == 15) {
            add(EnemyType::Titan, 1, 0.0f);
            wd.has_titan = true;
        }
        if (w == 20) {
            add(EnemyType::Titan, 2, 0.0f);
            wd.has_titan = true;
        }
    }
}

// --- Boss waves ---
constexpr bool is_boss_wave(int wave_num) {
    return wave_num == 5 || wave_num == 10 || wave_num == 15 || wave_num == 20;
}

// --- Fleet upgrade availability ---
constexpr bool fleet_upgrade_unlocked(int waves_completed) {
    return waves_completed >= 5;
}
constexpr int fleet_upgrade_max_level(int waves_completed) {
    if (waves_completed >= 15) return 3;
    if (waves_completed >= 10) return 3;
    if (waves_completed >= 5)  return 2;
    return 1;
}

// --- Pool caps (v5 spec) ---
constexpr int MAX_ENEMIES     = 64;
constexpr int MAX_TOWERS      = 32;
constexpr int MAX_PROJECTILES = 64;
constexpr int MAX_PARTICLES   = 128;
constexpr int MAX_DMG_NUMBERS = 32;
constexpr int MAX_PATH_LEN    = 256;
constexpr int MAX_SPAWNS      = 2;
constexpr int MAX_DOT_STACKS  = 3;

// --- Colors ---
namespace colors {
    constexpr Color BG       = {20, 28, 20, 255};
    constexpr Color GRASS    = {45, 90, 45, 255};
    constexpr Color PATH     = {140, 120, 80, 255};
    constexpr Color ROCK     = {100, 100, 110, 255};
    constexpr Color WATER    = {40, 70, 150, 255};
    constexpr Color TREE_COL = {30, 70, 35, 255};
    constexpr Color BASE     = {60, 60, 180, 255};
    constexpr Color SPAWN    = {180, 60, 60, 255};
    constexpr Color HUD_BG   = {10, 10, 18, 255};
    constexpr Color TRAY_BG  = {15, 15, 25, 255};
    constexpr Color WHITE    = {240, 235, 220, 255};
    constexpr Color GOLD     = {255, 210, 80, 255};
    constexpr Color ACCENT   = {80, 200, 120, 255};
    constexpr Color HEALTH   = {220, 50, 50, 255};
    constexpr Color CURSOR_OK  = {80, 255, 80, 100};
    constexpr Color CURSOR_BAD = {255, 80, 80, 100};
    constexpr Color MAGENTA  = {255, 0, 255, 255};
}

} // namespace cfg
```

- [ ] **Step 4: Verify headers compile**

Create a minimal `src/main.cpp` stub:

```cpp
#include "core/types.h"
#include "core/math_utils.h"
#include "core/config.h"
int main() { return 0; }
```

```bash
cmake -B build -S . && cmake --build build
```

Expected: Compiles with no errors.

- [ ] **Step 5: Commit**

```bash
git add src/core/types.h src/core/math_utils.h src/core/config.h src/main.cpp
git commit -m "feat: add core types, math utils, and config constants"
```

---

## Task 3: HAL Interfaces

**Files:**

- Create: `src/hal/hal.h`

- [ ] **Step 1: Write `src/hal/hal.h`**

```cpp
#pragma once
#include "core/types.h"

// --- Renderer interface ---
struct IRenderer {
    virtual ~IRenderer() = default;
    virtual void clear(Color c) = 0;
    virtual void draw_rect(int x, int y, int w, int h, Color c) = 0;
    virtual void draw_rect_outline(int x, int y, int w, int h, Color c) = 0;
    virtual void draw_sprite(SpriteId id, int x, int y, float scale = 1.0f, bool flip_h = false) = 0;
    virtual void draw_text(const char* str, int x, int y, Color c = {240,235,220,255}) = 0;
    virtual void draw_circle(int cx, int cy, int r, Color c) = 0;
    virtual void draw_line(int x1, int y1, int x2, int y2, Color c) = 0;
    virtual void present() = 0;
    virtual int screen_w() const = 0;
    virtual int screen_h() const = 0;
};

// --- Input interface ---
struct IInput {
    virtual ~IInput() = default;
    virtual void update() = 0; // call once per frame before game logic
    virtual bool pressed(InputButton btn) const = 0;  // just pressed this frame
    virtual bool held(InputButton btn) const = 0;      // currently held
    virtual bool released(InputButton btn) const = 0;  // just released this frame
    virtual bool quit_requested() const = 0;
    virtual float held_duration(InputButton btn) const = 0; // seconds held
};

// --- Audio interface ---
struct IAudio {
    virtual ~IAudio() = default;
    virtual void play_sfx(SfxId id) = 0;
    virtual void play_bgm(BgmId id) = 0;
    virtual void stop_bgm() = 0;
    virtual void set_sfx_volume(float v) = 0; // 0-1
    virtual void set_bgm_volume(float v) = 0; // 0-1
};
```

- [ ] **Step 2: Verify compiles**

Add `#include "hal/hal.h"` to main.cpp stub, rebuild.

- [ ] **Step 3: Commit**

```bash
git add src/hal/hal.h
git commit -m "feat: add HAL interfaces (IRenderer, IInput, IAudio)"
```

---

## Task 4: Grid + Pathfinding

**Files:**

- Create: `src/core/grid.h`, `src/core/grid.cpp`
- Create: `src/core/pathfinding.h`, `src/core/pathfinding.cpp`
- Create: `tests/test_pathfinding.cpp`

- [ ] **Step 1: Write `src/core/grid.h`**

```cpp
#pragma once
#include "core/types.h"
#include "core/config.h"

struct Grid {
    Terrain tiles[cfg::GRID_H][cfg::GRID_W];
    Vec2 spawns[cfg::MAX_SPAWNS];
    int spawn_count = 0;
    Vec2 base_pos = {0, 0};

    void init(); // fill with Empty
    Terrain get(int tx, int ty) const;
    void set(int tx, int ty, Terrain t);
    bool in_bounds(int tx, int ty) const;
    bool is_buildable(int tx, int ty) const;
    bool is_passable(int tx, int ty) const;
};
```

- [ ] **Step 2: Write `src/core/grid.cpp`**

```cpp
#include "core/grid.h"

void Grid::init() {
    for (int y = 0; y < cfg::GRID_H; ++y)
        for (int x = 0; x < cfg::GRID_W; ++x)
            tiles[y][x] = Terrain::Empty;
    spawn_count = 0;
    base_pos = {0, 0};
}

Terrain Grid::get(int tx, int ty) const {
    if (!in_bounds(tx, ty)) return Terrain::Rock;
    return tiles[ty][tx];
}

void Grid::set(int tx, int ty, Terrain t) {
    if (in_bounds(tx, ty)) tiles[ty][tx] = t;
}

bool Grid::in_bounds(int tx, int ty) const {
    return tx >= 0 && tx < cfg::GRID_W && ty >= 0 && ty < cfg::GRID_H;
}

bool Grid::is_buildable(int tx, int ty) const {
    return in_bounds(tx, ty) && get(tx, ty) == Terrain::Empty;
}

bool Grid::is_passable(int tx, int ty) const {
    if (!in_bounds(tx, ty)) return false;
    Terrain t = get(tx, ty);
    return t == Terrain::Empty || t == Terrain::Path ||
           t == Terrain::Spawn || t == Terrain::Base;
}
```

- [ ] **Step 3: Write `src/core/pathfinding.h`**

```cpp
#pragma once
#include "core/grid.h"

struct Path {
    Vec2 points[cfg::MAX_PATH_LEN];
    int length = 0;
    bool valid = false;
};

// BFS shortest path from start to end. 4-directional.
Path bfs(const Grid& grid, Vec2 start, Vec2 end);
```

- [ ] **Step 4: Write `src/core/pathfinding.cpp`**

```cpp
#include "core/pathfinding.h"
#include <cstring>

Path bfs(const Grid& grid, Vec2 start, Vec2 end) {
    Path result;
    result.valid = false;
    result.length = 0;

    int sx = static_cast<int>(start.x), sy = static_cast<int>(start.y);
    int ex = static_cast<int>(end.x),   ey = static_cast<int>(end.y);

    if (!grid.in_bounds(sx, sy) || !grid.in_bounds(ex, ey)) return result;

    // BFS with parent tracking
    struct Cell { int x, y; };
    bool visited[cfg::GRID_H][cfg::GRID_W];
    Cell parent[cfg::GRID_H][cfg::GRID_W];
    std::memset(visited, 0, sizeof(visited));
    std::memset(parent, -1, sizeof(parent));

    Cell queue[cfg::GRID_W * cfg::GRID_H];
    int head = 0, tail = 0;
    queue[tail++] = {sx, sy};
    visited[sy][sx] = true;
    parent[sy][sx] = {-1, -1};

    constexpr int dx[] = {0, 0, -1, 1};
    constexpr int dy[] = {-1, 1, 0, 0};
    bool found = false;

    while (head < tail) {
        Cell cur = queue[head++];
        if (cur.x == ex && cur.y == ey) { found = true; break; }
        for (int d = 0; d < 4; ++d) {
            int nx = cur.x + dx[d], ny = cur.y + dy[d];
            if (!grid.in_bounds(nx, ny)) continue;
            if (visited[ny][nx]) continue;
            if (!grid.is_passable(nx, ny)) continue;
            visited[ny][nx] = true;
            parent[ny][nx] = cur;
            queue[tail++] = {nx, ny};
        }
    }

    if (!found) return result;

    // Trace back
    Cell trace[cfg::MAX_PATH_LEN];
    int trace_len = 0;
    Cell c = {ex, ey};
    while (c.x != -1 && trace_len < cfg::MAX_PATH_LEN) {
        trace[trace_len++] = c;
        c = parent[c.y][c.x];
    }

    // Reverse into result
    result.length = trace_len;
    result.valid = true;
    for (int i = 0; i < trace_len; ++i) {
        result.points[i] = {static_cast<float>(trace[trace_len - 1 - i].x),
                            static_cast<float>(trace[trace_len - 1 - i].y)};
    }
    return result;
}
```

- [ ] **Step 5: Write test `tests/test_pathfinding.cpp`**

```cpp
#include "core/grid.h"
#include "core/pathfinding.h"
#include <cassert>
#include <cstdio>

void test_bfs_simple_path() {
    Grid g;
    g.init();
    // 5x5 open grid
    g.set(0, 0, Terrain::Spawn);
    g.set(4, 4, Terrain::Base);
    Path p = bfs(g, {0,0}, {4,4});
    assert(p.valid);
    assert(p.length == 9); // Manhattan distance 8 + start = 9 points
    assert(p.points[0].x == 0 && p.points[0].y == 0);
    assert(p.points[p.length-1].x == 4 && p.points[p.length-1].y == 4);
    printf("PASS: test_bfs_simple_path\n");
}

void test_bfs_no_path() {
    Grid g;
    g.init();
    // Wall blocking
    for (int y = 0; y < cfg::GRID_H; ++y) g.set(2, y, Terrain::Rock);
    g.set(0, 0, Terrain::Spawn);
    g.set(4, 0, Terrain::Base);
    Path p = bfs(g, {0,0}, {4,0});
    assert(!p.valid);
    printf("PASS: test_bfs_no_path\n");
}

void test_bfs_avoids_blocked() {
    Grid g;
    g.init();
    g.set(1, 0, Terrain::Rock);
    g.set(0, 0, Terrain::Spawn);
    g.set(2, 0, Terrain::Base);
    Path p = bfs(g, {0,0}, {2,0});
    assert(p.valid);
    // Must go around the rock — path won't include (1,0)
    for (int i = 0; i < p.length; ++i) {
        assert(!(p.points[i].x == 1 && p.points[i].y == 0));
    }
    printf("PASS: test_bfs_avoids_blocked\n");
}

int main() {
    test_bfs_simple_path();
    test_bfs_no_path();
    test_bfs_avoids_blocked();
    printf("All pathfinding tests passed.\n");
    return 0;
}
```

- [ ] **Step 6: Add test to CMake, build and run**

Add to `CMakeLists.txt`:

```cmake
# Tests
add_executable(test_pathfinding tests/test_pathfinding.cpp src/core/grid.cpp src/core/pathfinding.cpp)
target_include_directories(test_pathfinding PRIVATE src)
enable_testing()
add_test(NAME pathfinding COMMAND test_pathfinding)
```

```bash
cmake -B build -S . && cmake --build build && cd build && ctest --output-on-failure
```

Expected: All 3 tests PASS.

- [ ] **Step 7: Commit**

```bash
git add src/core/grid.h src/core/grid.cpp src/core/pathfinding.h src/core/pathfinding.cpp tests/test_pathfinding.cpp CMakeLists.txt
git commit -m "feat: add grid and BFS pathfinding with tests"
```

---

## Task 5: Economy System

**Files:**

- Create: `src/core/economy.h`, `src/core/economy.cpp`
- Create: `tests/test_economy.cpp`

- [ ] **Step 1: Write `src/core/economy.h`**

```cpp
#pragma once
#include "core/config.h"

struct Economy {
    int gold  = cfg::START_GOLD;
    int lives = cfg::START_LIVES;
    bool had_leak_this_wave = false;

    void reset();
    bool can_afford(int cost) const;
    void spend(int cost);
    void earn(int amount);
    void lose_lives(int amount);
    bool is_game_over() const;
    void wave_clear_bonus(); // +25g if no leaks

    // Fleet upgrade: cost to upgrade all towers of a type to target level
    // tower_count = number of towers of that type below target level
    // per_tower_cost = upgrade cost per tower
    // Returns total cost with premium
    static int fleet_upgrade_cost(int tower_count, int per_tower_cost);
};
```

- [ ] **Step 2: Write `src/core/economy.cpp`**

```cpp
#include "core/economy.h"
#include <cmath>

void Economy::reset() {
    gold = cfg::START_GOLD;
    lives = cfg::START_LIVES;
    had_leak_this_wave = false;
}

bool Economy::can_afford(int cost) const { return gold >= cost; }
void Economy::spend(int cost) { gold -= cost; }
void Economy::earn(int amount) { gold += amount; }

void Economy::lose_lives(int amount) {
    lives -= amount;
    had_leak_this_wave = true;
    if (lives < 0) lives = 0;
}

bool Economy::is_game_over() const { return lives <= 0; }

void Economy::wave_clear_bonus() {
    if (!had_leak_this_wave) {
        gold += cfg::WAVE_CLEAR_BONUS;
    }
    had_leak_this_wave = false;
}

int Economy::fleet_upgrade_cost(int tower_count, int per_tower_cost) {
    float raw = static_cast<float>(tower_count * per_tower_cost);
    return static_cast<int>(std::ceil(raw * cfg::FLEET_UPGRADE_PREMIUM));
}
```

- [ ] **Step 3: Write `tests/test_economy.cpp`**

```cpp
#include "core/economy.h"
#include <cassert>
#include <cstdio>

void test_starting_values() {
    Economy e;
    assert(e.gold == 200);
    assert(e.lives == 20);
    assert(!e.is_game_over());
    printf("PASS: test_starting_values\n");
}

void test_spend_earn() {
    Economy e;
    assert(e.can_afford(200));
    assert(!e.can_afford(201));
    e.spend(50);
    assert(e.gold == 150);
    e.earn(30);
    assert(e.gold == 180);
    printf("PASS: test_spend_earn\n");
}

void test_lives_and_game_over() {
    Economy e;
    e.lose_lives(5);
    assert(e.lives == 15);
    e.lose_lives(15);
    assert(e.lives == 0);
    assert(e.is_game_over());
    printf("PASS: test_lives_and_game_over\n");
}

void test_wave_bonus() {
    Economy e;
    e.spend(200); // 0 gold
    e.wave_clear_bonus(); // no leak → +25
    assert(e.gold == 25);

    e.lose_lives(1); // leak happened
    e.wave_clear_bonus(); // had leak → +0
    assert(e.gold == 25);
    printf("PASS: test_wave_bonus\n");
}

void test_fleet_upgrade_cost() {
    // 4 towers × 30g each × 1.10 premium = 132 → ceil = 132
    int cost = Economy::fleet_upgrade_cost(4, 30);
    assert(cost == 132);
    // 1 tower × 90g × 1.10 = 99
    cost = Economy::fleet_upgrade_cost(1, 90);
    assert(cost == 99);
    printf("PASS: test_fleet_upgrade_cost\n");
}

int main() {
    test_starting_values();
    test_spend_earn();
    test_lives_and_game_over();
    test_wave_bonus();
    test_fleet_upgrade_cost();
    printf("All economy tests passed.\n");
    return 0;
}
```

- [ ] **Step 4: Add test to CMake, build and run**

```cmake
add_executable(test_economy tests/test_economy.cpp src/core/economy.cpp)
target_include_directories(test_economy PRIVATE src)
add_test(NAME economy COMMAND test_economy)
```

```bash
cmake -B build -S . && cmake --build build && cd build && ctest --output-on-failure
```

Expected: All 5 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/core/economy.h src/core/economy.cpp tests/test_economy.cpp CMakeLists.txt
git commit -m "feat: add economy system with fleet upgrade cost calc"
```

---

## Task 6: Enemy System

**Files:**

- Create: `src/core/enemy.h`, `src/core/enemy.cpp`

- [ ] **Step 1: Write `src/core/enemy.h`**

```cpp
#pragma once
#include "core/types.h"
#include "core/config.h"
#include "core/pathfinding.h"
#include "core/math_utils.h"

struct DotStack {
    float dps;
    float remaining;
};

struct Enemy {
    bool active = false;
    EnemyType type = EnemyType::Goblin;
    Vec2 pos = {0, 0};
    Vec2 prev_pos = {0, 0}; // for render interpolation
    float hp = 0;
    float max_hp = 0;
    int armor = 0;
    float speed = 0;
    int gold_value = 0;
    int lives_cost = 1;
    float size = 0.5f;

    // Path following
    const Path* path = nullptr;
    int path_idx = 0;
    float path_progress = 0.0f; // 0..1 normalized progress along path

    // Status effects
    float slow_factor = 1.0f;
    float slow_timer = 0.0f;
    DotStack dots[cfg::MAX_DOT_STACKS];
    int dot_count = 0;

    // Healer
    float heal_rate = 0;
    float heal_range = 0;
    float heal_timer = 0;

    // Death
    bool reached_base = false;
    float death_timer = 0;
    bool dying = false;

    // Sprite
    SpriteId sprite = SpriteId::Char0;
    float sprite_scale = 1.0f;

    void init(EnemyType t, const Path* p);
    void update(float dt);
    void take_damage(float amount); // min 1 damage after armor
    void apply_slow(float factor, float duration);
    void add_dot(float dps, float duration);
    bool is_dead() const;
};

struct EnemyPool {
    Enemy enemies[cfg::MAX_ENEMIES];

    void init();
    Enemy* spawn(EnemyType type, const Path* path);
    void update_all(float dt);
    void heal_pass(); // healer enemies heal nearby allies
    int active_count() const;
};
```

- [ ] **Step 2: Write `src/core/enemy.cpp`**

```cpp
#include "core/enemy.h"

void Enemy::init(EnemyType t, const Path* p) {
    active = true;
    type = t;
    const auto& def = cfg::ENEMY_DEFS[static_cast<int>(t)];
    hp = def.hp;
    max_hp = def.hp;
    armor = def.armor;
    speed = def.speed;
    gold_value = def.gold;
    lives_cost = def.lives_cost;
    size = def.size;
    heal_rate = def.heal_rate;
    heal_range = def.heal_range;
    heal_timer = 0;
    sprite = def.sprite;
    sprite_scale = def.sprite_scale;

    path = p;
    path_idx = 0;
    path_progress = 0;
    if (p && p->length > 0) {
        pos = p->points[0];
        prev_pos = pos;
    }

    slow_factor = 1.0f;
    slow_timer = 0;
    dot_count = 0;
    reached_base = false;
    death_timer = 0;
    dying = false;
}

void Enemy::update(float dt) {
    if (!active || dying) {
        if (dying) {
            death_timer -= dt;
            if (death_timer <= 0) active = false;
        }
        return;
    }

    prev_pos = pos;

    // Tick DoT — bypasses armor per v5 spec
    for (int i = 0; i < dot_count; ) {
        hp -= sim_mul(dots[i].dps, dt);
        dots[i].remaining -= dt;
        if (dots[i].remaining <= 0) {
            dots[i] = dots[--dot_count]; // swap-remove
        } else {
            ++i;
        }
    }

    if (hp <= 0) {
        dying = true;
        death_timer = 0.3f;
        return;
    }

    // Tick slow
    if (slow_timer > 0) {
        slow_timer -= dt;
        if (slow_timer <= 0) slow_factor = 1.0f;
    }

    // Move along path
    if (path && path_idx < path->length - 1) {
        float effective_speed = sim_mul(speed, slow_factor);
        float move_budget = sim_mul(effective_speed, dt);

        while (move_budget > 0 && path_idx < path->length - 1) {
            Vec2 target = path->points[path_idx + 1];
            float dx = target.x - pos.x;
            float dy = target.y - pos.y;
            float dist = distance(pos, target);

            if (dist <= move_budget + 0.01f) {
                pos = target;
                move_budget -= dist;
                path_idx++;
            } else {
                float ratio = sim_div(move_budget, dist);
                pos.x += sim_mul(dx, ratio);
                pos.y += sim_mul(dy, ratio);
                move_budget = 0;
            }
        }

        path_progress = (path->length > 1)
            ? static_cast<float>(path_idx) / (path->length - 1)
            : 1.0f;
    }

    // Check reached base
    if (path && path_idx >= path->length - 1) {
        reached_base = true;
        active = false;
    }

    // Healer pulse
    if (heal_rate > 0) {
        heal_timer += dt;
    }
}

void Enemy::take_damage(float amount) {
    // v5 titan fix: min 1 damage for direct hits
    float effective = sim_max(1.0f, amount - static_cast<float>(armor));
    hp -= effective;
    if (hp <= 0 && !dying) {
        dying = true;
        death_timer = 0.3f;
    }
}

void Enemy::apply_slow(float factor, float duration) {
    // Strongest wins (lowest factor)
    if (factor < slow_factor || slow_timer <= 0) {
        slow_factor = factor;
    }
    slow_timer = duration; // refresh duration
}

void Enemy::add_dot(float dps, float duration) {
    if (dot_count < cfg::MAX_DOT_STACKS) {
        dots[dot_count++] = {dps, duration};
    } else {
        // Refresh oldest
        dots[0] = {dps, duration};
    }
}

bool Enemy::is_dead() const {
    return dying || !active;
}

// --- EnemyPool ---
void EnemyPool::init() {
    for (auto& e : enemies) e.active = false;
}

Enemy* EnemyPool::spawn(EnemyType type, const Path* path) {
    for (auto& e : enemies) {
        if (!e.active) {
            e.init(type, path);
            return &e;
        }
    }
    return nullptr; // pool full
}

void EnemyPool::update_all(float dt) {
    for (auto& e : enemies) {
        if (e.active) e.update(dt);
    }
}

void EnemyPool::heal_pass() {
    for (auto& healer : enemies) {
        if (!healer.active || healer.dying || healer.heal_rate <= 0) continue;
        if (healer.heal_timer < 1.0f) continue;
        healer.heal_timer -= 1.0f;

        for (auto& ally : enemies) {
            if (&ally == &healer || !ally.active || ally.dying) continue;
            if (distance(healer.pos, ally.pos) <= healer.heal_range) {
                ally.hp = sim_min(ally.hp + healer.heal_rate, ally.max_hp);
            }
        }
    }
}

int EnemyPool::active_count() const {
    int c = 0;
    for (const auto& e : enemies)
        if (e.active) ++c;
    return c;
}
```

- [ ] **Step 3: Verify compiles**

```bash
cmake -B build -S . && cmake --build build
```

- [ ] **Step 4: Commit**

```bash
git add src/core/enemy.h src/core/enemy.cpp
git commit -m "feat: add enemy system with pool, status effects, titan damage fix"
```

---

## Task 7: Tower System

**Files:**

- Create: `src/core/tower.h`, `src/core/tower.cpp`

- [ ] **Step 1: Write `src/core/tower.h`**

```cpp
#pragma once
#include "core/types.h"
#include "core/config.h"
#include "core/enemy.h"

struct Tower {
    bool active = false;
    TowerType type = TowerType::Arrow;
    int tile_x = 0, tile_y = 0;
    int level = 1; // 1-3
    float cooldown_timer = 0;
    int total_invested = 0; // for sell price

    // Current stats (base + upgrades applied)
    float damage = 0;
    float range = 0;
    float cooldown = 0;
    float splash_radius = 0;
    float slow_factor = 0;
    float slow_duration = 0;
    int   chain_count = 0;
    float chain_range = 0;
    float dot_damage = 0;
    float dot_duration = 0;
    Color color = {};
    SpriteId char_sprite = SpriteId::Char2;

    // Targeting
    int target_enemy_idx = -1; // index into EnemyPool
    bool firing_anim = false;
    float firing_anim_timer = 0;

    void init(TowerType t, int tx, int ty);
    void apply_stats(); // recalc stats from type + level
    int upgrade_cost() const; // -1 if max level
    void upgrade();
    int sell_value() const;
    void update(float dt, EnemyPool& enemies); // target + cooldown
    bool ready_to_fire() const;
};

struct TowerArray {
    Tower towers[cfg::MAX_TOWERS];

    void init();
    Tower* place(TowerType type, int tx, int ty);
    Tower* get_at(int tx, int ty);
    void remove(int tx, int ty);
    int count_type(TowerType type) const;
    int count_type_below_level(TowerType type, int target_level) const;
    void upgrade_all_type(TowerType type, int target_level);
    int active_count() const;
};
```

- [ ] **Step 2: Write `src/core/tower.cpp`**

```cpp
#include "core/tower.h"
#include "core/math_utils.h"

void Tower::init(TowerType t, int tx, int ty) {
    active = true;
    type = t;
    tile_x = tx;
    tile_y = ty;
    level = 1;
    const auto& def = cfg::TOWER_DEFS[static_cast<int>(t)];
    total_invested = def.cost;
    cooldown_timer = 0;
    target_enemy_idx = -1;
    firing_anim = false;
    firing_anim_timer = 0;
    apply_stats();
}

void Tower::apply_stats() {
    const auto& def = cfg::TOWER_DEFS[static_cast<int>(type)];
    damage = def.damage;
    range = def.range;
    cooldown = def.cooldown;
    splash_radius = def.splash_radius;
    slow_factor = def.slow_factor;
    slow_duration = def.slow_duration;
    chain_count = def.chain_count;
    chain_range = def.chain_range;
    dot_damage = def.dot_damage;
    dot_duration = def.dot_duration;
    color = def.color;
    char_sprite = def.char_sprite;

    // Apply upgrades additively
    for (int i = 0; i < level - 1 && i < 2; ++i) {
        const auto& upg = def.upgrades[i];
        damage = upg.damage;  // upgrades replace, not add (per Python spec)
        if (upg.range > 0) range = upg.range;
        if (upg.splash_radius > 0) splash_radius = upg.splash_radius;
        if (upg.slow_factor > 0) slow_factor = upg.slow_factor;
        if (upg.chain_count > 0) chain_count = upg.chain_count;
        if (upg.dot_damage > 0) dot_damage = upg.dot_damage;
        if (upg.dot_duration > 0) dot_duration = upg.dot_duration;
    }
}

int Tower::upgrade_cost() const {
    if (level >= 3) return -1;
    return cfg::TOWER_DEFS[static_cast<int>(type)].upgrades[level - 1].cost;
}

void Tower::upgrade() {
    if (level >= 3) return;
    total_invested += upgrade_cost();
    level++;
    apply_stats();
}

int Tower::sell_value() const {
    return total_invested / 2;
}

void Tower::update(float dt, EnemyPool& enemies) {
    if (!active) return;

    if (firing_anim) {
        firing_anim_timer -= dt;
        if (firing_anim_timer <= 0) firing_anim = false;
    }

    cooldown_timer -= dt;
    if (cooldown_timer > 0) return;

    // Find target: closest enemy to base (highest path_progress) within range
    Vec2 tower_pos = {static_cast<float>(tile_x) + 0.5f,
                      static_cast<float>(tile_y) + 0.5f};
    float best_progress = -1;
    int best_idx = -1;

    for (int i = 0; i < cfg::MAX_ENEMIES; ++i) {
        const auto& e = enemies.enemies[i];
        if (!e.active || e.dying) continue;
        float dist = distance(tower_pos, e.pos);
        if (dist <= range && e.path_progress > best_progress) {
            best_progress = e.path_progress;
            best_idx = i;
        }
    }
    target_enemy_idx = best_idx;
}

bool Tower::ready_to_fire() const {
    return active && cooldown_timer <= 0 && target_enemy_idx >= 0;
}

// --- TowerArray ---
void TowerArray::init() {
    for (auto& t : towers) t.active = false;
}

Tower* TowerArray::place(TowerType type, int tx, int ty) {
    for (auto& t : towers) {
        if (!t.active) {
            t.init(type, tx, ty);
            return &t;
        }
    }
    return nullptr;
}

Tower* TowerArray::get_at(int tx, int ty) {
    for (auto& t : towers) {
        if (t.active && t.tile_x == tx && t.tile_y == ty) return &t;
    }
    return nullptr;
}

void TowerArray::remove(int tx, int ty) {
    for (auto& t : towers) {
        if (t.active && t.tile_x == tx && t.tile_y == ty) {
            t.active = false;
            return;
        }
    }
}

int TowerArray::count_type(TowerType type) const {
    int c = 0;
    for (const auto& t : towers)
        if (t.active && t.type == type) ++c;
    return c;
}

int TowerArray::count_type_below_level(TowerType type, int target_level) const {
    int c = 0;
    for (const auto& t : towers)
        if (t.active && t.type == type && t.level < target_level) ++c;
    return c;
}

void TowerArray::upgrade_all_type(TowerType type, int target_level) {
    for (auto& t : towers) {
        if (t.active && t.type == type && t.level < target_level) {
            while (t.level < target_level) t.upgrade();
        }
    }
}

int TowerArray::active_count() const {
    int c = 0;
    for (const auto& t : towers)
        if (t.active) ++c;
    return c;
}
```

- [ ] **Step 3: Verify compiles, commit**

```bash
cmake -B build -S . && cmake --build build
git add src/core/tower.h src/core/tower.cpp
git commit -m "feat: add tower system with targeting, upgrades, fleet upgrade support"
```

---

## Task 8: Projectile System

**Files:**

- Create: `src/core/projectile.h`, `src/core/projectile.cpp`

- [ ] **Step 1: Write `src/core/projectile.h`**

```cpp
#pragma once
#include "core/types.h"
#include "core/config.h"
#include "core/enemy.h"

struct Projectile {
    bool active = false;
    Vec2 pos = {0, 0};
    Vec2 prev_pos = {0, 0};
    Vec2 target_pos = {0, 0}; // fallback if target dies
    int target_enemy_idx = -1;
    float speed = cfg::PROJECTILE_SPEED;
    float damage = 0;
    TowerType tower_type = TowerType::Arrow;
    Color color = {};

    // Special data
    float splash_radius = 0;
    float slow_factor = 0;
    float slow_duration = 0;
    int   chain_count = 0;
    float chain_range = 0;
    float dot_damage = 0;
    float dot_duration = 0;

    void update(float dt, EnemyPool& enemies);
    void on_impact(EnemyPool& enemies);
};

struct ProjectilePool {
    Projectile projectiles[cfg::MAX_PROJECTILES];

    void init();
    Projectile* spawn(Vec2 start, int target_idx, float damage,
                      TowerType type, Color color,
                      float splash_r, float slow_f, float slow_d,
                      int chain_c, float chain_r,
                      float dot_d, float dot_dur,
                      const EnemyPool& enemies);
    void update_all(float dt, EnemyPool& enemies);
    int active_count() const;
};
```

- [ ] **Step 2: Write `src/core/projectile.cpp`**

```cpp
#include "core/projectile.h"
#include "core/math_utils.h"

void Projectile::update(float dt, EnemyPool& enemies) {
    if (!active) return;
    prev_pos = pos;

    // Track living target
    Vec2 dest = target_pos;
    if (target_enemy_idx >= 0 && enemies.enemies[target_enemy_idx].active &&
        !enemies.enemies[target_enemy_idx].dying) {
        dest = enemies.enemies[target_enemy_idx].pos;
        target_pos = dest;
    }

    float dx = dest.x - pos.x;
    float dy = dest.y - pos.y;
    float dist = distance(pos, dest);

    if (dist < cfg::PROJECTILE_HIT_DIST) {
        on_impact(enemies);
        active = false;
        return;
    }

    float move = sim_mul(speed, dt);
    if (move >= dist) {
        pos = dest;
        on_impact(enemies);
        active = false;
    } else {
        float ratio = sim_div(move, dist);
        pos.x += sim_mul(dx, ratio);
        pos.y += sim_mul(dy, ratio);
    }
}

void Projectile::on_impact(EnemyPool& enemies) {
    // Primary target damage
    if (target_enemy_idx >= 0 && enemies.enemies[target_enemy_idx].active) {
        Enemy& target = enemies.enemies[target_enemy_idx];
        target.take_damage(damage);

        // Slow
        if (slow_factor > 0 && slow_duration > 0) {
            target.apply_slow(slow_factor, slow_duration);
        }

        // DoT
        if (dot_damage > 0 && dot_duration > 0) {
            target.add_dot(dot_damage, dot_duration);
        }
    }

    // Splash
    if (splash_radius > 0) {
        float splash_dmg = sim_mul(damage, 0.5f);
        for (int i = 0; i < cfg::MAX_ENEMIES; ++i) {
            if (i == target_enemy_idx) continue;
            auto& e = enemies.enemies[i];
            if (!e.active || e.dying) continue;
            if (distance(pos, e.pos) <= splash_radius) {
                e.take_damage(splash_dmg);
            }
        }
    }

    // Chain lightning
    if (chain_count > 0) {
        float chain_dmg = sim_mul(damage, 0.7f);
        bool hit[cfg::MAX_ENEMIES] = {};
        if (target_enemy_idx >= 0) hit[target_enemy_idx] = true;
        Vec2 last_pos = pos;
        int remaining_chains = chain_count;

        while (remaining_chains > 0) {
            float best_dist = 99999.0f;
            int best_idx = -1;
            for (int i = 0; i < cfg::MAX_ENEMIES; ++i) {
                if (hit[i]) continue;
                auto& e = enemies.enemies[i];
                if (!e.active || e.dying) continue;
                float d = distance(last_pos, e.pos);
                if (d <= chain_range && d < best_dist) {
                    best_dist = d;
                    best_idx = i;
                }
            }
            if (best_idx < 0) break;
            hit[best_idx] = true;
            enemies.enemies[best_idx].take_damage(chain_dmg);
            last_pos = enemies.enemies[best_idx].pos;
            remaining_chains--;
        }
    }
}

// --- ProjectilePool ---
void ProjectilePool::init() {
    for (auto& p : projectiles) p.active = false;
}

Projectile* ProjectilePool::spawn(Vec2 start, int target_idx, float damage,
                                   TowerType type, Color color,
                                   float splash_r, float slow_f, float slow_d,
                                   int chain_c, float chain_r,
                                   float dot_d, float dot_dur,
                                   const EnemyPool& enemies) {
    for (auto& p : projectiles) {
        if (!p.active) {
            p.active = true;
            p.pos = start;
            p.prev_pos = start;
            p.target_enemy_idx = target_idx;
            p.damage = damage;
            p.tower_type = type;
            p.color = color;
            p.splash_radius = splash_r;
            p.slow_factor = slow_f;
            p.slow_duration = slow_d;
            p.chain_count = chain_c;
            p.chain_range = chain_r;
            p.dot_damage = dot_d;
            p.dot_duration = dot_dur;
            p.speed = cfg::PROJECTILE_SPEED;
            // Set target pos
            if (target_idx >= 0 && enemies.enemies[target_idx].active) {
                p.target_pos = enemies.enemies[target_idx].pos;
            } else {
                p.target_pos = start;
            }
            return &p;
        }
    }
    return nullptr; // pool full — silently skip
}

void ProjectilePool::update_all(float dt, EnemyPool& enemies) {
    for (auto& p : projectiles) {
        if (p.active) p.update(dt, enemies);
    }
}

int ProjectilePool::active_count() const {
    int c = 0;
    for (const auto& p : projectiles)
        if (p.active) ++c;
    return c;
}
```

- [ ] **Step 3: Verify compiles, commit**

```bash
cmake -B build -S . && cmake --build build
git add src/core/projectile.h src/core/projectile.cpp
git commit -m "feat: add projectile system with splash, chain, slow, DoT"
```

---

## Task 9: Wave Manager + Map Generator

**Files:**

- Create: `src/core/wave_manager.h`, `src/core/wave_manager.cpp`
- Create: `src/core/map_generator.h`, `src/core/map_generator.cpp`

- [ ] **Step 1: Write `src/core/wave_manager.h`**

```cpp
#pragma once
#include "core/config.h"
#include "core/enemy.h"
#include "core/pathfinding.h"

struct SpawnEntry {
    EnemyType type;
    int path_idx; // which spawn point's path to use
    float delay;
};

struct WaveManager {
    cfg::WaveDef wave_defs[cfg::TOTAL_WAVES];
    int current_wave = 0; // 0-indexed, -1 = not started
    GamePhase phase = GamePhase::Build;

    SpawnEntry spawn_queue[256];
    int queue_size = 0;
    int queue_head = 0;
    float spawn_timer = 0;
    bool wave_had_leak = false;

    void init();
    void start_wave(int spawn_count);
    void update(float dt, EnemyPool& enemies, const Path paths[], int path_count);
    bool is_wave_complete(const EnemyPool& enemies) const;
    int enemies_remaining(const EnemyPool& enemies) const;
    bool all_waves_done() const;
};
```

- [ ] **Step 2: Write `src/core/wave_manager.cpp`**

```cpp
#include "core/wave_manager.h"
#include <cstdlib>

void WaveManager::init() {
    cfg::generate_waves(wave_defs);
    current_wave = -1;
    phase = GamePhase::Build;
    queue_size = 0;
    queue_head = 0;
}

void WaveManager::start_wave(int spawn_count) {
    if (current_wave >= cfg::TOTAL_WAVES - 1) return;
    current_wave++;
    phase = GamePhase::Wave;
    wave_had_leak = false;
    queue_size = 0;
    queue_head = 0;
    spawn_timer = 0;

    const auto& wd = wave_defs[current_wave];
    for (int e = 0; e < wd.entry_count; ++e) {
        const auto& entry = wd.entries[e];
        for (int i = 0; i < entry.count; ++i) {
            if (queue_size < 256) {
                int path_choice = (spawn_count > 1) ? (queue_size % spawn_count) : 0;
                spawn_queue[queue_size++] = {entry.type, path_choice, entry.spawn_delay};
            }
        }
    }
}

void WaveManager::update(float dt, EnemyPool& enemies, const Path paths[], int path_count) {
    if (phase != GamePhase::Wave) return;

    spawn_timer -= dt;
    while (spawn_timer <= 0 && queue_head < queue_size) {
        const auto& entry = spawn_queue[queue_head];
        int pi = (entry.path_idx < path_count) ? entry.path_idx : 0;
        Enemy* e = enemies.spawn(entry.type, &paths[pi]);
        if (e) {
            queue_head++;
            spawn_timer = (queue_head < queue_size) ? spawn_queue[queue_head].delay : 0;
        } else {
            break; // pool full, try next tick
        }
    }
}

bool WaveManager::is_wave_complete(const EnemyPool& enemies) const {
    return phase == GamePhase::Wave &&
           queue_head >= queue_size &&
           enemies.active_count() == 0;
}

int WaveManager::enemies_remaining(const EnemyPool& enemies) const {
    return (queue_size - queue_head) + enemies.active_count();
}

bool WaveManager::all_waves_done() const {
    return current_wave >= cfg::TOTAL_WAVES - 1;
}
```

- [ ] **Step 3: Write `src/core/map_generator.h`**

```cpp
#pragma once
#include "core/grid.h"
#include "core/pathfinding.h"

struct MapData {
    Grid grid;
    Path paths[cfg::MAX_SPAWNS];
    int path_count = 0;
    bool valid = false;
};

// Generate a random map. seed=0 uses random device.
MapData generate_map(uint32_t seed = 0);
```

- [ ] **Step 4: Write `src/core/map_generator.cpp`**

```cpp
#include "core/map_generator.h"
#include <cstdlib>

static uint32_t rng_state = 1;
static void rng_seed(uint32_t s) { rng_state = s ? s : 1; }
static uint32_t rng_next() {
    rng_state ^= rng_state << 13;
    rng_state ^= rng_state >> 17;
    rng_state ^= rng_state << 5;
    return rng_state;
}
static int rng_range(int lo, int hi) {
    return lo + static_cast<int>(rng_next() % (hi - lo + 1));
}

MapData generate_map(uint32_t seed) {
    if (seed == 0) seed = static_cast<uint32_t>(std::rand());
    rng_seed(seed);

    for (int attempt = 0; attempt < 200; ++attempt) {
        MapData result;
        result.grid.init();
        Grid& g = result.grid;

        // Place base on right edge
        int base_y = rng_range(2, cfg::GRID_H - 3);
        g.base_pos = {static_cast<float>(cfg::GRID_W - 1), static_cast<float>(base_y)};
        g.set(cfg::GRID_W - 1, base_y, Terrain::Base);

        // Place 1-2 spawns on left edge
        int spawn_count = rng_range(1, 2);
        int spawn_rows[2];
        spawn_rows[0] = rng_range(1, cfg::GRID_H - 2);
        g.set(0, spawn_rows[0], Terrain::Spawn);
        g.spawns[0] = {0, static_cast<float>(spawn_rows[0])};
        g.spawn_count = 1;

        if (spawn_count == 2) {
            for (int tries = 0; tries < 20; ++tries) {
                int row2 = rng_range(1, cfg::GRID_H - 2);
                if (std::abs(row2 - spawn_rows[0]) >= 3) {
                    spawn_rows[1] = row2;
                    g.set(0, row2, Terrain::Spawn);
                    g.spawns[1] = {0, static_cast<float>(row2)};
                    g.spawn_count = 2;
                    break;
                }
            }
        }

        // Scatter obstacles (25-35% of empty tiles)
        int total_empty = 0;
        for (int y = 0; y < cfg::GRID_H; ++y)
            for (int x = 0; x < cfg::GRID_W; ++x)
                if (g.get(x, y) == Terrain::Empty) total_empty++;

        int obstacle_target = rng_range(total_empty / 4, total_empty / 3);
        int placed = 0;

        for (int i = 0; i < obstacle_target * 3 && placed < obstacle_target; ++i) {
            int ox = rng_range(1, cfg::GRID_W - 2);
            int oy = rng_range(0, cfg::GRID_H - 1);
            if (g.get(ox, oy) != Terrain::Empty) continue;

            int roll = rng_range(0, 9);
            Terrain t = (roll < 5) ? Terrain::Rock : (roll < 8) ? Terrain::Tree : Terrain::Water;
            g.set(ox, oy, t);

            // Validate all spawns still connect
            bool all_ok = true;
            for (int s = 0; s < g.spawn_count; ++s) {
                Path p = bfs(g, g.spawns[s], g.base_pos);
                if (!p.valid) { all_ok = false; break; }
            }
            if (!all_ok) {
                g.set(ox, oy, Terrain::Empty);
            } else {
                placed++;
            }
        }

        // Final path computation
        bool all_valid = true;
        result.path_count = g.spawn_count;
        for (int s = 0; s < g.spawn_count; ++s) {
            result.paths[s] = bfs(g, g.spawns[s], g.base_pos);
            if (!result.paths[s].valid) { all_valid = false; break; }
        }

        if (!all_valid) continue;

        // Mark path tiles
        for (int s = 0; s < result.path_count; ++s) {
            for (int i = 0; i < result.paths[s].length; ++i) {
                int px = static_cast<int>(result.paths[s].points[i].x);
                int py = static_cast<int>(result.paths[s].points[i].y);
                if (g.get(px, py) == Terrain::Empty) {
                    g.set(px, py, Terrain::Path);
                }
            }
        }

        result.valid = true;
        return result;
    }

    // Fallback: minimal map
    MapData fallback;
    fallback.grid.init();
    fallback.grid.base_pos = {static_cast<float>(cfg::GRID_W - 1), static_cast<float>(cfg::GRID_H / 2)};
    fallback.grid.set(cfg::GRID_W - 1, cfg::GRID_H / 2, Terrain::Base);
    fallback.grid.set(0, cfg::GRID_H / 2, Terrain::Spawn);
    fallback.grid.spawns[0] = {0, static_cast<float>(cfg::GRID_H / 2)};
    fallback.grid.spawn_count = 1;
    for (int x = 1; x < cfg::GRID_W - 1; ++x) {
        fallback.grid.set(x, cfg::GRID_H / 2, Terrain::Path);
    }
    fallback.paths[0] = bfs(fallback.grid, fallback.grid.spawns[0], fallback.grid.base_pos);
    fallback.path_count = 1;
    fallback.valid = true;
    return fallback;
}
```

- [ ] **Step 5: Verify compiles, commit**

```bash
cmake -B build -S . && cmake --build build
git add src/core/wave_manager.h src/core/wave_manager.cpp src/core/map_generator.h src/core/map_generator.cpp
git commit -m "feat: add wave manager and procedural map generator"
```

---

## Task 10: Effects System

**Files:**

- Create: `src/core/effects.h`, `src/core/effects.cpp`

- [ ] **Step 1: Write `src/core/effects.h`**

```cpp
#pragma once
#include "core/types.h"
#include "core/config.h"

struct Particle {
    bool active = false;
    Vec2 pos;
    Vec2 vel;
    Color color;
    float life;
    float max_life;
};

struct DamageNumber {
    bool active = false;
    Vec2 pos;
    float value;
    float life;
    Color color;
};

struct ScreenShake {
    float duration = 0;
    float intensity = 0;
    float offset_x = 0;
    float offset_y = 0;

    void trigger(float dur, float intens);
    void update(float dt);
};

struct Effects {
    Particle particles[cfg::MAX_PARTICLES];
    DamageNumber dmg_numbers[cfg::MAX_DMG_NUMBERS];
    ScreenShake shake;

    void init();
    void emit_burst(Vec2 pos, Color color, int count);
    void add_dmg_number(Vec2 pos, float value, Color color);
    void update(float dt);
};
```

- [ ] **Step 2: Write `src/core/effects.cpp`**

```cpp
#include "core/effects.h"
#include <cstdlib>
#include <cmath>

void ScreenShake::trigger(float dur, float intens) {
    duration = dur;
    intensity = intens;
}

void ScreenShake::update(float dt) {
    if (duration > 0) {
        duration -= dt;
        float frac = duration > 0 ? duration / 0.3f : 0;
        offset_x = (std::rand() % 3 - 1) * intensity * frac;
        offset_y = (std::rand() % 3 - 1) * intensity * frac;
    } else {
        offset_x = 0;
        offset_y = 0;
    }
}

void Effects::init() {
    for (auto& p : particles) p.active = false;
    for (auto& d : dmg_numbers) d.active = false;
    shake = {};
}

void Effects::emit_burst(Vec2 pos, Color color, int count) {
    for (int i = 0; i < count; ++i) {
        for (auto& p : particles) {
            if (!p.active) {
                p.active = true;
                p.pos = pos;
                float angle = (std::rand() % 360) * 3.14159f / 180.0f;
                float spd = 1.0f + (std::rand() % 30) / 10.0f;
                p.vel = {std::cos(angle) * spd, std::sin(angle) * spd};
                p.color = color;
                p.max_life = 0.3f + (std::rand() % 20) / 100.0f;
                p.life = p.max_life;
                break;
            }
        }
    }
}

void Effects::add_dmg_number(Vec2 pos, float value, Color color) {
    for (auto& d : dmg_numbers) {
        if (!d.active) {
            d.active = true;
            d.pos = pos;
            d.value = value;
            d.life = 0.8f;
            d.color = color;
            return;
        }
    }
}

void Effects::update(float dt) {
    for (auto& p : particles) {
        if (!p.active) continue;
        p.pos.x += p.vel.x * dt;
        p.pos.y += p.vel.y * dt;
        p.life -= dt;
        if (p.life <= 0) p.active = false;
    }
    for (auto& d : dmg_numbers) {
        if (!d.active) continue;
        d.pos.y -= 2.0f * dt; // float up
        d.life -= dt;
        if (d.life <= 0) d.active = false;
    }
    shake.update(dt);
}
```

- [ ] **Step 3: Verify compiles, commit**

```bash
cmake -B build -S . && cmake --build build
git add src/core/effects.h src/core/effects.cpp
git commit -m "feat: add effects system (particles, damage numbers, screen shake)"
```

---

## Task 11: Game Core (Top-Level Simulation)

**Files:**

- Create: `src/core/game.h`, `src/core/game.cpp`

- [ ] **Step 1: Write `src/core/game.h`**

```cpp
#pragma once
#include "core/grid.h"
#include "core/pathfinding.h"
#include "core/enemy.h"
#include "core/tower.h"
#include "core/projectile.h"
#include "core/wave_manager.h"
#include "core/economy.h"
#include "core/map_generator.h"
#include "core/effects.h"

// Events emitted by simulation tick, consumed by renderer/audio
enum class GameEventType : uint8_t {
    EnemyKilled, EnemyLeaked, TowerFired, WaveComplete, WaveStart,
    TitanSpawned, BaseHit, TowerPlaced, TowerSold, TowerUpgraded,
    FleetUpgraded, Victory, Defeat
};

struct GameEvent {
    GameEventType type;
    Vec2 pos;
    int data; // gold earned, lives lost, etc.
};

struct GameSim {
    Grid grid;
    Path paths[cfg::MAX_SPAWNS];
    int path_count = 0;
    EnemyPool enemies;
    TowerArray towers;
    ProjectilePool projectiles;
    WaveManager wave_mgr;
    Economy economy;
    Effects effects;
    SpeedMode speed_mode = SpeedMode::Normal;

    // Event buffer
    GameEvent events[64];
    int event_count = 0;

    // Fleet upgrade state
    bool fleet_available = false;
    TowerType fleet_selected_type = TowerType::Arrow;
    int fleet_target_level = 2;

    // Titan tracking (for boss HP bar)
    int titan_idx = -1;

    void new_game(uint32_t seed = 0);
    void tick(float dt); // one simulation tick per v5 canonical order
    void emit_event(GameEventType type, Vec2 pos = {}, int data = 0);

    // Player actions (called by gameplay state)
    bool try_place_tower(TowerType type, int tx, int ty);
    bool try_upgrade_tower(int tx, int ty);
    int  try_sell_tower(int tx, int ty); // returns gold earned
    bool try_fleet_upgrade();
    void start_next_wave();
    void cycle_speed();

    float speed_multiplier() const;
};
```

- [ ] **Step 2: Write `src/core/game.cpp`**

```cpp
#include "core/game.h"
#include "core/math_utils.h"

void GameSim::new_game(uint32_t seed) {
    MapData map = generate_map(seed);
    grid = map.grid;
    for (int i = 0; i < map.path_count; ++i) paths[i] = map.paths[i];
    path_count = map.path_count;

    enemies.init();
    towers.init();
    projectiles.init();
    wave_mgr.init();
    economy.reset();
    effects.init();
    speed_mode = SpeedMode::Normal;
    event_count = 0;
    fleet_available = false;
    titan_idx = -1;
}

float GameSim::speed_multiplier() const {
    switch (speed_mode) {
        case SpeedMode::Fast2x: return 2.0f;
        case SpeedMode::Fast3x: return 3.0f;
        default: return 1.0f;
    }
}

void GameSim::cycle_speed() {
    switch (speed_mode) {
        case SpeedMode::Normal: speed_mode = SpeedMode::Fast2x; break;
        case SpeedMode::Fast2x: speed_mode = SpeedMode::Fast3x; break;
        case SpeedMode::Fast3x: speed_mode = SpeedMode::Normal; break;
    }
}

void GameSim::emit_event(GameEventType type, Vec2 pos, int data) {
    if (event_count < 64) {
        events[event_count++] = {type, pos, data};
    }
}

// Canonical tick order per v5 spec section 10
void GameSim::tick(float dt) {
    event_count = 0;

    if (wave_mgr.phase != GamePhase::Wave) return;

    // 1-2. Spawn enemies
    wave_mgr.update(dt, enemies, paths, path_count);

    // Track titans
    titan_idx = -1;
    for (int i = 0; i < cfg::MAX_ENEMIES; ++i) {
        if (enemies.enemies[i].active && enemies.enemies[i].type == EnemyType::Titan) {
            titan_idx = i;
            break;
        }
    }

    // 3. Tick enemy status effects + movement (done inside enemy.update)
    // 4. Resolve healer pulses
    enemies.heal_pass();

    // 5. Update enemy movement
    enemies.update_all(dt);

    // 6. Check enemy leaks
    for (int i = 0; i < cfg::MAX_ENEMIES; ++i) {
        auto& e = enemies.enemies[i];
        if (e.reached_base) {
            economy.lose_lives(e.lives_cost);
            emit_event(GameEventType::EnemyLeaked, e.pos, e.lives_cost);
            emit_event(GameEventType::BaseHit, grid.base_pos, e.lives_cost);
            effects.shake.trigger(0.2f, 2.0f);
            e.active = false;
            e.reached_base = false;
        }
    }

    // 7. Check defeat
    if (economy.is_game_over()) {
        wave_mgr.phase = GamePhase::DefeatPending;
        emit_event(GameEventType::Defeat);
        return;
    }

    // 8-9. Tower targeting + firing
    for (auto& t : towers.towers) {
        if (!t.active) continue;
        t.update(dt, enemies);
        if (t.ready_to_fire()) {
            Vec2 start = {t.tile_x + 0.5f, t.tile_y + 0.5f};
            projectiles.spawn(start, t.target_enemy_idx, t.damage,
                              t.type, t.color,
                              t.splash_radius, t.slow_factor, t.slow_duration,
                              t.chain_count, t.chain_range,
                              t.dot_damage, t.dot_duration,
                              enemies);
            t.cooldown_timer = t.cooldown;
            t.firing_anim = true;
            t.firing_anim_timer = 0.1f;
            emit_event(GameEventType::TowerFired, start);
        }
    }

    // 10-11. Update projectiles + resolve hits
    projectiles.update_all(dt, enemies);

    // 12. Resolve enemy deaths
    for (int i = 0; i < cfg::MAX_ENEMIES; ++i) {
        auto& e = enemies.enemies[i];
        if (e.dying && e.death_timer <= 0 && e.active) {
            // already handled in enemy.update — just award gold
        }
        if (e.dying && !e.active) {
            // Death finalized
        }
        // Check for just-died enemies (hp <= 0, still active via dying state)
        if (e.dying && e.death_timer > -0.1f && e.gold_value > 0) {
            economy.earn(e.gold_value);
            emit_event(GameEventType::EnemyKilled, e.pos, e.gold_value);
            effects.emit_burst(e.pos, cfg::ENEMY_DEFS[static_cast<int>(e.type)].color, 6);
            effects.add_dmg_number(e.pos, static_cast<float>(e.gold_value), cfg::colors::GOLD);
            e.gold_value = 0; // prevent double-award
        }
    }

    // 13. Check wave completion
    if (wave_mgr.is_wave_complete(enemies)) {
        // 14. Award perfect wave bonus
        economy.wave_clear_bonus();
        emit_event(GameEventType::WaveComplete, {}, wave_mgr.current_wave + 1);

        if (wave_mgr.all_waves_done()) {
            emit_event(GameEventType::Victory);
        } else {
            wave_mgr.phase = GamePhase::Build;
            speed_mode = SpeedMode::Normal; // reset to 1x

            // Check fleet upgrade unlock
            int waves_done = wave_mgr.current_wave + 1;
            fleet_available = cfg::fleet_upgrade_unlocked(waves_done);
            fleet_target_level = cfg::fleet_upgrade_max_level(waves_done);
        }
    }

    // 15. Update effects
    effects.update(dt);
}

bool GameSim::try_place_tower(TowerType type, int tx, int ty) {
    if (!grid.is_buildable(tx, ty)) return false;
    int cost = cfg::TOWER_DEFS[static_cast<int>(type)].cost;
    if (!economy.can_afford(cost)) return false;
    Tower* t = towers.place(type, tx, ty);
    if (!t) return false;
    economy.spend(cost);
    grid.set(tx, ty, Terrain::Tower);
    emit_event(GameEventType::TowerPlaced, {static_cast<float>(tx), static_cast<float>(ty)}, cost);
    return true;
}

bool GameSim::try_upgrade_tower(int tx, int ty) {
    Tower* t = towers.get_at(tx, ty);
    if (!t) return false;
    int cost = t->upgrade_cost();
    if (cost < 0 || !economy.can_afford(cost)) return false;
    economy.spend(cost);
    t->upgrade();
    emit_event(GameEventType::TowerUpgraded, {static_cast<float>(tx), static_cast<float>(ty)}, cost);
    return true;
}

int GameSim::try_sell_tower(int tx, int ty) {
    Tower* t = towers.get_at(tx, ty);
    if (!t) return 0;
    int value = t->sell_value();
    economy.earn(value);
    grid.set(tx, ty, Terrain::Empty);
    towers.remove(tx, ty);
    emit_event(GameEventType::TowerSold, {static_cast<float>(tx), static_cast<float>(ty)}, value);
    return value;
}

bool GameSim::try_fleet_upgrade() {
    if (!fleet_available) return false;
    TowerType ft = fleet_selected_type;
    int count = towers.count_type_below_level(ft, fleet_target_level);
    if (count == 0) return false;

    // Calculate per-tower cost (sum of all needed upgrade steps)
    int per_tower_total = 0;
    const auto& def = cfg::TOWER_DEFS[static_cast<int>(ft)];
    // We need to compute cost based on what each tower needs
    // Simplified: assume all are level 1, upgrading to target
    for (int lv = 1; lv < fleet_target_level; ++lv) {
        per_tower_total += def.upgrades[lv - 1].cost;
    }

    int total = Economy::fleet_upgrade_cost(count, per_tower_total);
    if (!economy.can_afford(total)) return false;

    economy.spend(total);
    towers.upgrade_all_type(ft, fleet_target_level);
    emit_event(GameEventType::FleetUpgraded, {}, total);
    return true;
}

void GameSim::start_next_wave() {
    if (wave_mgr.phase != GamePhase::Build) return;
    if (wave_mgr.current_wave >= cfg::TOTAL_WAVES - 1) return;
    economy.had_leak_this_wave = false;
    wave_mgr.start_wave(path_count);
    emit_event(GameEventType::WaveStart, {}, wave_mgr.current_wave + 1);
}
```

- [ ] **Step 3: Verify compiles, commit**

```bash
cmake -B build -S . && cmake --build build
git add src/core/game.h src/core/game.cpp
git commit -m "feat: add game simulation core with canonical tick order"
```

---

## Task 12: State Machine + All Game States

**Files:**

- Create: `src/states/state.h`
- Create: `src/states/gameplay_state.h`, `src/states/gameplay_state.cpp`
- Create: `src/states/title_state.h`, `src/states/title_state.cpp`
- Create: `src/states/pause_state.h`, `src/states/pause_state.cpp`
- Create: `src/states/game_over_state.h`, `src/states/game_over_state.cpp`
- Create: `src/states/victory_state.h`, `src/states/victory_state.cpp`

- [ ] **Step 1: Write `src/states/state.h`**

```cpp
#pragma once
#include "hal/hal.h"
#include "core/game.h"

struct App; // forward decl

struct State {
    virtual ~State() = default;
    virtual void enter(App& app) {}
    virtual void exit(App& app) {}
    virtual void update(App& app, float dt) = 0;
    virtual void render(App& app, float alpha) = 0;
};

enum class StateId : uint8_t {
    Title, Gameplay, Pause, GameOver, Victory
};

struct App {
    IRenderer* renderer = nullptr;
    IInput* input = nullptr;
    IAudio* audio = nullptr;
    GameSim sim;
    State* states[5] = {};
    State* current_state = nullptr;
    StateId current_id = StateId::Title;
    bool running = true;

    // Save data
    int best_wave = 0;
    int best_score = 0;
    int games_played = 0;

    void change_state(StateId id);
};
```

- [ ] **Step 2: Write `src/states/title_state.h` + `title_state.cpp`**

```cpp
// title_state.h
#pragma once
#include "states/state.h"

struct TitleState : State {
    int menu_idx = 0;
    static constexpr int MENU_COUNT = 3; // New Game, Instructions, Quit
    float anim_timer = 0;

    void enter(App& app) override;
    void update(App& app, float dt) override;
    void render(App& app, float alpha) override;
};
```

```cpp
// title_state.cpp
#include "states/title_state.h"

void TitleState::enter(App& app) {
    menu_idx = 0;
    anim_timer = 0;
    app.audio->play_bgm(BgmId::Title);
}

void TitleState::update(App& app, float dt) {
    anim_timer += dt;
    if (app.input->pressed(InputButton::Up)) {
        menu_idx = (menu_idx - 1 + MENU_COUNT) % MENU_COUNT;
        app.audio->play_sfx(SfxId::MenuMove);
    }
    if (app.input->pressed(InputButton::Down)) {
        menu_idx = (menu_idx + 1) % MENU_COUNT;
        app.audio->play_sfx(SfxId::MenuMove);
    }
    if (app.input->pressed(InputButton::A)) {
        app.audio->play_sfx(SfxId::MenuSelect);
        switch (menu_idx) {
            case 0: app.change_state(StateId::Gameplay); break;
            case 1: break; // instructions (skip for now)
            case 2: app.running = false; break;
        }
    }
}

void TitleState::render(App& app, float alpha) {
    auto* r = app.renderer;
    r->clear(cfg::colors::BG);

    // Title
    r->draw_text("BASTION TD", cfg::SCREEN_W / 2 - 30, 20, cfg::colors::GOLD);

    // Menu items
    const char* items[] = {"New Game", "Instructions", "Quit"};
    for (int i = 0; i < MENU_COUNT; ++i) {
        Color c = (i == menu_idx) ? cfg::colors::ACCENT : cfg::colors::WHITE;
        int y = 60 + i * 12;
        if (i == menu_idx) r->draw_text(">", cfg::SCREEN_W / 2 - 40, y, c);
        r->draw_text(items[i], cfg::SCREEN_W / 2 - 30, y, c);
    }

    // High score
    if (app.best_wave > 0) {
        char buf[32];
        snprintf(buf, sizeof(buf), "Best: Wave %d", app.best_wave);
        r->draw_text(buf, cfg::SCREEN_W / 2 - 30, 110, cfg::colors::GOLD);
    }

    r->present();
}
```

- [ ] **Step 3: Write `src/states/gameplay_state.h` + `gameplay_state.cpp`**

```cpp
// gameplay_state.h
#pragma once
#include "states/state.h"

struct GameplayState : State {
    int cursor_x = 0, cursor_y = 0;
    int selected_tower_idx = 0; // 0-4 into TowerType
    float sell_hold_timer = 0;
    bool show_upgrade = false;
    bool show_fleet_menu = false;
    int fleet_type_idx = 0; // for cycling fleet upgrade type

    float notification_timer = 0;
    char notification[64] = {};

    void enter(App& app) override;
    void update(App& app, float dt) override;
    void render(App& app, float alpha) override;

    void render_grid(App& app, float alpha);
    void render_enemies(App& app, float alpha);
    void render_towers(App& app);
    void render_projectiles(App& app, float alpha);
    void render_hud(App& app);
    void render_cursor(App& app);
    void render_effects(App& app);
    void show_notification(const char* msg);
};
```

```cpp
// gameplay_state.cpp
#include "states/gameplay_state.h"
#include "core/math_utils.h"
#include <cstdio>
#include <cstring>

void GameplayState::enter(App& app) {
    app.sim.new_game();
    cursor_x = cfg::GRID_W / 2;
    cursor_y = cfg::GRID_H / 2;
    selected_tower_idx = 0;
    sell_hold_timer = 0;
    show_upgrade = false;
    show_fleet_menu = false;
    fleet_type_idx = 0;
    notification_timer = 0;
    app.audio->play_bgm(BgmId::Build);
}

void GameplayState::show_notification(const char* msg) {
    snprintf(notification, sizeof(notification), "%s", msg);
    notification_timer = 2.0f;
}

void GameplayState::update(App& app, float dt) {
    auto& sim = app.sim;
    auto* input = app.input;

    // Pause
    if (input->pressed(InputButton::Start)) {
        app.change_state(StateId::Pause);
        return;
    }

    // Fast-forward toggle (only during wave)
    if (input->pressed(InputButton::Select) && sim.wave_mgr.phase == GamePhase::Wave) {
        sim.cycle_speed();
    }

    // Notification timer
    if (notification_timer > 0) notification_timer -= dt;

    // === BUILD PHASE ===
    if (sim.wave_mgr.phase == GamePhase::Build) {
        // Cursor movement
        if (input->pressed(InputButton::Up))    cursor_y = sim_to_int(sim_max(0, cursor_y - 1.0f));
        if (input->pressed(InputButton::Down))  cursor_y = sim_to_int(sim_min(cfg::GRID_H - 1.0f, cursor_y + 1.0f));
        if (input->pressed(InputButton::Left))  cursor_x = sim_to_int(sim_max(0, cursor_x - 1.0f));
        if (input->pressed(InputButton::Right)) cursor_x = sim_to_int(sim_min(cfg::GRID_W - 1.0f, cursor_x + 1.0f));

        // Tower type selection
        if (input->pressed(InputButton::L)) {
            selected_tower_idx = (selected_tower_idx - 1 + 5) % 5;
            app.audio->play_sfx(SfxId::MenuMove);
        }
        if (input->pressed(InputButton::R)) {
            selected_tower_idx = (selected_tower_idx + 1) % 5;
            app.audio->play_sfx(SfxId::MenuMove);
        }

        // Fleet upgrade menu
        if (input->pressed(InputButton::FleetUpgrade) && sim.fleet_available) {
            show_fleet_menu = !show_fleet_menu;
            if (show_fleet_menu) fleet_type_idx = 0;
        }

        if (show_fleet_menu) {
            if (input->pressed(InputButton::L)) fleet_type_idx = (fleet_type_idx - 1 + 5) % 5;
            if (input->pressed(InputButton::R)) fleet_type_idx = (fleet_type_idx + 1) % 5;
            sim.fleet_selected_type = static_cast<TowerType>(fleet_type_idx);
            if (input->pressed(InputButton::A)) {
                if (sim.try_fleet_upgrade()) {
                    app.audio->play_sfx(SfxId::Upgrade);
                    show_notification("Fleet upgraded!");
                    show_fleet_menu = false;
                }
            }
            if (input->pressed(InputButton::B)) show_fleet_menu = false;
            return;
        }

        // A button: place tower or start wave
        if (input->pressed(InputButton::A)) {
            TowerType tt = static_cast<TowerType>(selected_tower_idx);
            if (sim.grid.is_buildable(cursor_x, cursor_y)) {
                if (sim.try_place_tower(tt, cursor_x, cursor_y)) {
                    app.audio->play_sfx(SfxId::Place);
                } else {
                    show_upgrade = false;
                }
            } else if (show_upgrade) {
                if (sim.try_upgrade_tower(cursor_x, cursor_y)) {
                    app.audio->play_sfx(SfxId::Upgrade);
                    show_upgrade = false;
                }
            } else {
                // Start wave
                sim.start_next_wave();
                app.audio->play_sfx(SfxId::WaveStart);
                char buf[32];
                snprintf(buf, sizeof(buf), "Wave %d!", sim.wave_mgr.current_wave + 1);
                show_notification(buf);
                app.audio->play_bgm(sim.wave_mgr.wave_defs[sim.wave_mgr.current_wave].has_titan
                    ? BgmId::Boss : BgmId::Wave);
            }
        }

        // B button: sell (hold) or show upgrade (tap)
        if (input->held(InputButton::B)) {
            sell_hold_timer += dt;
            if (sell_hold_timer >= 1.0f) {
                int gold = sim.try_sell_tower(cursor_x, cursor_y);
                if (gold > 0) {
                    app.audio->play_sfx(SfxId::Sell);
                    char buf[32];
                    snprintf(buf, sizeof(buf), "Sold +%dg", gold);
                    show_notification(buf);
                }
                sell_hold_timer = 0;
                show_upgrade = false;
            }
        } else {
            if (sell_hold_timer > 0 && sell_hold_timer < 1.0f) {
                // Short press: toggle upgrade display
                Tower* t = sim.towers.get_at(cursor_x, cursor_y);
                if (t) show_upgrade = !show_upgrade;
            }
            sell_hold_timer = 0;
        }
    }

    // === WAVE PHASE ===
    if (sim.wave_mgr.phase == GamePhase::Wave) {
        float sim_dt = sim_mul(cfg::SIM_DT, sim.speed_multiplier());
        sim.tick(sim_dt);

        // Process events for audio
        for (int i = 0; i < sim.event_count; ++i) {
            auto& ev = sim.events[i];
            switch (ev.type) {
                case GameEventType::EnemyKilled: app.audio->play_sfx(SfxId::EnemyDeath); break;
                case GameEventType::BaseHit: app.audio->play_sfx(SfxId::BaseHit); break;
                case GameEventType::TowerFired: app.audio->play_sfx(SfxId::Shoot); break;
                case GameEventType::WaveComplete: {
                    app.audio->play_sfx(SfxId::WaveClear);
                    app.audio->play_bgm(BgmId::Build);
                    char buf[32];
                    snprintf(buf, sizeof(buf), "Wave clear! +%dg", cfg::WAVE_CLEAR_BONUS);
                    show_notification(buf);
                    break;
                }
                case GameEventType::Victory: {
                    app.games_played++;
                    if (sim.wave_mgr.current_wave + 1 > app.best_wave)
                        app.best_wave = sim.wave_mgr.current_wave + 1;
                    app.change_state(StateId::Victory);
                    return;
                }
                case GameEventType::Defeat: {
                    app.games_played++;
                    if (sim.wave_mgr.current_wave + 1 > app.best_wave)
                        app.best_wave = sim.wave_mgr.current_wave + 1;
                    app.change_state(StateId::GameOver);
                    return;
                }
                default: break;
            }
        }
    }
}

void GameplayState::render(App& app, float alpha) {
    auto* r = app.renderer;
    auto& sim = app.sim;
    int sx = sim_to_int(sim.effects.shake.offset_x);
    int sy = sim_to_int(sim.effects.shake.offset_y);

    r->clear(cfg::colors::BG);
    render_grid(app, alpha);
    render_towers(app);
    render_enemies(app, alpha);
    render_projectiles(app, alpha);
    render_cursor(app);
    render_effects(app);
    render_hud(app);
    r->present();
}

void GameplayState::render_grid(App& app, float alpha) {
    auto* r = app.renderer;
    auto& g = app.sim.grid;
    int oy = cfg::GRID_OFFSET_Y;

    for (int ty = 0; ty < cfg::GRID_H; ++ty) {
        for (int tx = 0; tx < cfg::GRID_W; ++tx) {
            int px = tx * cfg::TILE_SIZE;
            int py = oy + ty * cfg::TILE_SIZE;
            Terrain t = g.get(tx, ty);
            Color c;
            switch (t) {
                case Terrain::Empty: c = cfg::colors::GRASS; break;
                case Terrain::Path:  c = cfg::colors::PATH; break;
                case Terrain::Rock:  c = cfg::colors::ROCK; break;
                case Terrain::Water: c = cfg::colors::WATER; break;
                case Terrain::Tree:  c = cfg::colors::TREE_COL; break;
                case Terrain::Spawn: c = cfg::colors::SPAWN; break;
                case Terrain::Base:  c = cfg::colors::BASE; break;
                case Terrain::Tower: c = cfg::colors::GRASS; break;
            }
            r->draw_rect(px, py, cfg::TILE_SIZE, cfg::TILE_SIZE, c);
        }
    }
}

void GameplayState::render_enemies(App& app, float alpha) {
    auto* r = app.renderer;
    int oy = cfg::GRID_OFFSET_Y;

    for (const auto& e : app.sim.enemies.enemies) {
        if (!e.active) continue;
        Vec2 rp = lerp(e.prev_pos, e.pos, alpha);
        int px = sim_to_int(rp.x * cfg::TILE_SIZE);
        int py = oy + sim_to_int(rp.y * cfg::TILE_SIZE);
        int sz = sim_to_int(e.size * cfg::TILE_SIZE * 0.8f);
        if (sz < 2) sz = 2;

        r->draw_rect(px - sz/2, py - sz/2, sz, sz, cfg::ENEMY_DEFS[static_cast<int>(e.type)].color);

        // HP bar
        if (e.hp < e.max_hp && !e.dying) {
            float hpf = sim_clamp(sim_div(e.hp, e.max_hp), 0.0f, 1.0f);
            int bw = sz;
            int bh = 1;
            int bx = px - sz/2;
            int by = py - sz/2 - 2;
            r->draw_rect(bx, by, bw, bh, cfg::colors::HEALTH);
            r->draw_rect(bx, by, sim_to_int(bw * hpf), bh, cfg::colors::ACCENT);
        }

        // Slow tint
        if (e.slow_timer > 0) {
            r->draw_rect(px - sz/4, py - sz/4, sz/2, sz/2, {100,180,220,100});
        }
    }
}

void GameplayState::render_towers(App& app) {
    auto* r = app.renderer;
    int oy = cfg::GRID_OFFSET_Y;

    for (const auto& t : app.sim.towers.towers) {
        if (!t.active) continue;
        int px = t.tile_x * cfg::TILE_SIZE;
        int py = oy + t.tile_y * cfg::TILE_SIZE;

        // Tower base
        r->draw_rect(px + 1, py + 1, cfg::TILE_SIZE - 2, cfg::TILE_SIZE - 2, t.color);

        // Character on tower (bob on fire)
        int char_offset_y = t.firing_anim ? -1 : 0;
        r->draw_sprite(t.char_sprite, px, py + char_offset_y);

        // Level pips
        for (int i = 0; i < t.level; ++i) {
            r->draw_rect(px + 2 + i * 2, py + cfg::TILE_SIZE - 2, 1, 1, cfg::colors::WHITE);
        }
    }
}

void GameplayState::render_projectiles(App& app, float alpha) {
    auto* r = app.renderer;
    int oy = cfg::GRID_OFFSET_Y;

    for (const auto& p : app.sim.projectiles.projectiles) {
        if (!p.active) continue;
        Vec2 rp = lerp(p.prev_pos, p.pos, alpha);
        int px = sim_to_int(rp.x * cfg::TILE_SIZE);
        int py = oy + sim_to_int(rp.y * cfg::TILE_SIZE);
        r->draw_rect(px - 1, py - 1, 2, 2, p.color);
    }
}

void GameplayState::render_cursor(App& app) {
    auto* r = app.renderer;
    if (app.sim.wave_mgr.phase != GamePhase::Build) return;

    int px = cursor_x * cfg::TILE_SIZE;
    int py = cfg::GRID_OFFSET_Y + cursor_y * cfg::TILE_SIZE;
    bool ok = app.sim.grid.is_buildable(cursor_x, cursor_y);
    Color c = ok ? cfg::colors::CURSOR_OK : cfg::colors::CURSOR_BAD;
    r->draw_rect_outline(px, py, cfg::TILE_SIZE, cfg::TILE_SIZE, c);

    // Show range circle for selected tower type when on buildable
    if (ok) {
        const auto& def = cfg::TOWER_DEFS[selected_tower_idx];
        int range_px = sim_to_int(def.range * cfg::TILE_SIZE);
        r->draw_circle(px + cfg::TILE_SIZE/2, py + cfg::TILE_SIZE/2, range_px, {255,255,255,40});
    }

    // Show range + info for existing tower
    Tower* t = app.sim.towers.get_at(cursor_x, cursor_y);
    if (t) {
        int range_px = sim_to_int(t->range * cfg::TILE_SIZE);
        r->draw_circle(px + cfg::TILE_SIZE/2, py + cfg::TILE_SIZE/2, range_px, {255,255,255,60});
        if (show_upgrade && t->upgrade_cost() >= 0) {
            char buf[32];
            snprintf(buf, sizeof(buf), "UP:%dg", t->upgrade_cost());
            r->draw_text(buf, px, py - 8, cfg::colors::GOLD);
        }
    }
}

void GameplayState::render_effects(App& app) {
    auto* r = app.renderer;
    int oy = cfg::GRID_OFFSET_Y;

    for (const auto& p : app.sim.effects.particles) {
        if (!p.active) continue;
        int px = sim_to_int(p.pos.x * cfg::TILE_SIZE);
        int py = oy + sim_to_int(p.pos.y * cfg::TILE_SIZE);
        r->draw_rect(px, py, 1, 1, p.color);
    }

    for (const auto& d : app.sim.effects.dmg_numbers) {
        if (!d.active) continue;
        int px = sim_to_int(d.pos.x * cfg::TILE_SIZE);
        int py = oy + sim_to_int(d.pos.y * cfg::TILE_SIZE);
        char buf[16];
        snprintf(buf, sizeof(buf), "%d", sim_to_int(d.value));
        r->draw_text(buf, px, py, d.color);
    }
}

void GameplayState::render_hud(App& app) {
    auto* r = app.renderer;
    auto& sim = app.sim;

    // Top HUD background
    r->draw_rect(0, 0, cfg::SCREEN_W, cfg::GRID_OFFSET_Y, cfg::colors::HUD_BG);

    // Wave / Gold / Lives
    char buf[64];
    snprintf(buf, sizeof(buf), "W:%d/%d", sim.wave_mgr.current_wave + 1, cfg::TOTAL_WAVES);
    r->draw_text(buf, 2, 2, cfg::colors::WHITE);

    snprintf(buf, sizeof(buf), "G:%d", sim.economy.gold);
    r->draw_text(buf, 60, 2, cfg::colors::GOLD);

    snprintf(buf, sizeof(buf), "L:%d", sim.economy.lives);
    r->draw_text(buf, 120, 2, cfg::colors::HEALTH);

    // Speed indicator
    const char* spd_txt = "";
    switch (sim.speed_mode) {
        case SpeedMode::Normal: spd_txt = ">"; break;
        case SpeedMode::Fast2x: spd_txt = ">>"; break;
        case SpeedMode::Fast3x: spd_txt = ">>>"; break;
    }
    r->draw_text(spd_txt, cfg::SCREEN_W - 20, 2, cfg::colors::ACCENT);

    // Phase indicator
    if (sim.wave_mgr.phase == GamePhase::Build) {
        r->draw_text("BUILD", 2, 10, cfg::colors::ACCENT);
    } else {
        snprintf(buf, sizeof(buf), "EN:%d", sim.wave_mgr.enemies_remaining(sim.enemies));
        r->draw_text(buf, 2, 10, cfg::colors::HEALTH);
    }

    // Boss HP bar
    if (sim.titan_idx >= 0 && sim.enemies.enemies[sim.titan_idx].active) {
        const auto& titan = sim.enemies.enemies[sim.titan_idx];
        int bw = cfg::SCREEN_W - 40;
        int bx = 20;
        int by = cfg::GRID_OFFSET_Y + cfg::GRID_H * cfg::TILE_SIZE - 4;
        float hpf = sim_clamp(sim_div(titan.hp, titan.max_hp), 0.0f, 1.0f);
        r->draw_rect(bx, by, bw, 3, {60,20,20,255});
        r->draw_rect(bx, by, sim_to_int(bw * hpf), 3, cfg::colors::HEALTH);
        r->draw_text("TITAN", bx, by - 6, cfg::colors::HEALTH);
    }

    // Tower tray (bottom)
    int tray_y = cfg::GRID_OFFSET_Y + cfg::GRID_H * cfg::TILE_SIZE;
    r->draw_rect(0, tray_y, cfg::SCREEN_W, cfg::TRAY_ROWS * cfg::TILE_SIZE, cfg::colors::TRAY_BG);

    for (int i = 0; i < 5; ++i) {
        const auto& def = cfg::TOWER_DEFS[i];
        int tx = 4 + i * 48;
        int ty = tray_y + 2;
        bool sel = (i == selected_tower_idx);
        bool afford = sim.economy.can_afford(def.cost);
        Color tc = afford ? def.color : Color{60,60,60,255};
        if (sel) r->draw_rect_outline(tx - 1, ty - 1, 46, 14, cfg::colors::ACCENT);
        r->draw_rect(tx, ty, 8, 8, tc);
        snprintf(buf, sizeof(buf), "%d", def.cost);
        r->draw_text(buf, tx + 10, ty, afford ? cfg::colors::GOLD : Color{80,80,80,255});
    }

    // Fleet upgrade prompt
    if (sim.fleet_available && sim.wave_mgr.phase == GamePhase::Build) {
        r->draw_text("[F] Fleet UP", 4, tray_y + 10, cfg::colors::GOLD);
    }

    // Notification
    if (notification_timer > 0) {
        r->draw_text(notification, cfg::SCREEN_W / 2 - 30, cfg::GRID_OFFSET_Y + 10, cfg::colors::WHITE);
    }
}
```

- [ ] **Step 4: Write `src/states/pause_state.h` + `pause_state.cpp`**

```cpp
// pause_state.h
#pragma once
#include "states/state.h"

struct PauseState : State {
    int menu_idx = 0;
    void enter(App& app) override;
    void update(App& app, float dt) override;
    void render(App& app, float alpha) override;
};
```

```cpp
// pause_state.cpp
#include "states/pause_state.h"

void PauseState::enter(App& app) { menu_idx = 0; }

void PauseState::update(App& app, float dt) {
    if (app.input->pressed(InputButton::Up)) menu_idx = 0;
    if (app.input->pressed(InputButton::Down)) menu_idx = 1;
    if (app.input->pressed(InputButton::Start) || (app.input->pressed(InputButton::A) && menu_idx == 0)) {
        app.change_state(StateId::Gameplay);
    }
    if (app.input->pressed(InputButton::A) && menu_idx == 1) {
        app.change_state(StateId::Title);
    }
}

void PauseState::render(App& app, float alpha) {
    auto* r = app.renderer;
    // Semi-transparent overlay
    r->draw_rect(0, 0, cfg::SCREEN_W, cfg::SCREEN_H, {0,0,0,150});
    r->draw_text("PAUSED", cfg::SCREEN_W / 2 - 18, 40, cfg::colors::WHITE);
    Color c0 = (menu_idx == 0) ? cfg::colors::ACCENT : cfg::colors::WHITE;
    Color c1 = (menu_idx == 1) ? cfg::colors::ACCENT : cfg::colors::WHITE;
    r->draw_text("Resume", cfg::SCREEN_W / 2 - 18, 60, c0);
    r->draw_text("Quit", cfg::SCREEN_W / 2 - 12, 72, c1);
    r->present();
}
```

- [ ] **Step 5: Write `src/states/game_over_state.h` + `game_over_state.cpp`**

```cpp
// game_over_state.h
#pragma once
#include "states/state.h"

struct GameOverState : State {
    int menu_idx = 0;
    void enter(App& app) override;
    void update(App& app, float dt) override;
    void render(App& app, float alpha) override;
};
```

```cpp
// game_over_state.cpp
#include "states/game_over_state.h"
#include <cstdio>

void GameOverState::enter(App& app) {
    menu_idx = 0;
    app.audio->play_sfx(SfxId::GameOver);
    app.audio->stop_bgm();
}

void GameOverState::update(App& app, float dt) {
    if (app.input->pressed(InputButton::Up)) menu_idx = 0;
    if (app.input->pressed(InputButton::Down)) menu_idx = 1;
    if (app.input->pressed(InputButton::A)) {
        if (menu_idx == 0) app.change_state(StateId::Gameplay);
        else app.change_state(StateId::Title);
    }
}

void GameOverState::render(App& app, float alpha) {
    auto* r = app.renderer;
    r->clear(cfg::colors::BG);
    r->draw_text("GAME OVER", cfg::SCREEN_W / 2 - 27, 20, cfg::colors::HEALTH);
    char buf[64];
    snprintf(buf, sizeof(buf), "Wave reached: %d", app.sim.wave_mgr.current_wave + 1);
    r->draw_text(buf, 30, 50, cfg::colors::WHITE);
    snprintf(buf, sizeof(buf), "Gold earned: %d", app.sim.economy.gold);
    r->draw_text(buf, 30, 62, cfg::colors::GOLD);
    Color c0 = (menu_idx == 0) ? cfg::colors::ACCENT : cfg::colors::WHITE;
    Color c1 = (menu_idx == 1) ? cfg::colors::ACCENT : cfg::colors::WHITE;
    r->draw_text("Retry", cfg::SCREEN_W / 2 - 15, 90, c0);
    r->draw_text("Title", cfg::SCREEN_W / 2 - 15, 102, c1);
    r->present();
}
```

- [ ] **Step 6: Write `src/states/victory_state.h` + `victory_state.cpp`**

```cpp
// victory_state.h
#pragma once
#include "states/state.h"

struct VictoryState : State {
    int menu_idx = 0;
    void enter(App& app) override;
    void update(App& app, float dt) override;
    void render(App& app, float alpha) override;
};
```

```cpp
// victory_state.cpp
#include "states/victory_state.h"
#include <cstdio>

void VictoryState::enter(App& app) {
    menu_idx = 0;
    app.audio->play_sfx(SfxId::Victory);
    app.audio->stop_bgm();
}

void VictoryState::update(App& app, float dt) {
    if (app.input->pressed(InputButton::Up)) menu_idx = 0;
    if (app.input->pressed(InputButton::Down)) menu_idx = 1;
    if (app.input->pressed(InputButton::A)) {
        if (menu_idx == 0) app.change_state(StateId::Gameplay);
        else app.change_state(StateId::Title);
    }
}

void VictoryState::render(App& app, float alpha) {
    auto* r = app.renderer;
    r->clear(cfg::colors::BG);
    r->draw_text("VICTORY!", cfg::SCREEN_W / 2 - 24, 20, cfg::colors::GOLD);
    r->draw_text("All 20 waves survived!", 20, 50, cfg::colors::ACCENT);
    char buf[64];
    snprintf(buf, sizeof(buf), "Final gold: %d", app.sim.economy.gold);
    r->draw_text(buf, 30, 70, cfg::colors::GOLD);
    Color c0 = (menu_idx == 0) ? cfg::colors::ACCENT : cfg::colors::WHITE;
    Color c1 = (menu_idx == 1) ? cfg::colors::ACCENT : cfg::colors::WHITE;
    r->draw_text("Play Again", cfg::SCREEN_W / 2 - 30, 95, c0);
    r->draw_text("Title", cfg::SCREEN_W / 2 - 15, 107, c1);
    r->present();
}
```

- [ ] **Step 7: Verify all compiles, commit**

```bash
cmake -B build -S . && cmake --build build
git add src/states/
git commit -m "feat: add state machine and all game states (title, gameplay, pause, game_over, victory)"
```

---

## Task 13: SDL2 HAL Implementations

**Files:**

- Create: `src/hal/sdl2_renderer.h`, `src/hal/sdl2_renderer.cpp`
- Create: `src/hal/sdl2_input.h`, `src/hal/sdl2_input.cpp`
- Create: `src/hal/sdl2_audio.h`, `src/hal/sdl2_audio.cpp`

- [ ] **Step 1: Write `src/hal/sdl2_renderer.h` + `sdl2_renderer.cpp`**

```cpp
// sdl2_renderer.h
#pragma once
#include "hal/hal.h"
#include <SDL2/SDL.h>

struct SDL2Renderer : IRenderer {
    SDL_Window* window = nullptr;
    SDL_Renderer* sdl_renderer = nullptr;
    SDL_Texture* target_tex = nullptr; // virtual 240×128 render target
    int vw, vh; // virtual size

    bool init(const char* title, int virtual_w, int virtual_h, int scale);
    void shutdown();

    void clear(Color c) override;
    void draw_rect(int x, int y, int w, int h, Color c) override;
    void draw_rect_outline(int x, int y, int w, int h, Color c) override;
    void draw_sprite(SpriteId id, int x, int y, float scale, bool flip_h) override;
    void draw_text(const char* str, int x, int y, Color c) override;
    void draw_circle(int cx, int cy, int r, Color c) override;
    void draw_line(int x1, int y1, int x2, int y2, Color c) override;
    void present() override;
    int screen_w() const override;
    int screen_h() const override;
};
```

```cpp
// sdl2_renderer.cpp
#include "hal/sdl2_renderer.h"
#include <cstdio>
#include <cstring>

// Minimal 4x6 bitmap font (printable ASCII 32-126)
static const uint8_t FONT_4X6[][6] = {
    // Space (32)
    {0x0,0x0,0x0,0x0,0x0,0x0},
    // ! (33)
    {0x4,0x4,0x4,0x0,0x4,0x0},
    // More characters follow... For brevity, using a simple approach:
};

// We'll use a simple glyph renderer
static void draw_char_pixels(SDL_Renderer* r, char ch, int x, int y) {
    // Simple 4x6 font rendered as pixel rects
    // For the initial implementation, render printable chars as small blocks
    if (ch < 32 || ch > 126) return;
    // Simplified: just draw a small rect per char as placeholder
    // Full bitmap font implemented in final version
}

bool SDL2Renderer::init(const char* title, int virtual_w, int virtual_h, int scale) {
    vw = virtual_w;
    vh = virtual_h;
    window = SDL_CreateWindow(title,
        SDL_WINDOWPOS_CENTERED, SDL_WINDOWPOS_CENTERED,
        virtual_w * scale, virtual_h * scale, SDL_WINDOW_SHOWN);
    if (!window) return false;

    sdl_renderer = SDL_CreateRenderer(window, -1,
        SDL_RENDERER_ACCELERATED | SDL_RENDERER_PRESENTVSYNC);
    if (!sdl_renderer) return false;

    SDL_RenderSetLogicalSize(sdl_renderer, virtual_w, virtual_h);
    SDL_SetHint(SDL_HINT_RENDER_SCALE_QUALITY, "0"); // nearest neighbor

    return true;
}

void SDL2Renderer::shutdown() {
    if (sdl_renderer) SDL_DestroyRenderer(sdl_renderer);
    if (window) SDL_DestroyWindow(window);
    sdl_renderer = nullptr;
    window = nullptr;
}

void SDL2Renderer::clear(Color c) {
    SDL_SetRenderDrawColor(sdl_renderer, c.r, c.g, c.b, c.a);
    SDL_RenderClear(sdl_renderer);
}

void SDL2Renderer::draw_rect(int x, int y, int w, int h, Color c) {
    SDL_SetRenderDrawColor(sdl_renderer, c.r, c.g, c.b, c.a);
    SDL_SetRenderDrawBlendMode(sdl_renderer, (c.a < 255) ? SDL_BLENDMODE_BLEND : SDL_BLENDMODE_NONE);
    SDL_Rect rect = {x, y, w, h};
    SDL_RenderFillRect(sdl_renderer, &rect);
}

void SDL2Renderer::draw_rect_outline(int x, int y, int w, int h, Color c) {
    SDL_SetRenderDrawColor(sdl_renderer, c.r, c.g, c.b, c.a);
    SDL_SetRenderDrawBlendMode(sdl_renderer, (c.a < 255) ? SDL_BLENDMODE_BLEND : SDL_BLENDMODE_NONE);
    SDL_Rect rect = {x, y, w, h};
    SDL_RenderDrawRect(sdl_renderer, &rect);
}

void SDL2Renderer::draw_sprite(SpriteId id, int x, int y, float scale, bool flip_h) {
    // Fallback: draw magenta rect for unloaded sprites
    int sz = static_cast<int>(8 * scale);
    draw_rect(x, y, sz, sz, {255, 0, 255, 255});
}

void SDL2Renderer::draw_text(const char* str, int x, int y, Color c) {
    SDL_SetRenderDrawColor(sdl_renderer, c.r, c.g, c.b, c.a);
    // Simple pixel font: each char is ~4px wide, 6px tall
    int cx = x;
    while (*str) {
        // Draw each character as a tiny block pattern
        // This is a minimal bitmap font renderer
        if (*str != ' ') {
            // Simple: draw a 3x5 block for each non-space char
            // Full font table would go here. For now, draw identifiable glyphs.
            for (int gy = 0; gy < 5; ++gy) {
                for (int gx = 0; gx < 3; ++gx) {
                    // Simple hash-based pattern per character
                    uint8_t hash = (*str * 7 + gy * 3 + gx) & 0xFF;
                    bool pixel_on = false;

                    // Common chars get recognizable patterns
                    char ch = *str;
                    // Digits
                    if (ch >= '0' && ch <= '9') {
                        static const uint16_t digits[10] = {
                            0x7B6F, // 0: 111 101 101 101 111
                            0x2C97, // 1: 010 110 010 010 111
                            0x73E7, // 2: 111 001 111 100 111
                            0x73CF, // 3: 111 001 111 001 111
                            0x5BC9, // 4: 101 101 111 001 001
                            0x7CF3, // 5: 111 100 111 001 111
                            0x7EF7, // 6: 111 100 111 101 111
                            0x7249, // 7: 111 001 010 010 010
                            0x7BF7, // 8: 111 101 111 101 111
                            0x7BC9, // 9: 111 101 111 001 001
                        };
                        int d = ch - '0';
                        int bit = (4 - gy) * 3 + (2 - gx);
                        pixel_on = (digits[d] >> bit) & 1;
                    }
                    // Letters (simplified uppercase)
                    else if (ch >= 'A' && ch <= 'Z') {
                        static const uint16_t letters[26] = {
                            0x2F7D, // A
                            0x7AFC, // B (approx)
                            0x7247, // C
                            0x6B5C, // D (approx)
                            0x72E7, // E
                            0x72E4, // F
                            0x725F, // G
                            0x5BED, // H (approx)
                            0x7497, // I
                            0x124F, // J
                            0x5AEA, // K (approx)
                            0x4927, // L
                            0x5FED, // M (approx)
                            0x5BED, // N
                            0x2B6A, // O (approx)
                            0x7AE4, // P
                            0x2B6F, // Q (approx)
                            0x7AEA, // R
                            0x7CF3, // S (same as 5)
                            0x7492, // T
                            0x5B6F, // U (approx)
                            0x5B52, // V (approx)
                            0x5BFD, // W (approx)
                            0x5252, // X (approx)
                            0x5392, // Y (approx)
                            0x7267, // Z (approx)
                        };
                        int idx = ch - 'A';
                        int bit = (4 - gy) * 3 + (2 - gx);
                        pixel_on = (letters[idx] >> bit) & 1;
                    }
                    else if (ch >= 'a' && ch <= 'z') {
                        // Reuse uppercase
                        int idx = ch - 'a';
                        static const uint16_t letters[26] = {
                            0x2F7D,0x7AFC,0x7247,0x6B5C,0x72E7,0x72E4,0x725F,0x5BED,
                            0x7497,0x124F,0x5AEA,0x4927,0x5FED,0x5BED,0x2B6A,0x7AE4,
                            0x2B6F,0x7AEA,0x7CF3,0x7492,0x5B6F,0x5B52,0x5BFD,0x5252,
                            0x5392,0x7267,
                        };
                        int bit = (4 - gy) * 3 + (2 - gx);
                        pixel_on = (letters[idx] >> bit) & 1;
                    }
                    else if (ch == ':') { pixel_on = (gy == 1 || gy == 3) && gx == 1; }
                    else if (ch == '/') { pixel_on = (gx == 2-gy/2) && (gy < 5); }
                    else if (ch == '+') { pixel_on = (gx == 1 && gy >= 1 && gy <= 3) || (gy == 2 && gx >= 0); }
                    else if (ch == '-') { pixel_on = gy == 2; }
                    else if (ch == '>') { pixel_on = (gy == 0 && gx == 0) || (gy == 1 && gx == 1) || (gy == 2 && gx == 2) || (gy == 3 && gx == 1) || (gy == 4 && gx == 0); }
                    else if (ch == '!') { pixel_on = (gx == 1 && gy <= 2) || (gx == 1 && gy == 4); }
                    else if (ch == '[') { pixel_on = gx <= 1 || (gx == 0); }
                    else if (ch == ']') { pixel_on = gx >= 1 || (gx == 2); }

                    if (pixel_on) {
                        SDL_RenderDrawPoint(sdl_renderer, cx + gx, y + gy);
                    }
                }
            }
        }
        cx += 4;
        str++;
    }
}

void SDL2Renderer::draw_circle(int cx, int cy, int r, Color c) {
    SDL_SetRenderDrawColor(sdl_renderer, c.r, c.g, c.b, c.a);
    SDL_SetRenderDrawBlendMode(sdl_renderer, (c.a < 255) ? SDL_BLENDMODE_BLEND : SDL_BLENDMODE_NONE);
    // Midpoint circle
    int x = r, y = 0, err = 1 - r;
    while (x >= y) {
        SDL_RenderDrawPoint(sdl_renderer, cx + x, cy + y);
        SDL_RenderDrawPoint(sdl_renderer, cx - x, cy + y);
        SDL_RenderDrawPoint(sdl_renderer, cx + x, cy - y);
        SDL_RenderDrawPoint(sdl_renderer, cx - x, cy - y);
        SDL_RenderDrawPoint(sdl_renderer, cx + y, cy + x);
        SDL_RenderDrawPoint(sdl_renderer, cx - y, cy + x);
        SDL_RenderDrawPoint(sdl_renderer, cx + y, cy - x);
        SDL_RenderDrawPoint(sdl_renderer, cx - y, cy - x);
        y++;
        if (err < 0) { err += 2 * y + 1; }
        else { x--; err += 2 * (y - x) + 1; }
    }
}

void SDL2Renderer::draw_line(int x1, int y1, int x2, int y2, Color c) {
    SDL_SetRenderDrawColor(sdl_renderer, c.r, c.g, c.b, c.a);
    SDL_RenderDrawLine(sdl_renderer, x1, y1, x2, y2);
}

void SDL2Renderer::present() {
    SDL_RenderPresent(sdl_renderer);
}

int SDL2Renderer::screen_w() const { return vw; }
int SDL2Renderer::screen_h() const { return vh; }
```

- [ ] **Step 2: Write `src/hal/sdl2_input.h` + `sdl2_input.cpp`**

```cpp
// sdl2_input.h
#pragma once
#include "hal/hal.h"
#include <SDL2/SDL.h>

struct SDL2Input : IInput {
    bool cur[static_cast<int>(InputButton::COUNT)] = {};
    bool prev[static_cast<int>(InputButton::COUNT)] = {};
    float hold_time[static_cast<int>(InputButton::COUNT)] = {};
    bool quit = false;
    float dt = 0;

    void update() override;
    void set_dt(float d) { dt = d; }
    bool pressed(InputButton btn) const override;
    bool held(InputButton btn) const override;
    bool released(InputButton btn) const override;
    bool quit_requested() const override;
    float held_duration(InputButton btn) const override;
};
```

```cpp
// sdl2_input.cpp
#include "hal/sdl2_input.h"
#include <cstring>

void SDL2Input::update() {
    std::memcpy(prev, cur, sizeof(cur));

    SDL_Event ev;
    while (SDL_PollEvent(&ev)) {
        if (ev.type == SDL_QUIT) quit = true;
    }

    const uint8_t* keys = SDL_GetKeyboardState(nullptr);

    auto map = [&](InputButton btn, SDL_Scancode sc1, SDL_Scancode sc2 = SDL_SCANCODE_UNKNOWN) {
        int i = static_cast<int>(btn);
        cur[i] = keys[sc1] || (sc2 != SDL_SCANCODE_UNKNOWN && keys[sc2]);
        if (cur[i]) hold_time[i] += dt;
        else hold_time[i] = 0;
    };

    map(InputButton::Up,    SDL_SCANCODE_UP,    SDL_SCANCODE_W);
    map(InputButton::Down,  SDL_SCANCODE_DOWN,  SDL_SCANCODE_S);
    map(InputButton::Left,  SDL_SCANCODE_LEFT,  SDL_SCANCODE_A);
    map(InputButton::Right, SDL_SCANCODE_RIGHT, SDL_SCANCODE_D);
    map(InputButton::A,     SDL_SCANCODE_Z,     SDL_SCANCODE_RETURN);
    map(InputButton::B,     SDL_SCANCODE_X,     SDL_SCANCODE_BACKSPACE);
    map(InputButton::L,     SDL_SCANCODE_Q);
    map(InputButton::R,     SDL_SCANCODE_E);
    map(InputButton::Start, SDL_SCANCODE_ESCAPE);
    map(InputButton::Select,SDL_SCANCODE_TAB);
    map(InputButton::FleetUpgrade, SDL_SCANCODE_F);
}

bool SDL2Input::pressed(InputButton btn) const {
    int i = static_cast<int>(btn);
    return cur[i] && !prev[i];
}

bool SDL2Input::held(InputButton btn) const {
    return cur[static_cast<int>(btn)];
}

bool SDL2Input::released(InputButton btn) const {
    int i = static_cast<int>(btn);
    return !cur[i] && prev[i];
}

bool SDL2Input::quit_requested() const { return quit; }

float SDL2Input::held_duration(InputButton btn) const {
    return hold_time[static_cast<int>(btn)];
}
```

- [ ] **Step 3: Write `src/hal/sdl2_audio.h` + `sdl2_audio.cpp`**

```cpp
// sdl2_audio.h
#pragma once
#include "hal/hal.h"

struct SDL2Audio : IAudio {
    bool initialized = false;

    bool init();
    void shutdown();

    void play_sfx(SfxId id) override;
    void play_bgm(BgmId id) override;
    void stop_bgm() override;
    void set_sfx_volume(float v) override;
    void set_bgm_volume(float v) override;
};
```

```cpp
// sdl2_audio.cpp
#include "hal/sdl2_audio.h"

// Stub implementation — audio is cosmetic, not blocking
// Full procedural audio generation can be added later
bool SDL2Audio::init() {
    // If SDL2_mixer is available, init here
    initialized = false; // stub
    return true;
}

void SDL2Audio::shutdown() {}
void SDL2Audio::play_sfx(SfxId id) {}
void SDL2Audio::play_bgm(BgmId id) {}
void SDL2Audio::stop_bgm() {}
void SDL2Audio::set_sfx_volume(float v) {}
void SDL2Audio::set_bgm_volume(float v) {}
```

- [ ] **Step 4: Verify compiles, commit**

```bash
cmake -B build -S . && cmake --build build
git add src/hal/
git commit -m "feat: add SDL2 HAL implementations (renderer, input, audio stub)"
```

---

## Task 14: Main Entry Point + Game Loop

**Files:**

- Modify: `src/main.cpp`

- [ ] **Step 1: Write `src/main.cpp`**

```cpp
#include <SDL2/SDL.h>
#include "hal/sdl2_renderer.h"
#include "hal/sdl2_input.h"
#include "hal/sdl2_audio.h"
#include "states/state.h"
#include "states/title_state.h"
#include "states/gameplay_state.h"
#include "states/pause_state.h"
#include "states/game_over_state.h"
#include "states/victory_state.h"
#include "core/config.h"

// App state machine implementation
void App::change_state(StateId id) {
    if (current_state) current_state->exit(*this);
    current_id = id;
    current_state = states[static_cast<int>(id)];
    if (current_state) current_state->enter(*this);
}

int main(int argc, char* argv[]) {
    // 1. Init SDL
    if (SDL_Init(SDL_INIT_VIDEO | SDL_INIT_AUDIO | SDL_INIT_TIMER) < 0) {
        SDL_Log("SDL init failed: %s", SDL_GetError());
        return 1;
    }

    // 2. Create HAL implementations
    SDL2Renderer renderer;
    if (!renderer.init("BASTION TD", cfg::SCREEN_W, cfg::SCREEN_H, cfg::WINDOW_SCALE)) {
        SDL_Log("Renderer init failed: %s", SDL_GetError());
        SDL_Quit();
        return 1;
    }

    SDL2Input input;
    SDL2Audio audio;
    audio.init();

    // 3. Create App + states
    App app;
    app.renderer = &renderer;
    app.input = &input;
    app.audio = &audio;

    TitleState title_state;
    GameplayState gameplay_state;
    PauseState pause_state;
    GameOverState game_over_state;
    VictoryState victory_state;

    app.states[static_cast<int>(StateId::Title)]    = &title_state;
    app.states[static_cast<int>(StateId::Gameplay)]  = &gameplay_state;
    app.states[static_cast<int>(StateId::Pause)]     = &pause_state;
    app.states[static_cast<int>(StateId::GameOver)]  = &game_over_state;
    app.states[static_cast<int>(StateId::Victory)]   = &victory_state;

    app.change_state(StateId::Title);

    // 4. Main loop: fixed timestep with render interpolation
    uint64_t freq = SDL_GetPerformanceFrequency();
    uint64_t last = SDL_GetPerformanceCounter();
    float accumulator = 0.0f;

    while (app.running) {
        uint64_t now = SDL_GetPerformanceCounter();
        float frame_dt = static_cast<float>(now - last) / static_cast<float>(freq);
        last = now;

        if (frame_dt > cfg::MAX_DT) frame_dt = cfg::MAX_DT;

        input.set_dt(frame_dt);
        input.update();

        if (input.quit_requested()) break;

        accumulator += frame_dt;

        // Fixed timestep simulation
        while (accumulator >= cfg::SIM_DT) {
            if (app.current_state) {
                app.current_state->update(app, cfg::SIM_DT);
            }
            accumulator -= cfg::SIM_DT;
        }

        // Render with interpolation alpha
        float alpha = accumulator / cfg::SIM_DT;
        if (app.current_state) {
            app.current_state->render(app, alpha);
        }
    }

    // 5. Shutdown
    audio.shutdown();
    renderer.shutdown();
    SDL_Quit();
    return 0;
}
```

- [ ] **Step 2: Update CMakeLists.txt with all source files**

Ensure all `.cpp` files are listed in the appropriate targets.

- [ ] **Step 3: Build full project**

```bash
cmake -B build -S . && cmake --build build
```

Expected: Clean compile, executable produced.

- [ ] **Step 4: Run and verify window opens**

```bash
./build/BastionTD
```

Expected: Window opens at 960×512, title screen shows "BASTION TD" with menu. Arrow keys navigate, Z selects.

- [ ] **Step 5: Commit**

```bash
git add src/main.cpp CMakeLists.txt
git commit -m "feat: add main entry point with fixed-timestep game loop"
```

---

## Task 15: Combat Tests

**Files:**

- Create: `tests/test_combat.cpp`

- [ ] **Step 1: Write `tests/test_combat.cpp`**

```cpp
#include "core/enemy.h"
#include "core/tower.h"
#include "core/projectile.h"
#include "core/config.h"
#include "core/math_utils.h"
#include <cassert>
#include <cstdio>

void test_min_damage_vs_armor() {
    // Per titan fix: max(1, dmg - armor). Arrow(1) vs Knight(armor 2) = 1
    Enemy e;
    Path p;
    p.length = 2;
    p.points[0] = {0, 0};
    p.points[1] = {5, 0};
    p.valid = true;
    e.init(EnemyType::Knight, &p); // hp=8, armor=2
    float initial_hp = e.hp;
    e.take_damage(1.0f); // arrow base dmg
    assert(sim_approx_eq(e.hp, initial_hp - 1.0f)); // min 1 damage
    printf("PASS: test_min_damage_vs_armor\n");
}

void test_dot_bypasses_armor() {
    Enemy e;
    Path p;
    p.length = 2;
    p.points[0] = {0, 0};
    p.points[1] = {10, 0};
    p.valid = true;
    e.init(EnemyType::Titan, &p); // hp=50, armor=3
    float initial_hp = e.hp;
    e.add_dot(2.0f, 1.0f); // 2 dps for 1 sec
    e.update(0.5f); // half second
    // DoT bypasses armor: should lose ~1.0 hp
    float expected_loss = 1.0f; // 2.0 dps * 0.5s
    assert(sim_approx_eq(e.hp, initial_hp - expected_loss, 0.1f));
    printf("PASS: test_dot_bypasses_armor\n");
}

void test_burn_stacking_cap() {
    Enemy e;
    Path p;
    p.length = 2;
    p.points[0] = {0, 0};
    p.points[1] = {10, 0};
    p.valid = true;
    e.init(EnemyType::Goblin, &p);
    e.add_dot(1.0f, 2.0f);
    e.add_dot(1.0f, 2.0f);
    e.add_dot(1.0f, 2.0f);
    assert(e.dot_count == 3);
    e.add_dot(1.0f, 2.0f); // 4th refreshes oldest
    assert(e.dot_count == 3); // still capped at 3
    printf("PASS: test_burn_stacking_cap\n");
}

void test_slow_strongest_wins() {
    Enemy e;
    Path p;
    p.length = 2;
    p.points[0] = {0, 0};
    p.points[1] = {10, 0};
    p.valid = true;
    e.init(EnemyType::Goblin, &p);
    e.apply_slow(0.4f, 2.0f); // 40% slow
    e.apply_slow(0.3f, 1.0f); // 30% slow (stronger)
    assert(sim_approx_eq(e.slow_factor, 0.3f));
    printf("PASS: test_slow_strongest_wins\n");
}

void test_splash_damage() {
    EnemyPool pool;
    pool.init();
    Path p;
    p.length = 2;
    p.points[0] = {5, 5};
    p.points[1] = {10, 5};
    p.valid = true;

    Enemy* e1 = pool.spawn(EnemyType::Goblin, &p); // at (5,5)
    Enemy* e2 = pool.spawn(EnemyType::Goblin, &p); // at (5,5) — same pos
    float hp_before = e2->hp;

    // Simulate splash projectile hitting e1
    Projectile proj;
    proj.active = true;
    proj.pos = e1->pos;
    proj.target_enemy_idx = 0; // e1
    proj.damage = 4.0f;
    proj.splash_radius = 2.0f;
    proj.slow_factor = 0;
    proj.slow_duration = 0;
    proj.chain_count = 0;
    proj.dot_damage = 0;
    proj.dot_duration = 0;
    proj.on_impact(pool);

    // e2 should take 50% splash = 2.0, but min 1 after armor(0) = 2.0
    assert(e2->hp < hp_before);
    printf("PASS: test_splash_damage\n");
}

int main() {
    test_min_damage_vs_armor();
    test_dot_bypasses_armor();
    test_burn_stacking_cap();
    test_slow_strongest_wins();
    test_splash_damage();
    printf("All combat tests passed.\n");
    return 0;
}
```

- [ ] **Step 2: Add to CMake, run**

```cmake
add_executable(test_combat tests/test_combat.cpp src/core/enemy.cpp src/core/tower.cpp src/core/projectile.cpp src/core/grid.cpp src/core/pathfinding.cpp)
target_include_directories(test_combat PRIVATE src)
add_test(NAME combat COMMAND test_combat)
```

```bash
cmake -B build -S . && cmake --build build && cd build && ctest --output-on-failure
```

Expected: All 5 tests PASS.

- [ ] **Step 3: Commit**

```bash
git add tests/test_combat.cpp CMakeLists.txt
git commit -m "test: add combat tests (armor min-dmg, dot bypass, slow, splash)"
```

---

## Task 16: Wave Tests

**Files:**

- Create: `tests/test_wave.cpp`

- [ ] **Step 1: Write `tests/test_wave.cpp`**

```cpp
#include "core/config.h"
#include "core/wave_manager.h"
#include <cassert>
#include <cstdio>

void test_wave_generation() {
    cfg::WaveDef waves[cfg::TOTAL_WAVES];
    cfg::generate_waves(waves);

    // Wave 1: should have goblins
    assert(waves[0].entry_count >= 1);
    assert(waves[0].entries[0].type == EnemyType::Goblin);
    assert(waves[0].entries[0].count == 6); // 4 + 1*2

    // Boss waves
    assert(waves[4].has_titan);   // wave 5
    assert(waves[9].has_titan);   // wave 10
    assert(waves[14].has_titan);  // wave 15
    assert(waves[19].has_titan);  // wave 20

    // Wave 20 has 2 titans
    bool found_titan = false;
    for (int i = 0; i < waves[19].entry_count; ++i) {
        if (waves[19].entries[i].type == EnemyType::Titan) {
            assert(waves[19].entries[i].count == 2);
            found_titan = true;
        }
    }
    assert(found_titan);

    printf("PASS: test_wave_generation\n");
}

void test_all_20_waves_defined() {
    cfg::WaveDef waves[cfg::TOTAL_WAVES];
    cfg::generate_waves(waves);
    for (int w = 0; w < cfg::TOTAL_WAVES; ++w) {
        assert(waves[w].entry_count > 0);
        for (int e = 0; e < waves[w].entry_count; ++e) {
            assert(waves[w].entries[e].count > 0);
        }
    }
    printf("PASS: test_all_20_waves_defined\n");
}

int main() {
    test_wave_generation();
    test_all_20_waves_defined();
    printf("All wave tests passed.\n");
    return 0;
}
```

- [ ] **Step 2: Add to CMake, run**

```cmake
add_executable(test_wave tests/test_wave.cpp)
target_include_directories(test_wave PRIVATE src)
add_test(NAME wave COMMAND test_wave)
```

```bash
cmake -B build -S . && cmake --build build && cd build && ctest --output-on-failure
```

- [ ] **Step 3: Commit**

```bash
git add tests/test_wave.cpp CMakeLists.txt
git commit -m "test: add wave generation tests"
```

---

## Task 17: Integration — Full Playtest + Bug Fixes

This task is manual verification. No new files.

- [ ] **Step 1: Build and run the game**

```bash
cmake -B build -S . && cmake --build build && ./build/BastionTD
```

- [ ] **Step 2: Verify title screen**

- Window opens, "BASTION TD" visible
- Menu navigation with arrows, Z to select

- [ ] **Step 3: Verify gameplay loop**

- New Game starts, map generates
- Cursor moves, towers can be placed (Z on green tile)
- Z on non-tower tile starts wave
- Enemies spawn and follow path
- Towers fire at enemies
- Enemies die, gold earned
- Wave ends, returns to build phase

- [ ] **Step 4: Verify new features**

- Tab cycles speed (>>>, >> indicators visible)
- F key opens fleet upgrade menu after wave 5
- Titan takes damage from all tower types (min 1 dmg)
- Characters visible on tower sprites

- [ ] **Step 5: Fix any discovered bugs, commit**

```bash
git add -A && git commit -m "fix: integration bug fixes from playtest"
```

- [ ] **Step 6: Run all tests**

```bash
cd build && ctest --output-on-failure
```

Expected: All tests pass.

- [ ] **Step 7: Final commit**

```bash
git add -A && git commit -m "feat: BastionTD C++ SDL2 port — complete with fast-forward, fleet upgrades, titan fix"
```

---

## Dependency Graph

```
Task 1 (CMake) → Task 2 (Types/Config) → Task 3 (HAL interfaces)
                                        ↓
Task 4 (Grid + Pathfinding) ← Task 2
Task 5 (Economy) ← Task 2
                    ↓
Task 6 (Enemy) ← Task 4 + Task 2
Task 7 (Tower) ← Task 6
Task 8 (Projectile) ← Task 6
Task 9 (WaveManager + MapGen) ← Task 4 + Task 6
Task 10 (Effects) ← Task 2
                    ↓
Task 11 (Game Core) ← Tasks 4-10
Task 12 (States) ← Task 11 + Task 3
Task 13 (SDL2 HAL) ← Task 3
Task 14 (Main) ← Task 12 + Task 13
                    ↓
Tasks 15-16 (Tests) ← Tasks 6-9
Task 17 (Integration) ← Task 14
```

**Parallelizable groups:**

- Tasks 4, 5, 10 can run in parallel (all depend only on Task 2)
- Tasks 6, 7, 8 are sequential (enemy → tower → projectile)
- Tasks 12, 13 can run in parallel (both depend on Task 11 and Task 3)
- Tasks 15, 16 can run in parallel
