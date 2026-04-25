# BASTION TD — Complete Implementation Spec

## You are building a complete, playable tower defense game in Python/Pygame called BASTION TD.

**Read this entire document before writing any code.** Every section is load-bearing. Do not deviate from these specs. Do not leave TODOs. Do not stub systems. Do not ask for clarification. Make reasonable assumptions and keep building until the game is fully playable end-to-end.

---

## TECH CONSTRAINTS (NON-NEGOTIABLE)

- **Python 3.12 + Pygame** — no other dependencies
- **Resolution:** 768×480 (24×15 tiles at 32px). Top 2 rows = HUD, bottom 1 row = tower tray, middle 12 rows = playable grid (24×12)
- **All game logic in tile coordinates** (integers or floats referencing tile positions), not pixels
- **Fixed 60 FPS game loop** with delta-time accumulator, matching GBA's ~59.7Hz VBlank
- **Input abstracted to GBA buttons:** D-pad, A, B, L, R, Start, Select mapped to keyboard
- **State machine architecture:** each screen is a State with `enter()`, `exit()`, `update(dt)`, `render(screen)`
- **No external asset files** — all graphics drawn with Pygame primitives, all audio generated procedurally with wave math at startup
- **GBA portability discipline:** tile/grid logic, FSMs, deterministic updates, no physics engines, no floating-point-heavy rendering, data-driven definitions, clean module boundaries

---

## CORE GAME LOOP

```
1. MAP GENERATES    → random terrain with guaranteed path(s) from spawn(s) to base
2. BUILD PHASE      → player moves cursor, places/upgrades towers with gold
3. PLAYER STARTS WAVE → press A on "Start Wave" or a hotkey
4. WAVE PHASE       → enemies spawn, follow path, towers auto-fire, gold earned from kills
5. WAVE ENDS        → enemies that reached base cost lives. Return to step 2
6. GAME OVER        → lives ≤ 0
7. VICTORY          → survived wave 20 + final boss
```

Build and wave phases alternate. Player cannot place towers during a wave (GBA-style simplicity). Each new round (after victory or game over + "New Game") generates a fresh map.

---

## PROJECT STRUCTURE

```
BastionTD/
├── main.py               Entry point, Game class, game loop, state registration
├── settings.py            All constants, colors, input map, tower/enemy/wave data
├── input_handler.py       GBA-button abstraction (held/pressed/released per frame)
├── grid.py                Tile grid: terrain types, buildable queries, path storage
├── map_generator.py       Random terrain placement + BFS path computation
├── pathfinding.py         BFS on tile grid, returns ordered list of tile coords
├── tower.py               Tower class: targeting, cooldown, firing, upgrade logic
├── projectile.py          Projectile/effect entities flying from tower to enemy
├── enemy.py               Enemy class: path-following, HP, armour, speed, death
├── wave_manager.py        Wave definitions, spawn queue, timing, phase control
├── economy.py             Gold, lives, cost validation, wave-clear bonus
├── hud.py                 Top bar, tower tray, cursor, notifications, boss HP
├── effects.py             Particles, damage numbers, screen shake
├── audio_manager.py       Procedural WAV generation for all SFX + BGM loops
├── save_manager.py        JSON high-score persistence
├── states/
│   ├── state_machine.py   State base class + StateMachine (register/change/update/render)
│   ├── title.py           Title screen with New Game / Instructions / Quit
│   ├── instructions.py    Controls + how-to-play screen
│   ├── gameplay.py        Core state: build phase ↔ wave phase, integrates all systems
│   ├── pause.py           Pause overlay with Resume / Quit to Title
│   ├── game_over.py       Stats display, Retry / Title options
│   └── victory.py         Completion screen after wave 20
```

---

## SETTINGS & CONSTANTS (`settings.py`)

