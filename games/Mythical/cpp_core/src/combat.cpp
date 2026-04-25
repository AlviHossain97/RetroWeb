#include "mythical/core/combat.hpp"

namespace mythical {

int compute_damage(int attack, int defense) {
    int d = attack - defense / 2;
    if (d < 1) d = 1;
    return d;
}

AttackResult player_attacks(Player& player, Enemy& enemy, int loot_roll) {
    AttackResult out;
    if (!enemy.alive()) return out;
    const int atk = player.total_attack(player.inventory());
    const int def = enemy.def() ? enemy.def()->defense : 0;
    const int dmg = compute_damage(atk, def);
    out.damage_dealt = dmg;
    out.enemy_killed = enemy.take_damage(dmg);
    if (out.enemy_killed && enemy.def()) {
        out.xp_gained = enemy.def()->xp_reward;
        out.coins_gained = enemy.def()->coin_reward;
        player.gain_xp(out.xp_gained);
        player.inventory().wallet().add(out.coins_gained);
        if (!enemy.def()->loot_id.empty() && loot_roll >= 0 && loot_roll < enemy.def()->loot_chance_pct) {
            out.loot_id = enemy.def()->loot_id;
            player.inventory().add(out.loot_id, 1);
        }
    }
    return out;
}

int enemy_attacks(const Enemy& enemy, Player& player) {
    if (!enemy.alive()) return 0;
    const int atk = enemy.def() ? enemy.def()->attack : 1;
    const int def = player.total_defense(player.inventory());
    const int dmg = compute_damage(atk, def);
    player.take_damage(dmg);
    return dmg;
}

}  // namespace mythical
