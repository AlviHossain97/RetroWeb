#include "core/pathfinding.h"

#include <cstring>

Path bfs(const Grid& grid, Vec2 start, Vec2 end) {
    Path result{};

    const int sx = static_cast<int>(start.x);
    const int sy = static_cast<int>(start.y);
    const int ex = static_cast<int>(end.x);
    const int ey = static_cast<int>(end.y);

    if (!grid.in_bounds(sx, sy) || !grid.in_bounds(ex, ey)) {
        return result;
    }

    struct Cell {
        int x;
        int y;
    };

#ifdef BASTION_GBA
    static bool visited[cfg::GRID_H][cfg::GRID_W] __attribute__((section(".sbss")));
    static Cell parent[cfg::GRID_H][cfg::GRID_W] __attribute__((section(".sbss")));
    static Cell queue[cfg::GRID_W * cfg::GRID_H] __attribute__((section(".sbss")));
    static Cell trace[cfg::MAX_PATH_LEN] __attribute__((section(".sbss")));
#else
    bool visited[cfg::GRID_H][cfg::GRID_W];
    Cell parent[cfg::GRID_H][cfg::GRID_W];
    Cell queue[cfg::GRID_W * cfg::GRID_H];
    Cell trace[cfg::MAX_PATH_LEN];
#endif

    std::memset(visited, 0, sizeof(visited));
    std::memset(parent, 0xFF, sizeof(parent));
    int head = 0;
    int tail = 0;

    queue[tail++] = {sx, sy};
    visited[sy][sx] = true;

    constexpr int kDx[4] = {0, 0, -1, 1};
    constexpr int kDy[4] = {-1, 1, 0, 0};

    bool found = false;
    while (head < tail) {
        const Cell cur = queue[head++];
        if (cur.x == ex && cur.y == ey) {
            found = true;
            break;
        }

        for (int dir = 0; dir < 4; ++dir) {
            const int nx = cur.x + kDx[dir];
            const int ny = cur.y + kDy[dir];
            if (!grid.in_bounds(nx, ny) || visited[ny][nx] || !grid.is_passable(nx, ny)) {
                continue;
            }
            visited[ny][nx] = true;
            parent[ny][nx] = cur;
            queue[tail++] = {nx, ny};
        }
    }

    if (!found) {
        return result;
    }

    int trace_len = 0;
    Cell current = {ex, ey};
    while (current.x != -1 && trace_len < cfg::MAX_PATH_LEN) {
        trace[trace_len++] = current;
        current = parent[current.y][current.x];
    }

    result.valid = true;
    result.length = trace_len;
    for (int i = 0; i < trace_len; ++i) {
        const Cell c = trace[trace_len - 1 - i];
        result.points[i] = {static_cast<float>(c.x), static_cast<float>(c.y)};
    }
    return result;
}
