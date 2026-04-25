"""
pathfinding.py - BFS pathfinding on the tile grid.

Provides a single public function that computes an ordered tile-coordinate path
from a spawn point to the base, respecting passable terrain types.
"""
from collections import deque

from settings import TERRAIN_EMPTY, TERRAIN_PATH, TERRAIN_SPAWN, TERRAIN_BASE

# Set of terrain types that BFS may traverse
_PASSABLE = {TERRAIN_EMPTY, TERRAIN_PATH, TERRAIN_SPAWN, TERRAIN_BASE}


def bfs(grid, start, end, grid_w, grid_h):
    """Breadth-first search on a 2D tile grid.

    Parameters
    ----------
    grid : list[list[int]]
        2D array indexed ``grid[row][col]`` containing terrain type integers.
    start : tuple[int, int]
        ``(tx, ty)`` of the starting tile (spawn).
    end : tuple[int, int]
        ``(tx, ty)`` of the destination tile (base).
    grid_w : int
        Number of columns in the grid.
    grid_h : int
        Number of rows in the grid.

    Returns
    -------
    list[tuple[int, int]] | None
        Ordered path from *start* to *end* inclusive (both endpoints), or
        ``None`` if no path exists. Movement is 4-directional only.
    """
    sx, sy = start
    ex, ey = end

    # Quick sanity: start or end out of bounds
    if not (0 <= sx < grid_w and 0 <= sy < grid_h):
        return None
    if not (0 <= ex < grid_w and 0 <= ey < grid_h):
        return None

    # Trivial case
    if start == end:
        return [start]

    # BFS
    visited = [[False] * grid_w for _ in range(grid_h)]
    visited[sy][sx] = True
    # Each queue entry: (x, y)
    queue = deque()
    queue.append((sx, sy))
    # Parent map for path reconstruction: (x,y) -> (px,py)
    parent = {(sx, sy): None}

    # 4-directional neighbours (right, left, down, up)
    directions = ((1, 0), (-1, 0), (0, 1), (0, -1))

    while queue:
        cx, cy = queue.popleft()

        for dx, dy in directions:
            nx, ny = cx + dx, cy + dy

            # Bounds check
            if nx < 0 or nx >= grid_w or ny < 0 or ny >= grid_h:
                continue

            # Already visited
            if visited[ny][nx]:
                continue

            # Passability check
            if grid[ny][nx] not in _PASSABLE:
                continue

            visited[ny][nx] = True
            parent[(nx, ny)] = (cx, cy)

            # Goal reached -- reconstruct
            if (nx, ny) == (ex, ey):
                path = []
                node = (nx, ny)
                while node is not None:
                    path.append(node)
                    node = parent[node]
                path.reverse()
                return path

            queue.append((nx, ny))

    # No path found
    return None
