// SRAM-backed SaveManager for the butano/GBA build. Bytes 0..27 of SRAM
// hold the same layout used by the original gba_project so existing dashboard
// tooling keeps working. Checksum = unsigned sum of the preceding 24 bytes.

#include "core/save_manager.h"

#include "bn_sram.h"

#include <cstdint>
#include <cstring>

namespace {

constexpr std::uint32_t kMagic = 0x42535444; // "BSTD"
constexpr std::uint32_t kVersion = 1;

struct SramLayout {
    std::uint32_t magic;
    std::uint32_t version;
    std::uint32_t high_score;
    std::uint32_t total_games;
    std::uint32_t total_wins;
    std::uint8_t  selected_tower;
    std::uint8_t  padding[3];
    std::uint32_t checksum;
};

std::uint32_t compute_checksum(const SramLayout& s) {
    std::uint32_t sum = 0;
    const auto* p = reinterpret_cast<const std::uint8_t*>(&s);
    const int len = static_cast<int>(sizeof(SramLayout) - sizeof(std::uint32_t));
    for (int i = 0; i < len; ++i) {
        sum += p[i];
    }
    return sum;
}

SramLayout read_layout() {
    SramLayout s{};
    bn::sram::read(s);
    return s;
}

void write_layout(SramLayout& s) {
    s.checksum = compute_checksum(s);
    bn::sram::write(s);
}

bool valid(const SramLayout& s) {
    return s.magic == kMagic && s.version == kVersion && s.checksum == compute_checksum(s);
}

} // namespace

SaveData SaveManager::load() const {
    SaveData out;
    SramLayout s = read_layout();
    if (!valid(s)) {
        return out;
    }
    out.best_wave    = static_cast<int>(s.total_wins);
    out.best_score   = static_cast<int>(s.high_score);
    out.games_played = static_cast<int>(s.total_games);
    return out;
}

void SaveManager::save(const SaveData& data) const {
    SramLayout s = read_layout();
    if (!valid(s)) {
        std::memset(&s, 0, sizeof(s));
        s.magic = kMagic;
        s.version = kVersion;
    }
    s.high_score  = static_cast<std::uint32_t>(data.best_score);
    s.total_wins  = static_cast<std::uint32_t>(data.best_wave);
    s.total_games = static_cast<std::uint32_t>(data.games_played);
    write_layout(s);
}

void SaveManager::record_result(int wave, int score) {
    SaveData data = load();
    if (wave > data.best_wave) {
        data.best_wave = wave;
    }
    if (score > data.best_score) {
        data.best_score = score;
    }
    save(data);
}

void SaveManager::increment_games() {
    SaveData data = load();
    data.games_played += 1;
    save(data);
}
