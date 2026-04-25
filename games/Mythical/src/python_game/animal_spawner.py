"""
animal_spawner.py — Zone-based animal spawning system.

Spawn zones are defined per map as named rectangular regions.  Each zone
has an animal roster and a max-count cap.  The spawner respects difficulty
(spawn rates and animal aggression), and persists dead animals via a killed-
animal ID set shared with the gameplay state.

Zone definitions live here and in the extended content_registry; the spawner
is owned by GameplayState, which calls spawn_for_map() on map load and
update() every frame.
"""
from __future__ import annotations

import random
from typing import Optional

from animal import Animal

# ─────────────────────────────────────────────────────────────────────────────
# ZONE DEFINITIONS  (map_name → list of zones)
# Each zone: name, tile rect (x1,y1,x2,y2), roster list, max_count, respawn_sec
# ─────────────────────────────────────────────────────────────────────────────

# Valid outdoor ground tiles (grass, dirt, sand, flowers, cobble)
HABITAT_TILES_LAND = {0, 1, 3, 10, 14, 15}
HABITAT_TILES_WATER = {4, 16}

ZONE_DEFS: dict[str, list[dict]] = {
    "village": [
        {
            "name": "village_forest",
            "rect": (1, 22, 15, 35),           # south-west forest area
            "roster": [
                {"atype": "deer",   "weight": 40},
                {"atype": "rabbit", "weight": 35},
                {"atype": "wolf",   "weight": 15},
                {"atype": "boar",   "weight": 10},
            ],
            "max_count": 8,
            "respawn_sec": 120,
            "allowed_tiles": HABITAT_TILES_LAND,
        },
        {
            "name": "village_plains",
            "rect": (1, 1, 20, 21),            # grassy open area north-west
            "roster": [
                {"atype": "rabbit", "weight": 60},
                {"atype": "deer",   "weight": 40},
            ],
            "max_count": 5,
            "respawn_sec": 90,
            "allowed_tiles": HABITAT_TILES_LAND,
        },
        {
            "name": "village_water",
            "rect": (34, 8, 42, 28),           # river area
            "roster": [
                {"atype": "fish", "weight": 100},
            ],
            "max_count": 4,
            "respawn_sec": 60,
            "allowed_tiles": HABITAT_TILES_WATER,
        },
    ],
    "dungeon": [
        {
            "name": "dungeon_path",
            "rect": (1, 1, 18, 12),            # forest path before the cave
            "roster": [
                {"atype": "deer",  "weight": 30},
                {"atype": "wolf",  "weight": 40},
                {"atype": "bear",  "weight": 30},
            ],
            "max_count": 5,
            "respawn_sec": 180,
            "allowed_tiles": HABITAT_TILES_LAND,
        },
    ],
    "ruins_approach": [
        {
            "name": "ruins_wilds",
            "rect": (1, 1, 30, 14),            # northern dead-grass area
            "roster": [
                {"atype": "wolf",  "weight": 40},
                {"atype": "boar",  "weight": 35},
                {"atype": "deer",  "weight": 25},
            ],
            "max_count": 6,
            "respawn_sec": 100,
            "allowed_tiles": HABITAT_TILES_LAND,
        },
        {
            "name": "ruins_south",
            "rect": (1, 23, 28, 34),           # southern grassy patches
            "roster": [
                {"atype": "deer",   "weight": 45},
                {"atype": "rabbit", "weight": 30},
                {"atype": "wolf",   "weight": 25},
            ],
            "max_count": 5,
            "respawn_sec": 90,
            "allowed_tiles": HABITAT_TILES_LAND,
        },
    ],
}

# Per-difficulty multipliers: Easy has more animals; Hard has fewer but wilder
DIFFICULTY_SPAWN_MULT: dict[str, float] = {
    "easy":   1.4,   # 40% more animals
    "normal": 1.0,
    "hard":   0.65,  # 35% fewer animals, but the ones that exist are more skittish
}


