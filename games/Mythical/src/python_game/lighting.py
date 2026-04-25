"""
lighting.py — Dynamic lighting with point lights and soft shadow overlay.

Approach (no shaders needed):
  1. Build a dark "shadow mask" surface (full-screen, black SRCALPHA).
  2. "Punch out" circular gradient light cones centered on each light source.
  3. Blit the mask over the world before rendering UI.

Light sources:
  • Player — ambient personal light (radius scaled by equipped items)
  • Torches / lamps — static point lights per map (from decor defs)
  • Enemies / animals — subtle bio-luminescent glow (optional)
  • Magic effects — bright flash on spell cast
  • Fast travel gates — coloured ambient pulse

Zone ambient:
  • Village → high ambient (near-daytime)
  • Dungeon → very dark ambient
  • Both support a day-cycle multiplier (stubbed; can be wired to real-time clock)

Performance: mask is rebuilt each frame only if any dynamic light changed.
Static lights are cached on map load.
"""
from __future__ import annotations

import math
from typing import Optional

import pygame

from runtime.display_defaults import (
    DEFAULT_VIEWPORT_HEIGHT,
    DEFAULT_VIEWPORT_WIDTH,
)
from settings import (
    TILE_SIZE,
    AMBIENT_VILLAGE_LIGHT, AMBIENT_DUNGEON_LIGHT,
    TORCH_LIGHT_RADIUS, PLAYER_LIGHT_RADIUS,
)

# ─────────────────────────────────────────────────────────────────────────────
# ZONE AMBIENT CONFIG
# ─────────────────────────────────────────────────────────────────────────────

ZONE_AMBIENT: dict[str, int] = {
    "village":  AMBIENT_VILLAGE_LIGHT,   # 220 — bright outdoor
    "dungeon":  AMBIENT_DUNGEON_LIGHT,   # 80  — dark cave
    "ruins_approach": 140, 
    "ruins_depths":   80,  
    "sanctum_halls":  100, 
    "throne_room":    120, 
}

# Colours for biome-tinted ambient overlay (very subtle)
ZONE_TINT: dict[str, tuple] = {
    "village":  (0,   5,  0),    # very slight green warmth
    "dungeon":  (0,   0, 10),    # very slight blue-cold
    "ruins_approach": (10,  5,  0),   
    "ruins_depths":   (10,  0,  5),   
    "sanctum_halls":  (0,   0, 15),   
    "throne_room":    (15,  0, 20),   
}

# Light source colors
TORCH_COLOR   = (255, 200, 100)
PLAYER_COLOR  = (200, 220, 255)
MAGIC_COLOR   = (100, 140, 255)
GATE_COLOR    = (120, 160, 240)
FIRE_COLOR    = (255, 150,  50)


def _gradient_circle(radius_px: int, color: tuple, inner_alpha: int = 220) -> pygame.Surface:
    """
    Build a pre-rendered radial-gradient circle surface (SRCALPHA).
    Center is bright (inner_alpha), edge fades to transparent.
    """
    diam = radius_px * 2
    surf = pygame.Surface((diam, diam), pygame.SRCALPHA)
    cx = cy = radius_px
    for r in range(radius_px, 0, -1):
        t = r / radius_px                       # 1.0 at edge → 0.0 at center
        alpha = int(inner_alpha * (1 - t * t))  # quadratic falloff
        pygame.draw.circle(surf, (*color, alpha), (cx, cy), r)
    return surf


class PointLight:
    """A dynamic or static in-world light source."""
    __slots__ = ("x", "y", "radius", "color", "intensity", "flicker", "_flicker_t")

    def __init__(
        self,
        world_x: float,
        world_y: float,
        radius_tiles: float = TORCH_LIGHT_RADIUS,
        color: tuple = TORCH_COLOR,
        intensity: float = 1.0,
        flicker: bool = False,
    ):
        self.x = world_x
        self.y = world_y
        self.radius = radius_tiles
        self.color = color
        self.intensity = intensity
        self.flicker = flicker
        self._flicker_t = 0.0

    def update(self, dt: float):
        if self.flicker:
            import random
            self._flicker_t += dt
            self.intensity = 0.85 + 0.15 * math.sin(self._flicker_t * 8 +
                             math.sin(self._flicker_t * 17) * 0.5)

    def effective_radius_px(self) -> int:
        return max(1, int(self.radius * TILE_SIZE * self.intensity))


