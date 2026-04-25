#pragma once

#include "mythical/core/enemies.hpp"
#include "mythical/core/inventory.hpp"
#include "mythical/core/player.hpp"

namespace mythical {

struct AttackResult {
    int damage_dealt = 0;
    bool enemy_killed = false;
    int xp_gained = 0;
    int coins_gained = 0;
    std::string loot_id;  // empty if no drop
};

int compute_damage(int attack, int defense);

// Player attacks enemy. Loot RNG is deterministic via the caller-provided roll (0..99).
AttackResult player_attacks(Player& player, Enemy& enemy, int loot_roll);

// Enemy retaliates against the player. Returns damage dealt (may be 0).
int enemy_attacks(const Enemy& enemy, Player& player);

}  // namespace mythical
