#include "mythical/core/tilemap.hpp"

#include <cstdlib>
#include <iostream>

static void require(bool condition, const char* message) {
    if (!condition) {
        std::cerr << "FAIL: " << message << "\n";
        std::exit(1);
    }
}

int main() {
    using namespace mythical;

    TileMap m(10, 8, TileKind::Grass);
    require(m.width() == 10 && m.height() == 8, "size");
    require(m.at(0, 0) == TileKind::Grass, "default tile");
    require(!m.is_solid(0, 0), "grass not solid");

    m.set(5, 5, TileKind::Wall);
    require(m.at(5, 5) == TileKind::Wall, "set works");
    require(m.is_solid(5, 5), "wall is solid");

    require(m.is_solid(-1, 0), "out of bounds treated as solid");

    m.draw_rect(0, 0, 9, 7, TileKind::Wall);
    require(m.at(0, 0) == TileKind::Wall, "border set");
    require(m.at(5, 4) == TileKind::Grass, "interior not touched");

    auto village = build_map("village");
    require(village.width() == 50 && village.height() == 36, "village built at shipped size");

    auto unknown = build_map("nowhere");
    require(unknown.width() > 0, "unknown map still returns a map");

    return 0;
}
