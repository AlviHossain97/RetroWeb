"""
consequence_system.py - Narrative consequence tracking and non-combat resolution.

The ConsequenceState object persists in the save file and is consulted by:
  - NPC dialogue (which branches based on prior choices)
  - Quest unlock conditions (e.g. faction questlines open after threshold reputation)
  - World events (certain doors unlock, areas change)

Design: decisions are stored as a flat string-keyed dict so the save
system can serialize them without schema coupling.
"""

from __future__ import annotations
from typing import Optional

# ── Known consequence flag constants ────────────────────────────────────────
CHOSE_PEACE_WITH_GOLEM = "chose_peace_with_golem"
HELPED_ELDER_WILLINGLY = "helped_elder_willingly"

# ── Decision outcome definitions ──────────────────────────────────────────
# Each key is a consequence flag; each value is a dict with:
#   - "type": persuasion | puzzle | stealth | negotiation
#   - "name": short label for UI
#   - "desc": flavour text
#   - "check": callable(ConsequenceState, progression, inventory) -> bool
D = {
    "dark_golem_persuade": {
        "type": "persuasion",
        "name": "Speak the True Name",
        "desc": "You found the Golem's true name in the ancient tome.",
    },
    "dark_golem_puzzle": {
        "type": "puzzle",
        "name": "Solve the Crystal Resonance",
        "desc": "Align the dark crystals to break the curse peacefully.",
    },
    "dark_golem_negotiate": {
        "type": "persuasion",
        "name": "Negotiate a reward first",
        "desc": "Demand payment upfront. Elder reluctantly agrees.",
    },
    "dark_golem_stealth": {
        "type": "stealth",
        "name": "Shadow Slip",
        "desc": "Your Rogue skills let you slip past unnoticed.",
    },
}


class ConsequenceState:
    """
    Tracks narrative decisions and their outcomes.

    Flags are set once and persist across saves. Downstream systems
    (dialogue, quests, world events) check these flags to gate content.
    """

    def __init__(self) -> None:
        self._flags: dict[str, bool] = {}

    # ── Core API ────────────────────────────────────────────────────────────

    def set_flag(self, key: str, value: bool = True) -> None:
        self._flags[key] = value

    def get_flag(self, key: str, default: bool = False) -> bool:
        return self._flags.get(key, default)

    def has_flag(self, key: str) -> bool:
        return key in self._flags

    # ── Convenient shortcuts for known flags ───────────────────────────────

    def chose_peace_with_golem(self) -> bool:
        return self.get_flag(CHOSE_PEACE_WITH_GOLEM)

    def helped_elder_willingly(self) -> bool:
        return self.get_flag(HELPED_ELDER_WILLINGLY)

    # ── Non-combat resolution checks ──────────────────────────────────────

    def can_resolve(self, encounter_id: str, progression=None, inventory=None) -> bool:
        """Check whether a non-combat resolution path is available."""
        path = D.get(encounter_id)
        if path is None:
            return False

        path_type = path["type"]

        if path_type == "persuasion":
            if progression is None:
                return False
            return self._check_persuasion(encounter_id, progression, inventory)

        if path_type == "puzzle":
            if inventory is None:
                return False
            return self._check_puzzle(encounter_id, inventory)

        if path_type == "stealth":
            if progression is None:
                return False
            return self._check_stealth(encounter_id, progression)

        return False

    def resolve(self, encounter_id: str) -> Optional[dict]:
        """Mark an encounter as peacefully resolved and return the outcome."""
        if encounter_id not in D:
            return None
        self.set_flag(f"{encounter_id}_resolved", True)
        return D[encounter_id]

    # ── Save/load ──────────────────────────────────────────────────────────

    def to_save(self) -> dict:
        return dict(self._flags)

    @classmethod
    def from_save(cls, data: dict) -> "ConsequenceState":
        cs = cls()
        cs._flags = dict(data) if data else {}
        return cs

    # ── Private checks ────────────────────────────────────────────────────

    def _check_persuasion(self, encounter_id: str, progression, inventory) -> bool:
        # Persuasion requires sufficient reputation (checked externally) + dialogue choice
        return True  # Base check; gameplay.py gates with reputation

    def _check_puzzle(self, encounter_id: str, inventory) -> bool:
        # Puzzle requires specific lore items in inventory
        if encounter_id == "dark_golem_puzzle":
            return (
                inventory.has("runic_crystal") if hasattr(inventory, "has") else False
            )
        return False

    def _check_stealth(self, encounter_id: str, progression) -> bool:
        # Stealth requires specific rogue skill ranks
        if progression is None:
            return False
        rank = (
            progression.get_skill_rank("rogue", "shadow_step")
            if hasattr(progression, "get_skill_rank")
            else 0
        )
        return rank > 0
