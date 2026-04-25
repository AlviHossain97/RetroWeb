#include "mythical/core/campaign.hpp"

namespace mythical {

namespace {

const char* entry_map_for_stage(int stage) {
    switch (stage) {
        case 1:
            return "village";
        case 2:
            return "ruins_approach";
        case 3:
            return "sanctum_halls";
        default:
            return "village";
    }
}

const char* stage_name_for_stage(int stage) {
    switch (stage) {
        case 1:
            return "Act I";
        case 2:
            return "Act II";
        case 3:
            return "Act III";
        default:
            return "Act I";
    }
}

const char* loot_tier_for_stage(int stage) {
    switch (stage) {
        case 1:
            return "common";
        case 2:
            return "rare";
        case 3:
            return "mythic";
        default:
            return "common";
    }
}

}  // namespace

StageAdvance::StageAdvance() : has_value_(false), stage_(0) {}

StageAdvance::StageAdvance(int stage) : has_value_(true), stage_(stage) {}

bool StageAdvance::has_value() const {
    return has_value_;
}

int StageAdvance::operator*() const {
    return stage_;
}

Campaign::Campaign()
    : world_stage_(1), final_stage_complete_(false), current_form_("base") {}

Campaign::Campaign(int world_stage, bool final_stage_complete, const std::string& form)
    : world_stage_(world_stage),
      final_stage_complete_(final_stage_complete),
      current_form_(form) {
    if (world_stage_ < 1) {
        world_stage_ = 1;
    }
    if (world_stage_ > 3) {
        world_stage_ = 3;
    }
    if (current_form_ != "base" && current_form_ != "hero" && current_form_ != "mythic") {
        current_form_ = "base";
    }
}

int Campaign::world_stage() const {
    return world_stage_;
}

bool Campaign::is_stage_unlocked(int stage) const {
    return stage >= 1 && stage <= world_stage_;
}

bool Campaign::is_final_stage_complete() const {
    return final_stage_complete_;
}

std::string Campaign::entry_map() const {
    return entry_map_for_stage(world_stage_);
}

std::string Campaign::stage_name() const {
    return stage_name_for_stage(world_stage_);
}

std::string Campaign::loot_tier() const {
    return loot_tier_for_stage(world_stage_);
}

std::string Campaign::current_form() const {
    return current_form_;
}

StageAdvance Campaign::on_boss_defeated(const std::string& boss_id) {
    if (boss_id == "dark_golem") {
        complete_stage(1);
        world_stage_ = 2;
        unlock_player_form("hero");
        return StageAdvance(2);
    }
    if (boss_id == "gravewarden") {
        complete_stage(2);
        world_stage_ = 3;
        unlock_player_form("mythic");
        return StageAdvance(3);
    }
    if (boss_id == "mythic_sovereign") {
        complete_stage(3);
        final_stage_complete_ = true;
        return StageAdvance();
    }
    return StageAdvance();
}

void Campaign::complete_stage(int stage) {
    if (stage >= 3) {
        final_stage_complete_ = true;
    }
}

void Campaign::unlock_player_form(const std::string& form) {
    current_form_ = form;
}

}  // namespace mythical
