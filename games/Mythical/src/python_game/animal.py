"""
animal.py — Animal entities with contextual FSM AI.

Animal types and their base behaviours:
  deer   — passive herd animal; flees immediately when player is nearby.
  rabbit — very skittish; flees at long range, very fast.
  wolf   — territorial; neutral until within aggro range or attacked.
  boar   — charging attacker; charges in a straight line when aggro'd.
  bear   — large and aggressive; high HP, slow but powerful.
  fish   — passive water animal; cannot leave water, no attacks.

Difficulty ties:
  Easy   — high density, fully passive until struck.
  Normal — moderate density, wolves/boars will aggro at normal range.
  Hard   — low density, animals are skittish (+30% flee range).

Animals drop raw_meat on death. Hides also drop at a configurable chance.
State is persistent across map reloads via saved kill records.
"""
from __future__ import annotations

import math
import random
from typing import Optional

import pygame
from runtime.asset_manager import get_frame, load_sprite_sheet

from game_math import oscillate, point_distance, polar_offset, safe_normalize
from settings import TILE_SIZE, ENEMY_KNOCKBACK


# ─────────────────────────────────────────────────────────────────────────────
# ANIMAL DEFINITIONS  (loaded at runtime; see also data/animal_configs.json)
# ─────────────────────────────────────────────────────────────────────────────
ANIMAL_DEFS: dict[str, dict] = {
    "deer": {
        "name": "Deer",
        "max_hp": 4,
        "speed": 4.2,
        "flee_range": 5.0,
        "aggro_range": 0.0,
        "attack_damage": 0,
        "size": 0.85,
        "color": (170, 120, 60),
        "accent": (220, 180, 100),
        "drops": [
            {"item_id": "raw_meat",    "qty": 1, "chance": 1.0},   # guaranteed 1
            {"item_id": "raw_meat",    "qty": 1, "chance": 0.3},   # 30% bonus → max 2
            {"item_id": "animal_hide", "qty": 1, "chance": 0.6},
        ],
        "xp": 3,
        "behavior": "flee",
        "zones": ["village_forest", "dungeon_path"],
    },
    "rabbit": {
        "name": "Rabbit",
        "max_hp": 1,
        "speed": 5.5,
        "flee_range": 7.0,
        "aggro_range": 0.0,
        "attack_damage": 0,
        "size": 0.4,
        "color": (200, 190, 170),
        "accent": (230, 220, 200),
        "drops": [
            {"item_id": "raw_meat",    "qty": 1, "chance": 1.0},   # guaranteed 1
            {"item_id": "raw_meat",    "qty": 1, "chance": 0.3},   # 30% bonus → max 2
        ],
        "xp": 1,
        "behavior": "flee",
        "zones": ["village_forest", "village_plains"],
    },
    "wolf": {
        "name": "Wolf",
        "max_hp": 6,
        "speed": 3.6,
        "flee_range": 0.0,
        "aggro_range": 4.0,
        "attack_damage": 1,
        "attack_cd": 1.8,
        "size": 0.8,
        "color": (80, 80, 90),
        "accent": (120, 120, 130),
        "drops": [
            {"item_id": "raw_meat",    "qty": 1, "chance": 1.0},   # guaranteed 1
            {"item_id": "raw_meat",    "qty": 1, "chance": 0.3},   # 30% bonus → max 2
            {"item_id": "animal_hide", "qty": 1, "chance": 0.7},
        ],
        "xp": 8,
        "behavior": "territorial",
        "zones": ["village_forest", "dungeon_path"],
    },
    "boar": {
        "name": "Boar",
        "max_hp": 8,
        "speed": 2.8,
        "charge_speed": 6.5,
        "flee_range": 0.0,
        "aggro_range": 3.5,
        "attack_damage": 2,
        "attack_cd": 2.5,
        "size": 0.9,
        "color": (110, 75, 50),
        "accent": (150, 110, 80),
        "drops": [
            {"item_id": "raw_meat",    "qty": 1, "chance": 1.0},   # guaranteed 1
            {"item_id": "raw_meat",    "qty": 1, "chance": 0.3},   # 30% bonus → max 2
            {"item_id": "animal_hide", "qty": 1, "chance": 0.6},
        ],
        "xp": 10,
        "behavior": "aggressive",
        "zones": ["village_forest"],
    },
    "bear": {
        "name": "Bear",
        "max_hp": 14,
        "speed": 2.2,
        "flee_range": 0.0,
        "aggro_range": 3.0,
        "attack_damage": 3,
        "attack_cd": 2.2,
        "size": 1.1,
        "color": (90, 60, 40),
        "accent": (130, 100, 70),
        "drops": [
            {"item_id": "raw_meat",    "qty": 1, "chance": 1.0},   # guaranteed 1
            {"item_id": "raw_meat",    "qty": 1, "chance": 0.3},   # 30% bonus → max 2
            {"item_id": "animal_hide", "qty": 1, "chance": 0.8},
        ],
        "xp": 18,
        "behavior": "aggressive",
        "zones": ["dungeon_path"],
    },
    "fish": {
        "name": "Fish",
        "max_hp": 1,
        "speed": 2.0,
        "flee_range": 3.0,
        "aggro_range": 0.0,
        "attack_damage": 0,
        "size": 0.35,
        "color": (60, 150, 200),
        "accent": (100, 200, 230),
        "drops": [
            {"item_id": "raw_meat",    "qty": 1, "chance": 1.0},   # guaranteed 1
            {"item_id": "raw_meat",    "qty": 1, "chance": 0.3},   # 30% bonus → max 2
        ],
        "xp": 1,
        "behavior": "flee",
        "zones": ["village_water"],
    },
}


