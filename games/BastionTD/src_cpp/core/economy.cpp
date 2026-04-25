#include "core/economy.h"

#include <cmath>

void Economy::reset() {
    gold = cfg::START_GOLD;
    lives = cfg::START_LIVES;
    had_leak_this_wave = false;
}

bool Economy::can_afford(int cost) const { return gold >= cost; }

void Economy::spend(int cost) { gold -= cost; }

void Economy::earn(int amount) { gold += amount; }

void Economy::lose_lives(int amount) {
    lives -= amount;
    had_leak_this_wave = true;
    if (lives < 0) {
        lives = 0;
    }
}

bool Economy::is_game_over() const { return lives <= 0; }

void Economy::wave_clear_bonus() {
    if (!had_leak_this_wave) {
        gold += cfg::WAVE_CLEAR_BONUS;
    }
    had_leak_this_wave = false;
}

int Economy::fleet_upgrade_cost(int tower_count, int per_tower_cost) {
    const float raw = static_cast<float>(tower_count * per_tower_cost);
    return static_cast<int>(std::ceil(raw * cfg::FLEET_UPGRADE_PREMIUM));
}
