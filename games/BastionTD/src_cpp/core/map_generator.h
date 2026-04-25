#pragma once

#include "core/grid.h"
#include "core/pathfinding.h"

#include <cstdint>

struct MapData {
    Grid grid;
    Path paths[cfg::MAX_SPAWNS];
    int path_count = 0;
    bool valid = false;
};

void generate_map(uint32_t seed, MapData& out);
MapData generate_map(uint32_t seed = 0);
