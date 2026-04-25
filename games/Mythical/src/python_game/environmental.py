"""
environmental.py — Interactive environment elements.

Three classes of interactive objects:

1. FreezableTile  — water tile that a Mage ice attack can freeze into a
                    traversable ice platform for 8 seconds. Resets after
                    thaw. Visually: blue shimmer → white ice sheet.

2. ConductiveTile — metal floor/surface that becomes electrified for 5
                    seconds when hit by a Mage lightning ability OR combined
                    with water (wet surface + fire staff = steam hazard variant).
                    Enemies that walk on it take periodic damage; the player
                    with Shadow Cloak is immune (rubber soles perk).

3. DestructibleObject — barrel, crate, or boulder that can be broken by
                    melee attack or pushed into enemies (environmental kill).
                    On destruction: drops loot, clears the tile for pathfinding,
                    and triggers a boss-room collapse event if in the boss chamber.

Design notes:
  • All objects carry a tile_x / tile_y so the collision system can be patched.
  • Gameplay layer calls update() and resolves interactions.
  • Objects are per-map and saved/loaded in environmental_state within the save.
"""

from __future__ import annotations

import math
import random
from typing import Optional

import pygame

from runtime.frame_clock import get_time
from settings import TILE_SIZE


# ─────────────────────────────────────────────────────────────────────────────
# FREEZABLE WATER TILE
# ─────────────────────────────────────────────────────────────────────────────

FREEZE_DURATION = 8.0  # seconds before thaw
ICE_DAMAGE_BONUS = 1.5  # multiplier for attacks on frozen enemies


class FreezableTile:
    """
    Represents a water tile that can be frozen.
    When frozen, is_passable() returns True (players can walk over it).
    """

    def __init__(self, tile_x: int, tile_y: int, tile_id: str = "water"):
        self.tile_x = tile_x
        self.tile_y = tile_y
        self.tile_id = tile_id
        self.frozen = False
        self._freeze_timer = 0.0
        self._thaw_particles = False

    @property
    def is_passable(self) -> bool:
        return self.frozen

    def freeze(self):
        """Call when an ice/frost ability hits this tile."""
        self.frozen = True
        self._freeze_timer = FREEZE_DURATION
        self._thaw_particles = False

    def update(self, dt: float) -> bool:
        """Returns True if thawed this frame (particle event needed)."""
        if not self.frozen:
            return False
        self._freeze_timer -= dt
        if self._freeze_timer <= 1.5 and not self._thaw_particles:
            self._thaw_particles = True  # signal to gameplay to spawn steam
        if self._freeze_timer <= 0:
            self.frozen = False
            return True
        return False

    def render(self, screen: pygame.Surface, cam_x: int, cam_y: int):
        T = TILE_SIZE
        sx = self.tile_x * T - cam_x
        sy = self.tile_y * T - cam_y
        if not (-T <= sx <= screen.get_width() + T):
            return
        if self.frozen:
            # Draw ice overlay
            t = max(0.0, self._freeze_timer / FREEZE_DURATION)
            alpha = int(180 + 40 * t)
            ice_surf = pygame.Surface((T, T), pygame.SRCALPHA)
            ice_surf.fill((180, 220, 240, alpha))
            # Crack lines
            crack_col = (220, 240, 255, min(255, alpha + 40))
            for i in range(3):
                x1 = random.randint(4, T - 4)
                y1 = random.randint(4, T - 4)
                x2 = x1 + random.randint(-8, 8)
                y2 = y1 + random.randint(-8, 8)
                pygame.draw.line(ice_surf, crack_col, (x1, y1), (x2, y2), 1)
            screen.blit(ice_surf, (sx, sy))

            # Warning shimmer near thaw
            if self._thaw_particles:
                warn = pygame.Surface((T, T), pygame.SRCALPHA)
                pulse = abs(math.sin(get_time() * 5.0))
                warn.fill((200, 200, 100, int(60 * pulse)))
                screen.blit(warn, (sx, sy))

    def to_save(self) -> dict:
        return {
            "tx": self.tile_x,
            "ty": self.tile_y,
            "frozen": self.frozen,
            "timer": self._freeze_timer,
        }

    @classmethod
    def from_save(cls, data: dict) -> "FreezableTile":
        ft = cls(data["tx"], data["ty"])
        ft.frozen = data.get("frozen", False)
        ft._freeze_timer = float(data.get("timer", 0))
        return ft