class LightingSystem:
    """
    Renders the full-screen shadow overlay with punched-out light regions.

    Usage:
      lighting = LightingSystem()
      lighting.set_map("dungeon")
      lighting.set_static_lights([...])      # on map load
      lighting.update(dt, player_x, player_y, equipment_effects, dynamic_lights)
      lighting.render(screen, cam_x, cam_y)  # call after tilemap, before HUD
    """

    def __init__(
        self,
        viewport_width: int = DEFAULT_VIEWPORT_WIDTH,
        viewport_height: int = DEFAULT_VIEWPORT_HEIGHT,
        *,
        supports_alpha: bool = True,
    ):
        self._map_name = "village"
        self._ambient = AMBIENT_VILLAGE_LIGHT
        self._tint = ZONE_TINT.get("village", (0, 0, 0))
        self.viewport_width = max(1, int(viewport_width))
        self.viewport_height = max(1, int(viewport_height))
        self._supports_alpha = supports_alpha
        self._static_lights: list[PointLight] = []
        self._dynamic_lights: list[PointLight] = []
        self._mask: Optional[pygame.Surface] = None
        self._gradient_cache: dict[tuple, pygame.Surface] = {}
        self._player_light = PointLight(0, 0, PLAYER_LIGHT_RADIUS, PLAYER_COLOR, 1.0, False)

    def set_viewport_size(self, width: int, height: int) -> None:
        width = max(1, int(width))
        height = max(1, int(height))
        if (width, height) != (self.viewport_width, self.viewport_height):
            self.viewport_width = width
            self.viewport_height = height
            self._mask = None

    def _sync_viewport(self, screen: pygame.Surface) -> None:
        if screen is not None and hasattr(screen, "get_size"):
            self.set_viewport_size(*screen.get_size())

    def set_map(self, map_name: str):
        self._map_name = map_name
        self._ambient = ZONE_AMBIENT.get(map_name, 200)
        self._tint = ZONE_TINT.get(map_name, (0, 0, 0))
        self._gradient_cache.clear()
        self._mask = None

    def set_static_lights(self, lights: list[PointLight]):
        """Call on map load with torch/lamp positions from the map data."""
        self._static_lights = lights
        self._gradient_cache.clear()

    # ── Update ────────────────────────────────────────────────────────

    def update(
        self,
        dt: float,
        player_x: float,
        player_y: float,
        equipment_effects: set[str],
        extra_lights: Optional[list[PointLight]] = None,
    ):
        # Player light — bigger if mage or magical effects active
        player_radius = PLAYER_LIGHT_RADIUS
        if "amplify_magic" in equipment_effects:
            player_radius += 1.5
        self._player_light.x = player_x
        self._player_light.y = player_y
        self._player_light.radius = player_radius

        # Update flickering torches
        for light in self._static_lights:
            light.update(dt)

        # Dynamic lights from gameplay (e.g. fire projectiles, magic casts)
        self._dynamic_lights = extra_lights or []

    # ── Render ────────────────────────────────────────────────────────

    def render(self, screen: pygame.Surface, cam_x: int, cam_y: int):
        """
        Render the shadow overlay onto the screen.
        Does nothing in fully-lit zones (ambient >= 240).
        """
        self._sync_viewport(screen)
        if self._ambient >= 235:
            # Village is bright enough — skip heavy overlay but add subtle tint
            if any(self._tint) and self._supports_alpha:
                tsurf = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
                tsurf.fill((*self._tint, 20))
                screen.blit(tsurf, (0, 0))
            return

        if not self._supports_alpha:
            self._render_non_alpha_fallback(screen, cam_x, cam_y)
            return

        # Build shadow mask
        if self._mask is None or self._mask.get_size() != screen.get_size():
            self._mask = pygame.Surface(screen.get_size(), pygame.SRCALPHA)

        # Fill with dark overlay (higher = darker)
        darkness = 255 - self._ambient
        # Add biome tint to darkness colour
        tr, tg, tb = self._tint
        self._mask.fill((max(0, tr), max(0, tg), max(0, min(20, tb)), darkness))

        # Punch out light regions
        all_lights = (self._static_lights + self._dynamic_lights +
                      [self._player_light])
        for light in all_lights:
            self._punch_light(self._mask, light, cam_x, cam_y)

        screen.blit(self._mask, (0, 0))

    def _render_non_alpha_fallback(self, screen: pygame.Surface, cam_x: int, cam_y: int) -> None:
        """
        Approximate darkness on targets without per-pixel alpha.

        This is intentionally simple: darken the whole frame with RGB multiply,
        then draw small light markers so gameplay-relevant light sources still
        have a visible presence on low-capability targets.
        """
        darkness = max(0, min(255, 255 - self._ambient))
        if darkness <= 0:
            return

        multiplier = max(0, 255 - darkness)
        shade = pygame.Surface((self.viewport_width, self.viewport_height))
        shade.fill((multiplier, multiplier, multiplier))
        screen.blit(shade, (0, 0), special_flags=pygame.BLEND_RGB_MULT)

        for light in self._static_lights + self._dynamic_lights + [self._player_light]:
            lx = int(light.x * TILE_SIZE) - cam_x + TILE_SIZE // 2
            ly = int(light.y * TILE_SIZE) - cam_y + TILE_SIZE // 2
            lr = max(2, light.effective_radius_px() // 6)
            pygame.draw.circle(screen, light.color, (lx, ly), lr, 1)

    def _punch_light(
        self,
        mask: pygame.Surface,
        light: PointLight,
        cam_x: int, cam_y: int,
    ):
        """Subtract a gradient circle from the mask at the light's screen position."""
        r_px = light.effective_radius_px()
        cache_key = (r_px, light.color)
        if cache_key not in self._gradient_cache:
            self._gradient_cache[cache_key] = _gradient_circle(r_px, light.color)
        grad = self._gradient_cache[cache_key]

        # World → screen
        sx = int(light.x * TILE_SIZE) - cam_x - r_px + TILE_SIZE // 2
        sy = int(light.y * TILE_SIZE) - cam_y - r_px + TILE_SIZE // 2

        # Blend mode BLEND_RGBA_SUB removes darkness where light shines
        mask.blit(grad, (sx, sy), special_flags=pygame.BLEND_RGBA_SUB)

    # ── Factory helpers ───────────────────────────────────────────────

    @staticmethod
    def make_torch_from_tile(tx: int, ty: int) -> PointLight:
        return PointLight(tx + 0.5, ty + 0.5, TORCH_LIGHT_RADIUS, TORCH_COLOR,
                          1.0, flicker=True)

    @staticmethod
    def make_gate_light(tx: int, ty: int) -> PointLight:
        return PointLight(tx + 0.5, ty + 0.5, 3.0, GATE_COLOR, 0.8, flicker=False)

    @staticmethod
    def make_fire_light(wx: float, wy: float) -> PointLight:
        """Temporary light from a fireball or burning enemy."""
        return PointLight(wx, wy, 2.5, FIRE_COLOR, 1.2, flicker=True)


def build_static_lights_for_map(map_name: str, map_data: dict) -> list[PointLight]:
    """
    Scan the map's decor layer for lamp_post and other light-emitting tiles
    and return PointLight objects for them.  Maps without lamp_post decor
    fall back to per-map hardcoded torch/arcane positions so every dark
    zone has authored light sources.
    """
    lights = []
    decor = map_data.get("decor")
    if decor:
        from tilemap import DECOR_DEFS
        for row_idx, row in enumerate(decor):
            for col_idx, did in enumerate(row):
                ddef = DECOR_DEFS.get(did)
                if not ddef:
                    continue
                name = ddef.get("name", "")
                if name == "lamp_post":
                    lights.append(LightingSystem.make_torch_from_tile(col_idx, row_idx))
                elif name == "well":
                    lights.append(PointLight(
                        col_idx + 0.5, row_idx + 0.5, 1.5, (80, 120, 180), 0.5, False))

    # Per-map fallback torches for maps with no lamp_post decor tiles.
    # Positions chosen to match the map's authored corridor/room layout.
    _FALLBACK: dict[str, list[tuple]] = {
        # dungeon: 40×40 — cave corridors, orange wall torches
        "dungeon": [
            (8,  20, 2.0, TORCH_COLOR),
            (14, 18, 2.0, TORCH_COLOR),
            (20, 20, 2.2, TORCH_COLOR),
            (26, 15, 2.0, TORCH_COLOR),
            (26, 25, 2.0, TORCH_COLOR),
            (32, 20, 2.2, TORCH_COLOR),
            (37, 20, 2.5, TORCH_COLOR),   # boss chamber
        ],
        # ruins_depths: 60×40 — bone crypts, dim red-orange torches
        "ruins_depths": [
            (5,  20, 1.8, (200, 120, 60)),
            (15, 15, 1.8, (200, 120, 60)),
            (15, 25, 1.8, (200, 120, 60)),
            (28, 20, 2.0, (200, 120, 60)),
            (38, 20, 2.0, (200, 120, 60)),
            (48, 20, 2.2, (200, 100, 50)),  # near boss chamber
        ],
        # sanctum_halls: 60×40 — arcane crystal halls, cold blue-purple lights
        "sanctum_halls": [
            (5,  20, 2.0, MAGIC_COLOR),
            (12, 12, 1.8, MAGIC_COLOR),
            (12, 28, 1.8, MAGIC_COLOR),
            (24, 20, 2.2, MAGIC_COLOR),
            (36, 20, 2.2, MAGIC_COLOR),
            (46, 12, 1.8, MAGIC_COLOR),
            (46, 28, 1.8, MAGIC_COLOR),
            (54, 20, 2.0, MAGIC_COLOR),
        ],
        # throne_room: 50×36 — sovereign's chamber, dramatic gold/white lights
        "throne_room": [
            (5,  18, 2.0, GATE_COLOR),
            (14, 10, 2.0, (255, 220, 120)),
            (14, 26, 2.0, (255, 220, 120)),
            (25, 18, 2.5, (255, 240, 180)),  # centre of arena
            (36, 10, 2.0, (255, 220, 120)),
            (36, 26, 2.0, (255, 220, 120)),
            (44, 18, 2.2, GATE_COLOR),
        ],
    }
    for tx, ty, radius, color in _FALLBACK.get(map_name, []):
        lights.append(PointLight(tx + 0.5, ty + 0.5, radius, color, 0.8, flicker=True))

    return lights
