"""
progression.py — Classless XP / levelling / skill-point system.

Design:
  • XP is earned by defeating enemies and animals, discovering secrets,
    completing quests, and executing environmental kills.
  • Level-up grants SKILL_POINTS_PER_LEVEL points to allocate in the skill tree.
  • Stats boosted on level-up: max HP +1 every 2 levels, speed fractionally.
  • No hard class lock — players can invest freely across warrior/rogue/mage trees.
  • Active skill effects are evaluated by the gameplay layer via get_combat_stats().
"""
from __future__ import annotations

import math

from settings import PLAYER_MAX_LEVEL, XP_BASE, XP_SCALE, SKILL_POINTS_PER_LEVEL


def xp_for_level(level: int) -> int:
    """Total XP required to reach the given level from level 1."""
    if level <= 1:
        return 0
    return int(XP_BASE * (XP_SCALE ** (level - 2)) * (level - 1))


def xp_threshold(level: int) -> int:
    """XP needed to advance FROM this level (i.e. XP for next level - XP for this level)."""
    return xp_for_level(level + 1) - xp_for_level(level)


class Progression:
    """
    Tracks player XP, level, and skill points.
    Integrates with skill_tree.py for allocated skills.

    Usage:
      prog = Progression()
      levelled_up = prog.add_xp(xp_amount)   # returns True on level-up
      prog.spend_skill_point("warrior", "power_strike")
    """

    def __init__(self):
        self.xp: int = 0
        self.level: int = 1
        self.skill_points: int = 0           # unspent points
        self.total_skill_points_earned: int = 0
        # Allocated skill levels: {tree: {skill_id: rank}}
        self.allocated: dict[str, dict[str, int]] = {
            "warrior": {},
            "rogue":   {},
            "mage":    {},
        }

    # ─────────────────────────────────────────────────────────────────

    @property
    def xp_to_next_level(self) -> int:
        """XP needed to reach the next level."""
        if self.level >= PLAYER_MAX_LEVEL:
            return 0
        return xp_for_level(self.level + 1) - self.xp

    @property
    def level_progress_ratio(self) -> float:
        """0.0–1.0 progress toward the next level (for XP bar display)."""
        if self.level >= PLAYER_MAX_LEVEL:
            return 1.0
        cur_thresh = xp_for_level(self.level)
        nxt_thresh = xp_for_level(self.level + 1)
        span = max(1, nxt_thresh - cur_thresh)
        return max(0.0, min(1.0, (self.xp - cur_thresh) / span))

    # ─────────────────────────────────────────────────────────────────

    def add_xp(self, amount: int) -> bool:
        """
        Add XP. Returns True if at least one level-up occurred.
        Caller should trigger a level-up notification and effect.
        """
        if self.level >= PLAYER_MAX_LEVEL:
            return False
        self.xp += max(0, int(amount))
        levelled = False
        while (self.level < PLAYER_MAX_LEVEL
               and self.xp >= xp_for_level(self.level + 1)):
            self.level += 1
            pts = SKILL_POINTS_PER_LEVEL
            self.skill_points += pts
            self.total_skill_points_earned += pts
            levelled = True
        return levelled

    def grant_skill_point(self):
        """Grant a bonus skill point (e.g. from Ancient Tome item)."""
        self.skill_points += 1
        self.total_skill_points_earned += 1

    # ─────────────────────────────────────────────────────────────────

    def spend_skill_point(self, tree: str, skill_id: str) -> bool:
        """
        Allocate one skill point to a skill. Returns True on success.
        Validates against the skill_tree's requirements.
        Validation import is lazy to avoid circular deps.
        """
        from skill_tree import SKILL_TREES, get_skill
        if self.skill_points <= 0:
            return False
        if tree not in self.allocated:
            return False
        skill = get_skill(tree, skill_id)
        if not skill:
            return False

        current_rank = self.allocated[tree].get(skill_id, 0)
        if current_rank >= skill["max_rank"]:
            return False   # already maxed

        # Check prerequisite
        prereq = skill.get("requires")
        if prereq:
            p_tree, p_skill = prereq.split(".")
            if self.allocated.get(p_tree, {}).get(p_skill, 0) < 1:
                return False

        self.allocated[tree][skill_id] = current_rank + 1
        self.skill_points -= 1
        return True

    def get_skill_rank(self, tree: str, skill_id: str) -> int:
        return self.allocated.get(tree, {}).get(skill_id, 0)

    def has_skill(self, tree: str, skill_id: str, min_rank: int = 1) -> bool:
        return self.get_skill_rank(tree, skill_id) >= min_rank

    # ─────────────────────────────────────────────────────────────────

    def get_combat_stats(self) -> dict:
        """
        Aggregate all active skill bonuses into a flat stat dict.
        Called by gameplay each frame to modify combat behavior.

        Returns keys:
          attack_bonus      — flat damage bonus
          speed_bonus       — tile/s bonus
          defense           — flat damage reduction
          flank_bonus       — extra flank multiplier
          crit_chance       — 0.0-1.0 crit probability
          crit_mult         — crit damage multiplier
          xp_bonus_mult     — XP gain multiplier
          magic_amp         — magic damage multiplier
          dash_i_frames     — extra invulnerability seconds on dash
          combo_window      — seconds to chain attacks for combo bonus
          env_kill_bonus    — extra XP for environmental kills
        """
        from skill_tree import SKILL_TREES
        stats = {
            "attack_bonus":   0,
            "speed_bonus":    0.0,
            "defense":        0,
            "flank_bonus":    0.0,
            "crit_chance":    0.0,
            "crit_mult":      1.5,
            "xp_bonus_mult":  1.0,
            "magic_amp":      1.0,
            "dash_i_frames":  0.0,
            "combo_window":   0.0,
            "env_kill_bonus": 0,
        }

        for tree_id, tree in SKILL_TREES.items():
            for skill in tree["skills"]:
                rank = self.get_skill_rank(tree_id, skill["id"])
                if rank <= 0:
                    continue
                for stat_key, per_rank in skill.get("stats_per_rank", {}).items():
                    if stat_key in stats:
                        val = per_rank * rank
                        if stat_key in ("crit_mult", "xp_bonus_mult", "magic_amp"):
                            stats[stat_key] += val - (1.0 if stat_key != "crit_mult" else 0)
                        else:
                            stats[stat_key] += val

        # ── Cross-archetype synergies ──────────────────────────────────
        #
        # SYNERGY 1: Warrior "Shield Wall" + Rogue "Evasion"
        #   → When blocking or dashing, brief invuln window +0.35 s
        if self.has_skill("warrior", "shield_wall") and self.has_skill("rogue", "evasion"):
            stats["dash_i_frames"] += 0.35
        #
        # SYNERGY 2: Rogue "Backstab" + Mage "Frost Slow"
        #   → Attacks on slowed/frozen enemies always crit
        if self.has_skill("rogue", "backstab") and self.has_skill("mage", "frost_slow"):
            stats["crit_chance"] = max(stats["crit_chance"], 1.0)   # guaranteed crit on slowed
        #
        # SYNERGY 3: Warrior "Power Strike" + Mage "Fire Imbue"
        #   → Heavy attacks set enemies on fire (AoE burn DoT)
        # Flagged via "fire_strike_combo" in get_active_effects
        #
        # SYNERGY 4: Rogue "Phantom Step" + Warrior "Momentum"
        #   → First attack after a dash deals 1.75× damage
        if self.has_skill("rogue", "phantom_step") and self.has_skill("warrior", "momentum"):
            stats["combo_window"] += 1.0   # 1-second window after dash
        #
        # SYNERGY 5: Mage "Arcane Surge" + Rogue "Exploit Weakness"
        #   → Each magic hit stacks a vulnerability; next physical hit consumes for +100% dmg
        # Tracked as active effect flag, not a simple stat
        #
        return stats

    def get_active_effects(self) -> set[str]:
        """Return a set of active special-effect tags from allocated skills."""
        effects = set()
        if self.has_skill("rogue", "phantom_step") and self.has_skill("warrior", "momentum"):
            effects.add("dash_strike_combo")
        if self.has_skill("warrior", "power_strike") and self.has_skill("mage", "fire_imbue"):
            effects.add("fire_strike_combo")
        if self.has_skill("mage", "arcane_surge") and self.has_skill("rogue", "exploit_weakness"):
            effects.add("arcane_exploit_combo")
        if self.has_skill("warrior", "executioner"):
            effects.add("execute_low_hp")   # bonus damage vs enemies < 25% HP
        if self.has_skill("rogue", "shadow_step"):
            effects.add("shadow_step")      # teleport short range (dungeon rogue fantasy)
        return effects

    # ─────────────────────────────────────────────────────────────────

    def get_hp_bonus(self) -> int:
        """Extra max HP from levelling (+1 every 2 levels above 1)."""
        return (self.level - 1) // 2

    # ─────────────────────────────────────────────────────────────────
    # SERIALISATION
    # ─────────────────────────────────────────────────────────────────

    def to_save(self) -> dict:
        return {
            "xp": self.xp,
            "level": self.level,
            "skill_points": self.skill_points,
            "total_skill_points_earned": self.total_skill_points_earned,
            "allocated": {t: dict(sk) for t, sk in self.allocated.items()},
        }

    @classmethod
    def from_save(cls, data: dict) -> "Progression":
        prog = cls()
        prog.xp = int(data.get("xp", 0))
        prog.level = max(1, int(data.get("level", 1)))
        prog.skill_points = max(0, int(data.get("skill_points", 0)))
        prog.total_skill_points_earned = int(data.get("total_skill_points_earned", 0))
        alloc = data.get("allocated", {})
        for tree in ("warrior", "rogue", "mage"):
            if tree in alloc:
                prog.allocated[tree] = {k: int(v) for k, v in alloc[tree].items()}
        return prog
