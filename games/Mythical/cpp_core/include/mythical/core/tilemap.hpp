#pragma once

#include <string>
#include <vector>

namespace mythical {

enum class TileKind : unsigned char {
    Grass = 0,
    Path = 1,
    Water = 2,
    Tree = 3,
    House = 4,
    HouseDoor = 5,
    Wall = 6,
    Floor = 7,
    Door = 8,
    Chest = 9,
    Stone = 10,
    Sand = 11,
    DungeonFloor = 12,
    DungeonWall = 13,
    RuinsFloor = 14,
    Lava = 15,
};

bool is_tile_solid(TileKind t);

class TileMap {
public:
    TileMap();
    TileMap(int width, int height, TileKind fill);

    int width() const;
    int height() const;

    TileKind at(int x, int y) const;
    void set(int x, int y, TileKind t);

    bool in_bounds(int x, int y) const;
    bool is_solid(int x, int y) const;

    // Fill rectangle [x0,y0]..[x1,y1] inclusive with the given tile.
    void fill_rect(int x0, int y0, int x1, int y1, TileKind t);
    void draw_rect(int x0, int y0, int x1, int y1, TileKind t);

    const std::vector<unsigned char>& raw() const;

private:
    int width_;
    int height_;
    std::vector<unsigned char> tiles_;
};

TileMap build_map(const std::string& map_id);

}  // namespace mythical
