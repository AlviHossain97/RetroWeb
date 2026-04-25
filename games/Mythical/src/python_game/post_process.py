"""
post_process.py — Screen-space post-processing effects.

Effects implemented:
  1. Vignette    — permanent dark border that focuses attention on center.
                   Intensity can increase during combat/low HP.
  2. Color grade — per-biome colour tint over the rendered frame.
                   Done via a transparent colored overlay (cheap LUT substitute).
  3. Motion blur — player dash / fast movement trails (alpha ghost behind player).
  4. Hit flash   — brief full-screen white flash when player takes damage.
  5. Death fade  — full-screen fade to black during death sequence.

All effects are composited in a single render() call after the world but
before the HUD, so HUD elements are always crisp.
"""
from __future__ import annotations

from typing import Optional

import pygame

from game_math import point_distance
from runtime.display_defaults import (
    DEFAULT_VIEWPORT_HEIGHT,
    DEFAULT_VIEWPORT_WIDTH,
)


# ─────────────────────────────────────────────────────────────────────────────
# BIOME COLOR GRADES
# ─────────────────────────────────────────────────────────────────────────────
# Each entry: (r, g, b, alpha)  — the alpha controls strength of the tint.

BIOME_GRADE: dict[str, tuple] = {
    "village":  (  0,  20,  0, 18),   # warm green lush outdoor
    "dungeon":  (  0,   0, 30, 30),   # cool blue-black cave atmosphere
    "default":  (  0,   0,  0,  0),
}


# ─────────────────────────────────────────────────────────────────────────────
# POST PROCESSOR
# ─────────────────────────────────────────────────────────────────────────────