# ─────────────────────────────────────────────────────────────────────────────
# CONDUCTIVE SURFACE
# ─────────────────────────────────────────────────────────────────────────────

ELECTRIFY_DURATION = 5.0
ELECTRIFY_DAMAGE_INTERVAL = 0.8  # seconds between damage ticks
ELECTRIFY_DAMAGE = 1


class ConductiveTile:
    """
    Metal floor that becomes electrified when struck by lightning/water combo.
    Damages entities standing on it; player immune with shadow_cloak.
    """

    def __init__(self, tile_x: int, tile_y: int):
        self.tile_x = tile_x
        self.tile_y = tile_y
        self.electrified = False
        self._timer = 0.0
        self._damage_accum = 0.0
        self._arc_phase = 0.0

    def electrify(self):
        self.electrified = True
        self._timer = ELECTRIFY_DURATION
        self._damage_accum = 0.0

    def update(self, dt: float) -> int:
        """
        Returns number of damage ticks that fired this frame.
        Caller applies ELECTRIFY_DAMAGE per tick to all entities on this tile.
        """
        if not self.electrified:
            return 0
        self._arc_phase += dt * 8
        self._timer -= dt
        if self._timer <= 0:
            self.electrified = False
            return 0
        self._damage_accum += dt
        ticks = 0
        while self._damage_accum >= ELECTRIFY_DAMAGE_INTERVAL:
            ticks += 1
            self._damage_accum -= ELECTRIFY_DAMAGE_INTERVAL
        return ticks

    def entity_on_tile(self, ex: float, ey: float) -> bool:
        return abs(ex - self.tile_x) < 0.6 and abs(ey - self.tile_y) < 0.6

    def render(self, screen: pygame.Surface, cam_x: int, cam_y: int):
        T = TILE_SIZE
        sx = self.tile_x * T - cam_x
        sy = self.tile_y * T - cam_y
        if not (-T <= sx <= screen.get_width() + T):
            return
        if not self.electrified:
            return
        t = max(0, self._timer / ELECTRIFY_DURATION)
        base_alpha = int(80 * t)
        arc_surf = pygame.Surface((T, T), pygame.SRCALPHA)
        arc_surf.fill((80, 160, 255, base_alpha))
        screen.blit(arc_surf, (sx, sy))
        # Electric arcs
        for i in range(4):
            a = self._arc_phase + i * math.pi / 2
            x1 = T // 2 + int(math.cos(a) * 6)
            y1 = T // 2 + int(math.sin(a) * 6)
            x2 = T // 2 + int(math.cos(a + 0.4) * 12)
            y2 = T // 2 + int(math.sin(a + 0.4) * 12)
            pygame.draw.line(arc_surf, (180, 220, 255, 200), (x1, y1), (x2, y2), 1)
        screen.blit(arc_surf, (sx, sy))

    def to_save(self) -> dict:
        return {
            "tx": self.tile_x,
            "ty": self.tile_y,
            "electrified": self.electrified,
            "timer": self._timer,
        }

    @classmethod
    def from_save(cls, data: dict) -> "ConductiveTile":
        ct = cls(data["tx"], data["ty"])
        ct.electrified = data.get("electrified", False)
        ct._timer = float(data.get("timer", 0))
        return ct


# ─────────────────────────────────────────────────────────────────────────────
# DESTRUCTIBLE OBJECT
# ─────────────────────────────────────────────────────────────────────────────

DESTRUCT_TYPES = {
    "barrel": {
        "hp": 2,
        "color": (120, 85, 45),
        "drops": [
            {"item_id": "raw_meat", "qty": 1, "chance": 0.3},
            {"item_id": "iron_ore", "qty": 1, "chance": 0.4},
        ],
    },
    "crate": {
        "hp": 2,
        "color": (140, 110, 65),
        "drops": [
            {"item_id": "forest_herbs", "qty": 2, "chance": 0.5},
            {"item_id": "bones", "qty": 1, "chance": 0.35},
        ],
    },
    "boulder": {
        "hp": 4,
        "color": (120, 118, 110),
        "drops": [
            {"item_id": "iron_ore", "qty": 2, "chance": 0.6},
            {"item_id": "crystal_shard", "qty": 1, "chance": 0.25},
        ],
    },
    "crystal": {
        "hp": 3,
        "color": (170, 140, 255),
        "drops": [
            {"item_id": "crystal_shard", "qty": 2, "chance": 0.7},
            {"item_id": "arcane_dust", "qty": 1, "chance": 0.4},
        ],
    },
}


