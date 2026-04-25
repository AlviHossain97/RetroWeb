#pragma once

#include "core/config.h"

struct Economy {
    int gold = cfg::START_GOLD;
    int lives = cfg::START_LIVES;
    bool had_leak_this_wave = false;

    void reset();
    bool can_afford(int cost) const;
    void spend(int cost);
    void earn(int amount);
    void lose_lives(int amount);
    bool is_game_over() const;
    void wave_clear_bonus();

    static int fleet_upgrade_cost(int tower_count, int per_tower_cost);
};
