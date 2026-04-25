#pragma once

#include "core/config.h"
#include "core/enemy.h"
#include "core/types.h"

struct Projectile {
    bool active = false;
    Vec2 pos = {0.0f, 0.0f};
    Vec2 prev_pos = {0.0f, 0.0f};
    Vec2 target_pos = {0.0f, 0.0f};
    int target_enemy_idx = -1;
    float speed = cfg::PROJECTILE_SPEED;
    float damage = 0.0f;
    TowerType tower_type = TowerType::Arrow;
    Color color = {};

    float splash_radius = 0.0f;
    float slow_factor = 0.0f;
    float slow_duration = 0.0f;
    int chain_count = 0;
    float chain_range = 0.0f;
    float dot_damage = 0.0f;
    float dot_duration = 0.0f;

    void update(float dt, EnemyPool& enemies);
    void on_impact(EnemyPool& enemies);
};

struct ProjectilePool {
    Projectile projectiles[cfg::MAX_PROJECTILES];

    void init();
    Projectile* spawn(Vec2 start, int target_idx, float damage,
                      TowerType type, Color color,
                      float splash_r, float slow_f, float slow_d,
                      int chain_c, float chain_r,
                      float dot_d, float dot_dur,
                      const EnemyPool& enemies);
    void update_all(float dt, EnemyPool& enemies);
    int active_count() const;
};
