"""
campaign.py — World / campaign-stage tracker.

SEPARATE from quest.stage, which tracks local quest logic within a single
quest chain.  This module owns the outer progression arc:

  Stage 1 = Village + Dungeon arc (existing content)
  Stage 2 = Haunted Ruins arc     (mid-game escalation)
  Stage 3 = Mythic Sanctum arc    (true finale)

Nothing in the quest system touches world_stage.
Nothing here touches quest.stage integers.
"""
from __future__ import annotations

STAGE_NAMES: dict[int, str] = {
    1: "Act I: The Eastern Forest",
    2: "Act II: The Haunted Ruins",
    3: "Act III: The Mythic Sanctum",
}

# Boss ID that completes each stage
STAGE_BOSS_IDS: dict[int, str] = {
    1: "dark_golem",
    2: "gravewarden",
    3: "mythic_sovereign",
}

# Maps belonging to each stage (ordered entry → exit)
STAGE_MAPS: dict[int, list[str]] = {
    1: ["village", "dungeon"],
    2: ["ruins_approach", "ruins_depths"],
    3: ["sanctum_halls", "throne_room"],
}

# Player form unlocked when entering each stage
STAGE_PLAYER_FORMS: dict[int, str] = {
    1: "base",
    2: "hero",
    3: "mythic",
}

# Human-readable labels for each player form
FORM_LABELS: dict[str, str] = {
    "base":   "Adventurer",
    "hero":   "Hero",
    "mythic": "Mythic Champion",
}

# Loot tiers per stage (used to gate item availability)
STAGE_LOOT_TIERS: dict[int, str] = {
    1: "common",
    2: "rare",
    3: "mythic",
}


class Campaign:
    """
    Tracks which act the player is in and which milestones have been reached.

    Attributes
    ----------
    world_stage : int
        Current active campaign stage (1, 2, or 3).
    completed_stages : set[int]
        Stages whose final boss has been defeated.
    boss_kills : dict[str, bool]
        Which boss IDs have been killed (True = defeated).
    stage_flags : dict[str, any]
        Arbitrary key-value flags for stage-specific logic.
    player_form : str
        Current player visual form identifier.
    """

    def __init__(self) -> None:
        self.world_stage:       int        = 1
        self.completed_stages:  set[int]   = set()
        self.boss_kills:        dict       = {}
        self.stage_flags:       dict       = {}
        self.player_form:       str        = "base"

    # ── Stage access helpers ──────────────────────────────────────────────────

    def is_stage_unlocked(self, stage: int) -> bool:
        """Stage 1 is always unlocked; others require the previous stage done."""
        if stage <= 1:
            return True
        return (stage - 1) in self.completed_stages

    def is_final_stage_complete(self) -> bool:
        return 3 in self.completed_stages

    def get_entry_map(self, stage: int | None = None) -> str:
        """Return the first map of the given (or current) stage."""
        s = stage if stage is not None else self.world_stage
        return STAGE_MAPS.get(s, ["village"])[0]

    def get_stage_name(self, stage: int | None = None) -> str:
        s = stage if stage is not None else self.world_stage
        return STAGE_NAMES.get(s, f"Act {s}")

    def get_loot_tier(self, stage: int | None = None) -> str:
        s = stage if stage is not None else self.world_stage
        return STAGE_LOOT_TIERS.get(s, "common")

    # ── Progression ───────────────────────────────────────────────────────────

    def on_boss_killed(self, boss_id: str) -> int | None:
        """
        Record a boss kill.  Returns the completed stage number if a stage
        was just finished, otherwise None.
        """
        self.boss_kills[boss_id] = True
        for stage, bid in STAGE_BOSS_IDS.items():
            if bid == boss_id and stage not in self.completed_stages:
                self.complete_stage(stage)
                return stage
        return None

    def complete_stage(self, stage: int) -> None:
        self.completed_stages.add(stage)
        if stage < 3:
            self.world_stage = stage + 1
            new_form = STAGE_PLAYER_FORMS.get(stage + 1, self.player_form)
            if new_form != self.player_form:
                self.player_form = new_form

    def unlock_player_form(self, form: str) -> None:
        self.player_form = form

    def set_flag(self, key: str, value) -> None:
        self.stage_flags[key] = value

    def get_flag(self, key: str, default=None):
        return self.stage_flags.get(key, default)

    # ── Form helpers ──────────────────────────────────────────────────────────

    def get_form_label(self) -> str:
        return FORM_LABELS.get(self.player_form, self.player_form.title())

    def is_mythic_form(self) -> bool:
        return self.player_form == "mythic"

    def is_hero_form(self) -> bool:
        return self.player_form in ("hero", "mythic")

    # ── Serialisation ─────────────────────────────────────────────────────────

    def to_save(self) -> dict:
        return {
            "world_stage":       self.world_stage,
            "completed_stages":  sorted(self.completed_stages),
            "boss_kills":        dict(self.boss_kills),
            "stage_flags":       dict(self.stage_flags),
            "player_form":       self.player_form,
        }

    @classmethod
    def from_save(cls, data: dict) -> "Campaign":
        c = cls()
        c.world_stage      = int(data.get("world_stage", 1))
        c.completed_stages = set(int(x) for x in data.get("completed_stages", []))
        c.boss_kills       = dict(data.get("boss_kills", {}))
        c.stage_flags      = dict(data.get("stage_flags", {}))
        c.player_form      = data.get("player_form", "base")
        return c
