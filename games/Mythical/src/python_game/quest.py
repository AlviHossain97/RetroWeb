"""
Quest tracker — drives the main story progression.
Each quest has stages that advance via triggers (item pickup, NPC talk, etc.).
On GBA: a small struct in SRAM with stage indices.
"""


class Quest:
    def __init__(self, quest_id: str, name: str, stages: list[dict]):
        """
        stages: list of {
            "desc": str,           # journal description
            "trigger": str,        # what advances this stage
            "trigger_data": any,   # context for the trigger
        }
        """
        self.id = quest_id
        self.name = name
        self.stages = stages
        self.stage = 0
        self.complete = False

    @property
    def current_desc(self) -> str:
        if self.complete:
            return "Complete!"
        if self.stage < len(self.stages):
            return self.stages[self.stage]["desc"]
        return ""

    def advance(self):
        self.stage += 1
        if self.stage >= len(self.stages):
            self.complete = True

    def check_trigger(self, trigger: str, data=None) -> bool:
        """Check if the current stage's trigger matches. Returns True if stage advances."""
        if self.complete or self.stage >= len(self.stages):
            return False
        s = self.stages[self.stage]
        if s["trigger"] == trigger:
            if s.get("trigger_data") is None or s["trigger_data"] == data:
                self.advance()
                return True
        return False


class QuestManager:
    def __init__(self):
        self.quests: dict[str, Quest] = {}
        self._init_quests()

    def _init_quests(self):
        # Stage 1 main quest: investigate the forest
        self.quests["main"] = Quest(
            quest_id="main",
            name="The Eastern Forest",
            stages=[
                {
                    "desc": "Talk to Elder Rowan in the village.",
                    "trigger": "talk_npc",
                    "trigger_data": "elder",
                },
                {
                    "desc": "Find the Old Sword. Check the chest in the garden.",
                    "trigger": "pickup_item",
                    "trigger_data": "old_sword",
                },
                {
                    "desc": "Get the Forest Key from Merchant Lira.",
                    "trigger": "talk_npc",
                    "trigger_data": "merchant",
                },
                {
                    "desc": "Bring the Healing Herb to Gardener Fenn.",
                    "trigger": "talk_npc",
                    "trigger_data": "gardener",
                },
                {
                    "desc": "Cross the bridge. Enter the dungeon cave.",
                    "trigger": "talk_npc",
                    "trigger_data": "elder",
                },
                {
                    "desc": "Defeat the Dark Golem in the boss chamber.",
                    "trigger": "boss_defeated",
                    "trigger_data": "golem",
                },
            ],
        )

        # Stage 2 quest: the Haunted Ruins
        self.quests["main_s2"] = Quest(
            quest_id="main_s2",
            name="The Haunted Ruins",
            stages=[
                {
                    "desc": "Explore the ruins approach. Find a guide.",
                    "trigger": "map_entered",
                    "trigger_data": "ruins_approach",
                },
                {
                    "desc": "Push into the ruins depths.",
                    "trigger": "map_entered",
                    "trigger_data": "ruins_depths",
                },
                {
                    "desc": "Defeat the Gravewarden in the depths.",
                    "trigger": "boss_defeated",
                    "trigger_data": "gravewarden",
                },
            ],
        )

        # Stage 3 quest: the Mythic Sanctum
        self.quests["main_s3"] = Quest(
            quest_id="main_s3",
            name="The Mythic Sanctum",
            stages=[
                {
                    "desc": "Ascend into the Mythic Sanctum halls.",
                    "trigger": "map_entered",
                    "trigger_data": "sanctum_halls",
                },
                {
                    "desc": "Reach the Sovereign's Throne Room.",
                    "trigger": "map_entered",
                    "trigger_data": "throne_room",
                },
                {
                    "desc": "Destroy the Mythic Sovereign.",
                    "trigger": "boss_defeated",
                    "trigger_data": "mythic_sovereign",
                },
            ],
        )

    def fire_trigger(self, trigger: str, data=None) -> list[str]:
        """Fire a trigger across all quests. Returns list of quest IDs that advanced."""
        advanced = []
        for qid, quest in self.quests.items():
            if quest.check_trigger(trigger, data):
                advanced.append(qid)
        return advanced

    def get_active_quests(self) -> list[Quest]:
        return [q for q in self.quests.values() if not q.complete]

    def get_quest(self, quest_id: str) -> Quest | None:
        return self.quests.get(quest_id)