class DestructibleObject:
    """
    An in-world object that can be broken, altering traversal and dropping loot.
    When destroyed, notifies gameplay via .destroyed = True so the tile can be
    cleared from the collision map.
    """

    def __init__(
        self,
        tile_x: int,
        tile_y: int,
        obj_type: str = "barrel",
        obj_id: Optional[str] = None,
    ):
        self.tile_x = tile_x
        self.tile_y = tile_y
        self.obj_type = obj_type
        self.obj_id = obj_id or f"{obj_type}_{tile_x}_{tile_y}"
        d = DESTRUCT_TYPES.get(obj_type, DESTRUCT_TYPES["barrel"])
        self.max_hp = d["hp"]
        self.hp = self.max_hp
        self.color = d["color"]
        self.drops = d["drops"]
        self.destroyed = False
        self._crack_alpha = 0.0
        self._death_timer = 0.0

    def take_damage(self, dmg: int = 1) -> bool:
        """Returns True if destroyed this hit."""
        if self.destroyed:
            return False
        self.hp -= dmg
        self._crack_alpha = 200.0
        if self.hp <= 0:
            self.hp = 0
            self.destroyed = True
            self._death_timer = 0.4
        return self.destroyed

    def get_drops(self) -> list[dict]:
        """Roll drops and return list of {item_id, qty}."""
        result = []
        for drop in self.drops:
            if random.random() < drop["chance"]:
                result.append({"item_id": drop["item_id"], "qty": drop["qty"]})
        return result

    def update(self, dt: float) -> bool:
        """Returns True when death animation is complete (safe to remove)."""
        self._crack_alpha = max(0, self._crack_alpha - 400 * dt)
        if self.destroyed and self._death_timer > 0:
            self._death_timer -= dt
            if self._death_timer <= 0:
                return True
        return False

    def render(self, screen: pygame.Surface, cam_x: int, cam_y: int):
        T = TILE_SIZE
        sx = self.tile_x * T - cam_x
        sy = self.tile_y * T - cam_y
        if not (-T <= sx <= screen.get_width() + T):
            return

        if self.destroyed:
            # Debris scatter
            t = max(0, self._death_timer / 0.4)
            for i in range(6):
                angle = i * math.pi / 3 + self._death_timer * 5
                dist = int((1 - t) * T * 0.6)
                px_ = sx + T // 2 + int(math.cos(angle) * dist)
                py_ = sy + T // 2 + int(math.sin(angle) * dist)
                sz = max(2, int(5 * t))
                col = (*self.color, int(255 * t))
                surf = pygame.Surface((sz * 2, sz * 2), pygame.SRCALPHA)
                pygame.draw.circle(surf, col, (sz, sz), sz)
                screen.blit(surf, (px_ - sz, py_ - sz))
            return

        # Base object
        obj_w = T * 3 // 5
        ox = sx + T // 2 - obj_w // 2
        oy = sy + T - obj_w - 2
        pygame.draw.rect(screen, self.color, (ox, oy, obj_w, obj_w), border_radius=3)
        dark = tuple(max(0, c - 30) for c in self.color)
        pygame.draw.rect(screen, dark, (ox, oy, obj_w, obj_w), 2, border_radius=3)

        # Crack overlay when damaged
        if self._crack_alpha > 0 and self.hp < self.max_hp:
            crack_surf = pygame.Surface((obj_w, obj_w), pygame.SRCALPHA)
            ca = int(self._crack_alpha)
            for i in range(3):
                x1 = random.randint(2, obj_w - 2)
                y1 = random.randint(2, obj_w - 2)
                pygame.draw.line(
                    crack_surf,
                    (30, 20, 10, ca),
                    (x1, y1),
                    (x1 + random.randint(-5, 5), y1 + random.randint(-5, 5)),
                    1,
                )
            screen.blit(crack_surf, (ox, oy))

        # HP indicator (visible when damaged)
        if self.hp < self.max_hp:
            ratio = self.hp / self.max_hp
            pygame.draw.rect(screen, (40, 15, 15), (ox, oy - 5, obj_w, 3))
            pygame.draw.rect(screen, (200, 80, 40), (ox, oy - 5, int(obj_w * ratio), 3))

    def to_save(self) -> dict:
        return {
            "id": self.obj_id,
            "tx": self.tile_x,
            "ty": self.tile_y,
            "type": self.obj_type,
            "hp": self.hp,
            "destroyed": self.destroyed,
        }

    @classmethod
    def from_save(cls, data: dict):
        d = cls(data["tx"], data["ty"], data.get("type", "barrel"), data.get("id"))
        d.hp = int(data.get("hp", d.max_hp))
        d.destroyed = bool(data.get("destroyed", False))
        return d


