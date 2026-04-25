"""
map_generator.py - Procedural map generation with guaranteed solvable paths.

Generates a random grid with obstacles, spawn points, and a base, then validates
connectivity via BFS. Returns a fully populated Grid ready for gameplay.
"""
import random

from settings import (
    TERRAIN_EMPTY,
    TERRAIN_PATH,
    TERRAIN_ROCK,
    TERRAIN_WATER,
    TERRAIN_TREE,
    TERRAIN_SPAWN,
    TERRAIN_BASE,
)
from grid import Grid
from pathfinding import bfs


def generate_map(grid_w: int, grid_h: int):
    """Create a random, guaranteed-solvable map.

    Parameters
    ----------
    grid_w : int
        Number of tile columns (typically 24).
    grid_h : int
        Number of tile rows (typically 12).

    Returns
    -------
    tuple[Grid, dict, list, tuple]
        ``(grid, paths_dict, spawn_positions, base_position)``

        * *grid* -- fully populated :class:`Grid` with terrain set.
        * *paths_dict* -- ``{(sx,sy): [(tx,ty), ...]}`` BFS paths from each spawn.
        * *spawn_positions* -- list of ``(tx, ty)`` spawn tiles.
        * *base_position* -- ``(tx, ty)`` of the player base.
    """
    # Retry loop -- extremely unlikely to need more than one attempt given the
    # per-obstacle validation, but this guarantees we never return a broken map.
    for _attempt in range(200):
        result = _try_generate(grid_w, grid_h)
        if result is not None:
            return result
    # Absolute fallback: minimal obstacle-free map
    return _fallback_map(grid_w, grid_h)


# ------------------------------------------------------------------
# Internal helpers
# ------------------------------------------------------------------

def _try_generate(grid_w, grid_h):
    """Single generation attempt.  Returns result tuple or None on failure."""
    grid = Grid(grid_w, grid_h)

    # 1. Place base on right edge, random row 2-9
    base_y = random.randint(2, min(9, grid_h - 1))
    base_x = grid_w - 1  # column 23
    base_pos = (base_x, base_y)
    grid.set(base_x, base_y, TERRAIN_BASE)
    grid.base = base_pos

    # 2. Place 1-2 spawn points on left edge (column 0), rows at least 3 apart
    num_spawns = random.choice([1, 2])
    spawns = []
    if num_spawns == 1:
        sy = random.randint(1, grid_h - 2)
        spawns.append((0, sy))
    else:
        # Two spawns at least 3 rows apart
        for _try in range(100):
            s1 = random.randint(1, grid_h - 2)
            s2 = random.randint(1, grid_h - 2)
            if abs(s1 - s2) >= 3:
                spawns.append((0, s1))
                spawns.append((0, s2))
                break
        if not spawns:
            # Fall back to single spawn
            sy = random.randint(1, grid_h - 2)
            spawns.append((0, sy))

    for sp in spawns:
        grid.set(sp[0], sp[1], TERRAIN_SPAWN)
    grid.spawns = list(spawns)

    # 3. Scatter obstacles: 25-35 % of remaining empty tiles
    empty_tiles = [
        (tx, ty)
        for ty in range(grid_h)
        for tx in range(grid_w)
        if grid.get(tx, ty) == TERRAIN_EMPTY
    ]
    random.shuffle(empty_tiles)
    target_pct = random.uniform(0.25, 0.35)
    target_count = int(len(empty_tiles) * target_pct)

    # Helper to pick obstacle type with clustering tendency
    placed_obstacles = []  # [(tx, ty, type)]

    def _pick_obstacle_type(tx, ty):
        """Choose an obstacle type, biased toward neighbours of the same type
        so rocks cluster with rocks, trees with trees, water in patches."""
        # Check what obstacles are adjacent
        neighbour_types = []
        for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            nx, ny = tx + dx, ty + dy
            if 0 <= nx < grid_w and 0 <= ny < grid_h:
                t = grid.get(nx, ny)
                if t in (TERRAIN_ROCK, TERRAIN_TREE, TERRAIN_WATER):
                    neighbour_types.append(t)
        # If we have a neighbouring obstacle, 70 % chance to match it
        if neighbour_types and random.random() < 0.70:
            return random.choice(neighbour_types)
        # Water only spawns next to existing water — keeps it in clusters
        has_water_neighbour = TERRAIN_WATER in neighbour_types
        if has_water_neighbour and random.random() < 0.50:
            return TERRAIN_WATER
        # Base distribution: 55% rock, 35% tree, 10% water seed (starts a cluster)
        roll = random.random()
        if roll < 0.55:
            return TERRAIN_ROCK
        elif roll < 0.90:
            return TERRAIN_TREE
        else:
            return TERRAIN_WATER

    placed = 0
    for tx, ty in empty_tiles:
        if placed >= target_count:
            break

        obs_type = _pick_obstacle_type(tx, ty)
        grid.set(tx, ty, obs_type)

        # Validate: every spawn must still reach the base
        valid = True
        for sp in spawns:
            if bfs(grid.tiles, sp, base_pos, grid_w, grid_h) is None:
                valid = False
                break

        if not valid:
            # Revert
            grid.set(tx, ty, TERRAIN_EMPTY)
        else:
            placed_obstacles.append((tx, ty, obs_type))
            placed += 1

    # 4. Final BFS from each spawn to base, store paths
    paths_dict = {}
    all_ok = True
    for sp in spawns:
        path = bfs(grid.tiles, sp, base_pos, grid_w, grid_h)
        if path is None:
            all_ok = False
            break
        paths_dict[sp] = path

    if not all_ok:
        return None  # trigger retry

    # 5. Mark path tiles as TERRAIN_PATH (but keep spawn and base as-is)
    for sp, path in paths_dict.items():
        for tx, ty in path:
            if grid.get(tx, ty) == TERRAIN_EMPTY:
                grid.set(tx, ty, TERRAIN_PATH)

    grid.paths = paths_dict

    # 6. Remove isolated water tiles (no adjacent water → convert to rock)
    for ty in range(grid_h):
        for tx in range(grid_w):
            if grid.get(tx, ty) == TERRAIN_WATER:
                has_adj_water = False
                for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                    nx, ny = tx + dx, ty + dy
                    if 0 <= nx < grid_w and 0 <= ny < grid_h:
                        if grid.get(nx, ny) == TERRAIN_WATER:
                            has_adj_water = True
                            break
                if not has_adj_water:
                    grid.set(tx, ty, TERRAIN_ROCK)

    # 7. Scatter decorative props on empty non-path tiles
    _scatter_props(grid, grid_w, grid_h)

    return (grid, paths_dict, list(spawns), base_pos)


