#include "mythical/core/tilemap.hpp"

#include "mythical/core/maps.hpp"

namespace mythical {

bool is_tile_solid(TileKind t) {
    switch (t) {
        case TileKind::Tree:
        case TileKind::House:
        case TileKind::Wall:
        case TileKind::DungeonWall:
        case TileKind::Water:
        case TileKind::Lava:
        case TileKind::Stone:
            return true;
        default:
            return false;
    }
}

TileMap::TileMap() : width_(0), height_(0) {}

TileMap::TileMap(int width, int height, TileKind fill)
    : width_(width < 1 ? 1 : width),
      height_(height < 1 ? 1 : height),
      tiles_(static_cast<std::size_t>(width_) * height_, static_cast<unsigned char>(fill)) {}

int TileMap::width() const { return width_; }
int TileMap::height() const { return height_; }

bool TileMap::in_bounds(int x, int y) const {
    return x >= 0 && y >= 0 && x < width_ && y < height_;
}

TileKind TileMap::at(int x, int y) const {
    if (!in_bounds(x, y)) {
        return TileKind::Wall;
    }
    return static_cast<TileKind>(tiles_[static_cast<std::size_t>(y) * width_ + x]);
}

void TileMap::set(int x, int y, TileKind t) {
    if (!in_bounds(x, y)) return;
    tiles_[static_cast<std::size_t>(y) * width_ + x] = static_cast<unsigned char>(t);
}

bool TileMap::is_solid(int x, int y) const {
    if (!in_bounds(x, y)) return true;
    return is_tile_solid(at(x, y));
}

void TileMap::fill_rect(int x0, int y0, int x1, int y1, TileKind t) {
    for (int y = y0; y <= y1; ++y) {
        for (int x = x0; x <= x1; ++x) {
            set(x, y, t);
        }
    }
}

void TileMap::draw_rect(int x0, int y0, int x1, int y1, TileKind t) {
    for (int x = x0; x <= x1; ++x) {
        set(x, y0, t);
        set(x, y1, t);
    }
    for (int y = y0; y <= y1; ++y) {
        set(x0, y, t);
        set(x1, y, t);
    }
}

const std::vector<unsigned char>& TileMap::raw() const { return tiles_; }

namespace {

TileMap build_village() {
    TileMap m(50, 36, TileKind::Grass);
    // Ring of trees around edges.
    m.draw_rect(0, 0, 49, 35, TileKind::Tree);
    // Path down the middle.
    m.fill_rect(24, 1, 25, 34, TileKind::Path);
    // Small houses.
    m.fill_rect(8, 6, 13, 10, TileKind::House);
    m.set(10, 10, TileKind::HouseDoor);
    m.fill_rect(34, 6, 39, 10, TileKind::House);
    m.set(36, 10, TileKind::HouseDoor);
    m.fill_rect(8, 20, 13, 24, TileKind::House);
    m.set(10, 24, TileKind::HouseDoor);
    m.fill_rect(34, 20, 39, 24, TileKind::House);
    m.set(36, 24, TileKind::HouseDoor);
    // Chest in top-right corner.
    m.set(45, 4, TileKind::Chest);
    // Dungeon entrance door at bottom.
    m.set(24, 34, TileKind::Door);
    return m;
}

TileMap build_dungeon() {
    TileMap m(40, 40, TileKind::DungeonWall);
    // Carve rooms.
    m.fill_rect(2, 2, 17, 12, TileKind::DungeonFloor);
    m.fill_rect(22, 2, 37, 12, TileKind::DungeonFloor);
    m.fill_rect(2, 20, 17, 37, TileKind::DungeonFloor);
    m.fill_rect(22, 20, 37, 37, TileKind::DungeonFloor);
    // Corridors.
    m.fill_rect(17, 6, 22, 7, TileKind::DungeonFloor);
    m.fill_rect(17, 28, 22, 29, TileKind::DungeonFloor);
    m.fill_rect(9, 12, 10, 20, TileKind::DungeonFloor);
    m.fill_rect(29, 12, 30, 20, TileKind::DungeonFloor);
    // Boss chest.
    m.set(30, 30, TileKind::Chest);
    // Exit back to village.
    m.set(19, 2, TileKind::Door);
    return m;
}

TileMap build_ruins_approach() {
    TileMap m(50, 36, TileKind::Sand);
    m.draw_rect(0, 0, 49, 35, TileKind::Stone);
    m.fill_rect(10, 10, 40, 25, TileKind::RuinsFloor);
    m.draw_rect(10, 10, 40, 25, TileKind::Wall);
    m.set(25, 25, TileKind::Door);
    m.set(25, 1, TileKind::Door);
    return m;
}

TileMap build_ruins_depths() {
    TileMap m(60, 40, TileKind::Wall);
    m.fill_rect(2, 2, 57, 37, TileKind::RuinsFloor);
    m.draw_rect(2, 2, 57, 37, TileKind::Wall);
    m.fill_rect(10, 18, 50, 22, TileKind::RuinsFloor);
    m.set(58, 20, TileKind::Door);
    m.set(2, 20, TileKind::Door);
    return m;
}

TileMap build_sanctum_halls() {
    TileMap m(60, 40, TileKind::Floor);
    m.draw_rect(0, 0, 59, 39, TileKind::Wall);
    m.fill_rect(20, 15, 40, 25, TileKind::Floor);
    m.fill_rect(10, 5, 12, 35, TileKind::Wall);
    m.fill_rect(48, 5, 50, 35, TileKind::Wall);
    m.set(59, 20, TileKind::Door);
    m.set(0, 20, TileKind::Door);
    return m;
}

TileMap build_throne_room() {
    TileMap m(50, 36, TileKind::Floor);
    m.draw_rect(0, 0, 49, 35, TileKind::Wall);
    m.fill_rect(10, 5, 40, 30, TileKind::Floor);
    m.draw_rect(10, 5, 40, 30, TileKind::Wall);
    m.set(25, 5, TileKind::Door);
    m.set(25, 30, TileKind::Chest);
    return m;
}

}  // namespace

TileMap build_map(const std::string& map_id) {
    if (map_id == "village") return build_village();
    if (map_id == "dungeon") return build_dungeon();
    if (map_id == "ruins_approach") return build_ruins_approach();
    if (map_id == "ruins_depths") return build_ruins_depths();
    if (map_id == "sanctum_halls") return build_sanctum_halls();
    if (map_id == "throne_room") return build_throne_room();
    return TileMap(32, 24, TileKind::Grass);
}

}  // namespace mythical