class AnimalSpawner:
    """
    Manages all living animals on the current map.

    Usage in GameplayState:
      self.animal_spawner = AnimalSpawner(difficulty_mode)
      animals = self.animal_spawner.spawn_for_map(map_name, killed_animals)

      # Each frame:
      self.animal_spawner.update(dt, player_x, player_y, tilemap)

      # Access live animals:
      for animal in self.animal_spawner.animals: ...
    """

    def __init__(self, difficulty_mode: str = "normal"):
        self.difficulty_mode = difficulty_mode
        self.animals: list[Animal] = []
        self._spawn_mult = DIFFICULTY_SPAWN_MULT.get(difficulty_mode, 1.0)
        self._zone_timers: dict[str, float] = {}   # zone_name → seconds until next trickle spawn
        self._zone_deficits: dict[str, int] = {}   # zone_name → animals killed awaiting respawn
        self._animal_zones: dict[str, str] = {}    # spawn_id → zone_name (for deficit tracking)
        self._current_map: str = ""
        self._killed_ids: set[str] = set()         # only truly persistent kills (named animals)
        self._next_id: int = 0  # for unique spawn IDs within a session

    # ─────────────────────────────────────────────────────────────────

    def spawn_for_map(self, map_name: str, killed_animal_ids: set[str],
                      tilemap=None) -> list[Animal]:
        """
        Populate animals for the given map from zone definitions.
        Animals whose spawn_id is in killed_animal_ids are skipped (persistent kills).
        Returns the list of alive animals.
        """
        self.animals.clear()
        self._current_map = map_name
        self._killed_ids = set(killed_animal_ids)
        self._zone_timers.clear()
        self._zone_deficits.clear()
        self._animal_zones.clear()
        self._tilemap = tilemap

        # Pre-compute reachable tiles for spawn validation
        self._reachable: set[tuple[int, int]] | None = None
        if tilemap:
            self._reachable = _flood_fill_reachable(tilemap)

        zones = ZONE_DEFS.get(map_name, [])
        for zone in zones:
            cap = max(1, int(zone["max_count"] * self._spawn_mult))
            self._fill_zone(zone, cap)
            self._zone_deficits[zone["name"]] = 0
            self._zone_timers[zone["name"]] = self._per_animal_interval(zone)

        return self.animals

    def _per_animal_interval(self, zone: dict) -> float:
        """Respawn interval per individual animal (smooth trickle rate)."""
        cap = max(1, int(zone["max_count"] * self._spawn_mult))
        return max(15.0, zone["respawn_sec"] / cap)

    def _fill_zone(self, zone: dict, cap: int):
        """Spawn animals in zone up to cap, respecting killed_ids and walkability."""
        rect = zone["rect"]
        roster = zone["roster"]
        existing_in_zone = sum(
            1 for a in self.animals if _in_rect(a.x, a.y, rect)
        )
        needed = cap - existing_in_zone
        if needed <= 0:
            return

        attempts_per_animal = 12  # avoid infinite loops on dense maps
        for _ in range(needed):
            atype = _weighted_choice(roster)
            if not atype:
                continue
            # Try several positions to find a valid walkable tile
            for _attempt in range(attempts_per_animal):
                tx, ty = _random_tile(rect)

                # Habitat check (ground tile type)
                if self._tilemap:
                    ground_id = self._tilemap.ground[int(ty)][int(tx)]
                    allowed_tiles = zone.get("allowed_tiles")
                    if allowed_tiles and ground_id not in allowed_tiles:
                        continue

                # Validate walkability and reachability
                if self._tilemap and not validate_spawn_tile(self._tilemap, tx, ty, self._reachable):
                    continue

                spawn_id = f"animal_{self._current_map}_{zone['name']}_{atype}_{self._next_id}"
                self._next_id += 1
                if spawn_id in self._killed_ids:
                    continue
                a = Animal(atype, tx, ty, spawn_id, self.difficulty_mode)
                self.animals.append(a)
                self._animal_zones[a.spawn_id] = zone["name"]
                break
            # If we couldn't place after attempts, skip this animal

    def _spawn_one_in_zone(self, zone: dict) -> bool:
        """Try to trickle-spawn a single animal in the zone. Returns True on success."""
        rect = zone["rect"]
        roster = zone["roster"]
        for _attempt in range(15):
            atype = _weighted_choice(roster)
            if not atype:
                return False
            tx, ty = _random_tile(rect)
            if self._tilemap:
                ground_id = self._tilemap.ground[int(ty)][int(tx)]
                allowed_tiles = zone.get("allowed_tiles")
                if allowed_tiles and ground_id not in allowed_tiles:
                    continue
            if self._tilemap and not validate_spawn_tile(self._tilemap, tx, ty, self._reachable):
                continue
            spawn_id = f"animal_{self._current_map}_{zone['name']}_{atype}_{self._next_id}"
            self._next_id += 1
            a = Animal(atype, tx, ty, spawn_id, self.difficulty_mode)
            self.animals.append(a)
            self._animal_zones[a.spawn_id] = zone["name"]
            return True
        return False

    # ─────────────────────────────────────────────────────────────────

    def update(
        self,
        dt: float,
        player_x: float,
        player_y: float,
        tilemap,
    ) -> list[Animal]:
        """
        Update all animals and handle death cleanup + zone respawns.
        Returns list of animals that dealt damage this frame (caller applies to player).
        """
        attackers: list[Animal] = []

        for animal in self.animals:
            hit = animal.update(dt, player_x, player_y, tilemap)
            if hit:
                attackers.append(animal)

        # Remove fully-dead animals (after fade); track deficit per zone
        dead = [a for a in self.animals if a.should_remove]
        for a in dead:
            zname = self._animal_zones.pop(a.spawn_id, None)
            if zname is not None:
                # Regular wildlife — increment zone deficit for smooth respawn
                self._zone_deficits[zname] = self._zone_deficits.get(zname, 0) + 1
            else:
                # Named / non-zone animal — persist kill across saves
                self._killed_ids.add(a.spawn_id)
        self.animals = [a for a in self.animals if not a.should_remove]

        # Trickle respawn: one animal per interval per zone
        zones = ZONE_DEFS.get(self._current_map, [])
        for zone in zones:
            zname = zone["name"]
            if self._zone_deficits.get(zname, 0) <= 0:
                continue
            interval = self._per_animal_interval(zone)
            self._zone_timers[zname] = self._zone_timers.get(zname, interval) - dt
            if self._zone_timers[zname] <= 0:
                self._zone_timers[zname] = interval
                if self._spawn_one_in_zone(zone):
                    self._zone_deficits[zname] = max(0, self._zone_deficits[zname] - 1)

        return attackers

    # ─────────────────────────────────────────────────────────────────

    def on_animal_killed(self, spawn_id: str):
        """Eagerly record a kill (called by gameplay when death is processed)."""
        self._killed_ids.add(spawn_id)

    def collect_killed_ids(self) -> set[str]:
        """Return the set of killed animal IDs for save persistence."""
        return set(self._killed_ids)

    def get_animal_at(self, tile_x: int, tile_y: int) -> Optional[Animal]:
        """Find a living animal at the given tile (for attack resolution)."""
        for a in self.animals:
            if not a.is_dead and abs(a.x - tile_x) < 0.7 and abs(a.y - tile_y) < 0.7:
                return a
        return None

    def get_animals_in_radius(self, cx: float, cy: float, radius: float) -> list[Animal]:
        """Used by attack hitbox resolution."""
        return [
            a for a in self.animals
            if not a.is_dead and a.dist_to(cx, cy) <= radius
        ]

    def render(self, screen, cam_x: int, cam_y: int):
        """Render all animals (sorted by y for basic depth)."""
        for animal in sorted(self.animals, key=lambda a: a.y):
            animal.render(screen, cam_x, cam_y)


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _weighted_choice(roster: list[dict]) -> Optional[str]:
    """Pick a random animal type from a weighted roster."""
    if not roster:
        return None
    total = sum(e["weight"] for e in roster)
    r = random.uniform(0, total)
    cumulative = 0
    for entry in roster:
        cumulative += entry["weight"]
        if r <= cumulative:
            return entry["atype"]
    return roster[-1]["atype"]