# ─────────────────────────────────────────────────────────────────────────────
# ENVIRONMENTAL MANAGER
# ─────────────────────────────────────────────────────────────────────────────


class EnvironmentalManager:
    """
    Owns all interactive env objects for the current map.
    Called by GameplayState every frame.
    """

    def __init__(self):
        self.freezable: list[FreezableTile] = []
        self.conductive: list[ConductiveTile] = []
        self.destructibles: list[DestructibleObject] = []
        self._pending_drops: list[dict] = []  # {tile_x, tile_y, item_id, qty}

    def load_for_map(self, map_name: str, defs: dict):
        """Populate from map-specific env definitions passed from gameplay."""
        self.freezable = [
            FreezableTile(d["tx"], d["ty"]) for d in defs.get("freezable", [])
        ]
        self.conductive = [
            ConductiveTile(d["tx"], d["ty"]) for d in defs.get("conductive", [])
        ]
        self.destructibles = [
            DestructibleObject(d["tx"], d["ty"], d.get("type", "barrel"), d.get("id"))
            for d in defs.get("destructibles", [])
        ]
        self._pending_drops.clear()

    def update(
        self, dt: float, entities_positions: list[tuple[float, float, bool]]
    ) -> list[dict]:
        """
        entities_positions: list of (x, y, player_has_rubber_soles)
        Returns list of {entity_idx, damage} for conductive damage events.
        Also populates self._pending_drops with destructible loot.
        """
        damage_events = []

        # Freezable thaws
        for ft in self.freezable:
            ft.update(dt)

        # Conductive damage
        for ct in self.conductive:
            ticks = ct.update(dt)
            if ticks > 0:
                for idx, (ex, ey, immune) in enumerate(entities_positions):
                    if not immune and ct.entity_on_tile(ex, ey):
                        for _ in range(ticks):
                            damage_events.append(
                                {"entity_idx": idx, "damage": ELECTRIFY_DAMAGE}
                            )

        # Destructible cleanup
        to_remove = []
        for obj in self.destructibles:
            done = obj.update(dt)
            if done and obj.destroyed:
                drops = obj.get_drops()
                for drop in drops:
                    self._pending_drops.append(
                        {"tile_x": obj.tile_x, "tile_y": obj.tile_y, **drop}
                    )
                to_remove.append(obj)
        for obj in to_remove:
            self.destructibles.remove(obj)

        return damage_events

    def collect_pending_drops(self) -> list[dict]:
        drops = list(self._pending_drops)
        self._pending_drops.clear()
        return drops

    def try_freeze_tile(self, tile_x: int, tile_y: int) -> bool:
        for ft in self.freezable:
            if ft.tile_x == tile_x and ft.tile_y == tile_y:
                ft.freeze()
                return True
        return False

    def try_electrify_tile(self, tile_x: int, tile_y: int) -> bool:
        for ct in self.conductive:
            if ct.tile_x == tile_x and ct.tile_y == tile_y:
                ct.electrify()
                return True
        return False

    def hit_destructible(
        self, tile_x: int, tile_y: int, dmg: int = 1
    ) -> Optional[DestructibleObject]:
        """Returns the object if it was struck, else None."""
        for obj in self.destructibles:
            if not obj.destroyed and obj.tile_x == tile_x and obj.tile_y == tile_y:
                obj.take_damage(dmg)
                return obj
        return None

    def get_passable_ice_tiles(self) -> set[tuple]:
        return {(ft.tile_x, ft.tile_y) for ft in self.freezable if ft.frozen}

    def render(self, screen: pygame.Surface, cam_x: int, cam_y: int):
        for ft in self.freezable:
            ft.render(screen, cam_x, cam_y)
        for ct in self.conductive:
            ct.render(screen, cam_x, cam_y)
        for obj in sorted(self.destructibles, key=lambda o: o.tile_y):
            obj.render(screen, cam_x, cam_y)
