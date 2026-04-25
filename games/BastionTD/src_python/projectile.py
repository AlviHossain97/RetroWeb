"""
projectile.py - Projectile class: flies from tower to enemy, applies damage + specials.
"""
from __future__ import annotations

import math
from typing import TYPE_CHECKING
import pygame
from settings import *

if TYPE_CHECKING:
    from enemy import Enemy


class Projectile:
    """A projectile entity that travels from a tower toward an enemy target."""

    def __init__(
        self,
        start_x: float,
        start_y: float,
        target_enemy: Enemy,
        tower_type: str,
        damage: float,
        special_data: dict,
    ) -> None:
        self.x: float = start_x   # tile coords (float)
        self.y: float = start_y
        self.target: Enemy = target_enemy
        self.tower_type: str = tower_type
        self.damage: float = damage
        self.special: dict = special_data  # splash_radius, slow_factor, etc.
        self.speed: float = 12.0           # tiles per second
        self.alive: bool = True
        self.color: tuple[int, int, int] = TOWER_DEFS[tower_type]["color"]

        # Cache last known target position (in case target dies mid-flight)
        self._last_target_x: float = target_enemy.x
        self._last_target_y: float = target_enemy.y

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------
    def update(self, dt: float, all_enemies: list[Enemy]) -> None:
        if not self.alive:
            return

        # Determine destination: living target or last known position
        if self.target.alive:
            dest_x = self.target.x
            dest_y = self.target.y
            self._last_target_x = dest_x
            self._last_target_y = dest_y
        else:
            dest_x = self._last_target_x
            dest_y = self._last_target_y

        # Move toward destination
        dx = dest_x - self.x
        dy = dest_y - self.y
        dist = math.hypot(dx, dy)

        if dist < 0.3:
            self._on_impact(all_enemies)
            return

        move_dist = self.speed * dt
        if move_dist >= dist:
            self.x = dest_x
            self.y = dest_y
            self._on_impact(all_enemies)
        else:
            self.x += (dx / dist) * move_dist
            self.y += (dy / dist) * move_dist

    # ------------------------------------------------------------------
    # Impact logic
    # ------------------------------------------------------------------
    def _on_impact(self, all_enemies: list[Enemy]) -> None:
        self.alive = False

        # Apply primary damage to target (if still alive)
        if self.target.alive:
            self.target.take_damage(self.damage)

        # --- Splash ---------------------------------------------------
        splash_radius = self.special.get("splash_radius", 0)
        if splash_radius > 0:
            splash_dmg = self.damage * 0.5
            for enemy in all_enemies:
                if enemy is self.target or not enemy.alive:
                    continue
                edist = math.hypot(enemy.x - self.x, enemy.y - self.y)
                if edist <= splash_radius:
                    enemy.take_damage(splash_dmg)

        # --- Slow -----------------------------------------------------
        slow_factor = self.special.get("slow_factor", 0)
        slow_duration = self.special.get("slow_duration", 0)
        if slow_factor > 0 and slow_duration > 0 and self.target.alive:
            self.target.apply_slow(slow_factor, slow_duration)

        # --- Chain ----------------------------------------------------
        chain_count = self.special.get("chain_count", 0)
        chain_range = self.special.get("chain_range", 0)
        if chain_count > 0 and chain_range > 0:
            chain_dmg = self.damage * 0.7
            last_x = self._last_target_x
            last_y = self._last_target_y
            already_hit: set[int] = {id(self.target)}
            for _ in range(chain_count):
                best_enemy: Enemy | None = None
                best_dist = float("inf")
                for enemy in all_enemies:
                    if id(enemy) in already_hit or not enemy.alive:
                        continue
                    edist = math.hypot(enemy.x - last_x, enemy.y - last_y)
                    if edist <= chain_range and edist < best_dist:
                        best_dist = edist
                        best_enemy = enemy
                if best_enemy is None:
                    break
                best_enemy.take_damage(chain_dmg)
                already_hit.add(id(best_enemy))
                last_x = best_enemy.x
                last_y = best_enemy.y

        # --- DoT (damage over time) ------------------------------------
        dot_damage = self.special.get("dot_damage", 0)
        dot_duration = self.special.get("dot_duration", 0)
        if dot_damage > 0 and dot_duration > 0 and self.target.alive:
            self.target.add_dot(dot_damage, dot_duration)

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------
    def render(self, screen: pygame.Surface, offset_x: int, offset_y: int) -> None:
        if not self.alive:
            return
        px = int(self.x * TILE_SIZE + TILE_SIZE // 2) + offset_x
        py = int(self.y * TILE_SIZE + TILE_SIZE // 2) + offset_y
        pygame.draw.circle(screen, self.color, (px, py), 3)