from runtime.gba_compat import GBAEntity
from runtime.fixed_point import FixedVec2

class Animal(GBAEntity):
    """
    A living world animal with a lightweight FSM.

    States:
      idle_wander — roaming freely on random timer
      flee        — running away from threat
      aggro       — chasing the player (predators only)
      charge      — boar charge (straight-line rush)
      attack      — melee swing animation
      hurt        — brief stagger
      death       — fade-out then remove

    Persistence: animals are saved by spawn_id in the defeated_animals set
    so that killed animals don't respawn on map reload.
    """

    def __init__(
        self,
        atype: str,
        tile_x: float,
        tile_y: float,
        spawn_id: str,
        difficulty_mode: str = "normal",
    ):
        super().__init__(tile_x, tile_y)
        adef = ANIMAL_DEFS.get(atype, ANIMAL_DEFS["deer"])
        self.atype = atype
        self.spawn_id = spawn_id
        self.spawn_x = self.x
        self.spawn_y = self.y

        # Difficulty scaling for flee/aggro ranges
        scale = {"easy": 0.7, "normal": 1.0, "hard": 1.3}.get(difficulty_mode, 1.0)
        aggro_scale = {"easy": 0.0, "normal": 1.0, "hard": 1.2}.get(difficulty_mode, 1.0)

        self.max_hp = adef["max_hp"]
        self.hp = self.max_hp
        self.speed = adef["speed"]
        self.flee_range = adef["flee_range"] * scale
        self.aggro_range = adef["aggro_range"] * aggro_scale
        self.attack_damage = adef.get("attack_damage", 0)
        self.attack_cd = adef.get("attack_cd", 2.0)
        self.charge_speed = adef.get("charge_speed", self.speed * 2.0)
        self.size = adef["size"]
        self.color = tuple(adef["color"])
        self.accent = tuple(adef["accent"])
        self.drops = adef.get("drops", [])
        self.xp = adef.get("xp", 1)
        self.behavior = adef.get("behavior", "flee")

        # On easy difficulty, all animals are passive until hit
        self._force_passive = difficulty_mode == "easy"

        # FSM state
        self.state = "idle_wander"
        self.state_timer = 0.0
        self.alive = True
        self.facing = "down"

        # Wander
        self._wander_timer = random.uniform(1.5, 4.0)
        self._wander_vx = 0.0
        self._wander_vy = 0.0

        # Combat
        self.attack_timer = 0.0
        self.hurt_timer = 0.0
        self.death_timer = 0.6
        self._attacked_once = False   # easy: trigger aggro after first hit

        # Charge state
        self._charge_dir_x = 0.0
        self._charge_dir_y = 0.0
        self._charge_dur = 0.0

        # Knockback
        self.knockback_vx = 0.0
        self.knockback_vy = 0.0

        # Flee panic (Minecraft-style: short burst after being hit)
        self._flee_panic_timer = 0.0   # time left in panic flee
        self._flee_panic_dur = 1.8     # how long panic lasts

        # Animation
        self.anim_timer = 0.0
        self.loot_spawned = False

    # ── Canonical identity contract (parity with Enemy) ───────────────

    @property
    def x(self) -> float:
        return self.pos.xf

    @x.setter
    def x(self, val: float):
        self.pos = FixedVec2(val, self.pos.yf)

    @property
    def y(self) -> float:
        return self.pos.yf

    @y.setter
    def y(self, val: float):
        self.pos = FixedVec2(self.pos.xf, val)

    @property
    def enemy_type(self) -> str:
        """Canonical runtime identity for bestiary/XP/drops."""
        return self.atype

    @property
    def xp_reward(self) -> int:
        """XP granted on kill."""
        return self.xp

    # ─────────────────────────────────────────────────────────────────

    @property
    def is_dead(self):
        return self.state == "death"

    @property
    def should_remove(self):
        return self.state == "death" and self.death_timer <= 0

    def dist_to(self, tx, ty):
        return point_distance(self.x, self.y, tx, ty)

    def face_toward(self, tx, ty):
        dx, dy = tx - self.x, ty - self.y
        if abs(dx) > abs(dy):
            self.facing = "right" if dx > 0 else "left"
        else:
            self.facing = "down" if dy > 0 else "up"

    # ─────────────────────────────────────────────────────────────────

    def take_damage(self, dmg: int, kx: float = 0, ky: float = 0) -> bool:
        if self.state == "death":
            return False
        self.hp -= dmg
        self.knockback_vx = kx * ENEMY_KNOCKBACK
        self.knockback_vy = ky * ENEMY_KNOCKBACK
        self._attacked_once = True
        if self.hp <= 0:
            self.hp = 0
            self.state = "death"
            self.death_timer = 0.6
            self.alive = False
        else:
            self.state = "hurt"
            self.hurt_timer = 0.22
        return True

    # ─────────────────────────────────────────────────────────────────

    def update(self, dt: float, player_x: float, player_y: float, tilemap) -> bool:
        """
        Update FSM. Returns True if the animal executed an attack this frame
        (caller should apply damage to player).
        """
        self.anim_timer += dt
        self.state_timer += dt
        deal_damage = False

        # Knockback
        if abs(self.knockback_vx) > 0.1 or abs(self.knockback_vy) > 0.1:
            nx = self.x + self.knockback_vx * dt
            ny = self.y + self.knockback_vy * dt
            if tilemap.is_passable(nx, self.y):
                self.x = nx
            if tilemap.is_passable(self.x, ny):
                self.y = ny
            self.knockback_vx *= 0.82
            self.knockback_vy *= 0.82

        dist = self.dist_to(player_x, player_y)

        # ── Death ───────────────────────────────────────────────────
        if self.state == "death":
            self.death_timer -= dt
            return False

        # ── Hurt ────────────────────────────────────────────────────
        if self.state == "hurt":
            self.hurt_timer -= dt
            if self.hurt_timer <= 0:
                # After being hit: brief panic flee (Minecraft-style)
                if self.behavior in ("flee", "passive"):
                    self.state = "flee"
                    self._flee_panic_timer = self._flee_panic_dur
                else:
                    self.state = "aggro"
                    self._flee_panic_timer = 0.0
            return False

        # ── Attack cooldown ─────────────────────────────────────────
        self.attack_timer = max(0.0, self.attack_timer - dt)

        # ── Determine transitions ──────────────────────────────────────────
        # Passive / flee animals: do NOT auto-flee from player proximity.
        # They only flee after being attacked (handled in hurt → flee transition).

        # Territorial / aggressive animals: check aggro range
        if self.behavior in ("territorial", "aggressive"):
            active_aggro = not self._force_passive or self._attacked_once
            if active_aggro and self.aggro_range > 0 and dist <= self.aggro_range and self.state == "idle_wander":
                self.state = "aggro"

        # ── State logic ──────────────────────────────────────────────
        if self.state == "idle_wander":
            self._update_wander(dt, tilemap)

        elif self.state == "flee":
            # Panic flee — short burst then calm down
            self._flee_panic_timer -= dt
            if self._flee_panic_timer <= 0:
                # Calm down and go back to wandering
                self.state = "idle_wander"
                self._wander_timer = random.uniform(2.0, 4.0)
            else:
                self._move_away(player_x, player_y, dt, tilemap, self.speed * 1.2)

        elif self.state == "aggro":
            if dist > self.aggro_range * 2.5:
                self.state = "idle_wander"
            elif self.atype == "boar" and dist <= 1.8 and self.attack_timer <= 0:
                # Boar initiates a charge
                self._charge_dir_x = (player_x - self.x) / max(dist, 0.1)
                self._charge_dir_y = (player_y - self.y) / max(dist, 0.1)
                self._charge_dur = 0.55
                self.state = "charge"
            elif dist <= 1.1 and self.attack_timer <= 0:
                self.state = "attack"
                self.state_timer = 0.0
                self.attack_timer = self.attack_cd
            else:
                self._move_toward(player_x, player_y, dt, tilemap, self.speed)
                self.face_toward(player_x, player_y)

        elif self.state == "charge":
            # Charge in straight line
            self._charge_dur -= dt
            mx = self._charge_dir_x * self.charge_speed * dt
            my = self._charge_dir_y * self.charge_speed * dt
            if tilemap.is_passable(self.x + mx, self.y):
                self.x += mx
            if tilemap.is_passable(self.x, self.y + my):
                self.y += my
            # Check if we hit the player
            if self.dist_to(player_x, player_y) <= 1.1:
                deal_damage = True
                self.attack_timer = self.attack_cd
                self.state = "aggro"
            elif self._charge_dur <= 0:
                self.state = "aggro"
                # Brief stagger after failed charge
                self.knockback_vx = -self._charge_dir_x * 2
                self.knockback_vy = -self._charge_dir_y * 2

        elif self.state == "attack":
            if self.state_timer >= 0.28:
                if self.dist_to(player_x, player_y) <= 1.2:
                    deal_damage = True
                self.state = "aggro"

        return deal_damage

    def _update_wander(self, dt: float, tilemap):
        """Random wandering within spawn area."""
        self._wander_timer -= dt
        if self._wander_timer <= 0:
            angle = random.uniform(0, math.pi * 2)
            spd = self.speed * random.uniform(0.2, 0.6)
            self._wander_vx, self._wander_vy = polar_offset(angle, spd)
            self._wander_timer = random.uniform(0.8, 2.5)

        # Wander but stay near spawn point
        dist_from_spawn = point_distance(self.x, self.y, self.spawn_x, self.spawn_y)
        if dist_from_spawn > 5.0:
            # Push back toward spawn
            dx = self.spawn_x - self.x
            dy = self.spawn_y - self.y
            nx, ny, _ = safe_normalize(dx, dy, minimum=0.01)
            self._wander_vx = nx * self.speed * 0.4
            self._wander_vy = ny * self.speed * 0.4

        nx = self.x + self._wander_vx * dt
        ny = self.y + self._wander_vy * dt
        if tilemap.is_passable(nx, self.y):
            self.x = nx
        else:
            self._wander_vx *= -0.5
        if tilemap.is_passable(self.x, ny):
            self.y = ny
        else:
            self._wander_vy *= -0.5

        # Update facing from wander direction
        if abs(self._wander_vx) > abs(self._wander_vy):
            self.facing = "right" if self._wander_vx > 0 else "left"
        elif abs(self._wander_vy) > 0.01:
            self.facing = "down" if self._wander_vy > 0 else "up"

    def _move_toward(self, tx, ty, dt, tilemap, spd):
        dx, dy = tx - self.x, ty - self.y
        nx, ny, _ = safe_normalize(dx, dy, minimum=0.01)
        mx = nx * spd * dt
        my = ny * spd * dt
        if tilemap.is_passable(self.x + mx, self.y):
            self.x += mx
        if tilemap.is_passable(self.x, self.y + my):
            self.y += my

    def _move_away(self, fx, fy, dt, tilemap, spd):
        """Move away from (fx, fy)."""
        dx, dy = self.x - fx, self.y - fy
        nx, ny, _ = safe_normalize(dx, dy, minimum=0.01)
        mx = nx * spd * dt
        my = ny * spd * dt
        if tilemap.is_passable(self.x + mx, self.y):
            self.x += mx
        else:
            # Try perpendicular escape
            mx = -ny * spd * dt
            if tilemap.is_passable(self.x + mx, self.y):
                self.x += mx
        if tilemap.is_passable(self.x, self.y + my):
            self.y += my

    # ─────────────────────────────────────────────────────────────────
    # RENDERING
    # ─────────────────────────────────────────────────────────────────

    def render(self, screen: pygame.Surface, cam_x: int, cam_y: int):
        T = TILE_SIZE
        sz = int(T * self.size)
        sx = int(self.x * T) - cam_x
        sy = int(self.y * T) - cam_y
        off = (T - sz) // 2
        
        # In asset compiler, size dictates the sprite box, T dictates footprint
        rx, ry = sx + off, sy + off
        
        # Load the pre-compiled sprite base
        category_id = f"animal_{self.atype}"
        sheet = load_sprite_sheet(category_id)
        if not sheet:
            # Fallback for dev mode when compiler hasn't run yet
            pygame.draw.ellipse(screen, self.color, (rx, ry, sz, sz))
            return
            
        anim_name = f"{self.facing}_walk" if self.state in ("flee", "aggro", "charge") or self._wander_timer > 0 else f"{self.facing}_idle"
        if self.state == "hurt":
            anim_name = "hurt"
        elif self.state == "death":
            anim_name = "death"
            
        # Map state time to frame
        if self.state == "death":
            frame_idx = min(3, int((self.death_timer / 0.6) * 4))
        else:
            frame_idx = int(self.anim_timer / 0.15) % 4
            if "idle" in anim_name or anim_name == "hurt":
                frame_idx = 0
                
        surf = get_frame(category_id, anim_name, frame_idx)
        if surf:
            # Blit main graphic
            screen.blit(surf, (rx, ry))
            
        # HP bar for damaged animals
        if self.hp < self.max_hp and self.state != "death":
            ratio = max(0, self.hp / self.max_hp)
            bw = sz
            pygame.draw.rect(screen, (30, 10, 10), (rx, ry - 6, bw, 3))
            pygame.draw.rect(screen, (180, 50, 50), (rx, ry - 6, int(bw * ratio), 3))

        # Charge indicator
        if self.state == "charge":
            pygame.draw.circle(screen, (255, 100, 50), (sx + T // 2, sy + T // 2), 5)
