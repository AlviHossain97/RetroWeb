"""
GBA compatibility layer - provides GBA-compatible implementations of desktop features.

This module acts as a bridge during the port, allowing:
1. Desktop simulation of GBA constraints (memory, colors, etc)
2. Gradual migration of entity systems to fixed-point
3. Asset validation against GBA limits
4. Performance profiling with GBA-like budgets
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Tuple

import pygame

from runtime.fixed_point import FixedVec2, FP_ONE, to_fixed, to_int
from runtime.memory_budget import MemoryBudget, MemoryTracker, get_tracker


@dataclass
class GBASprite:
    """GBA-style sprite entry (simulates OAM format)."""

    obj_id: int  # 0-127
    x: int  # Screen X (0-511)
    y: int  # Screen Y (0-255)
    tile_index: int  # Tile in VRAM
    palette_bank: int  # 0-15
    h_flip: bool = False
    v_flip: bool = False
    size: Tuple[int, int] = (32, 32)  # Width, height

    # GBA OAM format (for reference):
    # Attr 0: Y coordinate (8 bits), shape (2 bits), etc
    # Attr 1: X coordinate (9 bits), size (2 bits), flip bits
    # Attr 2: Tile index (10 bits), priority (2 bits), palette (4 bits)

    def to_oam_bytes(self) -> bytes:
        """Convert to GBA OAM format (6 bytes)."""
        attr0 = self.y & 0xFF
        shape = self._get_shape_bits()
        attr0 |= shape[0] << 14

        attr1 = self.x & 0x1FF
        attr1 |= shape[1] << 14
        if self.h_flip:
            attr1 |= 0x1000
        if self.v_flip:
            attr1 |= 0x2000

        attr2 = self.tile_index & 0x3FF
        attr2 |= (self.palette_bank & 0xF) << 12

        return bytes(
            [
                attr0 & 0xFF,
                (attr0 >> 8) & 0xFF,
                attr1 & 0xFF,
                (attr1 >> 8) & 0xFF,
                attr2 & 0xFF,
                (attr2 >> 8) & 0xFF,
            ]
        )

    def _get_shape_bits(self) -> Tuple[int, int]:
        """Get GBA shape/size bits for this sprite size."""
        # GBA sprite sizes:
        # Square: 8x8(0), 16x16(1), 32x32(2), 64x64(3)
        # Wide:   16x8(0), 32x8(1), 32x16(2), 64x32(3)
        # Tall:   8x16(0), 8x32(1), 16x32(2), 32x64(3)
        w, h = self.size
        if w == h:
            # Square
            size_map = {8: 0, 16: 1, 32: 2, 64: 3}
            return (0, size_map.get(w, 2))  # Default 32x32
        elif w > h:
            # Wide
            wide_map = {(16, 8): 0, (32, 8): 1, (32, 16): 2, (64, 32): 3}
            return (1, wide_map.get((w, h), 2))
        else:
            # Tall
            tall_map = {(8, 16): 0, (8, 32): 1, (16, 32): 2, (32, 64): 3}
            return (2, tall_map.get((w, h), 2))


class GBAOAMManager:
    """Manages the 128 hardware sprites on GBA."""

    MAX_SPRITES = 128

    def __init__(self):
        self.sprites: Dict[int, GBASprite] = {}
        self._next_obj_id = 0

    def allocate(
        self, x: int, y: int, tile_index: int, size: Tuple[int, int] = (32, 32)
    ) -> int | None:
        """Allocate a sprite entry. Returns obj_id or None if full."""
        if len(self.sprites) >= self.MAX_SPRITES:
            return None

        obj_id = self._next_obj_id
        while obj_id in self.sprites:
            obj_id = (obj_id + 1) % self.MAX_SPRITES

        self.sprites[obj_id] = GBASprite(
            obj_id=obj_id, x=x, y=y, tile_index=tile_index, palette_bank=0, size=size
        )
        return obj_id

    def update_position(self, obj_id: int, x: int, y: int) -> bool:
        """Update sprite position (called every frame)."""
        if obj_id not in self.sprites:
            return False
        self.sprites[obj_id].x = x & 0x1FF  # GBA uses 9 bits
        self.sprites[obj_id].y = y & 0xFF  # GBA uses 8 bits
        return True

    def free(self, obj_id: int) -> None:
        """Release a sprite entry."""
        self.sprites.pop(obj_id, None)

    def get_used_count(self) -> int:
        return len(self.sprites)

    def clear(self) -> None:
        self.sprites.clear()


class GBAEntity:
    """Base class for GBA-compatible entities using fixed-point positions."""

    # Subpixels per pixel (for sub-tile precision)
    SUBPIXELS = FP_ONE  # 256 subpixels per pixel

    def __init__(self, tile_x: float, tile_y: float):
        # Position in fixed-point (subpixels)
        self.pos = FixedVec2(tile_x, tile_y)
        self.vel = FixedVec2(0, 0, fixed=True)  # Pixels per frame, fixed-point

        # Sprite management
        self._oam_id: int | None = None
        self._oam_manager: GBAOAMManager | None = None

        # Animation
        self.anim_frame = 0
        self.anim_timer = 0
        self.anim_fps = 8

        # Screen position (updated each frame)
        self.screen_x = 0
        self.screen_y = 0

    @property
    def tile_x(self) -> int:
        """Current tile X (for collision, etc)."""
        return self.pos.xi // 32  # TILE_SIZE = 32

    @property
    def tile_y(self) -> int:
        """Current tile Y."""
        return self.pos.yi // 32

    @property
    def pixel_x(self) -> int:
        """Pixel X position (for rendering)."""
        return self.pos.xi

    @property
    def pixel_y(self) -> int:
        """Pixel Y position (for rendering)."""
        return self.pos.yi

    def move_to_tile(self, tx: int, ty: int) -> None:
        """Set position to tile center."""
        self.pos = FixedVec2(tx * 32 + 16, ty * 32 + 16)

    def set_velocity(self, vx: float, vy: float) -> None:
        """Set velocity in pixels per frame."""
        self.vel = FixedVec2(vx, vy, fixed=False)

    def update(self, dt_fixed: int) -> None:
        """Update position based on velocity.

        dt_fixed is in fixed-point (1.0 = FP_ONE).
        """
        # pos += vel * dt
        dx = (self.vel.x * dt_fixed) // FP_ONE
        dy = (self.vel.y * dt_fixed) // FP_ONE
        self.pos = FixedVec2(self.pos.x + dx, self.pos.y + dy, fixed=True)

        # Update animation
        self.anim_timer += 1
        if self.anim_timer >= (60 // self.anim_fps):
            self.anim_timer = 0
            self.anim_frame = (self.anim_frame + 1) % 4  # 4 frame anims

    def set_screen_position(
        self, camera_x: int, camera_y: int, screen_w: int, screen_h: int
    ) -> bool:
        """Convert world position to screen position. Returns True if on screen."""
        self.screen_x = self.pos.xi - camera_x
        self.screen_y = self.pos.yi - camera_y

        # Check if on screen (with margin for sprites that straddle edges)
        margin = 64
        return (
            -margin <= self.screen_x < screen_w + margin
            and -margin <= self.screen_y < screen_h + margin
        )

    def is_on_screen(self, screen_w: int, screen_h: int) -> bool:
        """Check if entity is visible on screen."""
        return 0 <= self.screen_x < screen_w and 0 <= self.screen_y < screen_h


class GBACompatMode:
    """Context manager to enable GBA compatibility constraints."""

    def __init__(self, enable_limits: bool = True, show_warnings: bool = True):
        self.enable_limits = enable_limits
        self.show_warnings = show_warnings
        self._original_env = os.environ.get("MYTHICAL_TARGET")
        self._tracker = get_tracker()

    def __enter__(self):
        os.environ["MYTHICAL_TARGET"] = "gba"
        if self.enable_limits:
            # Switch to GBA budget
            from runtime.memory_budget import set_budget

            set_budget("gba")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._original_env is None:
            os.environ.pop("MYTHICAL_TARGET", None)
        else:
            os.environ["MYTHICAL_TARGET"] = self._original_env

        # Print report if there were issues
        if self.show_warnings:
            report = self._tracker.report()
            if report["warnings"] > 0:
                print("GBA Compatibility Warnings:")
                for warning in self._tracker.get_warnings():
                    print(f"  - {warning}")

        return False


# Distance check optimized for GBA (no sqrt)
def gba_distance_check(x1: int, y1: int, x2: int, y2: int, radius: int) -> bool:
    """Quick distance check without sqrt (uses squared distance)."""
    dx = abs(x2 - x1)
    dy = abs(y2 - y1)

    # Early out for large distances
    if dx > radius or dy > radius:
        return False

    # Check squared distance
    return (dx * dx + dy * dy) <= (radius * radius)


# Circle collision for entities
def gba_circle_collision(x1: int, y1: int, r1: int, x2: int, y2: int, r2: int) -> bool:
    """Circle collision using integer math only."""
    dx = x2 - x1
    dy = y2 - y1
    distance_sq = dx * dx + dy * dy
    radius_sum = r1 + r2
    return distance_sq <= (radius_sum * radius_sum)


# Angle approximation (no atan2)
def gba_angle_approx(dx: int, dy: int) -> int:
    """Approximate angle for 8-directional facing (0-7).

    Returns direction index: 0=E, 1=NE, 2=N, 3=NW, 4=W, 5=SW, 6=S, 7=SE
    """
    ax = abs(dx)
    ay = abs(dy)

    if ax > ay * 2:
        # Mostly horizontal
        return 0 if dx > 0 else 4
    elif ay > ax * 2:
        # Mostly vertical
        return 6 if dy > 0 else 2
    elif dx > 0:
        return 7 if dy > 0 else 1
    else:
        return 5 if dy > 0 else 3


# Screen-space culling for GBA
def gba_cull_entities(
    entities: List[GBAEntity],
    camera_x: int,
    camera_y: int,
    screen_w: int,
    screen_h: int,
    max_visible: int = 128,
) -> List[GBAEntity]:
    """Cull entities to those visible on screen, limited by OAM."""
    visible = []

    for ent in entities:
        # Update screen position
        if ent.set_screen_position(camera_x, camera_y, screen_w, screen_h):
            visible.append(ent)

    # Sort by Y for proper sprite priority (GBA uses Y for OAM priority)
    visible.sort(key=lambda e: e.screen_y)

    # Limit to hardware capacity
    return visible[:max_visible]


# GBA-style palette reduction
def gba_quantize_surface(
    surface: pygame.Surface,
    max_colors: int = 16,
    transparent_color: Tuple[int, int, int] = (255, 0, 255),
) -> Tuple[pygame.Surface, List[Tuple[int, int, int]]]:
    """Quantize surface to GBA-compatible palette.

    Returns (quantized_surface, palette).
    """
    # Convert to RGB if needed
    if surface.get_flags() & pygame.SRCALPHA:
        rgb_surface = pygame.Surface(surface.get_size())
        rgb_surface.blit(surface, (0, 0))
    else:
        rgb_surface = surface.convert()

    # Simple median cut quantization (simplified)
    width, height = surface.get_size()
    colors: Dict[Tuple[int, int, int], int] = {}

    # Collect color frequencies
    for y in range(height):
        for x in range(width):
            r, g, b, *a = surface.get_at((x, y))
            if a and a[0] < 128:
                continue  # Skip transparent
            rgb = (r, g, b)
            colors[rgb] = colors.get(rgb, 0) + 1

    # Sort by frequency and take top colors
    sorted_colors = sorted(colors.items(), key=lambda x: -x[1])

    # Build palette (first color is transparent)
    palette = [transparent_color]
    for rgb, _ in sorted_colors[: max_colors - 1]:
        palette.append(rgb)

    # Pad palette
    while len(palette) < max_colors:
        palette.append((0, 0, 0))

    # Create quantized surface
    quantized = pygame.Surface((width, height), depth=8)
    quantized.set_palette([(0, 0, 0)] * 256)  # Initialize

    # Map pixels to palette indices
    color_to_idx = {rgb: i for i, rgb in enumerate(palette)}

    for y in range(height):
        for x in range(width):
            r, g, b, *a = surface.get_at((x, y))
            if a and a[0] < 128:
                quantized.set_at((x, y), 0)  # Transparent
            else:
                rgb = (r, g, b)
                idx = color_to_idx.get(rgb, 1)
                quantized.set_at((x, y), idx)

    return quantized, palette[:max_colors]


# Validation helpers
def validate_for_gba(surface: pygame.Surface, name: str = "") -> List[str]:
    """Check if a surface is GBA-compatible."""
    issues = []

    w, h = surface.get_size()

    # GBA sprite size limits
    valid_sizes = [
        (8, 8),
        (16, 16),
        (32, 32),
        (64, 64),
        (16, 8),
        (32, 8),
        (32, 16),
        (64, 32),
        (8, 16),
        (8, 32),
        (16, 32),
        (32, 64),
    ]

    if (w, h) not in valid_sizes:
        issues.append(f"{name}: Size {w}x{h} not valid GBA sprite size")

    # Check if too many colors
    if surface.get_bitsize() > 8:
        issues.append(f"{name}: {surface.get_bitsize()}-bit color, GBA uses 4-8 bit")

    return issues


# Integration helpers for gradual porting
class HybridEntity:
    """Entity that can switch between float and fixed-point modes."""

    def __init__(self, tile_x: float, tile_y: float):
        self._float_pos = [tile_x * 32, tile_y * 32]
        self._fixed_pos = FixedVec2(tile_x, tile_y)
        self._use_fixed = False

    @property
    def use_fixed_point(self) -> bool:
        return self._use_fixed

    @use_fixed_point.setter
    def use_fixed_point(self, value: bool):
        if value and not self._use_fixed:
            # Convert float to fixed
            self._fixed_pos = FixedVec2(self._float_pos[0], self._float_pos[1])
        elif not value and self._use_fixed:
            # Convert fixed to float
            self._float_pos = [self._fixed_pos.xf, self._fixed_pos.yf]
        self._use_fixed = value

    @property
    def x(self) -> float:
        if self._use_fixed:
            return self._fixed_pos.xf
        return self._float_pos[0]

    @x.setter
    def x(self, value: float):
        if self._use_fixed:
            self._fixed_pos = FixedVec2(value, self._fixed_pos.yf)
        else:
            self._float_pos[0] = value

    @property
    def y(self) -> float:
        if self._use_fixed:
            return self._fixed_pos.yf
        return self._float_pos[1]

    @y.setter
    def y(self, value: float):
        if self._use_fixed:
            self._fixed_pos = FixedVec2(self._fixed_pos.xf, value)
        else:
            self._float_pos[1] = value
