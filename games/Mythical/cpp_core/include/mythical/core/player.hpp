#pragma once

#include "mythical/core/inventory.hpp"

#include <string>

namespace mythical {

enum class Facing : unsigned char {
    Down = 0,
    Up = 1,
    Left = 2,
    Right = 3,
};

class Player {
public:
    Player();

    int x() const;
    int y() const;
    int hp() const;
    int max_hp() const;
    Facing facing() const;
    int level() const;
    int xp() const;
    int skill_points() const;
    int base_attack() const;
    bool is_alive() const;

    void set_position(int x, int y);
    void set_facing(Facing f);

    // Returns true if damage killed the player.
    bool take_damage(int amount);
    void heal(int amount);
    void gain_xp(int amount);
    void set_form(const std::string& form);
    const std::string& form() const;

    // Full stats including equipment.
    int total_attack(const Inventory& inv) const;
    int total_defense(const Inventory& inv) const;

    Inventory& inventory();
    const Inventory& inventory() const;

private:
    int x_;
    int y_;
    int hp_;
    int max_hp_;
    Facing facing_;
    int level_;
    int xp_;
    int skill_points_;
    std::string form_;
    Inventory inventory_;
};

int xp_to_next_level(int level);

}  // namespace mythical
