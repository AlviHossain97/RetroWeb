#include "mythical/core/maps.hpp"

namespace mythical {

MapRegistry::MapRegistry(std::vector<MapDef> maps) : maps_(maps) {}

MapRegistry MapRegistry::shipped() {
    return MapRegistry({
        {"village", 50, 36, 1},
        {"dungeon", 40, 40, 1},
        {"ruins_approach", 50, 36, 2},
        {"ruins_depths", 60, 40, 2},
        {"sanctum_halls", 60, 40, 3},
        {"throne_room", 50, 36, 3},
    });
}

int MapRegistry::size() const {
    return static_cast<int>(maps_.size());
}

bool MapRegistry::contains(const std::string& id) const {
    return find(id) != nullptr;
}

bool MapRegistry::can_enter(const std::string& id, const Campaign& campaign) const {
    const MapDef* map = find(id);
    return map != nullptr && campaign.is_stage_unlocked(map->required_stage);
}

const MapDef* MapRegistry::find(const std::string& id) const {
    for (const auto& map : maps_) {
        if (map.id == id) {
            return &map;
        }
    }
    return nullptr;
}

int MapRegistry::map_index(const std::string& id) const {
    for (int i = 0; i < static_cast<int>(maps_.size()); ++i) {
        if (maps_[i].id == id) {
            return i;
        }
    }
    return 0;
}

std::string MapRegistry::map_id_at(int index) const {
    if (index < 0 || index >= static_cast<int>(maps_.size())) {
        return maps_.empty() ? std::string() : maps_[0].id;
    }
    return maps_[index].id;
}

}  // namespace mythical
