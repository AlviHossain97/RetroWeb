#pragma once

#include <string>

namespace mythical {

class StageAdvance {
public:
    StageAdvance();
    explicit StageAdvance(int stage);

    bool has_value() const;
    int operator*() const;

private:
    bool has_value_;
    int stage_;
};

class Campaign {
public:
    Campaign();
    Campaign(int world_stage, bool final_stage_complete, const std::string& form);

    int world_stage() const;
    bool is_stage_unlocked(int stage) const;
    bool is_final_stage_complete() const;
    std::string entry_map() const;
    std::string stage_name() const;
    std::string loot_tier() const;
    std::string current_form() const;

    StageAdvance on_boss_defeated(const std::string& boss_id);
    void complete_stage(int stage);
    void unlock_player_form(const std::string& form);

private:
    int world_stage_;
    bool final_stage_complete_;
    std::string current_form_;
};

}  // namespace mythical
