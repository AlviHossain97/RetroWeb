"""
weather.py — Weather system with visual overlays and gameplay effects.

States: clear → cloudy → rain → storm | snow | fog
Transitions are probabilistic and driven by a zone-preference table.
Each state affects:
  • Visibility (fog/storm reduce camera-effective draw distance)
  • Player speed (snow slows movement)
  • Audio (rain/storm add ambient sound layer)
  • Lighting (overcast dims ambient light)
  • Particles (rain drops, snow flakes, fog wisps)
"""
from __future__ import annotations

import math
import random
from typing import Optional

import pygame

from runtime.display_defaults import (
    DEFAULT_VIEWPORT_HEIGHT,
    DEFAULT_VIEWPORT_WIDTH,
)
from runtime.frame_clock import get_time


# ─────────────────────────────────────────────────────────────────────────────
# WEATHER DEFINITIONS
# ─────────────────────────────────────────────────────────────────────────────

WEATHER_DEFS: dict[str, dict] = {
    "clear": {
        "label":           "Clear",
        "speed_mult":       1.0,
        "visibility_mult":  1.0,
        "ambient_mult":     1.0,
        "overlay_alpha":    0,
        "overlay_color":    (0, 0, 0),
        "particle_type":    None,
        "duration_range":   (60, 180),   # seconds
    },
    "cloudy": {
        "label":           "Cloudy",
        "speed_mult":       1.0,
        "visibility_mult":  0.9,
        "ambient_mult":     0.85,
        "overlay_alpha":    25,
        "overlay_color":    (10, 10, 20),
        "particle_type":    None,
        "duration_range":   (30, 90),
    },
    "rain": {
        "label":           "Rainy",
        "speed_mult":       1.0,
        "visibility_mult":  0.75,
        "ambient_mult":     0.70,
        "overlay_alpha":    40,
        "overlay_color":    (5, 10, 30),
        "particle_type":    "rain",
        "sfx":             "rain_ambient",
        "duration_range":   (20, 60),
    },
    "storm": {
        "label":           "Storm",
        "speed_mult":       0.92,
        "visibility_mult":  0.55,
        "ambient_mult":     0.55,
        "overlay_alpha":    65,
        "overlay_color":    (0, 0, 20),
        "particle_type":    "heavy_rain",
        "sfx":             "storm_ambient",
        "duration_range":   (15, 45),
    },
    "snow": {
        "label":           "Snowing",
        "speed_mult":       0.78,    # slow movement
        "visibility_mult":  0.80,
        "ambient_mult":     0.95,    # snow is bright
        "overlay_alpha":    15,
        "overlay_color":    (200, 210, 220),
        "particle_type":    "snow",
        "sfx":             "wind_ambient",
        "duration_range":   (30, 90),
    },
    "fog": {
        "label":           "Foggy",
        "speed_mult":       1.0,
        "visibility_mult":  0.50,
        "ambient_mult":     0.75,
        "overlay_alpha":    90,
        "overlay_color":    (140, 150, 160),
        "particle_type":    None,
        "duration_range":   (20, 50),
    },
}

# Zone-preferred weather (map_name → weighted list)
ZONE_WEATHER: dict[str, list[dict]] = {
    "village": [
        {"state": "clear",  "weight": 40},
        {"state": "cloudy", "weight": 30},
        {"state": "rain",   "weight": 20},
        {"state": "storm",  "weight": 5},
        {"state": "fog",    "weight": 5},
    ],
    "dungeon": [
        {"state": "clear",  "weight": 20},
        {"state": "cloudy", "weight": 25},
        {"state": "fog",    "weight": 35},
        {"state": "rain",   "weight": 15},
        {"state": "storm",  "weight": 5},
    ],
    "ruins_approach": [
        {"state": "fog",    "weight": 40},
        {"state": "cloudy", "weight": 30},
        {"state": "rain",   "weight": 20},
        {"state": "storm",  "weight": 10},
    ],
    "ruins_depths": [
        {"state": "fog",    "weight": 50},
        {"state": "clear",  "weight": 50},
    ],
    "sanctum_halls": [
        {"state": "snow",   "weight": 60},
        {"state": "fog",    "weight": 30},
        {"state": "storm",  "weight": 10},
    ],
    "throne_room": [
        {"state": "snow",   "weight": 40},
        {"state": "clear",  "weight": 60},
    ],
}