```python
import pygame

GAME_TITLE = "BASTION TD"
TILE_SIZE = 32
GRID_W, GRID_H = 24, 12          # playable grid (below HUD, above tray)
HUD_H = 2                         # tile rows for top HUD
TRAY_H = 1                        # tile rows for bottom tower tray
SCREEN_W = TILE_SIZE * GRID_W     # 768
SCREEN_H = TILE_SIZE * (HUD_H + GRID_H + TRAY_H)  # 480
GRID_OFFSET_Y = HUD_H * TILE_SIZE # pixel Y where playable grid starts (64)

TARGET_FPS = 60
FIXED_DT = 1.0 / TARGET_FPS
MAX_DT = 0.1

START_GOLD = 200
START_LIVES = 20
WAVE_CLEAR_BONUS = 25             # extra gold for completing a wave with 0 leaks
TOTAL_WAVES = 20
BOSS_WAVES = [5, 10, 15, 20]      # waves that include a Titan

# Terrain tile types (for grid)
TERRAIN_EMPTY = 0     # buildable
TERRAIN_PATH = 1      # enemy walks here, not buildable
TERRAIN_ROCK = 2      # impassable, not buildable
TERRAIN_WATER = 3     # impassable, not buildable
TERRAIN_TREE = 4      # impassable, not buildable
TERRAIN_SPAWN = 5     # enemy entry point
TERRAIN_BASE = 6      # player base (defend this)
TERRAIN_TOWER = 7     # occupied by a placed tower

# Colors
COLOR_BG = (20, 28, 20)
COLOR_GRASS = (45, 90, 45)
COLOR_PATH = (140, 120, 80)
COLOR_ROCK = (100, 100, 110)
COLOR_WATER = (40, 70, 150)
COLOR_TREE = (30, 70, 35)
COLOR_BASE = (60, 60, 180)
COLOR_SPAWN = (180, 60, 60)
COLOR_CURSOR_OK = (80, 255, 80, 100)
COLOR_CURSOR_BAD = (255, 80, 80, 100)
COLOR_HUD_BG = (10, 10, 18)
COLOR_TRAY_BG = (15, 15, 25)
COLOR_WHITE = (240, 235, 220)
COLOR_GOLD = (255, 210, 80)
COLOR_ACCENT = (80, 200, 120)
COLOR_HEALTH = (220, 50, 50)

INPUT_MAP = {
    "up":     [pygame.K_UP, pygame.K_w],
    "down":   [pygame.K_DOWN, pygame.K_s],
    "left":   [pygame.K_LEFT, pygame.K_a],
    "right":  [pygame.K_RIGHT, pygame.K_d],
    "a":      [pygame.K_z, pygame.K_RETURN],      # place tower / confirm / start wave
    "b":      [pygame.K_x, pygame.K_BACKSPACE],    # cancel / sell / upgrade menu
    "l":      [pygame.K_q],                         # cycle tower selection left
    "r":      [pygame.K_e],                         # cycle tower selection right
    "start":  [pygame.K_ESCAPE],                    # pause
    "select": [pygame.K_TAB],                       # fast-forward toggle
}
```

---

## TOWER DEFINITIONS (data dict in `settings.py`)

```python
TOWER_DEFS = {
    "arrow":     {"name":"Arrow Tower",    "cost":50,  "range":3.5, "damage":1,   "cooldown":0.6,
                  "color":(160,130,60),  "special":"none",
                  "upgrades":[{"cost":30, "damage":2,"range":4.0},{"cost":50,"damage":3,"range":4.5}]},
    "cannon":    {"name":"Cannon Tower",   "cost":100, "range":2.5, "damage":3,   "cooldown":1.5,
                  "color":(120,80,60),   "special":"splash", "splash_radius":1.2,
                  "upgrades":[{"cost":60, "damage":5,"range":3.0},{"cost":90,"damage":8,"range":3.5}]},
    "ice":       {"name":"Ice Tower",      "cost":75,  "range":3.0, "damage":0.5, "cooldown":0.8,
                  "color":(100,180,220), "special":"slow", "slow_factor":0.4, "slow_duration":2.0,
                  "upgrades":[{"cost":45,"damage":1,"slow_factor":0.3},{"cost":70,"damage":1.5,"slow_factor":0.2}]},
    "lightning": {"name":"Lightning Tower","cost":150, "range":4.0, "damage":2,   "cooldown":1.0,
                  "color":(200,200,60),  "special":"chain", "chain_count":2, "chain_range":1.5,
                  "upgrades":[{"cost":90,"damage":3,"chain_count":3},{"cost":130,"damage":4,"chain_count":4}]},
    "flame":     {"name":"Flame Tower",    "cost":125, "range":2.0, "damage":1,   "cooldown":0.2,
                  "color":(220,100,40),  "special":"dot", "dot_damage":0.5, "dot_duration":2.0,
                  "upgrades":[{"cost":75,"damage":1.5,"dot_damage":1.0},{"cost":110,"damage":2,"dot_duration":3.0}]},
}
# Tower selection order for L/R cycling:
TOWER_ORDER = ["arrow", "cannon", "ice", "lightning", "flame"]
```

