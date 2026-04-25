#include "save_io.hpp"

#include <cstdio>
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
    using namespace mythical::port;

    const std::string path = "test_save_io_tmp.bin";
    std::remove(path.c_str());

    SaveState st;
    st.campaign = Campaign(2, false, "hero");
    st.current_map = "ruins_approach";
    st.player_x = 15;
    st.player_y = 7;
    st.coins = 99;

    require(save_to_file(st, path), "write save");
    const auto loaded = load_from_file(path);
    require(loaded.has_value(), "read save back");
    require(loaded->current_map == "ruins_approach", "map round trip");
    require(loaded->player_x == 15 && loaded->player_y == 7, "position round trip");
    require(loaded->coins == 99, "coins round trip");
    require(loaded->campaign.world_stage() == 2, "campaign round trip");
    require(loaded->campaign.current_form() == "hero", "form round trip");

    std::remove(path.c_str());
    return 0;
}