# Transition table: current → list of possible next states
TRANSITIONS: dict[str, list[str]] = {
    "clear":  ["clear", "cloudy"],
    "cloudy": ["clear", "cloudy", "rain", "fog"],
    "rain":   ["cloudy", "rain", "storm"],
    "storm":  ["rain", "cloudy"],
    "snow":   ["snow", "clear"],
    "fog":    ["clear", "cloudy", "fog"],
}


class WeatherParticle:
    __slots__ = ("x", "y", "vy", "vx", "life", "alive", "ptype")

    def __init__(self, ptype: str, viewport_width: int, viewport_height: int):
        self.ptype = ptype
        self.x = random.uniform(0, viewport_width)
        self.y = random.uniform(-10, 0)
        if ptype in ("rain", "heavy_rain"):
            self.vx = random.uniform(-20, -5)
            self.vy = random.uniform(300, 500) if ptype == "heavy_rain" else random.uniform(180, 280)
        else:  # snow
            self.vx = random.uniform(-15, 15)
            self.vy = random.uniform(40, 90)
        self.life = 1.0
        self.alive = True

    def update(self, dt: float, viewport_width: int, viewport_height: int):
        self.x += self.vx * dt
        self.y += self.vy * dt
        if self.y > viewport_height + 5 or self.x < -5 or self.x > viewport_width + 5:
            self.alive = False

    def render(self, screen: pygame.Surface):
        if not self.alive:
            return
        if self.ptype in ("rain", "heavy_rain"):
            length = 6 if self.ptype == "heavy_rain" else 4
            ex = int(self.x + self.vx * 0.03)
            ey = int(self.y + length)
            pygame.draw.line(screen, (120, 140, 180, 160),
                             (int(self.x), int(self.y)), (ex, ey), 1)
        else:
            pygame.draw.circle(screen, (230, 240, 250),
                               (int(self.x), int(self.y)), 2)


