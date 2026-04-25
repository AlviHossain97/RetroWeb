#include "mythical/core/items.hpp"

namespace mythical {

namespace {

const ItemDef ITEMS[] = {
    {"old_sword", ItemCategory::Weapon, Rarity::Common, 0, 2, 1},
    {"forest_key", ItemCategory::Key, Rarity::Common, 0, 0, 1},
    {"herb", ItemCategory::Material, Rarity::Common, 1, 0, 64},
    {"amulet", ItemCategory::Accessory, Rarity::Uncommon, 10, 1, 1},
    {"mushroom", ItemCategory::Material, Rarity::Common, 1, 0, 64},
    {"letter", ItemCategory::Key, Rarity::Common, 0, 0, 1},
    {"cave_map", ItemCategory::Key, Rarity::Common, 0, 0, 1},
    {"boss_key", ItemCategory::Key, Rarity::Rare, 0, 0, 1},
    {"crystal", ItemCategory::Material, Rarity::Rare, 12, 0, 64},
    {"iron_sword", ItemCategory::Weapon, Rarity::Uncommon, 25, 4, 1},
    {"shadow_blade", ItemCategory::Weapon, Rarity::Rare, 60, 6, 1},
    {"fire_staff", ItemCategory::Weapon, Rarity::Rare, 60, 5, 1},
    {"ice_wand", ItemCategory::Weapon, Rarity::Rare, 60, 5, 1},
    {"leather_armor", ItemCategory::Armor, Rarity::Common, 20, 1, 1},
    {"iron_armor", ItemCategory::Armor, Rarity::Uncommon, 45, 2, 1},
    {"shadow_cloak", ItemCategory::Armor, Rarity::Rare, 70, 2, 1},
    {"mage_robes", ItemCategory::Armor, Rarity::Rare, 70, 2, 1},
    {"speed_ring", ItemCategory::Accessory, Rarity::Uncommon, 35, 1, 1},
    {"hunters_necklace", ItemCategory::Accessory, Rarity::Uncommon, 35, 1, 1},
    {"health_potion", ItemCategory::Consumable, Rarity::Common, 8, 0, 64},
    {"healing_orb", ItemCategory::Consumable, Rarity::Uncommon, 15, 0, 64},
    {"raw_meat", ItemCategory::Consumable, Rarity::Common, 3, 0, 64},
    {"cooked_meat", ItemCategory::Consumable, Rarity::Common, 7, 0, 64},
    {"antidote", ItemCategory::Consumable, Rarity::Common, 6, 0, 64},
    {"animal_hide", ItemCategory::Material, Rarity::Common, 3, 0, 64},
    {"bones", ItemCategory::Material, Rarity::Common, 2, 0, 64},
    {"crystal_shard", ItemCategory::Material, Rarity::Uncommon, 6, 0, 64},
    {"forest_herbs", ItemCategory::Material, Rarity::Common, 2, 0, 64},
    {"mushroom_spore", ItemCategory::Material, Rarity::Common, 2, 0, 64},
    {"iron_ore", ItemCategory::Material, Rarity::Common, 4, 0, 64},
    {"iron_ingot", ItemCategory::Material, Rarity::Uncommon, 10, 0, 64},
    {"shadow_dust", ItemCategory::Material, Rarity::Rare, 14, 0, 64},
    {"fire_essence", ItemCategory::Material, Rarity::Rare, 14, 0, 64},
    {"ancient_tome", ItemCategory::Key, Rarity::Rare, 0, 0, 1},
    {"lore_fragment", ItemCategory::Key, Rarity::Uncommon, 0, 0, 64},
    {"hunters_bow", ItemCategory::Weapon, Rarity::Uncommon, 40, 4, 1},
    {"runic_bow", ItemCategory::Weapon, Rarity::Epic, 90, 7, 1},
    {"runic_sword", ItemCategory::Weapon, Rarity::Epic, 95, 8, 1},
    {"shadow_mail", ItemCategory::Armor, Rarity::Epic, 85, 4, 1},
    {"speed_talisman", ItemCategory::Accessory, Rarity::Rare, 75, 2, 1},
    {"runic_crystal", ItemCategory::Material, Rarity::Epic, 25, 0, 64},
    {"bone_arrow", ItemCategory::Material, Rarity::Common, 2, 0, 64},
    {"revenant_core", ItemCategory::Material, Rarity::Rare, 18, 0, 64},
    {"mythblade", ItemCategory::Weapon, Rarity::Mythic, 150, 10, 1},
    {"ascended_aegis", ItemCategory::Armor, Rarity::Mythic, 150, 6, 1},
    {"sovereign_crown", ItemCategory::Accessory, Rarity::Mythic, 150, 5, 1},
    {"void_shard", ItemCategory::Material, Rarity::Mythic, 40, 0, 64},
    {"mythic_core", ItemCategory::Material, Rarity::Mythic, 50, 0, 1},
};

}  // namespace

ItemLookup::ItemLookup(const ItemDef* item) : item_(item) {}

bool ItemLookup::has_value() const {
    return item_ != nullptr;
}

const ItemDef& ItemLookup::value() const {
    return *item_;
}

const ItemDef* ItemLookup::operator->() const {
    return item_;
}

ItemLookup find_item_def(const std::string& id) {
    for (const auto& item : ITEMS) {
        if (item.id == id) {
            return ItemLookup(&item);
        }
    }
    return ItemLookup(nullptr);
}

int shipped_item_count() {
    return static_cast<int>(sizeof(ITEMS) / sizeof(ITEMS[0]));
}

}  // namespace mythical