class PostProcessor:
    """
    Owns all post-process state and performs compositing.

    Lifetime: created once, lives in GameplayState.
    Call update() each game tick, render() after world / before HUD.
    """

    def __init__(
        self,
        viewport_width: int = DEFAULT_VIEWPORT_WIDTH,
        viewport_height: int = DEFAULT_VIEWPORT_HEIGHT,
        *,
        supports_alpha: bool = True,
    ):
        self.viewport_width = max(1, int(viewport_width))
        self.viewport_height = max(1, int(viewport_height))
        self._supports_alpha = supports_alpha
        # Cached surfaces (built on first use / when screen size changes)
        self._vignette: Optional[pygame.Surface] = None
        self._grade_cache: dict[tuple[str, tuple[int, int], bool], pygame.Surface] = {}
        self._vig_cache: dict[tuple[tuple[int, int], float, bool], pygame.Surface] = {}

        # Per-biome grade state
        self._current_map: str = "village"

        # Hit flash
        self._hit_flash_alpha: float = 0.0
        self._hit_flash_color: tuple = (255, 255, 255)

        # Death fade
        self._death_fade_alpha: float = 0.0
        self._death_fading: bool = False

        # Vignette intensity (0.0 – 1.0; increases during combat / low HP)
        self._vignette_base: float = 0.35
        self._vignette_intensity: float = self._vignette_base

        # Motion blur ghosts — list of (surface, alpha)
        self._motion_ghosts: list[tuple[pygame.Surface, float]] = []
        self._ghost_decay = 0.85   # per-frame multiplier

    def set_viewport_size(self, width: int, height: int) -> None:
        width = max(1, int(width))
        height = max(1, int(height))
        if (width, height) != (self.viewport_width, self.viewport_height):
            self.viewport_width = width
            self.viewport_height = height
            self._vignette = None
            self._grade_cache.clear()
            self._vig_cache.clear()

    def _sync_viewport(self, screen: pygame.Surface) -> None:
        if screen is not None and hasattr(screen, "get_size"):
            self.set_viewport_size(*screen.get_size())

    # ─────────────────────────────────────────────────────────────────

    def set_map(self, map_name: str):
        self._current_map = map_name

    def trigger_hit_flash(self, color: tuple = (255, 255, 255), intensity: float = 0.4):
        """Call when player takes damage. Creates a brief white flash."""
        self._hit_flash_alpha = max(self._hit_flash_alpha, intensity * 255)
        self._hit_flash_color = color

    def trigger_death_fade(self):
        """Start fading screen to black (called during death sequence)."""
        self._death_fading = True

    def reset_death_fade(self):
        self._death_fade_alpha = 0.0
        self._death_fading = False

    def add_combat_vignette(self, active: bool):
        """Increase vignette during combat encounters."""
        target = 0.6 if active else self._vignette_base
        self._vignette_intensity += (target - self._vignette_intensity) * 0.05

    def push_motion_ghost(self, player_surf: pygame.Surface, alpha: float = 180):
        """
        Add a ghost image at the player's current screen position for dash blur.
        Caller passes the player sprite to ghost.
        alpha: starting opacity 0-255.
        """
        ghost = player_surf.copy()
        ghost.set_alpha(int(alpha))
        self._motion_ghosts.append([ghost, float(alpha)])

    # ─────────────────────────────────────────────────────────────────

    def update(self, dt: float):
        # Decay hit flash
        self._hit_flash_alpha = max(0.0, self._hit_flash_alpha - 400 * dt)

        # Advance death fade
        if self._death_fading:
            self._death_fade_alpha = min(255, self._death_fade_alpha + 120 * dt)

        # Decay motion ghosts
        self._motion_ghosts = [
            [surf, alpha * self._ghost_decay]
            for surf, alpha in self._motion_ghosts
            if alpha > 5
        ]
        for entry in self._motion_ghosts:
            entry[0].set_alpha(int(entry[1]))

    # ─────────────────────────────────────────────────────────────────

    def render(
        self,
        screen: pygame.Surface,
        player_dash_ghost_pos: Optional[tuple] = None,
    ):
        """Composite all post-process effects onto screen."""
        self._sync_viewport(screen)
        size = screen.get_size()

        # 1. Color grade (biome tint)
        self._render_grade(screen, size)

        # 2. Vignette
        self._render_vignette(screen, size)

        # 3. Hit flash
        if self._hit_flash_alpha > 0:
            if self._supports_alpha:
                flash = pygame.Surface(size, pygame.SRCALPHA)
                flash.fill((*self._hit_flash_color, int(self._hit_flash_alpha)))
                screen.blit(flash, (0, 0))
            else:
                flash = pygame.Surface(size)
                intensity = max(0, min(255, int(self._hit_flash_alpha)))
                scaled = tuple(min(255, int(c * (intensity / 255.0))) for c in self._hit_flash_color)
                flash.fill(scaled)
                screen.blit(flash, (0, 0), special_flags=pygame.BLEND_RGB_ADD)

        # 4. Death fade
        if self._death_fade_alpha > 0:
            if self._supports_alpha:
                fade = pygame.Surface(size, pygame.SRCALPHA)
                fade.fill((0, 0, 0, int(self._death_fade_alpha)))
                screen.blit(fade, (0, 0))
            else:
                multiplier = max(0, 255 - int(self._death_fade_alpha))
                fade = pygame.Surface(size)
                fade.fill((multiplier, multiplier, multiplier))
                screen.blit(fade, (0, 0), special_flags=pygame.BLEND_RGB_MULT)

    def render_motion_ghosts(
        self,
        screen: pygame.Surface,
        ghost_positions: list[tuple[int, int]],
    ):
        """
        Render motion blur ghosts at given screen positions (left trail).
        Called BEFORE the player sprite render for correct depth.
        ghost_positions: list of (sx, sy) from oldest to newest.
        """
        for i, (entry, pos) in enumerate(zip(self._motion_ghosts, ghost_positions)):
            surf, _ = entry
            screen.blit(surf, pos)

    # ─────────────────────────────────────────────────────────────────

    def _render_grade(self, screen: pygame.Surface, size: tuple):
        grade = BIOME_GRADE.get(self._current_map, BIOME_GRADE["default"])
        if grade[3] == 0:
            return
        key = (self._current_map, size, self._supports_alpha)
        if key not in self._grade_cache:
            if self._supports_alpha:
                surf = pygame.Surface(size, pygame.SRCALPHA)
                surf.fill(grade)
            else:
                surf = pygame.Surface(size)
                strength = grade[3] / 255.0
                surf.fill(tuple(int(channel * strength) for channel in grade[:3]))
            self._grade_cache[key] = surf
        if self._supports_alpha:
            screen.blit(self._grade_cache[key], (0, 0))
        else:
            screen.blit(self._grade_cache[key], (0, 0), special_flags=pygame.BLEND_RGB_ADD)

    def _render_vignette(self, screen: pygame.Surface, size: tuple):
        key = (size, round(self._vignette_intensity, 2), self._supports_alpha)
        if key not in self._vig_cache:
            surf = pygame.Surface(size, pygame.SRCALPHA if self._supports_alpha else 0)
            cx, cy = size[0] // 2, size[1] // 2
            max_r = int(point_distance(0, 0, cx, cy))
            inner_r = int(max_r * 0.45)
            if self._supports_alpha:
                # Draw concentric rings from edge inward, increasing alpha toward edge
                for r in range(max_r, inner_r, -2):
                    t = (r - inner_r) / max(1, max_r - inner_r)
                    alpha = int(180 * self._vignette_intensity * (t ** 1.8))
                    c = (0, 0, 0, min(200, alpha))
                    pygame.draw.circle(surf, c, (cx, cy), r, 3)
            else:
                surf.fill((255, 255, 255))
                border = max(10, min(size) // 9)
                edge = max(64, 255 - int(110 * self._vignette_intensity))
                color = (edge, edge, edge)
                pygame.draw.rect(surf, color, (0, 0, size[0], border))
                pygame.draw.rect(surf, color, (0, size[1] - border, size[0], border))
                pygame.draw.rect(surf, color, (0, 0, border, size[1]))
                pygame.draw.rect(surf, color, (size[0] - border, 0, border, size[1]))
            self._vig_cache[key] = surf
            # Limit cache size
            if len(self._vig_cache) > 8:
                oldest = next(iter(self._vig_cache))
                del self._vig_cache[oldest]
        if self._supports_alpha:
            screen.blit(self._vig_cache[key], (0, 0))
        else:
            screen.blit(self._vig_cache[key], (0, 0), special_flags=pygame.BLEND_RGB_MULT)
