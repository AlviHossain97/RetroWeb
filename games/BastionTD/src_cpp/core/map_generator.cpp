#include "core/map_generator.h"

#include <cmath>
#include <cstdlib>

#ifndef BASTION_GBA
#include <random>
#endif

namespace {

uint32_t rng_state = 1;
uint32_t auto_seed_state = 0x1234ABCDu;

void rng_seed(uint32_t seed) {
    rng_state = seed == 0 ? 1 : seed;
}

uint32_t next_auto_seed() {
    auto_seed_state = auto_seed_state * 1664525u + 1013904223u;
    return auto_seed_state;
}

uint32_t rng_next() {
    rng_state ^= rng_state << 13;
    rng_state ^= rng_state >> 17;
    rng_state ^= rng_state << 5;
    return rng_state;
}

int rng_range(int lo, int hi) {
    return lo + static_cast<int>(rng_next() % static_cast<uint32_t>(hi - lo + 1));
}

void mark_path(Grid& grid, int tx, int ty) {
    if (grid.get(tx, ty) == Terrain::Empty) {
        grid.set(tx, ty, Terrain::Path);
    }
}

void carve_line(Grid& grid, int x0, int y0, int x1, int y1) {
    int x = x0;
    int y = y0;
    mark_path(grid, x, y);

    while (x != x1) {
        x += (x1 > x) ? 1 : -1;
        mark_path(grid, x, y);
    }

    while (y != y1) {
        y += (y1 > y) ? 1 : -1;
        mark_path(grid, x, y);
    }
}

Terrain pick_obstacle(const Grid& grid, int tx, int ty) {
    Terrain neighbors[4];
    int neighbor_count = 0;
    constexpr int kDx[4] = {-1, 1, 0, 0};
    constexpr int kDy[4] = {0, 0, -1, 1};
    for (int i = 0; i < 4; ++i) {
        const int nx = tx + kDx[i];
        const int ny = ty + kDy[i];
        if (!grid.in_bounds(nx, ny)) {
            continue;
        }
        const Terrain t = grid.get(nx, ny);
        if (t == Terrain::Rock || t == Terrain::Tree || t == Terrain::Water) {
            neighbors[neighbor_count++] = t;
        }
    }

    if (neighbor_count > 0 && rng_range(0, 99) < 70) {
        return neighbors[rng_range(0, neighbor_count - 1)];
    }

    const int roll = rng_range(0, 99);
    if (roll < 55) {
        return Terrain::Rock;
    }
    if (roll < 90) {
        return Terrain::Tree;
    }
    return Terrain::Water;
}

void fill_fallback_map(MapData& out) {
    out = MapData{};
    out.grid.init();
    out.grid.base_pos = {static_cast<float>(cfg::GRID_W - 1), static_cast<float>(cfg::GRID_H / 2)};
    out.grid.set(cfg::GRID_W - 1, cfg::GRID_H / 2, Terrain::Base);
    out.grid.spawn_count = 1;
    out.grid.spawns[0] = {0.0f, static_cast<float>(cfg::GRID_H / 2)};
    out.grid.set(0, cfg::GRID_H / 2, Terrain::Spawn);
    for (int x = 1; x < cfg::GRID_W - 1; ++x) {
        out.grid.set(x, cfg::GRID_H / 2, Terrain::Path);
    }
    out.paths[0] = bfs(out.grid, out.grid.spawns[0], out.grid.base_pos);
    out.path_count = 1;
    out.valid = out.paths[0].valid;
}

#ifdef BASTION_GBA
void carve_gba_route(Grid& grid, int spawn_y, int base_y) {
    const int bend_x1 = rng_range(3, cfg::GRID_W / 3);
    const int bend_x2 = rng_range(cfg::GRID_W / 2, cfg::GRID_W - 6);
    const int bend_y = rng_range(1, cfg::GRID_H - 2);

    carve_line(grid, 0, spawn_y, bend_x1, spawn_y);
    carve_line(grid, bend_x1, spawn_y, bend_x1, bend_y);
    carve_line(grid, bend_x1, bend_y, bend_x2, bend_y);
    carve_line(grid, bend_x2, bend_y, bend_x2, base_y);
    carve_line(grid, bend_x2, base_y, cfg::GRID_W - 1, base_y);
}

int count_non_empty_tiles(const Grid& grid) {
    int count = 0;
    for (int y = 0; y < cfg::GRID_H; ++y) {
        for (int x = 0; x < cfg::GRID_W; ++x) {
            if (grid.get(x, y) != Terrain::Empty) {
                ++count;
            }
        }
    }
    return count;
}

void place_gba_obstacles(Grid& grid) {
    const int used_tiles = count_non_empty_tiles(grid);
    const int target_budget = 88;
    int max_extra = target_budget - used_tiles;
    if (max_extra < 0) {
        max_extra = 0;
    }

    int empty_count = 0;
    for (int y = 0; y < cfg::GRID_H; ++y) {
        for (int x = 0; x < cfg::GRID_W; ++x) {
            if (grid.get(x, y) == Terrain::Empty) {
                ++empty_count;
            }
        }
    }

    int obstacle_target = rng_range(empty_count / 10, empty_count / 7);
    if (obstacle_target > max_extra) {
        obstacle_target = max_extra;
    }

    int placed = 0;
    for (int tries = 0; tries < obstacle_target * 5 && placed < obstacle_target; ++tries) {
        const int ox = rng_range(1, cfg::GRID_W - 2);
        const int oy = rng_range(0, cfg::GRID_H - 1);
        if (grid.get(ox, oy) != Terrain::Empty) {
            continue;
        }

        grid.set(ox, oy, pick_obstacle(grid, ox, oy));
        ++placed;
    }
}
#endif

} // namespace

