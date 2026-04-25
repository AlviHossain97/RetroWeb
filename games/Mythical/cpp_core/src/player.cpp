#include "mythical/core/player.hpp"

namespace mythical {

namespace {

int max_hp_for_level(int level, const std::string& form) {
    int base = 20 + (level - 1) * 4;
    if (form == "hero") base += 10;
    else if (form == "mythic") base += 25;
    return base;
}

int attack_for_level(int level, const std::string& form) {
    int base = 3 + level / 2;
    if (form == "hero") base += 2;
    else if (form == "mythic") base += 5;
    return base;
}

}  // namespace

int xp_to_next_level(int level) {
    if (level < 1) level = 1;
    return 20 + (level - 1) * 15;
}

Player::Player()
    : x_(0), y_(0),
      hp_(20), max_hp_(20),
      facing_(Facing::Down),
      level_(1), xp_(0), skill_points_(0),
      form_("base") {}

int Player::x() const { return x_; }
int Player::y() const { return y_; }
int Player::hp() const { return hp_; }
int Player::max_hp() const { return max_hp_; }
Facing Player::facing() const { return facing_; }
int Player::level() const { return level_; }
int Player::xp() const { return xp_; }
int Player::skill_points() const { return skill_points_; }
int Player::base_attack() const { return attack_for_level(level_, form_); }
bool Player::is_alive() const { return hp_ > 0; }

void Player::set_position(int x, int y) { x_ = x; y_ = y; }
void Player::set_facing(Facing f) { facing_ = f; }

bool Player::take_damage(int amount) {
    if (amount <= 0) return false;
    hp_ -= amount;
    if (hp_ <= 0) {
        hp_ = 0;
        return true;
    }
    return false;
}

void Player::heal(int amount) {
    if (amount <= 0) return;
    hp_ += amount;
    if (hp_ > max_hp_) hp_ = max_hp_;
}

void Player::gain_xp(int amount) {
    if (amount <= 0) return;
    xp_ += amount;
    while (xp_ >= xp_to_next_level(level_)) {
        xp_ -= xp_to_next_level(level_);
        ++level_;
        ++skill_points_;
        max_hp_ = max_hp_for_level(level_, form_);
        hp_ = max_hp_;
    }
}

void Player::set_form(const std::string& form) {
    form_ = form;
    const int prev_max = max_hp_;
    max_hp_ = max_hp_for_level(level_, form_);
    // Heal the difference when promoting to a stronger form.
    if (max_hp_ > prev_max) {
        hp_ += (max_hp_ - prev_max);
        if (hp_ > max_hp_) hp_ = max_hp_;
    }
}

const std::string& Player::form() const { return form_; }

int Player::total_attack(const Inventory& inv) const {
    int total = base_attack();
    const auto weapon = inv.equipped_weapon();
    if (weapon.has_value()) total += weapon->stat_bonus;
    const auto acc = inv.equipped_accessory();
    if (acc.has_value()) total += acc->stat_bonus;
    return total;
}

int Player::total_defense(const Inventory& inv) const {
    int total = 0;
    const auto armor = inv.equipped_armor();
    if (armor.has_value()) total += armor->stat_bonus;
    return total;
}

Inventory& Player::inventory() { return inventory_; }
const Inventory& Player::inventory() const { return inventory_; }

}  // namespace mythical
