#include "mythical/core/campaign.hpp"
#include "mythical/core/maps.hpp"
#include "mythical/core/save.hpp"

#include <cstdlib>
#include <iostream>

static void require(bool condition, const char* message) {
    if (!condition) {
        std::cerr << "FAIL: " << message << "\n";
        std::exit(1);
    }
}

int main() {
    mythical::Campaign campaign;
    const auto maps = mythical::MapRegistry::shipped();
    require(maps.size() == 6, "six shipped maps are registered");
    require(maps.can_enter("village", campaign), "village is open at start");
    require(!maps.can_enter("ruins_approach", campaign), "ruins are gated before stage 2");
    campaign.on_boss_defeated("dark_golem");
    require(maps.can_enter("ruins_approach", campaign), "ruins unlock after boss 1");

    mythical::SaveState state;
    state.campaign = campaign;
    state.current_map = "ruins_approach";
    state.player_x = 12;
    state.player_y = 18;
    state.coins = 33;
    const auto bytes = mythical::pack_save(state);
    const auto restored = mythical::unpack_save(bytes);
    require(restored.has_value(), "save round trip succeeds");
    require(restored->campaign.world_stage() == 2, "campaign stage survives save");
    require(restored->campaign.current_form() == "hero", "form survives save");
    require(restored->current_map == "ruins_approach", "map survives save");
    require(restored->player_x == 12, "player x survives save");
    require(restored->player_y == 18, "player y survives save");
    require(restored->coins == 33, "wallet survives save");
    return 0;
}
