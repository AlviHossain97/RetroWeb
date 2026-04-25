#pragma once

struct SaveData {
    int best_wave = 0;
    int best_score = 0;
    int games_played = 0;
};

struct SaveManager {
    const char* path = "bastion_td_save.json";

    SaveData load() const;
    void save(const SaveData& data) const;
    void record_result(int wave, int score);
    void increment_games();
};
