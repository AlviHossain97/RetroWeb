#include "mythical/core/combat.hpp"

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

    require(compute_damage(10, 0) == 10, "no defense = full damage");
    require(compute_damage(10, 6) == 7,  "defense halves and subtracts");
    require(compute_damage(1, 100) == 1, "damage floors at 1");

    Player p;
    p.inventory().add("iron_sword", 1);
    p.inventory().equip("iron_sword");
    Enemy wolf("wolf", 0, 0);
    const int start_coins = p.inventory().wallet().coins();

    // Loot roll 0 => will drop (wolf loot_chance_pct=40).
    AttackResult r = player_attacks(p, wolf, 0);
    require(r.damage_dealt > 0, "attack deals damage");
    // Iron sword + base attack should one-shot a 14hp wolf at level 1 (3 + 4 = 7) easily after a few hits.
    while (wolf.alive()) {
        r = player_attacks(p, wolf, 0);
    }
    require(r.enemy_killed, "wolf dies");
    require(r.xp_gained == 8, "wolf xp is granted");
    require(p.inventory().wallet().coins() == start_coins + 2, "coin reward added");
    require(p.inventory().has("animal_hide"), "loot drops at roll 0");

    Enemy bandit("bandit", 1, 1);
    const int hp_before = p.hp();
    enemy_attacks(bandit, p);
    require(p.hp() < hp_before, "enemy damages player");

    return 0;
}
