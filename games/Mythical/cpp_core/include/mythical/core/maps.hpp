#pragma once

#include "mythical/core/campaign.hpp"

#include <string>
#include <vector>

namespace mythical {

struct MapDef {
    std::string id;
    int width;
    int height;
    int required_stage;
};

class MapRegistry {
public:
    static MapRegistry shipped();

    int size() const;
    bool contains(const std::string& id) const;
    bool can_enter(const std::string& id, const Campaign& campaign) const;
    const MapDef* find(const std::string& id) const;
    int map_index(const std::string& id) const;
    std::string map_id_at(int index) const;

private:
    explicit MapRegistry(std::vector<MapDef> maps);

    std::vector<MapDef> maps_;
};

}  // namespace mythical
