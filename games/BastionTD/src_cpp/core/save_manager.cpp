#include "core/save_manager.h"

#ifndef BASTION_GBA

#include <cctype>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <sstream>
#include <string>

namespace {

// Minimal JSON scalar lookup: finds "key" then the integer after the next ':'.
// Tolerates whitespace and trailing commas. Format stays compatible with the
// python save_manager.py, which writes a flat object of int values.
int find_int(const std::string& text, const char* key, int fallback) {
    std::string needle = "\"";
    needle += key;
    needle += "\"";
    auto pos = text.find(needle);
    if (pos == std::string::npos) {
        return fallback;
    }
    pos = text.find(':', pos + needle.size());
    if (pos == std::string::npos) {
        return fallback;
    }
    ++pos;
    while (pos < text.size() && std::isspace(static_cast<unsigned char>(text[pos]))) {
        ++pos;
    }
    int sign = 1;
    if (pos < text.size() && text[pos] == '-') {
        sign = -1;
        ++pos;
    }
    int value = 0;
    bool seen = false;
    while (pos < text.size() && std::isdigit(static_cast<unsigned char>(text[pos]))) {
        value = value * 10 + (text[pos] - '0');
        seen = true;
        ++pos;
    }
    return seen ? value * sign : fallback;
}

} // namespace

SaveData SaveManager::load() const {
    SaveData data;
    std::ifstream in(path);
    if (!in.is_open()) {
        return data;
    }
    std::stringstream buf;
    buf << in.rdbuf();
    const std::string text = buf.str();
    data.best_wave    = find_int(text, "best_wave", 0);
    data.best_score   = find_int(text, "best_score", 0);
    data.games_played = find_int(text, "games_played", 0);
    return data;
}

void SaveManager::save(const SaveData& data) const {
    std::ofstream out(path, std::ios::trunc);
    if (!out.is_open()) {
        return;
    }
    out << "{\n"
        << "  \"best_wave\": " << data.best_wave << ",\n"
        << "  \"best_score\": " << data.best_score << ",\n"
        << "  \"games_played\": " << data.games_played << "\n"
        << "}\n";
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

#endif // BASTION_GBA
