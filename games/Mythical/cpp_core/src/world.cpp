#include "mythical/core/world.hpp"

#include <cstdlib>

namespace mythical {

namespace {

int dir_dx(Direction d) {
    switch (d) {
        case Direction::East: return 1;
        case Direction::West: return -1;
        default: return 0;
    }
}

int dir_dy(Direction d) {
    switch (d) {
        case Direction::South: return 1;
        case Direction::North: return -1;
        default: return 0;
    }
}

Facing facing_from(Direction d) {
    switch (d) {
        case Direction::North: return Facing::Up;
        case Direction::South: return Facing::Down;
        case Direction::East:  return Facing::Right;
        case Direction::West:  return Facing::Left;
        default: return Facing::Down;
    }
}

}  // namespace

World::World()
    : maps_(MapRegistry::shipped()),
      current_map_("village"),
      tilemap_(build_map("village")) {
    place_player_on_spawn();
    populate_enemies_for_map(current_map_);
}

const Campaign& World::campaign() const { return campaign_; }
Campaign& World::campaign() { return campaign_; }
const Player& World::player() const { return player_; }
Player& World::player() { return player_; }
const TileMap& World::tilemap() const { return tilemap_; }
const MapRegistry& World::maps() const { return maps_; }
QuestLog& World::quests() { return quests_; }
const QuestLog& World::quests() const { return quests_; }
const std::string& World::current_map() const { return current_map_; }
const std::vector<Enemy>& World::enemies() const { return enemies_; }
std::vector<Enemy>& World::enemies() { return enemies_; }

EnterResult World::enter_map(const std::string& id) {
    EnterResult r;
    if (!maps_.contains(id) || !maps_.can_enter(id, campaign_)) {
        return r;
    }
    current_map_ = id;
    tilemap_ = build_map(id);
    place_player_on_spawn();
    populate_enemies_for_map(id);
    r.ok = true;
    r.map_id = id;
    return r;
}

StepOutcome World::move_player(Direction dir) {
    if (dir == Direction::None) return StepOutcome::Blocked;
    const int nx = player_.x() + dir_dx(dir);
    const int ny = player_.y() + dir_dy(dir);
    player_.set_facing(facing_from(dir));
    if (!tilemap_.in_bounds(nx, ny)) return StepOutcome::Blocked;
    if (tilemap_.is_solid(nx, ny)) {
        const TileKind k = tilemap_.at(nx, ny);
        if (k == TileKind::Door || k == TileKind::HouseDoor) {
            return StepOutcome::ReachedExit;
        }
        return StepOutcome::Blocked;
    }
    if (tilemap_.at(nx, ny) == TileKind::Door || tilemap_.at(nx, ny) == TileKind::HouseDoor) {
        player_.set_position(nx, ny);
        return StepOutcome::ReachedExit;
    }
    if (enemy_index_at(nx, ny) >= 0) {
        return StepOutcome::BumpedEnemy;
    }
    player_.set_position(nx, ny);
    return StepOutcome::Moved;
}

AttackResult World::player_attack_front(int loot_roll) {
    int tx = player_.x();
    int ty = player_.y();
    switch (player_.facing()) {
        case Facing::Up:    ty -= 1; break;
        case Facing::Down:  ty += 1; break;
        case Facing::Left:  tx -= 1; break;
        case Facing::Right: tx += 1; break;
    }
    const int idx = enemy_index_at(tx, ty);
    if (idx < 0) return {};
    AttackResult res = player_attacks(player_, enemies_[idx], loot_roll);
    if (!enemies_[idx].alive()) {
        enemies_.erase(enemies_.begin() + idx);
    }
    return res;
}

int World::run_enemy_turn() {
    int total = 0;
    for (auto& enemy : enemies_) {
        if (!enemy.alive()) continue;
        const int dx = player_.x() - enemy.x();
        const int dy = player_.y() - enemy.y();
        const int adist = std::abs(dx) + std::abs(dy);
        if (adist == 1) {
            total += enemy_attacks(enemy, player_);
            continue;
        }
        int step_x = 0;
        int step_y = 0;
        if (std::abs(dx) > std::abs(dy)) {
            step_x = dx > 0 ? 1 : -1;
        } else if (dy != 0) {
            step_y = dy > 0 ? 1 : -1;
        }
        const int nx = enemy.x() + step_x;
        const int ny = enemy.y() + step_y;
        if (!tilemap_.is_solid(nx, ny) &&
            (nx != player_.x() || ny != player_.y()) &&
            enemy_index_at(nx, ny) < 0) {
            enemy.set_position(nx, ny);
        }
    }
    return total;
}

StageAdvance World::defeat_boss(const std::string& boss_id) {
    return campaign_.on_boss_defeated(boss_id);
}

void World::populate_enemies_for_map(const std::string& map_id) {
    enemies_.clear();
    if (map_id == "village") {
        enemies_.emplace_back("wolf", 30, 8);
        enemies_.emplace_back("bandit", 40, 28);
    } else if (map_id == "dungeon") {
        enemies_.emplace_back("skeleton", 6, 6);
        enemies_.emplace_back("skeleton", 30, 6);
        enemies_.emplace_back("bandit", 10, 30);
        enemies_.emplace_back("dark_golem", 30, 30);
    } else if (map_id == "ruins_approach") {
        enemies_.emplace_back("skeleton", 15, 15);
        enemies_.emplace_back("shadow_knight", 35, 20);
    } else if (map_id == "ruins_depths") {
        enemies_.emplace_back("shadow_knight", 20, 20);
        enemies_.emplace_back("revenant", 40, 20);
        enemies_.emplace_back("gravewarden", 50, 20);
    } else if (map_id == "sanctum_halls") {
        enemies_.emplace_back("revenant", 20, 20);
        enemies_.emplace_back("mythic_sentinel", 40, 20);
    } else if (map_id == "throne_room") {
        enemies_.emplace_back("mythic_sentinel", 20, 15);
        enemies_.emplace_back("mythic_sovereign", 25, 18);
    }
}

int World::enemy_index_at(int x, int y) const {
    for (int i = 0; i < static_cast<int>(enemies_.size()); ++i) {
        if (enemies_[i].alive() && enemies_[i].x() == x && enemies_[i].y() == y) {
            return i;
        }
    }
    return -1;
}

void World::place_player_on_spawn() {
    if (current_map_ == "village") {
        player_.set_position(24, 18);
    } else if (current_map_ == "dungeon") {
        player_.set_position(9, 4);
    } else if (current_map_ == "ruins_approach") {
        player_.set_position(25, 2);
    } else if (current_map_ == "ruins_depths") {
        player_.set_position(3, 20);
    } else if (current_map_ == "sanctum_halls") {
        player_.set_position(1, 20);
    } else if (current_map_ == "throne_room") {
        player_.set_position(25, 28);
    } else {
        player_.set_position(tilemap_.width() / 2, tilemap_.height() / 2);
    }
    player_.set_facing(Facing::Down);
}

}  // namespace mythical
