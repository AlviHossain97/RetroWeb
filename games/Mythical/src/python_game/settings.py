"""
Central settings — all constants in one place.
For GBA port: TILE_SIZE becomes 8 or 16, resolution becomes 240x160.
"""

# Display
GAME_TITLE = "MYTHICAL"
TILE_SIZE = 32
TILES_X = 24
TILES_Y = 16
SCREEN_WIDTH = TILE_SIZE * TILES_X
SCREEN_HEIGHT = TILE_SIZE * TILES_Y

# Timing
TARGET_FPS = 60
FIXED_DT = 1.0 / TARGET_FPS
MAX_DT = 0.1

# Player
PLAYER_SPEED = 4.0
PLAYER_MAX_HP = 6
PLAYER_IFRAMES = 1.0
PLAYER_ATTACK_RANGE = 1.2
PLAYER_ATTACK_DAMAGE = 1
PLAYER_ATTACK_WINDUP = 0.08
PLAYER_ATTACK_ACTIVE = 0.12
PLAYER_ATTACK_RECOVERY = 0.15
PLAYER_KNOCKBACK = 6.0

# Enemies
ENEMY_CHASE_RANGE = 6.0
ENEMY_ATTACK_RANGE = 1.0
ENEMY_KNOCKBACK = 4.0

# Colors
COLOR_BG = (12, 10, 18)
COLOR_WHITE = (240, 235, 220)
COLOR_ACCENT = (80, 200, 120)
COLOR_UI_BG = (8, 8, 16)
COLOR_UI_BORDER = (90, 85, 100)
COLOR_HEALTH = (200, 50, 50)
COLOR_HEALTH_BG = (60, 20, 20)
COLOR_BOSS_HP = (220, 60, 40)
COLOR_GOLD = (255, 210, 80)
COLOR_MANA = (60, 120, 220)

# ── Progression / XP ──────────────────────────────────────────────────
PLAYER_MAX_LEVEL = 20
XP_BASE = 10           # XP needed for level 2
XP_SCALE = 1.4         # multiplicative scaling per level
SKILL_POINTS_PER_LEVEL = 2

# ── Inventory grid ───────────────────────────────────────────────────
INV_COLS = 6
INV_ROWS = 4
HOTBAR_SIZE = 8        # first INV_COLS slots of row 0 + 2 overflow
INV_SLOT_SIZE = 38     # pixels per slot in the grid UI
INV_SLOT_PAD = 3

# ── Combat modifiers ─────────────────────────────────────────────────
FLANK_ANGLE_THRESHOLD = 120    # degrees — attack from behind this arc = flank
FLANK_DAMAGE_BONUS = 0.5       # +50 % damage on flank
ENV_KILL_XP_BONUS = 15         # flat XP bonus for environmental kills
ENV_KILL_COIN_BONUS = 5        # coin bonus for environmental kills

# ── Dash mechanic (unlocked via Shadow Cloak) ────────────────────────
DASH_SPEED = 14.0
DASH_DURATION = 0.18
DASH_COOLDOWN = 1.2

# ── Weather system ───────────────────────────────────────────────────
WEATHER_RAIN_SPEED_MULT = 1.0          # no slow in rain (just reduced vis)
WEATHER_SNOW_SPEED_MULT = 0.78         # snow slows movement
WEATHER_STORM_VISIBILITY_RADIUS = 6.0  # tiles visible in storm

# ── Lighting ─────────────────────────────────────────────────────────
AMBIENT_VILLAGE_LIGHT = 220    # 0-255, global ambient in village
AMBIENT_DUNGEON_LIGHT = 80     # much darker in dungeon
TORCH_LIGHT_RADIUS = 5         # tiles
PLAYER_LIGHT_RADIUS = 3        # default player ambient

# ── Mini-map ─────────────────────────────────────────────────────────
MINIMAP_W = 80
MINIMAP_H = 60
MINIMAP_SCALE = 2          # pixels per tile

# ── Reputation ───────────────────────────────────────────────────────
REP_MAX = 100
REP_MIN = -100
REP_NEUTRAL = 0

# ── Audio states ─────────────────────────────────────────────────────
AUDIO_STATE_EXPLORE = "explore"
AUDIO_STATE_COMBAT  = "combat"
AUDIO_STATE_BOSS    = "boss"
AUDIO_STATE_TITLE   = "title"

# Logical input registry.
# Runtime-specific adapters translate platform events into these button names.
INPUT_MAP = (
    "up",
    "down",
    "left",
    "right",
    "a",
    "b",
    "start",
    "select",
    "l",
    "r",
    "dash",
    "sort",
    "skill",
    "craft",
    "travel",
    "hotbar1",
    "hotbar2",
    "hotbar3",
    "hotbar4",
    "hotbar5",
    "hotbar6",
    "hotbar7",
    "hotbar8",
    "debug_paths",
    "debug_heatmap",
    "debug_labels",
    "debug_targets",
    "debug_info",
)
