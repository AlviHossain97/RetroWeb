#include "render.hpp"

#include <sstream>

namespace mythical::port {

namespace {

char tile_glyph(TileKind t) {
    switch (t) {
        case TileKind::Grass:        return '.';
        case TileKind::Path:         return '_';
        case TileKind::Water:        return '~';
        case TileKind::Tree:         return 'T';
        case TileKind::House:        return '#';
        case TileKind::HouseDoor:    return '/';
        case TileKind::Wall:         return '#';
        case TileKind::Floor:        return ' ';
        case TileKind::Door:         return '+';
        case TileKind::Chest:        return '$';
        case TileKind::Stone:        return ',';
        case TileKind::Sand:         return ':';
        case TileKind::DungeonFloor: return '.';
        case TileKind::DungeonWall:  return '#';
        case TileKind::RuinsFloor:   return '.';
        case TileKind::Lava:         return '!';
    }
    return '?';
}

char player_glyph(Facing f) {
    switch (f) {
        case Facing::Up:    return '^';
        case Facing::Down:  return 'v';
        case Facing::Left:  return '<';
        case Facing::Right: return '>';
    }
    return '@';
}

char enemy_glyph(const std::string& id) {
    if (id == "wolf") return 'w';
    if (id == "bandit") return 'b';
    if (id == "skeleton") return 's';
    if (id == "shadow_knight") return 'K';
    if (id == "revenant") return 'R';
    if (id == "mythic_sentinel") return 'S';
    if (id == "dark_golem") return 'G';
    if (id == "gravewarden") return 'W';
    if (id == "mythic_sovereign") return 'M';
    return 'e';
}

}  // namespace

std::string render_frame(const World& w, int view_w, int view_h) {
    const auto& tm = w.tilemap();
    const int px = w.player().x();
    const int py = w.player().y();
    int x0 = px - view_w / 2;
    int y0 = py - view_h / 2;
    if (x0 < 0) x0 = 0;
    if (y0 < 0) y0 = 0;
    if (x0 + view_w > tm.width())  x0 = tm.width()  - view_w;
    if (y0 + view_h > tm.height()) y0 = tm.height() - view_h;
    if (x0 < 0) x0 = 0;
    if (y0 < 0) y0 = 0;

    std::ostringstream out;
    for (int vy = 0; vy < view_h; ++vy) {
        for (int vx = 0; vx < view_w; ++vx) {
            const int mx = x0 + vx;
            const int my = y0 + vy;
            if (!tm.in_bounds(mx, my)) {
                out << ' ';
                continue;
            }
            if (mx == px && my == py) {
                out << player_glyph(w.player().facing());
                continue;
            }
            bool drew = false;
            for (const auto& e : w.enemies()) {
                if (e.alive() && e.x() == mx && e.y() == my) {
                    out << enemy_glyph(e.id());
                    drew = true;
                    break;
                }
            }
            if (drew) continue;
            out << tile_glyph(tm.at(mx, my));
        }
        out << '\n';
    }
    return out.str();
}

std::string render_status(const World& w) {
    std::ostringstream s;
    s << "Map: " << w.current_map()
      << " | Act: " << w.campaign().stage_name()
      << " | Form: " << w.player().form()
      << " | HP: " << w.player().hp() << "/" << w.player().max_hp()
      << " | Lv " << w.player().level() << " (xp " << w.player().xp() << ")"
      << " | Coins: " << w.player().inventory().wallet().coins();
    return s.str();
}

std::string render_inventory(const World& w) {
    const auto& inv = w.player().inventory();
    std::ostringstream s;
    s << "Inventory:\n";
    const auto wep = inv.equipped_weapon();
    const auto arm = inv.equipped_armor();
    const auto acc = inv.equipped_accessory();
    s << "  Weapon:    " << (wep.has_value() ? wep->id : "(none)") << "\n";
    s << "  Armor:     " << (arm.has_value() ? arm->id : "(none)") << "\n";
    s << "  Accessory: " << (acc.has_value() ? acc->id : "(none)") << "\n";
    return s.str();
}

}  // namespace mythical::port
