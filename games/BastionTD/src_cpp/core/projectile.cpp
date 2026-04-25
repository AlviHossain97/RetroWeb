#include "core/projectile.h"

#include "core/math_utils.h"

void Projectile::update(float dt, EnemyPool& enemies) {
    if (!active) {
        return;
    }

    prev_pos = pos;

    Vec2 dest = target_pos;
    if (target_enemy_idx >= 0 && target_enemy_idx < cfg::MAX_ENEMIES) {
        const auto& target = enemies.enemies[target_enemy_idx];
        if (target.targetable()) {
            dest = target.pos;
            target_pos = dest;
        }
    }

    const float dist = distance(pos, dest);
    if (dist < cfg::PROJECTILE_HIT_DIST) {
        on_impact(enemies);
        active = false;
        return;
    }

    const float move = sim_mul(speed, dt);
    if (move >= dist) {
        pos = dest;
        on_impact(enemies);
        active = false;
        return;
    }

    if (dist > EPSILON) {
        const float ratio = sim_div(move, dist);
        pos.x += sim_mul(dest.x - pos.x, ratio);
        pos.y += sim_mul(dest.y - pos.y, ratio);
    }
}

void Projectile::on_impact(EnemyPool& enemies) {
    if (target_enemy_idx >= 0 && target_enemy_idx < cfg::MAX_ENEMIES && enemies.enemies[target_enemy_idx].active) {
        Enemy& target = enemies.enemies[target_enemy_idx];
        target.take_damage(damage);
        if (slow_factor > 0.0f && slow_duration > 0.0f) {
            target.apply_slow(slow_factor, slow_duration);
        }
        if (dot_damage > 0.0f && dot_duration > 0.0f) {
            target.add_dot(dot_damage, dot_duration);
        }
    }

    if (splash_radius > 0.0f) {
        const float splash_damage = sim_mul(damage, 0.5f);
        for (int i = 0; i < cfg::MAX_ENEMIES; ++i) {
            if (i == target_enemy_idx) {
                continue;
            }
            auto& e = enemies.enemies[i];
            if (!e.targetable()) {
                continue;
            }
            if (distance(pos, e.pos) <= splash_radius) {
                e.take_damage(splash_damage);
            }
        }
    }

    if (chain_count > 0 && chain_range > 0.0f) {
        const float chain_damage = sim_mul(damage, 0.7f);
        bool hit[cfg::MAX_ENEMIES] = {};
        if (target_enemy_idx >= 0 && target_enemy_idx < cfg::MAX_ENEMIES) {
            hit[target_enemy_idx] = true;
        }

        Vec2 last_pos = pos;
        int remaining = chain_count;
        while (remaining > 0) {
            float best_dist = 99999.0f;
            int best_idx = -1;
            for (int i = 0; i < cfg::MAX_ENEMIES; ++i) {
                if (hit[i]) {
                    continue;
                }
                const auto& e = enemies.enemies[i];
                if (!e.targetable()) {
                    continue;
                }
                const float d = distance(last_pos, e.pos);
                if (d <= chain_range && d < best_dist) {
                    best_dist = d;
                    best_idx = i;
                }
            }
            if (best_idx < 0) {
                break;
            }
            hit[best_idx] = true;
            enemies.enemies[best_idx].take_damage(chain_damage);
            last_pos = enemies.enemies[best_idx].pos;
            --remaining;
        }
    }
}

void ProjectilePool::init() {
    for (auto& p : projectiles) {
        p.active = false;
    }
}

Projectile* ProjectilePool::spawn(Vec2 start, int target_idx, float dmg,
                                  TowerType type, Color tint,
                                  float splash_r, float slow_f, float slow_d,
                                  int chain_c, float chain_r,
                                  float dot_d, float dot_dur,
                                  const EnemyPool& enemies) {
    for (auto& p : projectiles) {
        if (!p.active) {
            p.active = true;
            p.pos = start;
            p.prev_pos = start;
            p.target_enemy_idx = target_idx;
            p.speed = cfg::PROJECTILE_SPEED;
            p.damage = dmg;
            p.tower_type = type;
            p.color = tint;
            p.splash_radius = splash_r;
            p.slow_factor = slow_f;
            p.slow_duration = slow_d;
            p.chain_count = chain_c;
            p.chain_range = chain_r;
            p.dot_damage = dot_d;
            p.dot_duration = dot_dur;
            if (target_idx >= 0 && target_idx < cfg::MAX_ENEMIES && enemies.enemies[target_idx].active) {
                p.target_pos = enemies.enemies[target_idx].pos;
            } else {
                p.target_pos = start;
            }
            return &p;
        }
    }
    return nullptr;
}

void ProjectilePool::update_all(float dt, EnemyPool& enemies) {
    for (auto& p : projectiles) {
        if (p.active) {
            p.update(dt, enemies);
        }
    }
}

int ProjectilePool::active_count() const {
    int count = 0;
    for (const auto& p : projectiles) {
        if (p.active) {
            ++count;
        }
    }
    return count;
}
