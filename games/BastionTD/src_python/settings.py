"""
settings.py - All constants, colors, input map, tower/enemy/wave data for Bastion TD.
"""
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
    "up":      [pygame.K_UP, pygame.K_w],
    "down":    [pygame.K_DOWN, pygame.K_s],
    "left":    [pygame.K_LEFT, pygame.K_a],
    "right":   [pygame.K_RIGHT, pygame.K_d],
    "a":       [pygame.K_z, pygame.K_RETURN],      # place tower / confirm / start wave
    "b":       [pygame.K_x],                         # cancel / sell / upgrade menu
    "l":       [pygame.K_q],                         # cycle tower selection left
    "r":       [pygame.K_e],                         # cycle tower selection right
    "start":   [pygame.K_ESCAPE, pygame.K_BACKSPACE], # pause
    "select":  [pygame.K_LSHIFT, pygame.K_RSHIFT],  # speed toggle
    "tower_1": [pygame.K_1, pygame.K_KP1],           # select Arrow Tower
    "tower_2": [pygame.K_2, pygame.K_KP2],           # select Cannon Tower
    "tower_3": [pygame.K_3, pygame.K_KP3],           # select Ice Tower
    "tower_4": [pygame.K_4, pygame.K_KP4],           # select Lightning Tower
    "tower_5": [pygame.K_5, pygame.K_KP5],           # select Flame Tower
}

TOWER_DEFS = {
    "arrow": {
        "name": "Arrow Tower",
        "cost": 50,
        "range": 3.5,
        "damage": 1,
        "cooldown": 0.6,
        "color": (160, 130, 60),
        "special": "none",
        "upgrades": [
            {"cost": 30, "damage": 2, "range": 4.0},
            {"cost": 50, "damage": 3, "range": 4.5},
        ],
    },
    "cannon": {
        "name": "Cannon Tower",
        "cost": 100,
        "range": 2.5,
        "damage": 3,
        "cooldown": 1.5,
        "color": (120, 80, 60),
        "special": "splash",
        "splash_radius": 1.2,
        "upgrades": [
            {"cost": 60, "damage": 5, "range": 3.0},
            {"cost": 90, "damage": 8, "range": 3.5},
        ],
    },
    "ice": {
        "name": "Ice Tower",
        "cost": 75,
        "range": 3.0,
        "damage": 0.5,
        "cooldown": 0.8,
        "color": (100, 180, 220),
        "special": "slow",
        "slow_factor": 0.4,
        "slow_duration": 2.0,
        "upgrades": [
            {"cost": 45, "damage": 1, "slow_factor": 0.3},
            {"cost": 70, "damage": 1.5, "slow_factor": 0.2},
        ],
    },
    "lightning": {
        "name": "Lightning Tower",
        "cost": 150,
        "range": 4.0,
        "damage": 2,
        "cooldown": 1.0,
        "color": (200, 200, 60),
        "special": "chain",
        "chain_count": 2,
        "chain_range": 1.5,
        "upgrades": [
            {"cost": 90, "damage": 3, "chain_count": 3},
            {"cost": 130, "damage": 4, "chain_count": 4},
        ],
    },
    "flame": {
        "name": "Flame Tower",
        "cost": 125,
        "range": 2.0,
        "damage": 1,
        "cooldown": 0.2,
        "color": (220, 100, 40),
        "special": "dot",
        "dot_damage": 0.5,
        "dot_duration": 2.0,
        "upgrades": [
            {"cost": 75, "damage": 1.5, "dot_damage": 1.0},
            {"cost": 110, "damage": 2, "dot_duration": 3.0},
        ],
    },
}

# Tower selection order for L/R cycling
TOWER_ORDER = ["arrow", "cannon", "ice", "lightning", "flame"]

ENEMY_DEFS = {
    "goblin": {
        "name": "Goblin",
        "hp": 3,
        "speed": 2.0,
        "armour": 0,
        "gold": 5,
        "color": (60, 160, 60),
        "size": 0.5,
    },
    "wolf": {
        "name": "Wolf",
        "hp": 2,
        "speed": 3.5,
        "armour": 0,
        "gold": 8,
        "color": (140, 120, 100),
        "size": 0.5,
    },
    "knight": {
        "name": "Knight",
        "hp": 8,
        "speed": 1.2,
        "armour": 2,
        "gold": 15,
        "color": (180, 180, 200),
        "size": 0.7,
    },
    "healer": {
        "name": "Healer",
        "hp": 4,
        "speed": 2.0,
        "armour": 0,
        "gold": 12,
        "color": (60, 200, 60),
        "size": 0.5,
        "special": "heal",
        "heal_rate": 1.0,
        "heal_range": 2.0,
    },
    "swarm": {
        "name": "Swarm",
        "hp": 1,
        "speed": 3.0,
        "armour": 0,
        "gold": 2,
        "color": (180, 180, 50),
        "size": 0.35,
    },
    "titan": {
        "name": "Titan",
        "hp": 50,
        "speed": 0.8,
        "armour": 3,
        "gold": 100,
        "color": (160, 80, 80),
        "size": 1.0,
        "lives_cost": 5,
    },
}


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
