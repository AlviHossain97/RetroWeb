"""Reusable tile-based A* pathfinding and tile-line checks."""
from __future__ import annotations

from heapq import heappop, heappush


Tile = tuple[int, int]


def quantize_tile(x: float | int, y: float | int) -> Tile:
    return int(float(x) + 0.5), int(float(y) + 0.5)


def manhattan(a: Tile, b: Tile) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def neighbors4(tile: Tile) -> list[Tile]:
    x, y = tile
    return [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]


def is_walkable(tilemap, tile: Tile, blockers: set[Tile] | None = None, goal: Tile | None = None) -> bool:
    if goal is not None and tile == goal:
        return True
    if blockers and tile in blockers:
        return False
    return not tilemap.is_solid(tile[0], tile[1])


def reconstruct_path(came_from: dict[Tile, Tile], current: Tile) -> list[Tile]:
    path = [current]
    while current in came_from:
        current = came_from[current]
        path.append(current)
    path.reverse()
    return path


def find_path(
    tilemap,
    start: Tile,
    goal: Tile,
    blockers: set[Tile] | None = None,
    max_nodes: int = 1024,
) -> list[Tile]:
    """Return a tile path including start and goal, or [] if unreachable."""
    if start == goal:
        return [start]
    if not is_walkable(tilemap, start, blockers, goal=start):
        return []
    if not is_walkable(tilemap, goal, blockers, goal=goal):
        return []

    frontier: list[tuple[int, int, Tile]] = []
    heappush(frontier, (manhattan(start, goal), 0, start))
    came_from: dict[Tile, Tile] = {}
    g_score: dict[Tile, int] = {start: 0}
    visited = 0

    while frontier and visited < max_nodes:
        _, cost, current = heappop(frontier)
        visited += 1
        if current == goal:
            return reconstruct_path(came_from, current)
        for nxt in neighbors4(current):
            if not is_walkable(tilemap, nxt, blockers, goal=goal):
                continue
            new_cost = cost + 1
            if new_cost >= g_score.get(nxt, 1_000_000):
                continue
            g_score[nxt] = new_cost
            came_from[nxt] = current
            priority = new_cost + manhattan(nxt, goal)
            heappush(frontier, (priority, new_cost, nxt))
    return []


def has_line_of_sight(tilemap, start: Tile, goal: Tile, blockers: set[Tile] | None = None) -> bool:
    """Bresenham-like tile line check that respects solids and optional blockers."""
    x0, y0 = start
    x1, y1 = goal
    dx = abs(x1 - x0)
    dy = abs(y1 - y0)
    sx = 1 if x1 > x0 else -1
    sy = 1 if y1 > y0 else -1
    err = dx - dy
    cx, cy = x0, y0

    while True:
        if (cx, cy) != start:
            if not is_walkable(tilemap, (cx, cy), blockers, goal=goal):
                return False
        if (cx, cy) == goal:
            return True
        e2 = err * 2
        if e2 > -dy:
            err -= dy
            cx += sx
        if e2 < dx:
            err += dx
            cy += sy
