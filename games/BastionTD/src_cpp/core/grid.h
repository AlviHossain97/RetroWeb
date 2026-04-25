#pragma once

#include "core/config.h"
#include "core/types.h"

struct Grid {
    Terrain tiles[cfg::GRID_H][cfg::GRID_W];
    Vec2 spawns[cfg::MAX_SPAWNS];
    int spawn_count = 0;
    Vec2 base_pos = {0.0f, 0.0f};

    void init();
    Terrain get(int tx, int ty) const;
    void set(int tx, int ty, Terrain t);
    bool in_bounds(int tx, int ty) const;
    bool is_buildable(int tx, int ty) const;
    bool is_passable(int tx, int ty) const;
};
