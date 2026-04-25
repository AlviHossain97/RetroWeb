#include "core/config.h"
#include "core/enemy.h"
#include "core/math_utils.h"
#include "core/projectile.h"
#include "core/tower.h"

#include <cassert>
#include <cstdio>

void test_min_damage_vs_armor() {
    Enemy e;
    Path p;
    p.length = 2;
    p.points[0] = {0.0f, 0.0f};
    p.points[1] = {5.0f, 0.0f};
    p.valid = true;
    e.init(EnemyType::Knight, &p);
    const float initial_hp = e.hp;
    e.take_damage(1.0f);
    assert(sim_approx_eq(e.hp, initial_hp - 1.0f));
    std::printf("PASS: test_min_damage_vs_armor\n");
}

void test_dot_bypasses_armor() {
    Enemy e;
    Path p;
    p.length = 2;
    p.points[0] = {0.0f, 0.0f};
    p.points[1] = {10.0f, 0.0f};
    p.valid = true;
    e.init(EnemyType::Titan, &p);
    const float initial_hp = e.hp;
    e.add_dot(2.0f, 1.0f);
    e.update(0.5f);
    assert(sim_approx_eq(e.hp, initial_hp - 1.0f, 0.1f));
    std::printf("PASS: test_dot_bypasses_armor\n");
}

void test_burn_stacking_cap() {
    Enemy e;
    Path p;
    p.length = 2;
    p.points[0] = {0.0f, 0.0f};
    p.points[1] = {10.0f, 0.0f};
    p.valid = true;
    e.init(EnemyType::Goblin, &p);
    e.add_dot(1.0f, 2.0f);
    e.add_dot(1.0f, 2.0f);
    e.add_dot(1.0f, 2.0f);
    assert(e.dot_count == 3);
    e.add_dot(1.0f, 2.0f);
    assert(e.dot_count == 3);
    std::printf("PASS: test_burn_stacking_cap\n");
}

void test_slow_strongest_wins() {
    Enemy e;
    Path p;
    p.length = 2;
    p.points[0] = {0.0f, 0.0f};
    p.points[1] = {10.0f, 0.0f};
    p.valid = true;
    e.init(EnemyType::Goblin, &p);
    e.apply_slow(0.4f, 2.0f);
    e.apply_slow(0.3f, 1.0f);
    assert(sim_approx_eq(e.slow_factor, 0.3f));
    std::printf("PASS: test_slow_strongest_wins\n");
}

void test_splash_damage() {
    EnemyPool pool;
    pool.init();
    Path p;
    p.length = 2;
    p.points[0] = {5.0f, 5.0f};
    p.points[1] = {10.0f, 5.0f};
    p.valid = true;

    Enemy* e1 = pool.spawn(EnemyType::Goblin, &p);
    Enemy* e2 = pool.spawn(EnemyType::Goblin, &p);
    const float hp_before = e2->hp;

    Projectile proj;
    proj.active = true;
    proj.pos = e1->pos;
    proj.target_enemy_idx = 0;
    proj.damage = 4.0f;
    proj.splash_radius = 2.0f;
    proj.on_impact(pool);

    assert(e2->hp < hp_before);
    std::printf("PASS: test_splash_damage\n");
}

int main() {
    test_min_damage_vs_armor();
    test_dot_bypasses_armor();
    test_burn_stacking_cap();
    test_slow_strongest_wins();
    test_splash_damage();
    std::printf("All combat tests passed.\n");
    return 0;
}
