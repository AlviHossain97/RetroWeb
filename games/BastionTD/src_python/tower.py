"""
tower.py - Tower class: targeting, cooldown, firing, upgrade, sell, rendering.
"""
from __future__ import annotations

import math
from typing import TYPE_CHECKING
import pygame
from settings import *
from projectile import Projectile

if TYPE_CHECKING:
    from enemy import Enemy


class Tower:
    """A player-placed tower that auto-targets and fires at enemies."""

    def __init__(self, tower_type: str, tile_x: int, tile_y: int) -> None:
        defn = TOWER_DEFS[tower_type]
        self.type: str = tower_type
        self.x: int = tile_x
        self.y: int = tile_y
        self.level: int = 1
        self.cooldown_timer: float = 0.0
        self.target: Enemy | None = None

        # Core stats (mutable -- upgrades modify these)
        self.range: float = float(defn["range"])
        self.damage: float = float(defn["damage"])
        self.cooldown: float = float(defn["cooldown"])
        self.color: tuple[int, int, int] = defn["color"]
        self.special: str = defn["special"]
        self.name: str = defn["name"]

        # Special-specific stats
        self.splash_radius: float = float(defn.get("splash_radius", 0))
        self.slow_factor: float = float(defn.get("slow_factor", 0))
        self.slow_duration: float = float(defn.get("slow_duration", 0))
        self.chain_count: int = int(defn.get("chain_count", 0))
        self.chain_range: float = float(defn.get("chain_range", 0))
        self.dot_damage: float = float(defn.get("dot_damage", 0))
        self.dot_duration: float = float(defn.get("dot_duration", 0))

        # Economy tracking
        self.cost: int = defn["cost"]
        self.total_invested: int = defn["cost"]

    # ------------------------------------------------------------------
    # Update -- returns a Projectile or None
    # ------------------------------------------------------------------
    def update(self, dt: float, enemies: list[Enemy]) -> Projectile | None:
        self.cooldown_timer -= dt

        # Find nearest enemy within range
        best_enemy: Enemy | None = None
        best_dist = float("inf")
        for enemy in enemies:
            if not enemy.alive:
                continue
            dx = enemy.x - (self.x + 0.5)
            dy = enemy.y - (self.y + 0.5)
            dist = math.hypot(dx, dy)
            if dist <= self.range and dist < best_dist:
                best_dist = dist
                best_enemy = enemy

        self.target = best_enemy

        if best_enemy is not None and self.cooldown_timer <= 0:
            self.cooldown_timer = self.cooldown
            # Build special_data dict for the projectile
            special_data: dict = {}
            if self.special == "splash":
                special_data["splash_radius"] = self.splash_radius
            elif self.special == "slow":
                special_data["slow_factor"] = self.slow_factor
                special_data["slow_duration"] = self.slow_duration
            elif self.special == "chain":
                special_data["chain_count"] = self.chain_count
                special_data["chain_range"] = self.chain_range
            elif self.special == "dot":
                special_data["dot_damage"] = self.dot_damage
                special_data["dot_duration"] = self.dot_duration

            return Projectile(
                start_x=self.x + 0.5,
                start_y=self.y + 0.5,
                target_enemy=best_enemy,
                tower_type=self.type,
                damage=self.damage,
                special_data=special_data,
            )

        return None

    # ------------------------------------------------------------------
    # Upgrade -- returns cost paid, or -1 if max level
    # ------------------------------------------------------------------
    def upgrade(self) -> int:
        defn = TOWER_DEFS[self.type]
        upgrades = defn["upgrades"]
        upgrade_idx = self.level - 1  # level 1 -> upgrade index 0, etc.
        if upgrade_idx >= len(upgrades):
            return -1

        upg = upgrades[upgrade_idx]
        cost = upg["cost"]

        # Apply stat changes from upgrade dict (values are new absolute targets)
        if "damage" in upg:
            self.damage = float(upg["damage"])
        if "range" in upg:
            self.range = float(upg["range"])
        if "cooldown" in upg:
            self.cooldown = float(upg["cooldown"])
        if "splash_radius" in upg:
            self.splash_radius = float(upg["splash_radius"])
        if "slow_factor" in upg:
            self.slow_factor = float(upg["slow_factor"])
        if "slow_duration" in upg:
            self.slow_duration = float(upg["slow_duration"])
        if "chain_count" in upg:
            self.chain_count = int(upg["chain_count"])
        if "chain_range" in upg:
            self.chain_range = float(upg["chain_range"])
        if "dot_damage" in upg:
            self.dot_damage = float(upg["dot_damage"])
        if "dot_duration" in upg:
            self.dot_duration = float(upg["dot_duration"])

        self.level += 1
        self.total_invested += cost
        return cost

    # ------------------------------------------------------------------
    # Sell
    # ------------------------------------------------------------------
    def sell_value(self) -> int:
        return self.total_invested // 2

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------
    def render(self, screen: pygame.Surface, offset_x: int, offset_y: int,
               assets=None) -> None:
        # Pixel position of tile top-left
        px = self.x * TILE_SIZE + offset_x
        py = self.y * TILE_SIZE + offset_y
        center_x = px + TILE_SIZE // 2
        center_y = py + TILE_SIZE // 2

        sprite = assets.get_tower_sprite(self.type, self.level) if assets else None

        if sprite:
            # Blit sprite centered in the tile
            sw, sh = sprite.get_size()
            screen.blit(sprite, (center_x - sw // 2, center_y - sh // 2))
        else:
            # Fallback: primitive rendering
            margin = (TILE_SIZE - 28) // 2
            pygame.draw.rect(screen, self.color, (px + margin, py + margin, 28, 28))
            dark_color = (
                max(0, self.color[0] - 50),
                max(0, self.color[1] - 50),
                max(0, self.color[2] - 50),
            )
            pygame.draw.circle(screen, dark_color, (center_x, center_y), 5)

        # Level pips (white dots below tower)
        pip_y = py + TILE_SIZE - 4
        pip_spacing = 6
        total_width = (self.level - 1) * pip_spacing
        start_x = center_x - total_width // 2
        for i in range(self.level):
            pip_x = start_x + i * pip_spacing
            pygame.draw.circle(screen, COLOR_WHITE, (pip_x, pip_y), 2)

    def render_range(self, screen: pygame.Surface, offset_x: int, offset_y: int) -> None:
        """Draw a thin semi-transparent range circle."""
        center_x = self.x * TILE_SIZE + TILE_SIZE // 2 + offset_x
        center_y = self.y * TILE_SIZE + TILE_SIZE // 2 + offset_y
        radius = int(self.range * TILE_SIZE)

        # Semi-transparent circle via surface
        size = radius * 2 + 4
        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        pygame.draw.circle(
            surf,
            (255, 255, 255, 40),
            (size // 2, size // 2),
            radius,
            1,  # thin outline
        )
        screen.blit(surf, (center_x - size // 2, center_y - size // 2))
