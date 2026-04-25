#include "core/grid.h"

void Grid::init() {
    for (int y = 0; y < cfg::GRID_H; ++y) {
        for (int x = 0; x < cfg::GRID_W; ++x) {
            tiles[y][x] = Terrain::Empty;
        }
    }
    spawn_count = 0;
    base_pos = {0.0f, 0.0f};
}

Terrain Grid::get(int tx, int ty) const {
    if (!in_bounds(tx, ty)) {
        return Terrain::Rock;
    }
    return tiles[ty][tx];
}

void Grid::set(int tx, int ty, Terrain t) {
    if (in_bounds(tx, ty)) {
        tiles[ty][tx] = t;
    }
}

bool Grid::in_bounds(int tx, int ty) const {
    return tx >= 0 && tx < cfg::GRID_W && ty >= 0 && ty < cfg::GRID_H;
}

bool Grid::is_buildable(int tx, int ty) const {
    return in_bounds(tx, ty) && get(tx, ty) == Terrain::Empty;
}

bool Grid::is_passable(int tx, int ty) const {
    if (!in_bounds(tx, ty)) {
        return false;
    }
    const Terrain t = get(tx, ty);
    return t == Terrain::Empty || t == Terrain::Path || t == Terrain::Spawn || t == Terrain::Base;
}
