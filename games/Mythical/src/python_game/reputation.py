"""
reputation.py — Faction-based reputation system.

Three factions with distinct worldviews that respond to player actions:
  Villagers       — helped by quests, protecting the village, sparing animals
  Forest Spirits  — pleased by animal preservation; angered by forest destruction
  Dungeon Seekers — mercenary explorers; respect power and profit

Rep range: -100 (hostile) to +100 (revered). Default 0 (neutral).
Thresholds:
  +50 → Ally: bonus dialogue, discounts, exclusive quests
  +25 → Friendly
    0 → Neutral
  -25 → Unfriendly: reduced service, hostile tone
  -50 → Hostile: faction NPCs attack or flee
"""
from __future__ import annotations
from settings import REP_MAX, REP_MIN

# ─────────────────────────────────────────────────────────────────────────────
# FACTION DEFINITIONS
# ─────────────────────────────────────────────────────────────────────────────

FACTION_DEFS: dict[str, dict] = {
    "villagers": {
        "name":    "Villagers",
        "desc":    "The folk of the village and surrounding settlements.",
        "color":   (180, 200, 120),
        "npc_ids": {"elder", "merchant", "gardener"},
        "symbol":  "🏘",
    },
    "forest_spirits": {
        "name":    "Forest Spirits",
        "desc":    "Ancient nature guardians that observe the forest's balance.",
        "color":   (60, 180, 80),
        "npc_ids": set(),            # spirit NPCs added later in content
        "symbol":  "🌳",
    },
    "dungeon_seekers": {
        "name":    "Dungeon Seekers",
        "desc":    "A loose guild of cave explorers and treasure hunters.",
        "color":   (160, 130, 60),
        "npc_ids": {"scout"},
        "symbol":  "⛏",
    },
}

# Actions that affect reputation
REP_EVENTS: dict[str, dict[str, int]] = {
    "quest_main_complete":       {"villagers": +20, "dungeon_seekers": +10},
    "elder_helped":              {"villagers": +15},
    "merchant_trade":            {"villagers": +5,  "dungeon_seekers": +3},
    "gardener_helped":           {"villagers": +10, "forest_spirits": +8},
    "animal_killed_deer":        {"forest_spirits": -5},
    "animal_killed_bear":        {"forest_spirits": -12},
    "animal_killed_rabbit":      {"forest_spirits": -2},
    "dungeon_captive_rescued":   {"dungeon_seekers": +15, "villagers": +8},
    "cave_map_shared":           {"dungeon_seekers": +10},
    "dark_crystal_destroyed":    {"villagers": +20, "forest_spirits": +15},
    "dark_crystal_kept":         {"dungeon_seekers": +10, "forest_spirits": -10},
    "boss_persuaded":            {"villagers": +30, "forest_spirits": +20, "dungeon_seekers": +5},
    "boss_killed":               {"villagers": +15, "dungeon_seekers": +8},
    "grove_protected":           {"forest_spirits": +20},
    "lore_fragment_found":       {"dungeon_seekers": +5},
}

# Standing label thresholds
STANDING_LABELS: list[tuple[int, str]] = [
    (50,  "Revered"),
    (25,  "Friendly"),
    (-24, "Neutral"),
    (-49, "Unfriendly"),
    (-100,"Hostile"),
]


def rep_standing(rep: int) -> str:
    for threshold, label in STANDING_LABELS:
        if rep >= threshold:
            return label
    return "Hostile"


class Reputation:
    """
    Tracks reputation with all three factions.

    Usage:
      rep = Reputation()
      rep.apply_event("elder_helped")          # fires an event
      rep.get("villagers")                     # → int
      rep.standing("villagers")               # → "Friendly"
      rep.get_dialogue_modifier("merchant")   # → "grateful" | "cold" | None
    """

    def __init__(self):
        self._rep: dict[str, int] = {fid: 0 for fid in FACTION_DEFS}

    # ── Core access ───────────────────────────────────────────────────

    def get(self, faction_id: str) -> int:
        return self._rep.get(faction_id, 0)

    def standing(self, faction_id: str) -> str:
        return rep_standing(self.get(faction_id))

    def is_ally(self, faction_id: str) -> bool:
        return self.get(faction_id) >= 50

    def is_hostile(self, faction_id: str) -> bool:
        return self.get(faction_id) <= -50

    def set(self, faction_id: str, value: int):
        if faction_id in self._rep:
            self._rep[faction_id] = max(REP_MIN, min(REP_MAX, int(value)))

    def modify(self, faction_id: str, delta: int):
        self.set(faction_id, self.get(faction_id) + delta)

    # ── Event system ──────────────────────────────────────────────────

    def apply_event(self, event_id: str) -> dict[str, int]:
        """
        Apply a named reputation event. Returns {faction: delta} for all
        affected factions (for notification display).
        """
        changes = REP_EVENTS.get(event_id, {})
        applied = {}
        for faction_id, delta in changes.items():
            if faction_id in self._rep:
                old = self.get(faction_id)
                self.modify(faction_id, delta)
                applied[faction_id] = self.get(faction_id) - old
        return applied

    # ── NPC dialogue modifier ─────────────────────────────────────────

    def get_dialogue_modifier(self, npc_id: str) -> str:
        """
        Return a tone tag for NPC dialogue based on their faction standing.
        Tags: "warm" / "friendly" / "neutral" / "cold" / "hostile"
        """
        for fid, fdef in FACTION_DEFS.items():
            if npc_id in fdef.get("npc_ids", set()):
                r = self.get(fid)
                if r >= 50:   return "warm"
                if r >= 25:   return "friendly"
                if r >= -24:  return "neutral"
                if r >= -49:  return "cold"
                return "hostile"
        return "neutral"

    def has_merchant_discount(self) -> bool:
        """Villagers rep ≥ 50 grants a 20% coin discount at merchants."""
        return self.is_ally("villagers")

    def has_forest_passage(self) -> bool:
        """Forest Spirits rep ≥ 25 lets player pass certain locked forest gates."""
        return self.get("forest_spirits") >= 25

    def has_seeker_maps(self) -> bool:
        """Dungeon Seekers rep ≥ 25 unlocks bonus dungeon maps / hints."""
        return self.get("dungeon_seekers") >= 25

    # ── Display ───────────────────────────────────────────────────────

    def get_display_list(self) -> list[dict]:
        result = []
        for fid, fdef in FACTION_DEFS.items():
            r = self.get(fid)
            result.append({
                "id":       fid,
                "name":     fdef["name"],
                "desc":     fdef["desc"],
                "color":    fdef["color"],
                "symbol":   fdef["symbol"],
                "rep":      r,
                "standing": rep_standing(r),
                "ratio":    (r - REP_MIN) / (REP_MAX - REP_MIN),  # 0-1 for bar
            })
        return result

    # ── Serialisation ─────────────────────────────────────────────────

    def to_save(self) -> dict:
        return dict(self._rep)

    @classmethod
    def from_save(cls, data: dict) -> "Reputation":
        rep = cls()
        for fid in FACTION_DEFS:
            if fid in data:
                rep.set(fid, int(data[fid]))
        return rep
