"""Lightweight Dijkstra / influence helpers for tactical tile choice."""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass

from ai.pathfinding import Tile, has_line_of_sight, manhattan, neighbors4


@dataclass
class DistanceField:
    origin: Tile
    radius: int
    distances: dict[Tile, int]

    def distance_at(self, tile: Tile) -> int | None:
        return self.distances.get(tile)


class InfluenceMapCache:
    """Cache player-centered distance fields per map and tile."""

    def __init__(self):
        self._cache: dict[tuple[str, Tile, int], DistanceField] = {}
        self.last_field: DistanceField | None = None
        self.last_map: str = ""

    def invalidate(self, map_name: str | None = None):
        if map_name is None:
            self._cache.clear()
            self.last_field = None
            self.last_map = ""
            return
        dead_keys = [key for key in self._cache if key[0] == map_name]
        for key in dead_keys:
            del self._cache[key]
        if self.last_map == map_name:
            self.last_field = None
            self.last_map = ""

    def get_player_field(self, map_name: str, tilemap, player_tile: Tile, radius: int) -> DistanceField:
        key = (map_name, player_tile, int(radius))
        field = self._cache.get(key)
        if field is None:
            field = build_distance_field(tilemap, player_tile, int(radius))
            self._cache[key] = field
        self.last_field = field
        self.last_map = map_name
        return field


def build_distance_field(tilemap, origin: Tile, radius: int) -> DistanceField:
    distances: dict[Tile, int] = {origin: 0}
    queue = deque([origin])

    while queue:
        tile = queue.popleft()
        base_cost = distances[tile]
        if base_cost >= radius:
            continue
        for nxt in neighbors4(tile):
            if nxt in distances:
                continue
            if tilemap.is_solid(nxt[0], nxt[1]):
                continue
            distances[nxt] = base_cost + 1
            queue.append(nxt)

    return DistanceField(origin=origin, radius=radius, distances=distances)


def _open_neighbor_ratio(tilemap, tile: Tile) -> float:
    open_count = 0
    for nxt in neighbors4(tile):
        if not tilemap.is_solid(nxt[0], nxt[1]):
            open_count += 1
    return open_count / 4.0


def choose_tactical_tile(
    tilemap,
    actor_tile: Tile,
    player_tile: Tile,
    field: DistanceField,
    desired_range: float,
    search_radius: int,
    retreat: bool = False,
    pressure_bias: float = 1.0,
    flank_bias: float = 0.0,
    line_of_sight_bias: float = 0.0,
    retreat_bias: float = 1.0,
    current_tile_bonus: float = 0.15,
) -> tuple[Tile | None, dict[Tile, float]]:
    """
    Score candidate tiles using player distance, openness, and flanking bias.
    Returns the best desired tile and the per-tile scores for debug overlays.
    """
    scores: dict[Tile, float] = {}
    best_tile: Tile | None = None
    best_score = -1_000_000.0
    ax, ay = actor_tile

    for x in range(ax - search_radius, ax + search_radius + 1):
        for y in range(ay - search_radius, ay + search_radius + 1):
            tile = (x, y)
            if manhattan(actor_tile, tile) > search_radius:
                continue
            if tilemap.is_solid(x, y):
                continue
            player_dist = field.distance_at(tile)
            if player_dist is None:
                continue

            dx = player_tile[0] - x
            dy = player_tile[1] - y
            line_bonus = line_of_sight_bias if has_line_of_sight(tilemap, tile, player_tile) else -0.15
            flank_score = 0.0
            if dx != 0 and dy != 0:
                flank_score = flank_bias
            elif flank_bias:
                flank_score = flank_bias * 0.2

            range_error = abs(player_dist - desired_range)
            move_cost = manhattan(actor_tile, tile) * 0.14
            openness = _open_neighbor_ratio(tilemap, tile)

            score = 0.0
            score -= range_error * 1.8
            score -= move_cost
            score += line_bonus
            score += flank_score

            if retreat:
                score += player_dist * 0.45 * retreat_bias
                score += (1.0 - openness) * 0.25 * retreat_bias
            else:
                score += openness * 0.35 * pressure_bias
                score -= player_dist * 0.08

            if tile == actor_tile:
                score += current_tile_bonus

            scores[tile] = score
            if score > best_score:
                best_score = score
                best_tile = tile

    return best_tile, scores
