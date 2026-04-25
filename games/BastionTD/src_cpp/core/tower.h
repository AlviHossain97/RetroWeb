#pragma once

#include "core/config.h"
#include "core/enemy.h"
#include "core/types.h"

struct Tower {
    bool active = false;
    TowerType type = TowerType::Arrow;
    int tile_x = 0;
    int tile_y = 0;
    int level = 1;
    float cooldown_timer = 0.0f;
    int total_invested = 0;

    float damage = 0.0f;
    float range = 0.0f;
    float cooldown = 0.0f;
    float splash_radius = 0.0f;
    float slow_factor = 0.0f;
    float slow_duration = 0.0f;
    int chain_count = 0;
    float chain_range = 0.0f;
    float dot_damage = 0.0f;
    float dot_duration = 0.0f;
    Color color = {};
    SpriteId char_sprite = SpriteId::Char2;

    int target_enemy_idx = -1;
    bool firing_anim = false;
    float firing_anim_timer = 0.0f;

    void init(TowerType t, int tx, int ty);
    void apply_stats();
    int upgrade_cost() const;
    int missing_upgrade_cost_to_level(int target_level) const;
    void upgrade();
    int sell_value() const;
    void update(float dt, EnemyPool& enemies);
    bool ready_to_fire() const;
};

struct TowerArray {
    Tower towers[cfg::MAX_TOWERS];

    void init();
    Tower* place(TowerType type, int tx, int ty);
    Tower* get_at(int tx, int ty);
    const Tower* get_at(int tx, int ty) const;
    void remove(int tx, int ty);
    int count_type(TowerType type) const;
    int count_type_below_level(TowerType type, int target_level) const;
    void upgrade_all_type(TowerType type, int target_level);
    int active_count() const;
};