class WeatherSystem:
    """
    Manages the current weather state, transitions, and visual rendering.

    Lifecycle:
      weather = WeatherSystem(map_name)
      weather.update(dt)             # advance particles + timer
      weather.render(screen)         # overlay + particles
      speed_mult = weather.speed_mult  # gameplay modifier
    """

    MAX_PARTICLES = 200

    def __init__(
        self,
        map_name: str = "village",
        *,
        viewport_width: int = DEFAULT_VIEWPORT_WIDTH,
        viewport_height: int = DEFAULT_VIEWPORT_HEIGHT,
    ):
        self.map_name = map_name
        self.viewport_width = max(1, int(viewport_width))
        self.viewport_height = max(1, int(viewport_height))
        self.state = "clear"
        self._state_timer = 0.0
        self._transition_timer = 2.0  # seconds for blend
        self._transition_alpha = 0.0
        self._next_state: Optional[str] = None
        self._duration = self._pick_duration()
        self._particles: list[WeatherParticle] = []
        self._spawn_rate = 0.0
        self._spawn_accum = 0.0
        self._overlay_surf: Optional[pygame.Surface] = None

    def set_viewport_size(self, width: int, height: int) -> None:
        width = max(1, int(width))
        height = max(1, int(height))
        if (width, height) != (self.viewport_width, self.viewport_height):
            self.viewport_width = width
            self.viewport_height = height
            self._overlay_surf = None

    def _sync_viewport(self, screen: pygame.Surface) -> None:
        if screen is not None and hasattr(screen, "get_size"):
            self.set_viewport_size(*screen.get_size())

    # ─────────────────────────────────────────────────────────────────

    def set_map(self, map_name: str):
        self.map_name = map_name
        # Seed a zone-appropriate initial weather state on map change.
        zone_entries = ZONE_WEATHER.get(map_name, [])
        if zone_entries:
            total = sum(e["weight"] for e in zone_entries)
            r = random.uniform(0, total)
            cumulative = 0.0
            for entry in zone_entries:
                cumulative += entry["weight"]
                if r <= cumulative:
                    self.state = entry["state"]
                    break
            self._state_timer = 0.0
            self._duration = self._pick_duration()
            self._particles.clear()

    def force_state(self, state: str):
        """Force a specific weather state (e.g. from a weather ritual)."""
        if state in WEATHER_DEFS:
            self.state = state
            self._duration = self._pick_duration()
            self._state_timer = 0.0
            self._particles.clear()

    @property
    def definition(self) -> dict:
        return WEATHER_DEFS.get(self.state, WEATHER_DEFS["clear"])

    @property
    def speed_mult(self) -> float:
        return self.definition["speed_mult"]

    @property
    def visibility_mult(self) -> float:
        return self.definition["visibility_mult"]

    @property
    def ambient_mult(self) -> float:
        return self.definition["ambient_mult"]

    @property
    def is_raining(self) -> bool:
        return self.state in ("rain", "storm")

    @property
    def is_snowing(self) -> bool:
        return self.state == "snow"

    @property
    def current_sfx(self) -> Optional[str]:
        return self.definition.get("sfx")

    # ─────────────────────────────────────────────────────────────────

    def update(self, dt: float):
        self._state_timer += dt

        # Advance duration → transition to next weather
        if self._state_timer >= self._duration:
            self._state_timer = 0.0
            self._duration = self._pick_duration()
            next_s = self._pick_next_state()
            if next_s != self.state:
                self.state = next_s
                self._particles.clear()

        # Spawn particles
        ptype = self.definition.get("particle_type")
        if ptype:
            rate = {"rain": 40, "heavy_rain": 80, "snow": 25}.get(ptype, 0)
            self._spawn_accum += rate * dt
            while self._spawn_accum >= 1.0 and len(self._particles) < self.MAX_PARTICLES:
                self._particles.append(
                    WeatherParticle(ptype, self.viewport_width, self.viewport_height)
                )
                self._spawn_accum -= 1.0

        for p in self._particles:
            p.update(dt, self.viewport_width, self.viewport_height)
        self._particles = [p for p in self._particles if p.alive]

    def render(self, screen: pygame.Surface):
        self._sync_viewport(screen)
        overlay_alpha = self.definition["overlay_alpha"]
        overlay_color = self.definition["overlay_color"]

        # Tinted overlay (fog / storm / rain darkness)
        if overlay_alpha > 0:
            if self._overlay_surf is None or self._overlay_surf.get_size() != screen.get_size():
                self._overlay_surf = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
            self._overlay_surf.fill((*overlay_color, overlay_alpha))
            screen.blit(self._overlay_surf, (0, 0))

        # Particles
        for p in self._particles:
            p.render(screen)

        # Fog uses a separate layered wipe
        if self.state == "fog":
            self._render_fog(screen)

    def _render_fog(self, screen: pygame.Surface):
        """Rolling horizontal fog bands."""
        t = get_time()
        width, height = screen.get_size()
        fog_surf = pygame.Surface((width, height), pygame.SRCALPHA)
        for i in range(4):
            offset_x = int(math.sin(t * 0.2 + i * 1.5) * 60)
            offset_y = height // 5 * i + int(math.sin(t * 0.3 + i) * 20)
            alpha = random.randint(18, 35)
            color = (150, 160, 170, alpha)
            pygame.draw.ellipse(fog_surf, color,
                                (offset_x, offset_y, width + 80, 60))
        screen.blit(fog_surf, (0, 0))

    # ─────────────────────────────────────────────────────────────────

    def _pick_duration(self) -> float:
        d_range = self.definition.get("duration_range", (60, 120))
        return random.uniform(*d_range)

    def _pick_next_state(self) -> str:
        candidates = TRANSITIONS.get(self.state, ["clear"])
        zone_prefs = {e["state"]: e["weight"]
                      for e in ZONE_WEATHER.get(self.map_name, [])}
        # Weight candidates by zone preference; fallback to uniform
        weights = [max(1, zone_prefs.get(c, 10)) for c in candidates]
        total = sum(weights)
        r = random.uniform(0, total)
        cumulative = 0
        for c, w in zip(candidates, weights):
            cumulative += w
            if r <= cumulative:
                return c
        return candidates[-1]

    # ─────────────────────────────────────────────────────────────────

    def to_save(self) -> dict:
        return {"state": self.state, "timer": self._state_timer, "duration": self._duration}

    @classmethod
    def from_save(cls, data: dict, map_name: str = "village") -> "WeatherSystem":
        ws = cls(map_name)
        ws.state = data.get("state", "clear")
        ws._state_timer = float(data.get("timer", 0))
        ws._duration = float(data.get("duration", ws._pick_duration()))
        return ws
