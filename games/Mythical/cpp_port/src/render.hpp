#pragma once

#include "mythical/core/world.hpp"

#include <string>

namespace mythical::port {

// Render the world as an ASCII frame centered on the player.
std::string render_frame(const World& w, int view_w = 40, int view_h = 18);

// Render a status line showing HP/Level/Map/Coins.
std::string render_status(const World& w);

// Render the inventory as a short multi-line string.
std::string render_inventory(const World& w);

}  // namespace mythical::port
