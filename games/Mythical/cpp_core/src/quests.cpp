#include "mythical/core/quests.hpp"

namespace mythical {

QuestLog::QuestLog() = default;

Quest* QuestLog::find(const std::string& id) {
    for (auto& q : quests_) {
        if (q.id == id) return &q;
    }
    return nullptr;
}

const Quest* QuestLog::find(const std::string& id) const {
    for (const auto& q : quests_) {
        if (q.id == id) return &q;
    }
    return nullptr;
}

void QuestLog::start(const std::string& id) {
    if (auto* existing = find(id)) {
        if (existing->stage == QuestStage::Inactive) {
            existing->stage = QuestStage::Active;
        }
        return;
    }
    quests_.push_back({id, QuestStage::Active});
}

bool QuestLog::complete(const std::string& id) {
    auto* q = find(id);
    if (!q || q->stage != QuestStage::Active) return false;
    q->stage = QuestStage::Complete;
    return true;
}

QuestStage QuestLog::stage(const std::string& id) const {
    const auto* q = find(id);
    return q ? q->stage : QuestStage::Inactive;
}

bool QuestLog::is_active(const std::string& id) const {
    return stage(id) == QuestStage::Active;
}

bool QuestLog::is_complete(const std::string& id) const {
    return stage(id) == QuestStage::Complete;
}

int QuestLog::active_count() const {
    int n = 0;
    for (const auto& q : quests_) if (q.stage == QuestStage::Active) ++n;
    return n;
}

int QuestLog::completed_count() const {
    int n = 0;
    for (const auto& q : quests_) if (q.stage == QuestStage::Complete) ++n;
    return n;
}

const std::vector<Quest>& QuestLog::quests() const { return quests_; }

}  // namespace mythical
