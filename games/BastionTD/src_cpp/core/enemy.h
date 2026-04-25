#pragma once

#include "core/config.h"
#include "core/math_utils.h"
#include "core/pathfinding.h"
#include "core/types.h"

struct DotStack {
    float dps = 0.0f;
    float remaining = 0.0f;
};

struct Enemy {
    bool active = false;
    EnemyType type = EnemyType::Goblin;
    Vec2 pos = {0.0f, 0.0f};
    Vec2 prev_pos = {0.0f, 0.0f};
    float hp = 0.0f;
    float max_hp = 0.0f;
    int armor = 0;
    float speed = 0.0f;
    int gold_value = 0;
    int lives_cost = 1;
    float size = 0.5f;

    const Path* path = nullptr;
    int path_idx = 0;
    float path_progress = 0.0f;

    float slow_factor = 1.0f;
    float slow_timer = 0.0f;
    DotStack dots[cfg::MAX_DOT_STACKS];
    int dot_count = 0;

    float heal_rate = 0.0f;
    float heal_range = 0.0f;
    float heal_timer = 0.0f;

    bool reached_base = false;
    float death_timer = 0.0f;
    bool dying = false;
    bool reward_given = false;

    SpriteId sprite = SpriteId::Char0;
    float sprite_scale = 1.0f;

    void init(EnemyType t, const Path* p);
    void begin_tick();
    void tick_status(float dt);
    void move(float dt);
    void update(float dt);
    void take_damage(float amount);
    void apply_slow(float factor, float duration);
    void add_dot(float dps, float duration);
    void kill();
    bool is_dead() const;
    bool targetable() const;
};

struct EnemyPool {
    Enemy enemies[cfg::MAX_ENEMIES];

    void init();
    Enemy* spawn(EnemyType type, const Path* path);
    void begin_tick();
    void tick_status_all(float dt);
    void heal_pass();
    void move_all(float dt);
    void update_all(float dt);
    int active_count() const;
};