def _scatter_props(grid, grid_w, grid_h):
    """Place decorative props on TERRAIN_EMPTY tiles not adjacent to paths."""
    def _adjacent_to_path(tx, ty):
        for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            nx, ny = tx + dx, ty + dy
            if 0 <= nx < grid_w and 0 <= ny < grid_h:
                if grid.get(nx, ny) == TERRAIN_PATH:
                    return True
        return False

    candidates = [
        (tx, ty)
        for ty in range(grid_h)
        for tx in range(grid_w)
        if grid.get(tx, ty) == TERRAIN_EMPTY and not _adjacent_to_path(tx, ty)
    ]
    random.shuffle(candidates)
    count = min(len(candidates), 5)

    # Groups 0-1 are trees (used by TERRAIN_TREE rendering, not props).
    # Props use only medium objects (group 1) and small items (groups 2-4).
    prop_choices = [
        (1, 0), (1, 1), (1, 2),  # medium decorative objects
        (4, 0), (4, 1),          # small ground items
    ]

    grid.props = []
    for i in range(count):
        tx, ty = candidates[i]
        group, variant = random.choice(prop_choices)
        grid.props.append((tx, ty, group, variant))


def _fallback_map(grid_w, grid_h):
    """Ultra-safe fallback: no obstacles, single spawn, straight path."""
    grid = Grid(grid_w, grid_h)
    base_pos = (grid_w - 1, grid_h // 2)
    grid.set(base_pos[0], base_pos[1], TERRAIN_BASE)
    grid.base = base_pos

    spawn = (0, grid_h // 2)
    grid.set(spawn[0], spawn[1], TERRAIN_SPAWN)
    grid.spawns = [spawn]

    path = bfs(grid.tiles, spawn, base_pos, grid_w, grid_h)
    if path is None:
        # Should never happen on an empty grid, but be safe
        path = [(x, grid_h // 2) for x in range(grid_w)]

    for tx, ty in path:
        if grid.get(tx, ty) == TERRAIN_EMPTY:
            grid.set(tx, ty, TERRAIN_PATH)

    paths_dict = {spawn: path}
    grid.paths = paths_dict
    _scatter_props(grid, grid_w, grid_h)

    return (grid, paths_dict, [spawn], base_pos)
