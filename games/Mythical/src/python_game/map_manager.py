"""
Map manager — handles loading maps, transitions between them, and fade effects.
Each map dict can contain an "exits" field mapping (tile_x, tile_y) to
{"map": "map_name", "spawn": (x, y)}.
"""

import pygame


class MapManager:
    def __init__(
        self,
        viewport_width: int = 320,
        viewport_height: int = 240,
        *,
        supports_alpha: bool = True,
    ):
        self._maps: dict[str, dict] = {}
        self.current_name: str = ""
        self.current_data: dict | None = None

        # Transition state
        self.transitioning = False
        self.fade_alpha = 0
        self.fade_speed = 600  # alpha per second
        self.fade_in = False
        self.fade_out = False
        self.pending_map: str = ""
        self.pending_spawn: tuple[float, float] = (0, 0)
        self.supports_alpha = bool(supports_alpha)

        self._fade_surf = pygame.Surface((1, 1))
        self._ensure_fade_surface((viewport_width, viewport_height))

    def _ensure_fade_surface(self, size: tuple[int, int]) -> None:
        width = max(1, int(size[0]))
        height = max(1, int(size[1]))
        if self._fade_surf.get_size() == (width, height):
            return
        self._fade_surf = pygame.Surface((width, height))
        self._fade_surf.fill((0, 0, 0))

    def _render_quantized_fade(self, screen: pygame.Surface) -> None:
        coverage = max(0.0, min(1.0, self.fade_alpha / 255.0))
        if coverage <= 0.0:
            return
        if coverage >= 0.95:
            screen.fill((0, 0, 0))
            return

        width, height = screen.get_size()
        solid_rows = max(1, min(3, int(coverage * 4)))
        for y in range(height):
            if (y % 4) < solid_rows:
                pygame.draw.line(screen, (0, 0, 0), (0, y), (width, y))

    def register(self, name: str, map_data: dict):
        self._maps[name] = map_data

    def load(self, name: str) -> dict:
        self.current_name = name
        self.current_data = self._maps[name]
        return self.current_data

    def check_exit(self, tile_x: float, tile_y: float) -> dict | None:
        """Check if a position is on an exit tile. Returns exit info or None."""
        if not self.current_data:
            return None
        exits = self.current_data.get("exits", {})
        tx, ty = int(tile_x + 0.5), int(tile_y + 0.5)
        return exits.get((tx, ty))

    def start_transition(self, map_name: str, spawn: tuple[float, float]):
        """Begin a fade-out -> load -> fade-in transition."""
        if self.transitioning:
            return
        self.transitioning = True
        self.fade_out = True
        self.fade_in = False
        self.fade_alpha = 0
        self.pending_map = map_name
        self.pending_spawn = spawn

    def update(self, dt: float) -> dict | None:
        """Update transition. Returns {"map": name, "spawn": (x,y)} when map should swap."""
        if not self.transitioning:
            return None

        result = None

        if self.fade_out:
            self.fade_alpha += self.fade_speed * dt
            if self.fade_alpha >= 255:
                self.fade_alpha = 255
                self.fade_out = False
                self.fade_in = True
                # Signal to swap map NOW (screen is fully black)
                result = {"map": self.pending_map, "spawn": self.pending_spawn}

        elif self.fade_in:
            self.fade_alpha -= self.fade_speed * dt
            if self.fade_alpha <= 0:
                self.fade_alpha = 0
                self.fade_in = False
                self.transitioning = False

        return result

    def render_fade(self, screen: pygame.Surface):
        """Draw fade overlay if transitioning."""
        if self.transitioning and self.fade_alpha > 0:
            self._ensure_fade_surface(screen.get_size())
            if self.supports_alpha:
                self._fade_surf.set_alpha(int(self.fade_alpha))
                screen.blit(self._fade_surf, (0, 0))
            else:
                self._render_quantized_fade(screen)
