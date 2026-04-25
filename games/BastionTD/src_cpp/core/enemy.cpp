#include "core/enemy.h"

void Enemy::init(EnemyType t, const Path* p) {
    active = true;
    type = t;
    const auto& def = cfg::ENEMY_DEFS[static_cast<int>(t)];
    hp = def.hp;
    max_hp = def.hp;
    armor = def.armor;
    speed = def.speed;
    gold_value = def.gold;
    lives_cost = def.lives_cost;
    size = def.size;
    heal_rate = def.heal_rate;
    heal_range = def.heal_range;
    heal_timer = 0.0f;
    sprite = def.sprite;
    sprite_scale = def.sprite_scale;

    path = p;
    path_idx = 0;
    path_progress = 0.0f;
    if (p != nullptr && p->length > 0) {
        pos = p->points[0];
        prev_pos = pos;
    } else {
        pos = {0.0f, 0.0f};
        prev_pos = pos;
    }

    slow_factor = 1.0f;
    slow_timer = 0.0f;
    dot_count = 0;
    reached_base = false;
    death_timer = 0.0f;
    dying = false;
    reward_given = false;
}

void Enemy::begin_tick() {
    if (active) {
        prev_pos = pos;
    }
}

void Enemy::tick_status(float dt) {
    if (!active) {
        return;
    }

    if (dying) {
        death_timer -= dt;
        if (death_timer <= 0.0f) {
            active = false;
        }
        return;
    }

    for (int i = 0; i < dot_count;) {
        hp -= sim_mul(dots[i].dps, dt);
        dots[i].remaining -= dt;
        if (dots[i].remaining <= 0.0f) {
            dots[i] = dots[dot_count - 1];
            --dot_count;
        } else {
            ++i;
        }
    }

    if (hp <= 0.0f) {
        kill();
        return;
    }

    if (slow_timer > 0.0f) {
        slow_timer -= dt;
        if (slow_timer <= 0.0f) {
            slow_timer = 0.0f;
            slow_factor = 1.0f;
        }
    }

    if (heal_rate > 0.0f) {
        heal_timer += dt;
    }
}

void Enemy::move(float dt) {
    if (!active || dying || path == nullptr || path->length <= 1) {
        return;
    }

    if (path_idx >= path->length - 1) {
        reached_base = true;
        active = false;
        path_progress = 1.0f;
        return;
    }

    const float effective_speed = sim_mul(speed, slow_timer > 0.0f ? slow_factor : 1.0f);
    float move_budget = sim_mul(effective_speed, dt);

    while (move_budget > 0.0f && path_idx < path->length - 1) {
        const Vec2 target = path->points[path_idx + 1];
        const float dist = distance(pos, target);
        if (dist <= move_budget + EPSILON) {
            pos = target;
            move_budget -= dist;
            ++path_idx;
        } else if (dist > EPSILON) {
            const float ratio = sim_div(move_budget, dist);
            pos.x += sim_mul(target.x - pos.x, ratio);
            pos.y += sim_mul(target.y - pos.y, ratio);
            move_budget = 0.0f;
        } else {
            ++path_idx;
        }
    }

    if (path_idx >= path->length - 1) {
        reached_base = true;
        active = false;
        path_progress = 1.0f;
        return;
    }

    const Vec2 seg_start = path->points[path_idx];
    const Vec2 seg_end = path->points[path_idx + 1];
    const float seg_len = distance(seg_start, seg_end);
    const float seg_prog = seg_len > EPSILON ? sim_clamp(sim_div(distance(seg_start, pos), seg_len), 0.0f, 1.0f) : 0.0f;
    path_progress = sim_div(static_cast<float>(path_idx) + seg_prog, static_cast<float>(path->length - 1));
}

void Enemy::update(float dt) {
    begin_tick();
    tick_status(dt);
    move(dt);
}

void Enemy::take_damage(float amount) {
    if (!active || dying || amount <= 0.0f) {
        return;
    }
    const float effective = sim_max(1.0f, amount - static_cast<float>(armor));
    hp -= effective;
    if (hp <= 0.0f) {
        kill();
    }
}

void Enemy::apply_slow(float factor, float duration) {
    if (!active || dying) {
        return;
    }
    if (slow_timer <= 0.0f || factor < slow_factor) {
        slow_factor = factor;
    }
    slow_timer = sim_max(slow_timer, duration);
}

void Enemy::add_dot(float dps, float duration) {
    if (!active || dying || dps <= 0.0f || duration <= 0.0f) {
        return;
    }

    if (dot_count < cfg::MAX_DOT_STACKS) {
        dots[dot_count++] = {dps, duration};
        return;
    }

    int oldest_idx = 0;
    for (int i = 1; i < dot_count; ++i) {
        if (dots[i].remaining < dots[oldest_idx].remaining) {
            oldest_idx = i;
        }
    }
    dots[oldest_idx] = {dps, duration};
}

void Enemy::kill() {
    if (!active || dying) {
        return;
    }
    hp = 0.0f;
    dying = true;
    death_timer = 0.3f;
    reward_given = false;
}

bool Enemy::is_dead() const {
    return !active || dying;
}

bool Enemy::targetable() const {
    return active && !dying && !reached_base;
}

void EnemyPool::init() {
    for (auto& e : enemies) {
        e.active = false;
        e.dying = false;
        e.reached_base = false;
    }
}

Enemy* EnemyPool::spawn(EnemyType type, const Path* path) {
    if (path == nullptr || !path->valid) {
        return nullptr;
    }
    for (auto& e : enemies) {
        if (!e.active) {
            e.init(type, path);
            return &e;
        }
    }
    return nullptr;
}

void EnemyPool::begin_tick() {
    for (auto& e : enemies) {
        if (e.active) {
            e.begin_tick();
        }
    }
}

void EnemyPool::tick_status_all(float dt) {
    for (auto& e : enemies) {
        if (e.active) {
            e.tick_status(dt);
        }
    }
}

void EnemyPool::heal_pass() {
    for (auto& healer : enemies) {
        if (!healer.active || healer.dying || healer.heal_rate <= 0.0f) {
            continue;
        }
        while (healer.heal_timer >= 1.0f) {
            healer.heal_timer -= 1.0f;
            for (auto& ally : enemies) {
                if (&ally == &healer || !ally.active || ally.dying) {
                    continue;
                }
                if (distance(healer.pos, ally.pos) <= healer.heal_range) {
                    ally.hp = sim_min(ally.hp + healer.heal_rate, ally.max_hp);
                }
            }
        }
    }
}

void EnemyPool::move_all(float dt) {
    for (auto& e : enemies) {
        if (e.active) {
            e.move(dt);
        }
    }
}

void EnemyPool::update_all(float dt) {
    begin_tick();
    tick_status_all(dt);
    heal_pass();
    move_all(dt);
}

int EnemyPool::active_count() const {
    int count = 0;
    for (const auto& e : enemies) {
        if (e.active) {
            ++count;
        }
    }
    return count;
}
