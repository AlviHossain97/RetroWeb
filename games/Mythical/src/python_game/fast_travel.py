"""
fast_travel.py — Unlockable waypoint system for world traversal.

Waypoints are scattered across maps and unlock when the player:
  • Physically walks over them, OR
  • Completes a specific quest stage that mentions the location.

Travel is free (no coin cost by default).
Waypoint types:
  "stone" — standing stone / monolith found in the world
  "camp"  — resting spot with a campfire (also enables cooking)
  "gate"  — magic gate (fast travel + teleport aesthetic)

Maps to waypoints: village has 2, dungeon has 2.
More can be added in content_registry without code changes.
"""

from __future__ import annotations
from typing import Optional
import pygame
import math
from game_math import point_distance, polar_offset, pulse01
from settings import TILE_SIZE, COLOR_ACCENT


# ─────────────────────────────────────────────────────────────────────────────
# WAYPOINT DEFINITIONS
# ─────────────────────────────────────────────────────────────────────────────

WAYPOINT_DEFS: dict[str, dict] = {
    "village_square": {
        "name": "Village Square",
        "map": "village",
        "tile_x": 17,
        "tile_y": 17,
        "wtype": "stone",
        "unlock_condition": "default",  # always starts unlocked
        "desc": "The central square of the village.",
    },
    "village_bridge": {
        "name": "River Bridge",
        "map": "village",
        "tile_x": 38,
        "tile_y": 17,
        "wtype": "stone",
        "unlock_condition": "explore",  # unlocked by walking near it
        "desc": "The bridge east of the village, crossing the river.",
    },
    "dungeon_entrance": {
        "name": "Cave Entrance",
        "map": "dungeon",
        "tile_x": 5,
        "tile_y": 3,
        "wtype": "camp",
        "unlock_condition": "explore",
        "desc": "Scout Mira's camp at the dungeon mouth. Campfire for cooking.",
    },
    "dungeon_crossroads": {
        "name": "Dungeon Crossroads",
        "map": "dungeon",
        "tile_x": 20,
        "tile_y": 15,
        "wtype": "gate",
        "unlock_condition": "explore",
        "desc": "A glowing archway deep in the dungeon. Ancient fast-travel magic.",
    },
    "ruins_approach": {
        "name": "Ruins Approach",
        "map": "ruins_approach",
        "tile_x": 2,
        "tile_y": 17,
        "wtype": "stone",
        "unlock_condition": "explore",
        "desc": "A shattered waystone at the edge of the battlefield.",
    },
    "ruins_depths": {
        "name": "Ruins Depths",
        "map": "ruins_depths",
        "tile_x": 2,
        "tile_y": 19,
        "wtype": "camp",
        "unlock_condition": "explore",
        "desc": "An old campfire inside the dark crypts. Safe for resting.",
    },
    "sanctum_halls": {
        "name": "Mythic Sanctum",
        "map": "sanctum_halls",
        "tile_x": 2,
        "tile_y": 19,
        "wtype": "gate",
        "unlock_condition": "explore",
        "desc": "A rift stone pulsing with mysterious cosmic energy.",
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# WAYPOINT OBJECT  (rendered in-world)
# ─────────────────────────────────────────────────────────────────────────────

ACTIVATE_RADIUS = 1.5  # tiles — auto-unlock when player walks this close


class FastTravelManager:
    """
    Manages all waypoints across maps.

    Usage:
      ftm = FastTravelManager()
      ftm.check_proximity(player_x, player_y, current_map)  # call each frame
      destinations = ftm.get_unlocked_for_map("village")    # for travel UI
      ftm.travel_to("dungeon_entrance")                      # returns travel data
    """

    def __init__(self):
        self.unlocked: set[str] = {"village_square"}  # default starting waypoint
        self._anim_timer = 0.0

    # ── Unlock logic ──────────────────────────────────────────────────

    def unlock(self, waypoint_id: str) -> bool:
        """Unlock a waypoint. Returns True if newly unlocked."""
        if waypoint_id not in WAYPOINT_DEFS:
            return False
        if waypoint_id not in self.unlocked:
            self.unlocked.add(waypoint_id)
            return True
        return False

    def unlock_by_quest_stage(self, quest_id: str, stage: int):
        """Called by QuestManager on stage advance to auto-unlock waypoints."""
        if quest_id == "main" and stage >= 4:
            self.unlock("village_bridge")
            self.unlock("dungeon_entrance")
        if quest_id == "main_s2" and stage >= 1:
            self.unlock("ruins_approach")
        if quest_id == "main_s2" and stage >= 2:
            self.unlock("ruins_depths")
        if quest_id == "main_s3" and stage >= 1:
            self.unlock("sanctum_halls")

    def check_proximity(self, px: float, py: float, map_name: str):
        """
        Call each frame. Auto-unlocks any waypoints the player walks near.
        Returns list of newly unlocked waypoint names (for notifications).
        """
        newly = []
        for wpid, wdef in WAYPOINT_DEFS.items():
            if wdef["map"] != map_name:
                continue
            if wpid in self.unlocked:
                continue
            if wdef.get("unlock_condition") != "explore":
                continue
            dx = px - wdef["tile_x"]
            dy = py - wdef["tile_y"]
            dist = point_distance(px, py, wdef["tile_x"], wdef["tile_y"])
            if dist <= ACTIVATE_RADIUS:
                self.unlocked.add(wpid)
                newly.append(wdef["name"])
        return newly

    def is_unlocked(self, waypoint_id: str) -> bool:
        return waypoint_id in self.unlocked

    # ── Travel ────────────────────────────────────────────────────────

    def get_unlocked_all(self) -> list[dict]:
        """All unlocked waypoints across all maps, for the travel screen."""
        result = []
        for wpid in sorted(self.unlocked):
            wdef = WAYPOINT_DEFS.get(wpid)
            if wdef:
                result.append({"id": wpid, **wdef})
        return result

    def get_unlocked_for_map(self, map_name: str) -> list[dict]:
        return [e for e in self.get_unlocked_all() if e["map"] == map_name]

    def travel_to(self, waypoint_id: str) -> Optional[dict]:
        """
        Return travel data dict for a waypoint, or None if not unlocked.
        Caller (gameplay) uses this to trigger a map transition.
        """
        if waypoint_id not in self.unlocked:
            return None
        wdef = WAYPOINT_DEFS.get(waypoint_id)
        if not wdef:
            return None
        return {
            "map": wdef["map"],
            "spawn": (wdef["tile_x"], wdef["tile_y"]),
            "name": wdef["name"],
        }

    def is_camp(self, waypoint_id: str) -> bool:
        """Camp-type waypoints enable cooking (station='cooking')."""
        wdef = WAYPOINT_DEFS.get(waypoint_id)
        return wdef and wdef.get("wtype") == "camp"

    # ── In-world rendering ────────────────────────────────────────────

    def update(self, dt: float):
        self._anim_timer += dt

    def render(self, screen: pygame.Surface, map_name: str, cam_x: int, cam_y: int):
        """Draw waypoint markers in the world for the current map."""
        T = TILE_SIZE
        for wpid, wdef in WAYPOINT_DEFS.items():
            if wdef["map"] != map_name:
                continue
            wx = int(wdef["tile_x"] * T) + T // 2 - cam_x
            wy = int(wdef["tile_y"] * T) + T // 2 - cam_y
            # Skip off-screen
            if not (-T <= wx <= screen.get_width() + T):
                continue

            unlocked = wpid in self.unlocked
            pulse = pulse01(self._anim_timer, 3.0)
            base_r = 6

            if wdef["wtype"] == "stone":
                color = (160, 200, 160) if unlocked else (80, 80, 90)
                # Standing stone shape
                pygame.draw.rect(screen, color, (wx - 4, wy - T // 2, 8, T // 2))
                # Glow if unlocked
                if unlocked:
                    glow_surf = pygame.Surface((T, T), pygame.SRCALPHA)
                    alpha = int(40 + 40 * pulse)
                    pygame.draw.circle(
                        glow_surf, (*color, alpha), (T // 2, T // 2), T // 2
                    )
                    screen.blit(glow_surf, (wx - T // 2, wy - T // 2))

            elif wdef["wtype"] == "camp":
                # Campfire glow
                color = (220, 120, 40) if unlocked else (80, 60, 40)
                r = int(base_r * (0.8 + 0.2 * pulse))
                pygame.draw.circle(screen, color, (wx, wy), r)
                if unlocked:
                    # Flame effect
                    flame_surf = pygame.Surface((T, T), pygame.SRCALPHA)
                    alpha = int(60 + 40 * pulse)
                    pygame.draw.circle(
                        flame_surf, (255, 160, 40, alpha), (T // 2, T // 2), T // 3
                    )
                    screen.blit(flame_surf, (wx - T // 2, wy - T // 2))

            elif wdef["wtype"] == "gate":
                # Magic gate — rotating ring
                color = (100, 140, 230) if unlocked else (50, 50, 80)
                angle = self._anim_timer * 1.5
                if unlocked:
                    for i in range(6):
                        a = angle + i * math.pi / 3
                        ox, oy = polar_offset(a, T * 0.4)
                        px_ = wx + int(ox)
                        py_ = wy + int(oy)
                        alpha = int(150 + 80 * math.sin(angle + i))
                        gsurf = pygame.Surface((8, 8), pygame.SRCALPHA)
                        pygame.draw.circle(gsurf, (*color, alpha), (4, 4), 4)
                        screen.blit(gsurf, (px_ - 4, py_ - 4))
                else:
                    pygame.draw.circle(screen, color, (wx, wy), 5, 1)

    # ── Serialisation ─────────────────────────────────────────────────

    def to_save(self) -> dict:
        return {"unlocked": list(self.unlocked)}

    @classmethod
    def from_save(cls, data: dict) -> "FastTravelManager":
        ftm = cls()
        ftm.unlocked = set(data.get("unlocked", ["village_square"]))
        return ftm
