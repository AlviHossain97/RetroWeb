#include "mythical/core/quests.hpp"

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

    QuestLog log;
    require(log.stage("find_key") == QuestStage::Inactive, "unknown quest is inactive");

    log.start("find_key");
    require(log.is_active("find_key"), "started quest is active");
    require(log.active_count() == 1, "one active quest");

    require(log.complete("find_key"), "can complete active quest");
    require(log.is_complete("find_key"), "quest now complete");
    require(log.active_count() == 0, "no active left");
    require(log.completed_count() == 1, "one completed");

    require(!log.complete("find_key"), "cannot re-complete");
    require(!log.complete("nonexistent"), "cannot complete unknown");

    return 0;
}
