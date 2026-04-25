#pragma once

#include "mythical/core/campaign.hpp"

#include <string>
#include <vector>

namespace mythical {

struct SaveState {
    Campaign campaign;
    std::string current_map;
    int player_x = 0;
    int player_y = 0;
    int coins = 0;
};

class SaveResult {
public:
    SaveResult();
    explicit SaveResult(const SaveState& state);

    bool has_value() const;
    const SaveState& value() const;
    const SaveState* operator->() const;

private:
    bool has_value_;
    SaveState state_;
};

std::vector<unsigned char> pack_save(const SaveState& state);
SaveResult unpack_save(const std::vector<unsigned char>& bytes);

}  // namespace mythical
