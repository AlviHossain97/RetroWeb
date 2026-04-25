"""
enemy.py - Enemy class: path-following, HP, armour, speed, status effects, death.
"""
from __future__ import annotations

import math
import pygame
from settings import *


class Enemy:
    """A single enemy unit that follows a pre-computed path toward the player base."""

    def __init__(self, enemy_type: str, path: list[tuple[int, int]], spawn_index: int = 0) -> None:
        defn = ENEMY_DEFS[enemy_type]
        self.type = enemy_type
        self.name: str = defn["name"]
        self.path = path
        self.path_idx = 0
        self.x: float = float(path[0][0])
        self.y: float = float(path[0][1])

        # Core stats
        self.hp: float = float(defn["hp"])
        self.max_hp: float = float(defn["hp"])
        self.speed: float = float(defn["speed"])
        self.armour: float = float(defn["armour"])
        self.gold: int = defn["gold"]
        self.color: tuple[int, int, int] = defn["color"]
        self.size: float = defn["size"]

        # State flags
        self.alive: bool = True
        self.reached_base: bool = False
        self.death_timer: float = 0.3

        # Status effects
        self.slow_timer: float = 0.0
        self.slow_factor: float = 1.0
        self.dot_stacks: list[dict] = []  # [{"dps": float, "remaining": float}]

        # Specials
        self.special: str = defn.get("special", "none")
        self.heal_rate: float = float(defn.get("heal_rate", 0.0))
        self.heal_range: float = float(defn.get("heal_range", 0.0))
        self._heal_cooldown: float = 0.0  # internal timer for healer ticks

        # Lives cost (Titan = 5, others = 1)
        self.lives_cost: int = defn.get("lives_cost", 1)

        # Spawn index for multi-spawn maps
        self.spawn_index: int = spawn_index

        # Visual timers
        self._burn_flicker: float = 0.0
        self._titan_pulse: float = 0.0

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------
    def update(self, dt: float, all_enemies: list[Enemy]) -> None:
        if not self.alive:
            self.death_timer -= dt
            return

        # 1. Process DoT stacks ----------------------------------------
        if self.dot_stacks:
            total_dps = sum(s["dps"] for s in self.dot_stacks)
            dot_raw = total_dps * dt
            dot_after_armour = max(0.0, dot_raw - self.armour * dt)
            self.hp -= dot_after_armour
            # Decrement timers, remove expired
            for stack in self.dot_stacks:
                stack["remaining"] -= dt
            self.dot_stacks = [s for s in self.dot_stacks if s["remaining"] > 0.0]
            if self.hp <= 0:
                self.alive = False
                return

        # 2. Slow timer -------------------------------------------------
        if self.slow_timer > 0:
            self.slow_timer -= dt
            if self.slow_timer <= 0:
                self.slow_factor = 1.0

        effective_speed = self.speed * self.slow_factor

        # 3. Move toward next waypoint ----------------------------------
        if self.path_idx < len(self.path):
            target_x = float(self.path[self.path_idx][0])
            target_y = float(self.path[self.path_idx][1])
            dx = target_x - self.x
            dy = target_y - self.y
            dist = math.hypot(dx, dy)

            if dist < 0.1:
                self.path_idx += 1
            else:
                move_dist = effective_speed * dt
                if move_dist >= dist:
                    self.x = target_x
                    self.y = target_y
                    self.path_idx += 1
                else:
                    self.x += (dx / dist) * move_dist
                    self.y += (dy / dist) * move_dist

        # 4. Reached base? -----------------------------------------------
        if self.path_idx >= len(self.path):
            self.reached_base = True
            self.alive = False
            return

        # 5. Healer special -----------------------------------------------
        if self.special == "heal":
            self._heal_cooldown -= dt
            if self._heal_cooldown <= 0:
                self._heal_cooldown = 1.0
                for other in all_enemies:
                    if other is self or not other.alive:
                        continue
                    edx = other.x - self.x
                    edy = other.y - self.y
                    if math.hypot(edx, edy) <= self.heal_range:
                        other.hp = min(other.hp + self.heal_rate, other.max_hp)

        # 6. Visual timers -------------------------------------------------
        self._burn_flicker += dt * 8.0
        self._titan_pulse += dt * 3.0

    # ------------------------------------------------------------------
    # Damage & effects
    # ------------------------------------------------------------------
    def take_damage(self, amount: float) -> None:
        effective = max(0.0, amount - self.armour)
        self.hp -= effective
        if self.hp <= 0:
            self.hp = 0
            self.alive = False

    def apply_slow(self, factor: float, duration: float) -> None:
        self.slow_factor = min(self.slow_factor, factor)
        self.slow_timer = duration

    def add_dot(self, dps: float, duration: float) -> None:
        if len(self.dot_stacks) < 3:
            self.dot_stacks.append({"dps": dps, "remaining": duration})

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------
    def render(self, screen: pygame.Surface, offset_x: int, offset_y: int,
               assets=None) -> None:
        px = int(self.x * TILE_SIZE + TILE_SIZE // 2) + offset_x
        py = int(self.y * TILE_SIZE + TILE_SIZE // 2) + offset_y
        radius = max(3, int(self.size * TILE_SIZE * 0.4))

        sprite = assets.get_enemy_sprite(self.type) if assets else None

        if not self.alive:
            # Death fade: shrink + fade alpha
            if self.death_timer > 0:
                alpha = max(0, int(255 * (self.death_timer / 0.3)))
                fade_ratio = self.death_timer / 0.3
                if sprite:
                    sw, sh = sprite.get_size()
                    fw = max(1, int(sw * fade_ratio))
                    fh = max(1, int(sh * fade_ratio))
                    faded = pygame.transform.scale(sprite, (fw, fh))
                    faded.set_alpha(alpha)
                    screen.blit(faded, (px - fw // 2, py - fh // 2))
                else:
                    fade_radius = max(1, int(radius * fade_ratio))
                    surf = pygame.Surface((fade_radius * 2, fade_radius * 2), pygame.SRCALPHA)
                    c = self.color
                    pygame.draw.circle(surf, (c[0], c[1], c[2], alpha),
                                       (fade_radius, fade_radius), fade_radius)
                    screen.blit(surf, (px - fade_radius, py - fade_radius))
            return

        # Titan pulsing outline
        if self.type == "titan":
            pulse = int(3 + 2 * math.sin(self._titan_pulse))
            outline_surf = pygame.Surface(((radius + pulse) * 2, (radius + pulse) * 2), pygame.SRCALPHA)
            pygame.draw.circle(outline_surf, (200, 60, 60, 120),
                               (radius + pulse, radius + pulse), radius + pulse)
            screen.blit(outline_surf, (px - radius - pulse, py - radius - pulse))

        # Main body
        if sprite:
            sw, sh = sprite.get_size()
            screen.blit(sprite, (px - sw // 2, py - sh // 2))
        else:
            pygame.draw.circle(screen, self.color, (px, py), radius)

        # Blue tint if slowed
        if self.slow_timer > 0:
            slow_surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(slow_surf, (60, 100, 220, 80), (radius, radius), radius)
            screen.blit(slow_surf, (px - radius, py - radius))

        # Orange flicker if burning (has dot stacks)
        if self.dot_stacks:
            flicker_alpha = int(60 + 40 * math.sin(self._burn_flicker))
            burn_surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
            pygame.draw.circle(burn_surf, (255, 140, 30, flicker_alpha),
                               (radius, radius), radius)
            screen.blit(burn_surf, (px - radius, py - radius))

        # HP bar above sprite (only if damaged)
        if self.hp < self.max_hp:
            bar_w = radius * 2
            bar_h = 3
            bar_x = px - radius
            bar_y = py - radius - 6
            pygame.draw.rect(screen, (40, 40, 40), (bar_x, bar_y, bar_w, bar_h))
            green_w = max(0, int(bar_w * (self.hp / self.max_hp)))
            if green_w > 0:
                pygame.draw.rect(screen, (60, 200, 60), (bar_x, bar_y, green_w, bar_h))
