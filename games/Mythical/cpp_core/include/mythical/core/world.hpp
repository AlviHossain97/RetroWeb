#pragma once

#include "mythical/core/campaign.hpp"
#include "mythical/core/combat.hpp"
#include "mythical/core/enemies.hpp"
#include "mythical/core/maps.hpp"
#include "mythical/core/player.hpp"
#include "mythical/core/quests.hpp"
#include "mythical/core/tilemap.hpp"

#include <string>
#include <vector>

namespace mythical {

enum class Direction : unsigned char {
    None = 0,
    North = 1,
    South = 2,
    East = 3,
    West = 4,
};

enum class StepOutcome : unsigned char {
    Moved = 0,
    Blocked = 1,
    MapLocked = 2,
    BumpedEnemy = 3,
    ReachedExit = 4,
};

struct EnterResult {
    bool ok = false;
    std::string map_id;
};

class World {
public:
    World();

    const Campaign& campaign() const;
    Campaign& campaign();
    const Player& player() const;
    Player& player();
    const TileMap& tilemap() const;
    const MapRegistry& maps() const;
    QuestLog& quests();
    const QuestLog& quests() const;

    const std::string& current_map() const;
    const std::vector<Enemy>& enemies() const;
    std::vector<Enemy>& enemies();

    EnterResult enter_map(const std::string& id);

    StepOutcome move_player(Direction dir);

    // Attack whatever is in front of the player. Returns result; if no enemy hit,
    // damage_dealt is 0 and enemy_killed is false.
    AttackResult player_attack_front(int loot_roll);

    // Run a simple enemy turn: each enemy chases the player one step and attacks if adjacent.
    // Returns total damage taken.
    int run_enemy_turn();

    // Defeat a boss by id and propagate campaign progression.
    StageAdvance defeat_boss(const std::string& boss_id);

private:
    Campaign campaign_;
    Player player_;
    QuestLog quests_;
    MapRegistry maps_;
    std::string current_map_;
    TileMap tilemap_;
    std::vector<Enemy> enemies_;

    void populate_enemies_for_map(const std::string& map_id);
    int enemy_index_at(int x, int y) const;
    void place_player_on_spawn();
};

}  // namespace mythical