void generate_map(uint32_t seed, MapData& out) {
    if (seed == 0) {
#ifdef BASTION_GBA
        seed = next_auto_seed();
#else
        seed = std::random_device{}();
#endif
    }
    rng_seed(seed);

#ifdef BASTION_GBA
    out = MapData{};
    out.grid.init();
    Grid& g = out.grid;

    const int base_y = rng_range(2, cfg::GRID_H - 3);
    g.base_pos = {static_cast<float>(cfg::GRID_W - 1), static_cast<float>(base_y)};
    g.set(cfg::GRID_W - 1, base_y, Terrain::Base);

    g.spawn_count = 1;
    const int spawn_y0 = rng_range(1, cfg::GRID_H - 2);
    g.spawns[0] = {0.0f, static_cast<float>(spawn_y0)};
    g.set(0, spawn_y0, Terrain::Spawn);

    if (rng_range(0, 1) == 1) {
        for (int tries = 0; tries < 16; ++tries) {
            const int spawn_y1 = rng_range(1, cfg::GRID_H - 2);
            if (std::abs(spawn_y1 - spawn_y0) >= 3) {
                g.spawn_count = 2;
                g.spawns[1] = {0.0f, static_cast<float>(spawn_y1)};
                g.set(0, spawn_y1, Terrain::Spawn);
                break;
            }
        }
    }

    for (int s = 0; s < g.spawn_count; ++s) {
        carve_gba_route(g, static_cast<int>(g.spawns[s].y), base_y);
    }

    place_gba_obstacles(g);

    out.path_count = g.spawn_count;
    for (int s = 0; s < g.spawn_count; ++s) {
        out.paths[s] = bfs(g, g.spawns[s], g.base_pos);
        if (!out.paths[s].valid) {
            fill_fallback_map(out);
            return;
        }
    }

    for (int s = 0; s < out.path_count; ++s) {
        for (int i = 0; i < out.paths[s].length; ++i) {
            const int px = static_cast<int>(out.paths[s].points[i].x);
            const int py = static_cast<int>(out.paths[s].points[i].y);
            mark_path(g, px, py);
        }
    }

    out.valid = true;
    return;
#else
    for (int attempt = 0; attempt < 200; ++attempt) {
        out = MapData{};
        out.grid.init();
        Grid& g = out.grid;

        const int base_y = rng_range(2, cfg::GRID_H - 3);
        g.base_pos = {static_cast<float>(cfg::GRID_W - 1), static_cast<float>(base_y)};
        g.set(cfg::GRID_W - 1, base_y, Terrain::Base);

        g.spawn_count = 1;
        const int spawn_y0 = rng_range(1, cfg::GRID_H - 2);
        g.spawns[0] = {0.0f, static_cast<float>(spawn_y0)};
        g.set(0, spawn_y0, Terrain::Spawn);

        if (rng_range(0, 1) == 1) {
            for (int tries = 0; tries < 32; ++tries) {
                const int spawn_y1 = rng_range(1, cfg::GRID_H - 2);
                if (std::abs(spawn_y1 - spawn_y0) >= 3) {
                    g.spawn_count = 2;
                    g.spawns[1] = {0.0f, static_cast<float>(spawn_y1)};
                    g.set(0, spawn_y1, Terrain::Spawn);
                    break;
                }
            }
        }

        int empty_count = 0;
        for (int y = 0; y < cfg::GRID_H; ++y) {
            for (int x = 0; x < cfg::GRID_W; ++x) {
                if (g.get(x, y) == Terrain::Empty) {
                    ++empty_count;
                }
            }
        }
        const int obstacle_target = rng_range(empty_count / 4, empty_count / 3);

        int placed = 0;
        for (int tries = 0; tries < obstacle_target * 4 && placed < obstacle_target; ++tries) {
            const int ox = rng_range(1, cfg::GRID_W - 2);
            const int oy = rng_range(0, cfg::GRID_H - 1);
            if (g.get(ox, oy) != Terrain::Empty) {
                continue;
            }

            const Terrain obstacle = pick_obstacle(g, ox, oy);
            g.set(ox, oy, obstacle);

            bool all_valid = true;
            for (int s = 0; s < g.spawn_count; ++s) {
                if (!bfs(g, g.spawns[s], g.base_pos).valid) {
                    all_valid = false;
                    break;
                }
            }
            if (!all_valid) {
                g.set(ox, oy, Terrain::Empty);
            } else {
                ++placed;
            }
        }

        out.path_count = g.spawn_count;
        bool success = true;
        for (int s = 0; s < g.spawn_count; ++s) {
            out.paths[s] = bfs(g, g.spawns[s], g.base_pos);
            if (!out.paths[s].valid) {
                success = false;
                break;
            }
        }
        if (!success) {
            continue;
        }

        for (int s = 0; s < out.path_count; ++s) {
            for (int i = 0; i < out.paths[s].length; ++i) {
                const int px = static_cast<int>(out.paths[s].points[i].x);
                const int py = static_cast<int>(out.paths[s].points[i].y);
                if (g.get(px, py) == Terrain::Empty) {
                    g.set(px, py, Terrain::Path);
                }
            }
        }

        out.valid = true;
        return;
    }

    fill_fallback_map(out);
#endif
}

MapData generate_map(uint32_t seed) {
    MapData out{};
    generate_map(seed, out);
    return out;
}