### Tower behaviour rules:
- Towers occupy exactly 1 tile. Placement sets that tile to `TERRAIN_TOWER`
- Towers auto-acquire the **nearest enemy within range** each cooldown cycle
- On fire: spawn a `Projectile` that travels toward the target enemy at 12 tiles/sec
- When projectile reaches target (distance < 0.3 tiles), apply damage + special effect
- **Splash:** deal `damage * 0.5` to all enemies within `splash_radius` of impact
- **Slow:** multiply enemy speed by `slow_factor` for `slow_duration` seconds (does not stack, refreshes)
- **Chain:** after hitting primary target, find `chain_count` additional enemies within `chain_range` of the last-hit enemy, deal `damage * 0.7` to each in sequence
- **DoT:** apply `dot_damage` per second for `dot_duration` to the hit enemy (stacks up to 3x)
- Upgrade: press B on a placed tower to see upgrade option. Press A to buy. Max 2 upgrades (3 levels total). Each upgrade applies the stat changes from `upgrades[level-1]` additively
- Sell: hold B for 1 second on a tower to sell for 50% of total invested gold. Tile reverts to `TERRAIN_EMPTY`

---

## ENEMY DEFINITIONS (data dict in `settings.py`)

```python
ENEMY_DEFS = {
    "goblin":   {"name":"Goblin",  "hp":3,  "speed":2.0, "armour":0, "gold":5,  "color":(60,160,60),  "size":0.5},
    "wolf":     {"name":"Wolf",    "hp":2,  "speed":3.5, "armour":0, "gold":8,  "color":(140,120,100),"size":0.5},
    "knight":   {"name":"Knight",  "hp":8,  "speed":1.2, "armour":2, "gold":15, "color":(180,180,200),"size":0.7},
    "healer":   {"name":"Healer",  "hp":4,  "speed":2.0, "armour":0, "gold":12, "color":(60,200,60),  "size":0.5,
                 "special":"heal", "heal_rate":1.0, "heal_range":2.0},
    "swarm":    {"name":"Swarm",   "hp":1,  "speed":3.0, "armour":0, "gold":2,  "color":(180,180,50), "size":0.35},
    "titan":    {"name":"Titan",   "hp":50, "speed":0.8, "armour":3, "gold":100,"color":(160,80,80),  "size":1.0,
                 "lives_cost":5},
}
```

### Enemy behaviour rules:
- Enemies follow the **pre-computed BFS path** tile by tile. They do NOT pathfind in real-time
- Movement: each frame, move toward next path tile at `speed * dt` tiles/sec. When within 0.1 of next waypoint, advance to following waypoint
- **Armour** reduces every incoming damage instance by `armour` (minimum 0 damage after reduction). DoT ticks are also reduced
- **Healer special:** every 1.0s, heal all allies within `heal_range` tiles for `heal_rate` HP (not self)
- **Titan** costs 5 lives if it reaches base instead of 1. Show a boss HP bar in the HUD when a Titan is alive
- When HP ≤ 0: enemy enters death state (0.3s fade), awards `gold` to player economy, may drop particle effects
- **Slow effect:** if slowed, `effective_speed = speed * slow_factor`. Timer counts down; when expired, speed returns to normal
- **DoT effect:** tracked as `dot_stacks` list of `{dps, remaining_time}`. Each frame, sum all active DoT dps and subtract from HP (after armour)

---

## WAVE DEFINITIONS (data in `settings.py`)

