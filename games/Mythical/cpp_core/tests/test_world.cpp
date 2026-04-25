#include "mythical/core/world.hpp"

#include <cstdlib>
#include <iostream>

static void require(bool condition, const char* message) {
    if (!condition) {
        std::cerr << "FAIL: " << message << "\n";
        std::exit(1);
    }
}

int main() {
    using namespace mythical;

    World w;
    require(w.current_map() == "village", "world starts in village");
    require(w.tilemap().width() == 50, "village is 50 wide");
    require(w.tilemap().height() == 36, "village is 36 tall");
    require(w.player().x() == 24 && w.player().y() == 18, "player spawn in village");
    require(!w.enemies().empty(), "village has enemies");

    // Cannot enter ruins before stage 2.
    auto fail = w.enter_map("ruins_approach");
    require(!fail.ok, "ruins gated before stage 2");

    // Can enter dungeon.
    auto ok = w.enter_map("dungeon");
    require(ok.ok, "can enter dungeon");
    require(w.current_map() == "dungeon", "current map updated");

    // Simulate defeating dark_golem.
    auto adv = w.defeat_boss("dark_golem");
    require(adv.has_value() && *adv == 2, "boss unlocks stage 2");
    require(w.player().form() != "hero", "player form on world is not auto-synced (campaign owns form)");

    // Now ruins_approach is enterable.
    auto r2 = w.enter_map("ruins_approach");
    require(r2.ok, "ruins open after boss 1");

    // Move player: place them on a known floor tile.
    w.player().set_position(20, 15);
    const auto outcome = w.move_player(Direction::East);
    require(outcome == StepOutcome::Moved || outcome == StepOutcome::Blocked ||
            outcome == StepOutcome::BumpedEnemy || outcome == StepOutcome::ReachedExit,
            "move returns a known outcome");

    return 0;
}
