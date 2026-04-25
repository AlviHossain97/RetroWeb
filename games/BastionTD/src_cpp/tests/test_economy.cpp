#include "core/economy.h"

#include <cassert>
#include <cstdio>

void test_starting_values() {
    Economy e;
    assert(e.gold == 200);
    assert(e.lives == 20);
    assert(!e.is_game_over());
    std::printf("PASS: test_starting_values\n");
}

void test_spend_earn() {
    Economy e;
    assert(e.can_afford(200));
    assert(!e.can_afford(201));
    e.spend(50);
    assert(e.gold == 150);
    e.earn(30);
    assert(e.gold == 180);
    std::printf("PASS: test_spend_earn\n");
}

void test_lives_and_game_over() {
    Economy e;
    e.lose_lives(5);
    assert(e.lives == 15);
    e.lose_lives(15);
    assert(e.lives == 0);
    assert(e.is_game_over());
    std::printf("PASS: test_lives_and_game_over\n");
}

void test_wave_bonus() {
    Economy e;
    e.spend(200);
    e.wave_clear_bonus();
    assert(e.gold == 25);
    e.lose_lives(1);
    e.wave_clear_bonus();
    assert(e.gold == 25);
    std::printf("PASS: test_wave_bonus\n");
}

void test_fleet_upgrade_cost() {
    int cost = Economy::fleet_upgrade_cost(4, 30);
    assert(cost == 132);
    cost = Economy::fleet_upgrade_cost(1, 90);
    assert(cost == 99);
    std::printf("PASS: test_fleet_upgrade_cost\n");
}

int main() {
    test_starting_values();
    test_spend_earn();
    test_lives_and_game_over();
    test_wave_bonus();
    test_fleet_upgrade_cost();
    std::printf("All economy tests passed.\n");
    return 0;
}