```python
def generate_waves():
    """Return list of 20 wave defs. Each wave = list of (enemy_type, count, spawn_delay)."""
    waves = []
    for w in range(1, TOTAL_WAVES + 1):
        composition = []
        if w <= 3:
            composition.append(("goblin", 4 + w * 2, 0.8))
        elif w <= 6:
            composition.append(("goblin", 6 + w, 0.7))
            composition.append(("wolf", w - 2, 0.6))
        elif w <= 10:
            composition.append(("wolf", 4 + w - 6, 0.6))
            composition.append(("knight", (w - 6), 1.2))
            if w >= 9:
                composition.append(("healer", 1, 1.5))
        elif w <= 15:
            composition.append(("knight", w - 8, 1.0))
            composition.append(("healer", (w - 9) // 2 + 1, 1.3))
            composition.append(("swarm", w * 2, 0.3))
        else:
            composition.append(("knight", w - 10, 0.9))
            composition.append(("wolf", w - 12, 0.5))
            composition.append(("healer", 2, 1.2))
            composition.append(("swarm", w * 3, 0.25))
        if w in BOSS_WAVES:
            composition.append(("titan", 1, 0.0))
        waves.append(composition)
    return waves
```

- `spawn_delay` = seconds between each enemy of that group spawning
- Groups spawn sequentially: all goblins finish spawning, then wolves begin, etc
- Titan always spawns last in its wave

---

## PROCEDURAL MAP GENERATION (`map_generator.py`)

### Algorithm (executed once per new game):

```
1. Create 24×12 grid, all tiles = TERRAIN_EMPTY
2. Place BASE at a random position on the right edge (column 23, random row 2-9)
3. Place 1-2 SPAWN points on the left edge (column 0, random rows at least 3 apart)
4. Scatter obstacles:
   a. Choose 25-35% of remaining tiles randomly
   b. Assign each: 50% ROCK, 30% TREE, 20% WATER
   c. After EACH obstacle placed, run BFS from every SPAWN to BASE
   d. If any SPAWN has no path → remove that obstacle and try a different tile
5. Run final BFS from each SPAWN to BASE. Store path as ordered list of (tx, ty)
6. Mark all tiles on any path as TERRAIN_PATH
7. Return: grid[][], paths{spawn_pos: [(tx,ty),...]}, spawn_positions[], base_position
```

