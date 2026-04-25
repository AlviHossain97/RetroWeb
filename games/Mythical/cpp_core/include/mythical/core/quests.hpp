#pragma once

#include <string>
#include <vector>

namespace mythical {

enum class QuestStage : unsigned char {
    Inactive = 0,
    Active = 1,
    Complete = 2,
};

struct Quest {
    std::string id;
    QuestStage stage = QuestStage::Inactive;
};

class QuestLog {
public:
    QuestLog();

    void start(const std::string& id);
    bool complete(const std::string& id);
    QuestStage stage(const std::string& id) const;
    bool is_active(const std::string& id) const;
    bool is_complete(const std::string& id) const;
    int active_count() const;
    int completed_count() const;

    const std::vector<Quest>& quests() const;

private:
    std::vector<Quest> quests_;
    Quest* find(const std::string& id);
    const Quest* find(const std::string& id) const;
};

}  // namespace mythical
