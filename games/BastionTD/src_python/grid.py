"""
grid.py - Tile grid: terrain types, buildable queries, path storage, and rendering.

All game logic operates in tile coordinates. Pixel conversion happens only at render time.
"""
import math

import pygame

from settings import (
    TILE_SIZE,
    GRID_OFFSET_Y,
    TERRAIN_EMPTY,
    TERRAIN_PATH,
    TERRAIN_ROCK,
    TERRAIN_WATER,
    TERRAIN_TREE,
    TERRAIN_SPAWN,
    TERRAIN_BASE,
    TERRAIN_TOWER,
    COLOR_GRASS,
    COLOR_PATH,
    COLOR_ROCK,
    COLOR_WATER,
    COLOR_TREE,
    COLOR_SPAWN,
    COLOR_BASE,
    COLOR_WHITE,
)

# Pre-set of passable terrain types for quick lookup
_PASSABLE_TYPES = {TERRAIN_EMPTY, TERRAIN_PATH, TERRAIN_SPAWN, TERRAIN_BASE}


def _tile_hash(tx, ty):
    """Deterministic hash for a tile position used for seeded texture variation."""
    return ((tx * 374761393) ^ (ty * 668265263)) & 0xFFFFFFFF


class Grid:
    """Manages the 2D tile map and draws it each frame."""

    def __init__(self, width: int, height: int):
        self.w = width   # columns (24)
        self.h = height  # rows (12)
        self.tiles: list[list[int]] = [
            [TERRAIN_EMPTY] * width for _ in range(height)
        ]
        self.paths: dict[tuple[int, int], list[tuple[int, int]]] = {}
        self.spawns: list[tuple[int, int]] = []
        self.base: tuple[int, int] = (0, 0)

    # ------------------------------------------------------------------
    # Accessors
    # ------------------------------------------------------------------

    def get(self, tx: int, ty: int) -> int:
        """Return the terrain type at tile (tx, ty)."""
        return self.tiles[ty][tx]

    def set(self, tx: int, ty: int, terrain_type: int) -> None:
        """Set the terrain type at tile (tx, ty)."""
        self.tiles[ty][tx] = terrain_type

    def is_buildable(self, tx: int, ty: int) -> bool:
        """True only if the tile is TERRAIN_EMPTY (player can place a tower)."""
        if not self.in_bounds(tx, ty):
            return False
        return self.tiles[ty][tx] == TERRAIN_EMPTY

    def is_passable(self, tx: int, ty: int) -> bool:
        """True if terrain is EMPTY, PATH, SPAWN, or BASE."""
        if not self.in_bounds(tx, ty):
            return False
        return self.tiles[ty][tx] in _PASSABLE_TYPES

    def in_bounds(self, tx: int, ty: int) -> bool:
        """True if (tx, ty) is within the grid dimensions."""
        return 0 <= tx < self.w and 0 <= ty < self.h

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def render(self, screen: pygame.Surface, cam_x: int = 0, cam_y: int = 0,
               game_time: float = 0.0, assets=None) -> None:
        """Draw every tile, using sprites when available, primitives as fallback.

        Parameters
        ----------
        screen : pygame.Surface
            The main display surface.
        cam_x, cam_y : int
            Camera / screen-shake offsets in pixels.
        game_time : float
            Elapsed game time in seconds (used for water animation and pulsing).
        assets : AssetManager or None
            Sprite provider; if None, falls back to primitive rendering.
        """
        ts = TILE_SIZE
        oy = GRID_OFFSET_Y  # vertical pixel offset for the playable area

        for ty in range(self.h):
            for tx in range(self.w):
                terrain = self.tiles[ty][tx]
                px = tx * ts + cam_x
                py = ty * ts + oy + cam_y
                rect = pygame.Rect(px, py, ts, ts)

                tile_sprite = assets.get_tile_sprite(terrain, tx, ty) if assets else None

                if tile_sprite:
                    screen.blit(tile_sprite, (px, py))
                    # Draw details on top of the sprite base for certain terrain
                    if terrain == TERRAIN_ROCK:
                        self._draw_rock_detail(screen, rect, tx, ty)
                    elif terrain == TERRAIN_TREE:
                        # Use prop tree sprite if available, else primitive
                        tree_drawn = False
                        if assets:
                            # Use prop group 0 (large trees), vary by position
                            tree_spr = assets.get_prop_sprite(0, tx % 3)
                            if tree_spr:
                                tw, th = tree_spr.get_size()
                                scale_f = min(ts / tw, ts / th, 1.0)
                                stw = max(1, int(tw * scale_f))
                                sth = max(1, int(th * scale_f))
                                scaled_tree = pygame.transform.scale(tree_spr, (stw, sth))
                                screen.blit(scaled_tree, (px + (ts - stw) // 2, py + ts - sth))
                                tree_drawn = True
                        if not tree_drawn:
                            self._draw_tree_detail(screen, rect)
                    elif terrain == TERRAIN_SPAWN:
                        self._draw_spawn_overlay(screen, rect, game_time)
                    elif terrain == TERRAIN_BASE:
                        self._draw_base_overlay(screen, rect, game_time)
                else:
                    # Primitive fallback (no assets)
                    if terrain == TERRAIN_EMPTY or terrain == TERRAIN_TOWER:
                        self._draw_grass(screen, rect, tx, ty)
                    elif terrain == TERRAIN_PATH:
                        self._draw_path(screen, rect, tx, ty)
                    elif terrain == TERRAIN_ROCK:
                        self._draw_rock(screen, rect, tx, ty)
                    elif terrain == TERRAIN_WATER:
                        self._draw_water(screen, rect, tx, ty, game_time)
                    elif terrain == TERRAIN_TREE:
                        self._draw_tree(screen, rect, tx, ty)
                    elif terrain == TERRAIN_SPAWN:
                        self._draw_spawn(screen, rect, tx, ty, game_time)
                    elif terrain == TERRAIN_BASE:
                        self._draw_base(screen, rect, tx, ty, game_time)
                    else:
                        self._draw_grass(screen, rect, tx, ty)

        # Draw props (decorative sprites on empty tiles)
        if assets and hasattr(self, 'props'):
            for ptx, pty, group, variant in self.props:
                prop_sprite = assets.get_prop_sprite(group, variant)
                if prop_sprite:
                    ppx = ptx * ts + cam_x
                    ppy = pty * ts + oy + cam_y
                    pw, ph = prop_sprite.get_size()
                    # Scale prop to fit within tile, bottom-aligned
                    scale_factor = min(ts / pw, ts / ph, 1.5)
                    sw = max(1, int(pw * scale_factor))
                    sh = max(1, int(ph * scale_factor))
                    scaled = pygame.transform.scale(prop_sprite, (sw, sh))
                    # Center horizontally, align bottom to tile bottom
                    screen.blit(scaled, (ppx + (ts - sw) // 2, ppy + ts - sh))

    # ---- sprite overlay helpers ----------------------------------------

    @staticmethod
    def _draw_spawn_overlay(screen, rect, game_time):
        """Pulsing border over a sprite-rendered spawn tile (no text label)."""
        pulse = int(abs(math.sin(game_time * 3.0)) * 80)
        border_color = (min(220 + pulse // 3, 255), pulse // 4, pulse // 4, 120)
        overlay = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
        pygame.draw.rect(overlay, border_color, (0, 0, rect.w, rect.h), 2)
        screen.blit(overlay, (rect.x, rect.y))

    @staticmethod
    def _draw_base_overlay(screen, rect, game_time):
        """Pulsing glow over a sprite-rendered base tile (no text label)."""
        pulse = int(abs(math.sin(game_time * 2.0)) * 60)
        glow_color = (pulse, pulse, min(200 + pulse, 255), 100)
        overlay = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
        pygame.draw.rect(overlay, glow_color, (0, 0, rect.w, rect.h), 3)
        screen.blit(overlay, (rect.x, rect.y))

    # ---- detail renderers (drawn on top of sprite base) ----------------

    @staticmethod
    def _draw_rock_detail(screen, rect, tx, ty):
        """Dark rock patches on top of grass sprite."""
        dark = (80, 80, 90)
        h = _tile_hash(tx, ty)
        for i in range(2):
            seed = _tile_hash(tx + i * 3, ty + i * 5)
            dx = 6 + (seed % (TILE_SIZE - 16))
            seed >>= 8
            dy = 6 + (seed % (TILE_SIZE - 16))
            pygame.draw.circle(screen, dark, (rect.x + dx, rect.y + dy), 4 + (h >> (i * 4)) % 3)

    @staticmethod
    def _draw_tree_detail(screen, rect):
        """Trunk + canopy on top of grass sprite."""
        cx = rect.x + TILE_SIZE // 2
        cy = rect.y + TILE_SIZE // 2
        trunk_color = (90, 60, 30)
        trunk_rect = pygame.Rect(cx - 2, cy + 2, 4, TILE_SIZE // 2 - 4)
        screen.fill(trunk_color, trunk_rect)
        canopy_color = (20, 60, 20)
        pygame.draw.circle(screen, canopy_color, (cx, cy - 2), 9)

    # ---- Mythical-quality primitive tile renderers (sprites OFF) --------
    # Ported from the Mythical project's baked tile rendering system.
    # Uses seeded hash for deterministic per-tile variation.

    @staticmethod
    def _vary(color, h_val, amount=8):
        """Deterministic color variation using hash instead of random."""
        return tuple(max(0, min(255, c + (((h_val >> (i * 8)) & 0xFF) % (amount * 2 + 1)) - amount))
                     for i, c in enumerate(color))

    @staticmethod
    def _darken(color, amt=30):
        return tuple(max(0, c - amt) for c in color)

    @staticmethod
    def _lighten(color, amt=30):
        return tuple(min(255, c + amt) for c in color)

    @staticmethod
    def _draw_grass(screen, rect, tx, ty):
        """Rich textured grass with blades and variation patches."""
        T = TILE_SIZE
        x, y = rect.x, rect.y
        base = COLOR_GRASS
        h = _tile_hash(tx, ty)
        # Base fill with subtle variation
        var_color = Grid._vary(base, h, 10)
        screen.fill(var_color, rect)
        # Darker shade patches
        shade1 = Grid._darken(base, 8)
        for i in range(5):
            seed = _tile_hash(tx + i * 7, ty + i * 3)
            px = x + (seed % T)
            seed >>= 8
            py = y + (seed % T)
            pygame.draw.circle(screen, Grid._vary(shade1, seed, 5), (px, py), 2)
        # Grass blades — varied heights and lean
        shade2 = Grid._lighten(base, 18)
        shade3 = Grid._lighten(base, 10)
        for i in range(6):
            seed = _tile_hash(tx * 11 + i, ty * 13 + i)
            gx = x + 3 + (seed % (T - 6))
            seed >>= 8
            gy = y + 4 + (seed % (T - 6))
            seed >>= 4
            gc = shade2 if (seed & 1) else shade3
            blade_h = 3 + (seed >> 1) % 4
            lean = ((seed >> 4) % 3) - 1
            pygame.draw.line(screen, gc, (gx, gy), (gx + lean, gy - blade_h), 1)
        # Occasional pebble
        if (h >> 12) % 6 == 0:
            seed = _tile_hash(tx + 99, ty + 77)
            px = x + 5 + (seed % (T - 10))
            seed >>= 8
            py = y + 5 + (seed % (T - 10))
            pygame.draw.circle(screen, Grid._darken(base, 30), (px, py), 1)
        # Subtle inner edge shadow (vignette)
        edge = pygame.Surface((T, T), pygame.SRCALPHA)
        pygame.draw.rect(edge, (0, 0, 0, 14), (0, 0, T, T), 1)
        screen.blit(edge, (x, y))

    @staticmethod
    def _draw_path(screen, rect, tx, ty):
        """Dirt path with pebbles, crack marks, and depth."""
        T = TILE_SIZE
        x, y = rect.x, rect.y
        base = COLOR_PATH
        h = _tile_hash(tx, ty)
        screen.fill(Grid._vary(base, h, 10), rect)
        # Pebbles
        dark = Grid._darken(base, 15)
        for i in range(4):
            seed = _tile_hash(tx + i * 5, ty + i * 7)
            dx = x + 3 + (seed % (T - 6))
            seed >>= 8
            dy = y + 3 + (seed % (T - 6))
            r = 1 + (seed >> 16) % 2
            pygame.draw.circle(screen, Grid._vary(dark, seed, 8), (dx, dy), r)
        # Subtle crack mark
        if (h >> 8) % 4 == 0:
            seed = _tile_hash(tx + 33, ty + 44)
            cx = x + 4 + (seed % (T - 12))
            seed >>= 8
            cy = y + 4 + (seed % (T - 12))
            seed >>= 4
            cw = 3 + (seed % 5)
            ch = 1 + (seed >> 4) % 3
            pygame.draw.line(screen, Grid._darken(base, 25), (cx, cy), (cx + cw, cy + ch), 1)
        # Inner edge
        edge = pygame.Surface((T, T), pygame.SRCALPHA)
        pygame.draw.rect(edge, (0, 0, 0, 18), (0, 0, T, T), 1)
        screen.blit(edge, (x, y))

    @staticmethod
    def _draw_rock(screen, rect, tx, ty):
        """Cobblestone-style rock with irregular stones and depth shading."""
        T = TILE_SIZE
        x, y = rect.x, rect.y
        base = COLOR_ROCK
        h = _tile_hash(tx, ty)
        screen.fill(Grid._vary(base, h, 8), rect)
        dark = Grid._darken(base, 18)
        light = Grid._lighten(base, 12)
        # Cobblestone circles with beveled highlights
        for i in range(5):
            seed = _tile_hash(tx + i * 9, ty + i * 11)
            cx = x + 4 + (seed % (T - 8))
            seed >>= 8
            cy = y + 4 + (seed % (T - 8))
            cr = 3 + (seed >> 16) % 4
            sc = Grid._vary(light, seed, 8)
            pygame.draw.circle(screen, sc, (cx, cy), cr)
            pygame.draw.circle(screen, dark, (cx, cy), cr, 1)
            # Highlight dot
            pygame.draw.circle(screen, Grid._lighten(base, 25), (cx - 1, cy - 1), max(1, cr // 3))
        # Vignette
        edge = pygame.Surface((T, T), pygame.SRCALPHA)
        pygame.draw.rect(edge, (0, 0, 0, 22), (0, 0, T, T), 2)
        screen.blit(edge, (x, y))

    @staticmethod
    def _draw_water(screen, rect, tx, ty, game_time):
        """Deep water with ripple bands, highlights, and sparkle dots."""
        T = TILE_SIZE
        x, y = rect.x, rect.y
        base = COLOR_WATER
        screen.fill(base, rect)
        deep = Grid._darken(base, 18)
        # Dark ripple bands
        for wy in range(y + 2, y + T, 6):
            h = _tile_hash(tx, wy)
            pygame.draw.line(screen, Grid._vary(deep, h, 5), (x, wy), (x + T, wy), 1)
        # Highlight ripple lines (animated)
        wc = Grid._lighten(base, 30)
        offset = int(game_time * 20) % T
        w1 = y + (tx * 4 + ty * 9 + offset) % T
        pygame.draw.line(screen, wc, (x + 5, w1 % T + y), (x + T - 5, (w1 + 3) % T + y), 1)
        w2 = y + (tx * 7 + ty * 5 + T // 3 + offset) % T
        h2 = _tile_hash(tx + 55, ty + 66)
        pygame.draw.line(screen, Grid._vary(wc, h2, 12),
                         (x + 3, w2 % T + y), (x + T // 2 - 2, (w2 + 2) % T + y), 1)
        # Sparkle dot
        if (_tile_hash(tx + int(game_time * 3), ty) >> 4) % 5 == 0:
            seed = _tile_hash(tx + 88, ty + 99)
            sx = x + 4 + (seed % (T - 8))
            seed >>= 8
            sy = y + 4 + (seed % (T - 8))
            pygame.draw.circle(screen, (180, 210, 255), (sx, sy), 1)
        # Vignette
        edge = pygame.Surface((T, T), pygame.SRCALPHA)
        pygame.draw.rect(edge, (0, 0, 0, 20), (0, 0, T, T), 1)
        screen.blit(edge, (x, y))

    @staticmethod
    def _draw_tree(screen, rect, tx, ty):
        """Grass base with detailed tree — multi-layer canopy and textured trunk."""
        T = TILE_SIZE
        x, y = rect.x, rect.y
        h = _tile_hash(tx, ty)
        # Grass base
        screen.fill(Grid._vary(COLOR_GRASS, h, 8), rect)
        cx = x + T // 2
        cy = y + T // 2
        # Trunk with grain
        trunk = (90, 60, 30)
        trunk_dark = Grid._darken(trunk, 15)
        trunk_rect = pygame.Rect(cx - 3, cy + 1, 6, T // 2 - 2)
        screen.fill(trunk, trunk_rect)
        pygame.draw.line(screen, trunk_dark, (cx - 1, cy + 2), (cx - 1, cy + T // 2 - 3), 1)
        pygame.draw.line(screen, Grid._lighten(trunk, 10), (cx + 1, cy + 2), (cx + 1, cy + T // 2 - 3), 1)
        # Multi-layer canopy (shadow, main, highlight)
        canopy_shadow = (15, 45, 15)
        canopy_main = (25, 75, 30)
        canopy_light = (40, 100, 45)
        r = 9 + (h % 3)
        pygame.draw.circle(screen, canopy_shadow, (cx + 1, cy - 1), r)
        pygame.draw.circle(screen, canopy_main, (cx, cy - 2), r)
        pygame.draw.circle(screen, canopy_light, (cx - 2, cy - 4), r - 3)
        # Leaf texture dots
        for i in range(4):
            seed = _tile_hash(tx + i * 17, ty + i * 23)
            lx = cx - r + 3 + (seed % (r * 2 - 6))
            seed >>= 8
            ly = cy - r - 1 + (seed % (r * 2 - 4))
            pygame.draw.circle(screen, Grid._lighten(canopy_main, 15), (lx, ly), 1)

    @staticmethod
    def _draw_spawn(screen, rect, tx, ty, game_time):
        """Spawn tile: red-tinted dirt with pulsing glow border."""
        T = TILE_SIZE
        x, y = rect.x, rect.y
        base = (160, 80, 60)
        h = _tile_hash(tx, ty)
        screen.fill(Grid._vary(base, h, 8), rect)
        # Dirt texture
        for i in range(3):
            seed = _tile_hash(tx + i * 5, ty + i * 7)
            dx = x + 3 + (seed % (T - 6))
            seed >>= 8
            dy = y + 3 + (seed % (T - 6))
            pygame.draw.circle(screen, Grid._darken(base, 20), (dx, dy), 1)
        # Pulsing red glow border
        pulse = int(abs(math.sin(game_time * 3.0)) * 80)
        border_color = (min(220 + pulse // 3, 255), pulse // 4, pulse // 4)
        pygame.draw.rect(screen, border_color, rect, width=2)
        # Arrow indicator pointing right (toward path)
        mid_y = y + T // 2
        pygame.draw.polygon(screen, (255, 220, 220), [
            (x + T - 6, mid_y), (x + T - 12, mid_y - 4), (x + T - 12, mid_y + 4),
        ])

    @staticmethod
    def _draw_base(screen, rect, tx, ty, game_time):
        """Base tile: blue-tinted stone with pulsing shield glow."""
        T = TILE_SIZE
        x, y = rect.x, rect.y
        base = (50, 55, 140)
        h = _tile_hash(tx, ty)
        screen.fill(Grid._vary(base, h, 8), rect)
        # Stone texture
        dark = Grid._darken(base, 20)
        light = Grid._lighten(base, 12)
        mx, my = x + T // 2, y + T // 2
        pygame.draw.line(screen, dark, (x, my), (x + T, my), 1)
        pygame.draw.line(screen, dark, (mx, y), (mx, y + T), 1)
        pygame.draw.line(screen, light, (x + 2, my - 1), (mx - 2, my - 1), 1)
        # Pulsing glow
        pulse = int(abs(math.sin(game_time * 2.0)) * 60)
        glow = (min(base[0] + pulse, 255), min(base[1] + pulse, 255), min(base[2] + pulse + 40, 255))
        pygame.draw.rect(screen, glow, rect, width=3)
        # Shield icon
        cx, cy = x + T // 2, y + T // 2
        shield_color = (200, 210, 255)
        points = [(cx, cy - 7), (cx - 6, cy - 3), (cx - 5, cy + 4), (cx, cy + 7),
                  (cx + 5, cy + 4), (cx + 6, cy - 3)]
        pygame.draw.polygon(screen, shield_color, points, 1)
        pygame.draw.line(screen, shield_color, (cx, cy - 5), (cx, cy + 5), 1)
        pygame.draw.line(screen, shield_color, (cx - 4, cy), (cx + 4, cy), 1)
