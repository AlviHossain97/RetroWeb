#include "mythical/core/enemies.hpp"

namespace mythical {

namespace {

const std::vector<EnemyDef>& enemy_defs() {
    static const std::vector<EnemyDef> defs = {
        {"wolf",           14,  3, 0, 8,  2, "animal_hide", 40},
        {"bandit",         18,  4, 1, 12, 5, "old_sword",    5},
        {"skeleton",       22,  5, 1, 16, 3, "bones",       60},
        {"shadow_knight",  30,  7, 2, 28, 6, "shadow_dust", 35},
        {"revenant",       38,  8, 3, 36, 8, "revenant_core", 25},
        {"mythic_sentinel",55, 11, 4, 60, 15, "void_shard",   30},
        {"dark_golem",     90, 12, 4, 100, 30, "boss_key",   100},
        {"gravewarden",   130, 15, 5, 160, 45, "ancient_tome", 100},
        {"mythic_sovereign", 200, 18, 6, 250, 80, "mythic_core", 100},
    };
    return defs;
}

}  // namespace

const EnemyDef* find_enemy_def(const std::string& id) {
    for (const auto& def : enemy_defs()) {
        if (def.id == id) return &def;
    }
    return nullptr;
}

int shipped_enemy_count() {
    return static_cast<int>(enemy_defs().size());
}

const std::vector<EnemyDef>& shipped_enemies() {
    return enemy_defs();
}

Enemy::Enemy() : x_(0), y_(0), hp_(0), def_(nullptr) {}

Enemy::Enemy(const std::string& def_id, int x, int y)
    : id_(def_id), x_(x), y_(y), hp_(0), def_(find_enemy_def(def_id)) {
    if (def_) hp_ = def_->hp;
}

bool Enemy::alive() const { return hp_ > 0; }
int Enemy::hp() const { return hp_; }
int Enemy::x() const { return x_; }
int Enemy::y() const { return y_; }
const std::string& Enemy::id() const { return id_; }
const EnemyDef* Enemy::def() const { return def_; }

void Enemy::set_position(int x, int y) { x_ = x; y_ = y; }

bool Enemy::take_damage(int amount) {
    if (amount <= 0 || !alive()) return false;
    hp_ -= amount;
    if (hp_ <= 0) {
        hp_ = 0;
        return true;
    }
    return false;
}

}  // namespace mythical
