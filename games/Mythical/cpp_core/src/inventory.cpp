#include "mythical/core/inventory.hpp"

namespace mythical {

Wallet::Wallet() : coins_(0) {}

Wallet::Wallet(int coins) : coins_(coins < 0 ? 0 : coins) {}

int Wallet::coins() const {
    return coins_;
}

void Wallet::add(int amount) {
    if (amount > 0) {
        coins_ += amount;
    }
}

bool Wallet::spend(int amount) {
    if (amount < 0 || amount > coins_) {
        return false;
    }
    coins_ -= amount;
    return true;
}

Inventory::Inventory() : hotbar_(9), wallet_() {}

bool Inventory::add(const std::string& id, int quantity) {
    const auto def = find_item_def(id);
    if (!def.has_value() || quantity <= 0) {
        return false;
    }

    ItemStack* existing = find_stack(id);
    if (existing) {
        existing->quantity += quantity;
        if (existing->quantity > def->stack_size) {
            existing->quantity = def->stack_size;
        }
        return true;
    }

    const int amount = quantity > def->stack_size ? def->stack_size : quantity;
    stacks_.push_back({id, amount});
    return true;
}

bool Inventory::remove(const std::string& id, int quantity) {
    if (quantity <= 0) {
        return false;
    }
    for (auto it = stacks_.begin(); it != stacks_.end(); ++it) {
        if (it->id == id) {
            if (it->quantity < quantity) {
                return false;
            }
            it->quantity -= quantity;
            if (it->quantity == 0) {
                stacks_.erase(it);
            }
            return true;
        }
    }
    return false;
}

int Inventory::count(const std::string& id) const {
    const ItemStack* stack = find_stack(id);
    return stack ? stack->quantity : 0;
}

bool Inventory::has(const std::string& id, int quantity) const {
    return count(id) >= quantity;
}

bool Inventory::equip(const std::string& id) {
    if (!has(id)) {
        return false;
    }
    const auto def = find_item_def(id);
    if (!def.has_value()) {
        return false;
    }
    if (def->category == ItemCategory::Weapon) {
        weapon_id_ = id;
        return true;
    }
    if (def->category == ItemCategory::Armor) {
        armor_id_ = id;
        return true;
    }
    if (def->category == ItemCategory::Accessory) {
        accessory_id_ = id;
        return true;
    }
    return false;
}

ItemLookup Inventory::equipped_weapon() const {
    return find_item_def(weapon_id_);
}

ItemLookup Inventory::equipped_armor() const {
    return find_item_def(armor_id_);
}

ItemLookup Inventory::equipped_accessory() const {
    return find_item_def(accessory_id_);
}

bool Inventory::set_hotbar(int slot, const std::string& id) {
    if (slot < 0 || slot >= static_cast<int>(hotbar_.size()) || !has(id)) {
        return false;
    }
    hotbar_[slot] = id;
    return true;
}

ItemLookup Inventory::hotbar_item(int slot) const {
    if (slot < 0 || slot >= static_cast<int>(hotbar_.size())) {
        return ItemLookup(nullptr);
    }
    return find_item_def(hotbar_[slot]);
}

Wallet& Inventory::wallet() {
    return wallet_;
}

const Wallet& Inventory::wallet() const {
    return wallet_;
}

ItemStack* Inventory::find_stack(const std::string& id) {
    for (auto& stack : stacks_) {
        if (stack.id == id) {
            return &stack;
        }
    }
    return nullptr;
}

const ItemStack* Inventory::find_stack(const std::string& id) const {
    for (const auto& stack : stacks_) {
        if (stack.id == id) {
            return &stack;
        }
    }
    return nullptr;
}

}  // namespace mythical
