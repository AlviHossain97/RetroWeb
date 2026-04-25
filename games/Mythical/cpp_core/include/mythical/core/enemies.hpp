#pragma once

#include <string>
#include <vector>

namespace mythical {

struct EnemyDef {
    std::string id;
    int hp;
    int attack;
    int defense;
    int xp_reward;
    int coin_reward;
    std::string loot_id;   // may be empty
    int loot_chance_pct;   // 0-100
};

const EnemyDef* find_enemy_def(const std::string& id);
int shipped_enemy_count();
const std::vector<EnemyDef>& shipped_enemies();

class Enemy {
public:
    Enemy();
    Enemy(const std::string& def_id, int x, int y);

    bool alive() const;
    int hp() const;
    int x() const;
    int y() const;
    const std::string& id() const;
    const EnemyDef* def() const;

    void set_position(int x, int y);
    bool take_damage(int amount);  // returns true if killed

private:
    std::string id_;
    int x_;
    int y_;
    int hp_;
    const EnemyDef* def_;
};

}  // namespace mythical
