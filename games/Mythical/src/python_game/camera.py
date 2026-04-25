"""
Camera — viewport that follows a target position (in tile coords).
Clamps to map bounds so you never see outside the map.
On GBA this maps to BG scroll register writes (REG_BGxHOFS / REG_BGxVOFS).
"""

from runtime.display_defaults import (
    DEFAULT_VIEWPORT_HEIGHT,
    DEFAULT_VIEWPORT_WIDTH,
)
from settings import TILE_SIZE


class Camera:
    def __init__(
        self,
        map_width_tiles: int,
        map_height_tiles: int,
        viewport_width: int = DEFAULT_VIEWPORT_WIDTH,
        viewport_height: int = DEFAULT_VIEWPORT_HEIGHT,
    ):
        self.map_w = map_width_tiles * TILE_SIZE
        self.map_h = map_height_tiles * TILE_SIZE
        self.viewport_width = viewport_width
        self.viewport_height = viewport_height
        # Pixel offset of the viewport's top-left corner
        self.x = 0.0
        self.y = 0.0

    def follow(self, target_tile_x: float, target_tile_y: float):
        """Center camera on a tile-coordinate target, clamped to map bounds."""
        # Convert target to pixel center
        tx = target_tile_x * TILE_SIZE + TILE_SIZE / 2
        ty = target_tile_y * TILE_SIZE + TILE_SIZE / 2

        # Center viewport on target
        self.x = tx - self.viewport_width / 2
        self.y = ty - self.viewport_height / 2

        # Clamp so we don't show outside the map
        self.x = max(0, min(self.x, self.map_w - self.viewport_width))
        self.y = max(0, min(self.y, self.map_h - self.viewport_height))

    def apply(self, world_px: float, world_py: float) -> tuple[int, int]:
        """Convert world pixel coords to screen pixel coords."""
        return int(world_px - self.x), int(world_py - self.y)

    @property
    def offset(self) -> tuple[int, int]:
        return int(self.x), int(self.y)
