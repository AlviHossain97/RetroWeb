#include "core/tower.h"

#include "core/math_utils.h"

void Tower::init(TowerType t, int tx, int ty) {
    active = true;
    type = t;
    tile_x = tx;
    tile_y = ty;
    level = 1;
    const auto& def = cfg::TOWER_DEFS[static_cast<int>(t)];
    total_invested = def.cost;
    cooldown_timer = 0.0f;
    target_enemy_idx = -1;
    firing_anim = false;
    firing_anim_timer = 0.0f;
    apply_stats();
}

void Tower::apply_stats() {
    const auto& def = cfg::TOWER_DEFS[static_cast<int>(type)];
    damage = def.damage;
    range = def.range;
    cooldown = def.cooldown;
    splash_radius = def.splash_radius;
    slow_factor = def.slow_factor;
    slow_duration = def.slow_duration;
    chain_count = def.chain_count;
    chain_range = def.chain_range;
    dot_damage = def.dot_damage;
    dot_duration = def.dot_duration;
    color = def.color;
    char_sprite = def.char_sprite;

    for (int i = 0; i < level - 1 && i < 2; ++i) {
        const auto& upg = def.upgrades[i];
        damage = upg.damage;
        if (upg.range > 0.0f) {
            range = upg.range;
        }
        if (upg.splash_radius > 0.0f) {
            splash_radius = upg.splash_radius;
        }
        if (upg.slow_factor > 0.0f) {
            slow_factor = upg.slow_factor;
        }
        if (upg.chain_count > 0) {
            chain_count = upg.chain_count;
        }
        if (upg.dot_damage > 0.0f) {
            dot_damage = upg.dot_damage;
        }
        if (upg.dot_duration > 0.0f) {
            dot_duration = upg.dot_duration;
        }
    }
}

int Tower::upgrade_cost() const {
    if (level >= 3) {
        return -1;
    }
    return cfg::TOWER_DEFS[static_cast<int>(type)].upgrades[level - 1].cost;
}

int Tower::missing_upgrade_cost_to_level(int target_level) const {
    int total = 0;
    const auto& def = cfg::TOWER_DEFS[static_cast<int>(type)];
    for (int current = level; current < target_level && current <= 2; ++current) {
        total += def.upgrades[current - 1].cost;
    }
    return total;
}

void Tower::upgrade() {
    const int cost = upgrade_cost();
    if (cost < 0) {
        return;
    }
    total_invested += cost;
    ++level;
    apply_stats();
}

int Tower::sell_value() const {
    return total_invested / 2;
}

void Tower::update(float dt, EnemyPool& enemies) {
    if (!active) {
        return;
    }

    if (firing_anim) {
        firing_anim_timer -= dt;
        if (firing_anim_timer <= 0.0f) {
            firing_anim = false;
        }
    }

    cooldown_timer -= dt;

    const Vec2 tower_pos = {static_cast<float>(tile_x), static_cast<float>(tile_y)};
    const float max_range_sq = sim_mul(range, range);
    float best_progress = -1.0f;
    float best_dist_sq = 99999.0f;
    int best_idx = -1;

    for (int i = 0; i < cfg::MAX_ENEMIES; ++i) {
        const auto& e = enemies.enemies[i];
        if (!e.targetable()) {
            continue;
        }
        const float dist_sq = distance_sq(tower_pos, e.pos);
        if (dist_sq > max_range_sq) {
            continue;
        }
        if (e.path_progress > best_progress + EPSILON ||
            (sim_approx_eq(e.path_progress, best_progress, 0.0001f) && dist_sq < best_dist_sq)) {
            best_progress = e.path_progress;
            best_dist_sq = dist_sq;
            best_idx = i;
        }
    }

    target_enemy_idx = best_idx;
}

bool Tower::ready_to_fire() const {
    return active && cooldown_timer <= 0.0f && target_enemy_idx >= 0;
}

void TowerArray::init() {
    for (auto& t : towers) {
        t.active = false;
    }
}

Tower* TowerArray::place(TowerType type, int tx, int ty) {
    for (auto& t : towers) {
        if (!t.active) {
            t.init(type, tx, ty);
            return &t;
        }
    }
    return nullptr;
}

Tower* TowerArray::get_at(int tx, int ty) {
    for (auto& t : towers) {
        if (t.active && t.tile_x == tx && t.tile_y == ty) {
            return &t;
        }
    }
    return nullptr;
}

const Tower* TowerArray::get_at(int tx, int ty) const {
    for (const auto& t : towers) {
        if (t.active && t.tile_x == tx && t.tile_y == ty) {
            return &t;
        }
    }
    return nullptr;
}

void TowerArray::remove(int tx, int ty) {
    for (auto& t : towers) {
        if (t.active && t.tile_x == tx && t.tile_y == ty) {
            t.active = false;
            return;
        }
    }
}

int TowerArray::count_type(TowerType type) const {
    int count = 0;
    for (const auto& t : towers) {
        if (t.active && t.type == type) {
            ++count;
        }
    }
    return count;
}

int TowerArray::count_type_below_level(TowerType type, int target_level) const {
    int count = 0;
    for (const auto& t : towers) {
        if (t.active && t.type == type && t.level < target_level) {
            ++count;
        }
    }
    return count;
}

void TowerArray::upgrade_all_type(TowerType type, int target_level) {
    for (auto& t : towers) {
        if (!t.active || t.type != type) {
            continue;
        }
        while (t.level < target_level && t.upgrade_cost() >= 0) {
            t.upgrade();
        }
    }
}

int TowerArray::active_count() const {
    int count = 0;
    for (const auto& t : towers) {
        if (t.active) {
            ++count;
        }
    }
    return count;
}
