#include "mythical/core/save.hpp"

#include "mythical/core/maps.hpp"

namespace mythical {

namespace {

const unsigned char SAVE_MAGIC[4] = {'M', 'Y', 'T', 'H'};
const unsigned char SAVE_VERSION = 1;

void write_u8(std::vector<unsigned char>& out, int value) {
    out.push_back(static_cast<unsigned char>(value & 0xff));
}

void write_u16(std::vector<unsigned char>& out, int value) {
    out.push_back(static_cast<unsigned char>(value & 0xff));
    out.push_back(static_cast<unsigned char>((value >> 8) & 0xff));
}

int read_u8(const std::vector<unsigned char>& bytes, int& offset) {
    if (offset >= static_cast<int>(bytes.size())) {
        return 0;
    }
    return bytes[offset++];
}

int read_u16(const std::vector<unsigned char>& bytes, int& offset) {
    const int low = read_u8(bytes, offset);
    const int high = read_u8(bytes, offset);
    return low | (high << 8);
}

int form_id(const std::string& form) {
    if (form == "hero") {
        return 1;
    }
    if (form == "mythic") {
        return 2;
    }
    return 0;
}

std::string form_from_id(int id) {
    if (id == 1) {
        return "hero";
    }
    if (id == 2) {
        return "mythic";
    }
    return "base";
}

}  // namespace

SaveResult::SaveResult() : has_value_(false), state_() {}

SaveResult::SaveResult(const SaveState& state) : has_value_(true), state_(state) {}

bool SaveResult::has_value() const {
    return has_value_;
}

const SaveState& SaveResult::value() const {
    return state_;
}

const SaveState* SaveResult::operator->() const {
    return &state_;
}

std::vector<unsigned char> pack_save(const SaveState& state) {
    std::vector<unsigned char> out;
    for (unsigned char byte : SAVE_MAGIC) {
        out.push_back(byte);
    }
    write_u8(out, SAVE_VERSION);
    write_u8(out, state.campaign.world_stage());
    write_u8(out, state.campaign.is_final_stage_complete() ? 1 : 0);
    write_u8(out, form_id(state.campaign.current_form()));

    const auto maps = MapRegistry::shipped();
    write_u8(out, maps.map_index(state.current_map));
    write_u16(out, state.player_x);
    write_u16(out, state.player_y);
    write_u16(out, state.coins);
    return out;
}

SaveResult unpack_save(const std::vector<unsigned char>& bytes) {
    if (bytes.size() < 13) {
        return SaveResult();
    }
    for (int i = 0; i < 4; ++i) {
        if (bytes[i] != SAVE_MAGIC[i]) {
            return SaveResult();
        }
    }
    int offset = 4;
    const int version = read_u8(bytes, offset);
    if (version != SAVE_VERSION) {
        return SaveResult();
    }

    const int world_stage = read_u8(bytes, offset);
    const bool final_complete = read_u8(bytes, offset) != 0;
    const std::string form = form_from_id(read_u8(bytes, offset));
    const int map_index = read_u8(bytes, offset);

    SaveState state;
    state.campaign = Campaign(world_stage, final_complete, form);
    state.current_map = MapRegistry::shipped().map_id_at(map_index);
    state.player_x = read_u16(bytes, offset);
    state.player_y = read_u16(bytes, offset);
    state.coins = read_u16(bytes, offset);
    return SaveResult(state);
}

}  // namespace mythical
