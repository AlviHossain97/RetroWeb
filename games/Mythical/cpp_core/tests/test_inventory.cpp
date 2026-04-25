#include "mythical/core/inventory.hpp"

#include <cstdlib>
#include <iostream>

static void require(bool condition, const char* message) {
    if (!condition) {
        std::cerr << "FAIL: " << message << "\n";
        std::exit(1);
    }
}

int main() {
    mythical::Inventory inventory;
    require(inventory.add("old_sword", 1), "can add old sword");
    require(inventory.add("health_potion", 3), "can add stacked potions");
    require(inventory.count("health_potion") == 3, "potion count is tracked");
    require(inventory.equip("old_sword"), "weapon can be equipped");
    require(inventory.equipped_weapon().has_value(), "equipped weapon exists");
    require(inventory.equipped_weapon()->id == "old_sword", "old sword is equipped");
    require(inventory.set_hotbar(0, "health_potion"), "can assign potion to hotbar");
    require(inventory.hotbar_item(0).has_value(), "hotbar item exists");
    require(inventory.hotbar_item(0)->id == "health_potion", "hotbar stores potion id");
    require(inventory.remove("health_potion", 1), "can consume one potion");
    require(inventory.count("health_potion") == 2, "potion count decrements");
    inventory.wallet().add(25);
    require(inventory.wallet().coins() == 25, "wallet stores coins");
    return 0;
}
