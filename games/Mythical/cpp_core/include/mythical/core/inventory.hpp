#pragma once

#include "mythical/core/items.hpp"

#include <string>
#include <vector>

namespace mythical {

class Wallet {
public:
    Wallet();
    explicit Wallet(int coins);

    int coins() const;
    void add(int amount);
    bool spend(int amount);

private:
    int coins_;
};

struct ItemStack {
    std::string id;
    int quantity;
};

class Inventory {
public:
    Inventory();

    bool add(const std::string& id, int quantity = 1);
    bool remove(const std::string& id, int quantity = 1);
    int count(const std::string& id) const;
    bool has(const std::string& id, int quantity = 1) const;

    bool equip(const std::string& id);
    ItemLookup equipped_weapon() const;
    ItemLookup equipped_armor() const;
    ItemLookup equipped_accessory() const;

    bool set_hotbar(int slot, const std::string& id);
    ItemLookup hotbar_item(int slot) const;

    Wallet& wallet();
    const Wallet& wallet() const;

private:
    ItemStack* find_stack(const std::string& id);
    const ItemStack* find_stack(const std::string& id) const;

    std::vector<ItemStack> stacks_;
    std::string weapon_id_;
    std::string armor_id_;
    std::string accessory_id_;
    std::vector<std::string> hotbar_;
    Wallet wallet_;
};

}  // namespace mythical
