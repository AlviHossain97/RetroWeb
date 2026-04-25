#pragma once

#include "mythical/core/save.hpp"

#include <string>

namespace mythical::port {

bool save_to_file(const SaveState& state, const std::string& path);
SaveResult load_from_file(const std::string& path);

}  // namespace mythical::port
