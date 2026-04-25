#include "mythical/core/campaign.hpp"

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
    require(campaign.world_stage() == 1, "new campaign starts at stage 1");
    require(campaign.entry_map() == "village", "stage 1 entry map is village");
    require(!campaign.is_stage_unlocked(2), "stage 2 starts locked");

    const auto next = campaign.on_boss_defeated("dark_golem");
    require(next.has_value(), "dark golem defeat unlocks next stage");
    require(*next == 2, "dark golem unlocks stage 2");
    require(campaign.world_stage() == 2, "world stage updates to 2");
    require(campaign.current_form() == "hero", "stage 2 unlocks hero form");
    require(campaign.entry_map() == "ruins_approach", "stage 2 entry map is ruins approach");

    const auto stage_three = campaign.on_boss_defeated("gravewarden");
    require(stage_three.has_value(), "gravewarden defeat unlocks next stage");
    require(*stage_three == 3, "gravewarden unlocks stage 3");
    require(campaign.current_form() == "mythic", "stage 3 unlocks mythic form");

    const auto final_next = campaign.on_boss_defeated("mythic_sovereign");
    require(!final_next.has_value(), "final boss has no next stage");
    require(campaign.is_final_stage_complete(), "final boss completes campaign");

    return 0;
}