def _random_tile(rect: tuple) -> tuple[float, float]:
    """Random tile coordinate within the given rect (x1,y1,x2,y2)."""
    x1, y1, x2, y2 = rect
    return (
        random.uniform(float(x1), float(x2)),
        random.uniform(float(y1), float(y2)),
    )


def _in_rect(x: float, y: float, rect: tuple) -> bool:
    x1, y1, x2, y2 = rect
    return x1 <= x <= x2 and y1 <= y <= y2


def _flood_fill_reachable(tilemap) -> set[tuple[int, int]]:
    """Flood-fill from all player spawn points to find walkable reachable tiles.
    Falls back to starting from first walkable tile if no spawns defined."""
    # Find seed tiles: try player spawn, else first passable tile
    seeds: list[tuple[int, int]] = []
    spawns = getattr(tilemap, 'spawns', {})
    if 'player' in spawns:
        px, py = spawns['player']
        seeds.append((int(px), int(py)))
    if not seeds:
        # Fallback: find first passable tile
        for row in range(tilemap.height):
            for col in range(tilemap.width):
                if not tilemap.is_solid(col, row):
                    seeds.append((col, row))
                    break
            if seeds:
                break
    if not seeds:
        return set()

    visited: set[tuple[int, int]] = set()
    stack = list(seeds)
    while stack:
        cx, cy = stack.pop()
        if (cx, cy) in visited:
            continue
        if cx < 0 or cy < 0 or cx >= tilemap.width or cy >= tilemap.height:
            continue
        if tilemap.is_solid(cx, cy):
            continue
        visited.add((cx, cy))
        stack.extend([(cx+1, cy), (cx-1, cy), (cx, cy+1), (cx, cy-1)])
    return visited


def validate_spawn_tile(tilemap, tx: float, ty: float,
                        reachable: set[tuple[int, int]] | None = None,
                        allowed_ground_ids: set[int] | None = None) -> bool:
    """Check if a tile is valid for animal spawning."""
    tile_x, tile_y = int(tx + 0.5), int(ty + 0.5)

    if not tilemap.is_passable(tx, ty):
        return False
        
    if allowed_ground_ids:
        # Check if the tile is within map bounds before checking ground array
        if tile_x < 0 or tile_y < 0 or tile_x >= tilemap.width or tile_y >= tilemap.height:
            return False
        ground_id = tilemap.ground[tile_y][tile_x]
        if ground_id not in allowed_ground_ids:
            return False

    if reachable is not None:
        if (tile_x, tile_y) not in reachable:
            return False
            
    return True