### Critical rules:
- **Every map MUST have a valid path.** The generate function must loop/retry until this is true. Never return an unsolvable map
- Obstacles should feel natural: cluster rocks together sometimes, put trees in small groups, water in 2-3 tile patches
- The path(s) should be visible to the player as a distinct trail color
- Player can only build towers on `TERRAIN_EMPTY` tiles (not on path, obstacles, spawn, or base)
- After a tower is placed, the tile becomes `TERRAIN_TOWER` (still passable for path validation isn't needed post-gen since enemies follow pre-computed paths, but it prevents double-placement)

---

## PATHFINDING (`pathfinding.py`)

Implement **BFS** (not A* — BFS is simpler, sufficient for small grids, and trivially portable to GBA).

```python
def bfs(grid, start, end, grid_w, grid_h):
    """
    grid: 2D list of terrain types. Passable = TERRAIN_EMPTY, TERRAIN_PATH, TERRAIN_SPAWN, TERRAIN_BASE.
    start: (tx, ty) spawn position.
    end: (tx, ty) base position.
    Returns: list of (tx, ty) from start to end inclusive, or None if no path.
    4-directional movement only (no diagonals).
    """
```

- Used during map generation to validate solvability
- Used once after generation to compute the enemy walking path
- Result is stored; enemies just follow the list index by index

---

## GRID (`grid.py`)

```python
class Grid:
    def __init__(self, width, height):
        self.w = width      # 24
        self.h = height     # 12
        self.tiles = [[TERRAIN_EMPTY]*width for _ in range(height)]
        self.paths = {}     # {(spawn_x, spawn_y): [(tx,ty), ...]}
        self.spawns = []    # [(tx,ty), ...]
        self.base = (0, 0)  # (tx,ty)

    def get(self, tx, ty) -> int           # return terrain type
    def set(self, tx, ty, terrain_type)    # set terrain
    def is_buildable(self, tx, ty) -> bool # True only if TERRAIN_EMPTY
    def is_passable(self, tx, ty) -> bool  # True if EMPTY, PATH, SPAWN, or BASE
    def in_bounds(self, tx, ty) -> bool
```

---

## TOWER (`tower.py`)

```python
class Tower:
    def __init__(self, tower_type: str, tile_x: int, tile_y: int):
        # Load stats from TOWER_DEFS[tower_type]
        self.type = tower_type
        self.x, self.y = tile_x, tile_y
        self.level = 1          # 1-3
        self.cooldown_timer = 0
        self.total_invested = cost  # tracks gold for sell price
        self.target = None      # current enemy reference

    def update(self, dt, enemies) -> Projectile | None:
        # 1. Decrement cooldown
        # 2. Find nearest enemy within range (Euclidean dist in tile coords)
        # 3. If target found and cooldown ready: reset cooldown, return new Projectile
        # 4. Return None if not firing

    def upgrade(self) -> int:  # returns cost, or -1 if max level
    def sell_value(self) -> int:  # 50% of total_invested
    def render(self, screen, cam_x, cam_y):
        # Draw as a filled square with tower color, centered dot for barrel
        # Level indicators: 1 dot = lv1, 2 dots = lv2, 3 dots = lv3
        # Range circle drawn only when cursor is on this tower
```

---

## PROJECTILE (`projectile.py`)

```python
class Projectile:
    def __init__(self, start_x, start_y, target_enemy, tower_type, damage, special_data):
        self.x, self.y = start_x, start_y  # tile coords (float)
        self.target = target_enemy          # Enemy reference
        self.speed = 12.0                   # tiles per second
        self.damage = damage
        self.tower_type = tower_type
        self.special = special_data         # dict with splash_radius, slow_factor, etc.
        self.alive = True

    def update(self, dt, all_enemies):
        # Move toward target. If target died, continue to last known position
        # On arrival (dist < 0.3): apply damage, apply special, set alive=False
        # Splash: damage nearby enemies
        # Slow: apply slow to target
        # Chain: find chain targets, damage each
        # DoT: add dot stack to target

    def render(self, screen, cam_x, cam_y):
        # Small colored circle (3-4px) matching tower color, flying toward target
```

---

## ENEMY (`enemy.py`)

```python
class Enemy:
    def __init__(self, enemy_type: str, path: list[tuple[int,int]], spawn_index: int):
        # Load stats from ENEMY_DEFS[enemy_type]
        self.path = path
        self.path_idx = 0
        self.x, self.y = float(path[0][0]), float(path[0][1])
        self.slow_timer = 0.0
        self.slow_factor = 1.0
        self.dot_stacks = []    # [{dps, remaining}]
        self.alive = True
        self.reached_base = False
        self.death_timer = 0.3

    def update(self, dt, all_enemies):
        # 1. Apply DoT: for each stack, reduce HP by dps*dt (after armour), decrement timer, remove expired
        # 2. Apply slow: if slow_timer > 0, use slow_factor; else speed = base speed
        # 3. Move toward path[path_idx] at effective_speed * dt
        # 4. If within 0.1 of waypoint, advance path_idx
        # 5. If path_idx >= len(path): reached_base = True, alive = False
        # 6. Healer special: every 1s, heal nearby allies

    def take_damage(self, amount):
        # Reduce by armour, clamp to 0 minimum. If HP <= 0, die

    def apply_slow(self, factor, duration):
        # Set slow_factor = min(current, factor), reset slow_timer

    def add_dot(self, dps, duration):
        # Append to dot_stacks, cap at 3 stacks

    def render(self, screen, cam_x, cam_y):
        # Filled circle sized by self.size * TILE_SIZE
        # HP bar above if damaged
        # Blue tint overlay if slowed
        # Orange flicker if burning (has dot stacks)
```

---

## WAVE MANAGER (`wave_manager.py`)

```python
class WaveManager:
    def __init__(self):
        self.waves = generate_waves()   # from settings.py
        self.current_wave = 0           # 0-indexed
        self.phase = "build"            # "build" or "wave"
        self.spawn_queue = []           # [(enemy_type, path_key, delay_timer)]
        self.active_enemies = []        # [Enemy]
        self.spawn_timer = 0.0

    def start_wave(self):
        # Set phase="wave", populate spawn_queue from waves[current_wave]

    def update(self, dt, grid) -> list of events:
        # During wave phase:
        # 1. Decrement spawn timers, spawn enemies when ready (create Enemy with grid path)
        # 2. Update all active enemies
        # 3. Remove dead enemies (return gold events), remove base-reachers (return life-loss events)
        # 4. If spawn_queue empty AND active_enemies empty: wave complete, advance, phase="build"

    def is_wave_active(self) -> bool
    def enemies_remaining(self) -> int  # queue + active
```

---

## ECONOMY (`economy.py`)

```python
class Economy:
    def __init__(self):
        self.gold = START_GOLD
        self.lives = START_LIVES

    def can_afford(self, cost) -> bool
    def spend(self, cost)           # subtract gold
    def earn(self, amount)          # add gold
    def lose_lives(self, amount)    # subtract lives
    def is_game_over(self) -> bool  # lives <= 0
    def wave_clear_bonus(self)      # add WAVE_CLEAR_BONUS gold
```

---

## HUD (`hud.py`)

### Layout (pixel Y regions):
- **Row 0-63 (top 2 tile rows):** HUD bar — wave counter, gold, lives, phase indicator, fast-forward icon
- **Row 64-447 (middle 12 tile rows):** Game grid with cursor overlay
- **Row 448-479 (bottom 1 tile row):** Tower tray — 5 tower icons with costs, selected one highlighted

### Cursor:
- Grid-snapped rectangle that moves with D-pad (tile by tile)
- Green semi-transparent fill if tile is buildable, red if not
- When cursor is on an existing tower, show range circle and upgrade/sell prompt

### HUD elements:
```
 Wave: 3/20    Gold: 350g    Lives: 18 ♥    [BUILD PHASE]
```
- During wave phase, show enemy count remaining instead of phase label
- Boss HP bar: centered at bottom of grid area (above tray), only when Titan alive

### Tower tray:
```
 [Arrow 50g] [Cannon 100g] [Ice 75g] [Lightning 150g] [Flame 125g]
```
- Selected tower has bright border + name shown
- Greyed out if player can't afford it
- L/R buttons cycle selection, shown by highlight moving left/right

### Notifications:
- Center-screen text that fades after 2s: "Wave 3 incoming!", "Wave complete! +25g bonus", etc.

---

## EFFECTS (`effects.py`)

Reuse particle + screen shake pattern from Mythical:
- `ParticleSystem`: emit on enemy death (burst in enemy color), tower shot impact, wave clear celebration
- `ScreenShake`: trigger on Titan spawn, Titan death, base hit
- `DamageNumberSystem`: float-up numbers on enemy damage

---

## AUDIO (`audio_manager.py`)

Generate all sounds procedurally at init using sine/square/noise wave math (same technique as Mythical). No external files.

### Required sounds:
| Key | Description | Approach |
|-----|-------------|----------|
| `place` | Tower placed | Short rising tone (300→500Hz, 0.08s) |
| `shoot` | Tower fires | Quick noise burst (0.05s) |
| `hit` | Enemy takes damage | Noise + low tone (0.06s) |
| `enemy_death` | Enemy dies | Descending tone + noise (0.1s) |
| `wave_start` | Wave begins | Two ascending tones (0.15s) |
| `wave_clear` | Wave completed | Ascending arpeggio (0.3s) |
| `boss_spawn` | Titan appears | Low rumble + rising (0.4s) |
| `base_hit` | Enemy reaches base | Harsh descending (0.15s) |
| `upgrade` | Tower upgraded | Rising ding (0.1s) |
| `sell` | Tower sold | Coin jingle (0.1s) |
| `menu_move` | Cursor/menu move | Tiny click (0.03s) |
| `menu_select` | Confirm selection | Click + rise (0.08s) |
| `game_over` | Defeat | Descending minor (0.4s) |
| `victory` | Win | Major fanfare (0.5s) |
| `bgm_build` | Build phase BGM loop | Gentle major melody, square wave (2-3s loop) |
| `bgm_wave` | Wave phase BGM loop | Tense minor melody, faster tempo (2-3s loop) |
| `bgm_boss` | Boss BGM loop | Aggressive, fast (2s loop) |
| `bgm_title` | Title screen BGM | Calm, inviting (3s loop) |

---

## SAVE (`save_manager.py`)

JSON file storing only high scores (not mid-game state — TD rounds are short):
```python
{"best_wave": 15, "best_score": 4200, "games_played": 7}
```
- Score = total gold earned across all waves
- Save on game over and victory. Load on title screen to show "Best: Wave X"

---

## STATES

### `states/title.py`
- Animated background (subtle grid pattern or scrolling terrain tiles)
- "BASTION TD" title in large text with glow effect
- Menu: New Game / Instructions / Quit
- Show "Best: Wave X" from save file if exists
- BGM: `bgm_title` loop

### `states/instructions.py`
- Controls table (GBA button → keyboard → action)
- Brief gameplay explanation: build towers, survive waves, don't let enemies reach your base
- Tower type summary (name, cost, special in one line each)
- "Press Z to return"

### `states/gameplay.py` — THE CORE STATE
This is the largest and most critical file. It integrates:

```python
class GameplayState(State):
    def __init__(self, game):
        self.grid = Grid(GRID_W, GRID_H)
        self.economy = Economy()
        self.wave_mgr = WaveManager()
        self.towers = []            # [Tower]
        self.projectiles = []       # [Projectile]
        self.particles = ParticleSystem()
        self.dmg_numbers = DamageNumberSystem()
        self.shake = ScreenShake()
        self.hud = HUD()
        self.cursor_x, self.cursor_y = GRID_W // 2, GRID_H // 2
        self.selected_tower_idx = 0  # index into TOWER_ORDER
        self.fast_forward = False
        self._generate_map()

    def _generate_map(self):
        # Call map_generator, store result in self.grid

    def update(self, dt):
        if self.fast_forward: dt *= 3  # triple speed
        # BUILD PHASE:
        #   - D-pad moves cursor (clamped to grid)
        #   - L/R cycles tower selection
        #   - A on empty buildable tile: place tower if affordable
        #   - A on "Start Wave" prompt (or specific key): begin next wave
        #   - B on existing tower: show upgrade/sell options
        # WAVE PHASE:
        #   - wave_mgr.update(dt) handles spawning + enemy movement
        #   - Tower.update(dt) handles targeting + firing → produces Projectiles
        #   - Projectile.update(dt) handles movement + impact → damages enemies
        #   - Check for enemy deaths → gold, particles
        #   - Check for base reaches → life loss, shake, sound
        #   - Check wave complete → bonus, phase change
        #   - Check game over → state change
        #   - Check victory (wave 20 complete) → state change

    def render(self, screen):
        # 1. Fill HUD background (top 64px)
        # 2. Render grid tiles (grass base, then terrain overlays)
        # 3. Render path highlight
        # 4. Render towers
        # 5. Render enemies
        # 6. Render projectiles
        # 7. Render cursor overlay
        # 8. Render particles + damage numbers
        # 9. Render HUD text + tower tray
        # 10. Apply screen shake offset to grid rendering (not HUD)
```

### `states/pause.py`
- Semi-transparent overlay
- Resume / Quit to Title
- ESC or B to resume

### `states/game_over.py`
- "GAME OVER" + stats (wave reached, gold earned, towers built)
- Retry (regenerate map, restart) / Title
- Save high score

### `states/victory.py`
- "VICTORY" celebration + stats
- Particle burst effect
- Return to Title
- Save high score

---

## VISUAL RENDERING GUIDE

All graphics are Pygame primitives. No images, no sprites, no external files.

### Grid tiles (32×32 each):
| Terrain | Rendering |
|---------|-----------|
| EMPTY (grass) | Fill `COLOR_GRASS`, 2-3 random darker dots for texture variation (seeded by tile position for consistency) |
| PATH | Fill `COLOR_PATH`, subtle lighter center line along path direction |
| ROCK | Fill `COLOR_ROCK`, irregular darker patches |
| WATER | Fill `COLOR_WATER`, small lighter sine-wave highlight that shifts with time |
| TREE | Fill `COLOR_GRASS` base, small dark green filled circle (canopy) + thin brown rect (trunk) |
| SPAWN | Fill `COLOR_SPAWN`, pulsing alpha border, "S" label |
| BASE | Fill `COLOR_BASE`, pulsing glow, shield/star icon drawn with lines, "B" label |
| TOWER | Covered by Tower.render() on top of grass base |

### Towers:
- Filled square (28×28, centered in 32×32 tile) in tower color
- Small darker circle in center (barrel/emitter)
- Level pips: 1/2/3 small white dots below the tower
- Range circle: thin semi-transparent circle, shown only when cursor hovers

### Enemies:
- Filled circle, radius = `size * TILE_SIZE * 0.4`
- Color from ENEMY_DEFS
- Titan: larger, pulsing outline
- HP bar: thin bar above sprite, red/green proportional
- Blue tint when slowed (draw semi-transparent blue circle on top)
- Orange flicker when burning

### Projectiles:
- Small filled circle (3px radius) in tower color
- Travels in straight line from tower to target position

### NO outlines/strokes on any game entity. Fills only. No `width` parameter > 0 on shape draws for entities (outlines on UI panels are fine).

---

## CONTROLS REFERENCE

| GBA | Keyboard | Build Phase Action | Wave Phase Action |
|-----|----------|--------------------|-------------------|
| D-pad | WASD/Arrows | Move cursor on grid | Move cursor (no effect on gameplay) |
| A | Z/Enter | Place tower / Start wave | — |
| B | X/Backspace | Upgrade/Sell tower | — |
| L | Q | Select previous tower type | — |
| R | E | Select next tower type | — |
| Start | ESC | Pause menu | Pause menu |
| Select | TAB | Toggle fast-forward | Toggle fast-forward |

---

## COMPLETION CHECKLIST

The game is NOT done until ALL of these are true:

- [ ] Title screen with menu, high score display, BGM
- [ ] Instructions screen with controls + gameplay summary
- [ ] Map generates randomly with guaranteed paths every time
- [ ] Path is visually distinct and enemies follow it exactly
- [ ] All 5 tower types placeable with correct costs
- [ ] All 5 tower specials work (splash, slow, chain, DoT, basic)
- [ ] Tower upgrades work (3 levels, stat increases, visual pips)
- [ ] Tower selling works (B hold, 50% refund)
- [ ] All 6 enemy types spawn with correct stats
- [ ] Enemies follow path, take damage, die, award gold
- [ ] Armour reduces damage correctly
- [ ] Healer enemy heals nearby allies
- [ ] Titan has boss HP bar, costs 5 lives
- [ ] 20 waves with escalating difficulty
- [ ] Build phase / wave phase alternation works cleanly
- [ ] Gold economy: earn from kills, spend on towers, wave bonus
- [ ] Lives: decrease on base reach, game over at 0
- [ ] HUD shows all info: wave, gold, lives, phase, tower tray
- [ ] Cursor shows green/red placement validity + range preview
- [ ] Fast-forward (3x speed) toggle works
- [ ] Particles on enemy death, base hit, wave clear
- [ ] Screen shake on Titan spawn/death, base hit
- [ ] Damage numbers float up on hits
- [ ] All SFX play at correct moments
- [ ] BGM loops per phase (build, wave, boss, title)
- [ ] Pause menu works
- [ ] Game over screen with stats + retry
- [ ] Victory screen after wave 20
- [ ] High score saves to JSON
- [ ] No crashes, no stalls, no soft-locks
- [ ] Game feels fun to play for 10+ minutes

---

## EXECUTION PRIORITY

1. Get a playable loop: grid + cursor + place towers + enemies walk + towers shoot + enemies die
2. Add economy + waves + phase switching
3. Add all tower specials + enemy types
4. Add boss waves + Titan
5. Add UI/HUD polish + tower tray
6. Add audio + effects
7. Add title/instructions/pause/gameover/victory states
8. Add save + fast-forward + final polish
9. Playtest and tune wave difficulty

**Do not skip ahead. Each layer must work before the next begins.**

---

*Spec version: 1.0 — April 2026*
*Target: C:\Users\alvi9\MyWork\BastionTD\*
