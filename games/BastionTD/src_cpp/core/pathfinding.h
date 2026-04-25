#pragma once

#include "core/grid.h"

struct Path {
    Vec2 points[cfg::MAX_PATH_LEN];
    int length = 0;
    bool valid = false;
};

Path bfs(const Grid& grid, Vec2 start, Vec2 end);
