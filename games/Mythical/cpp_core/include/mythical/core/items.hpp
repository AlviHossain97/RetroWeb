#pragma once

#include <string>

namespace mythical {

enum class ItemCategory {
    Weapon,
    Armor,
    Consumable,
    Material,
    Key,
    Accessory,
};

enum class Rarity {
    Common,
    Uncommon,
    Rare,
    Epic,
    Legendary,
    Mythic,
};

struct ItemDef {
    std::string id;
    ItemCategory category;
    Rarity rarity;
    int value;
    int stat_bonus;
    int stack_size;
};

class ItemLookup {
public:
    explicit ItemLookup(const ItemDef* item);

    bool has_value() const;
    const ItemDef& value() const;
    const ItemDef* operator->() const;

private:
    const ItemDef* item_;
};

ItemLookup find_item_def(const std::string& id);
int shipped_item_count();

}  // namespace mythical
