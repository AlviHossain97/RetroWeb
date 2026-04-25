"""
skill_tree.py — Skill tree definitions for all three archetypes.

Three trees: warrior, rogue, mage.
Each tree has 5 skills with 1–3 ranks.
Skills within a tree can have prerequisites (requires field: "tree.skill_id").

Cross-archetype synergies (documented and resolved in progression.py):
  1. warrior.shield_wall + rogue.evasion      → +0.35s invuln on dash
  2. rogue.backstab     + mage.frost_slow     → guaranteed crit on slowed enemies
  3. warrior.power_strike + mage.fire_imbue   → heavy attacks apply burning AoE
  4. rogue.phantom_step + warrior.momentum    → 1.75× damage window after dash
  5. mage.arcane_surge  + rogue.exploit_weakness → stacking magic vuln for physical burst

Gear interactions documented per skill where relevant.
"""
from __future__ import annotations
from typing import Optional

# ─────────────────────────────────────────────────────────────────────────────
# TREE DEFINITIONS
# ─────────────────────────────────────────────────────────────────────────────
# stats_per_rank: applied once per allocated rank by Progression.get_combat_stats()

SKILL_TREES: dict[str, dict] = {

    # ── WARRIOR ──────────────────────────────────────────────────────────────
    "warrior": {
        "name": "Warrior",
        "color": (220, 80, 60),
        "icon": "⚔",
        "desc": "Brute strength, heavy blows, and iron endurance.",
        "skills": [
            {
                "id":    "power_strike",
                "name":  "Power Strike",
                "desc":  "Increases melee attack damage. At rank 3, heavy attacks stagger enemies.",
                # SYNERGY NOTE: + mage.fire_imbue → burning AoE on heavy attack
                "icon":  "💥",
                "max_rank":  3,
                "requires":  None,
                "stats_per_rank": {"attack_bonus": 1},
                "tier":  1,
                "pos":   (1, 0),   # column, row in the skill tree grid UI
            },
            {
                "id":    "shield_wall",
                "name":  "Shield Wall",
                "desc":  "While standing still, take 1 less damage from all hits.",
                # SYNERGY NOTE: + rogue.evasion → +0.35s invuln on dash
                "icon":  "🛡",
                "max_rank":  2,
                "requires":  None,
                "stats_per_rank": {"defense": 1},
                "tier":  1,
                "pos":   (3, 0),
            },
            {
                "id":    "iron_skin",
                "name":  "Iron Skin",
                "desc":  "Permanent defense increase. Stacks with armor.",
                "icon":  "🔩",
                "max_rank":  3,
                "requires":  "warrior.power_strike",
                "stats_per_rank": {"defense": 1},
                "tier":  2,
                "pos":   (1, 1),
            },
            {
                "id":    "momentum",
                "name":  "Momentum",
                "desc":  "Attacks within 1 second of a dash deal bonus damage.",
                # SYNERGY NOTE: + rogue.phantom_step → 1.75× dash-strike window
                "icon":  "⚡",
                "max_rank":  2,
                "requires":  "warrior.iron_skin",
                "stats_per_rank": {"attack_bonus": 1, "combo_window": 0.4},
                "tier":  3,
                "pos":   (1, 2),
            },
            {
                "id":    "executioner",
                "name":  "Executioner",
                "desc":  "Attacks against enemies below 25% HP deal double damage. "
                         "Required: Power Strike rank 2.",
                "icon":  "☠",
                "max_rank":  1,
                "requires":  "warrior.momentum",
                "stats_per_rank": {"attack_bonus": 2},
                "tier":  4,
                "pos":   (2, 3),
            },
        ],
    },

    # ── ROGUE ─────────────────────────────────────────────────────────────────
    "rogue": {
        "name": "Rogue",
        "color": (80, 200, 140),
        "icon": "🗡",
        "desc": "Speed, cunning, and striking from the shadows.",
        "skills": [
            {
                "id":    "backstab",
                "name":  "Backstab",
                "desc":  "Flanking attacks deal an additional +50% damage per rank.",
                # SYNERGY NOTE: + mage.frost_slow → guaranteed crit on slowed enemies
                "icon":  "🎯",
                "max_rank":  3,
                "requires":  None,
                "stats_per_rank": {"flank_bonus": 0.5},
                "tier":  1,
                "pos":   (1, 0),
            },
            {
                "id":    "swift_feet",
                "name":  "Swift Feet",
                "desc":  "Permanently increases movement speed.",
                "icon":  "👟",
                "max_rank":  3,
                "requires":  None,
                "stats_per_rank": {"speed_bonus": 0.35},
                "tier":  1,
                "pos":   (3, 0),
            },
            {
                "id":    "evasion",
                "name":  "Evasion",
                "desc":  "Dodging attacks grants a brief invulnerability window.",
                # SYNERGY NOTE: + warrior.shield_wall → +0.35s invuln on dash
                "icon":  "💨",
                "max_rank":  2,
                "requires":  "rogue.swift_feet",
                "stats_per_rank": {"dash_i_frames": 0.18},
                "tier":  2,
                "pos":   (3, 1),
            },
            {
                "id":    "phantom_step",
                "name":  "Phantom Step",
                "desc":  "Dash becomes a short-range teleport, ignoring collision briefly.",
                # SYNERGY NOTE: + warrior.momentum → 1.75× damage combo window
                "icon":  "👻",
                "max_rank":  1,
                "requires":  "rogue.evasion",
                "stats_per_rank": {"speed_bonus": 0.2},
                "tier":  3,
                "pos":   (3, 2),
            },
            {
                "id":    "exploit_weakness",
                "name":  "Exploit Weakness",
                "desc":  "After landing a crit, next hit deals 25% more damage.",
                # SYNERGY NOTE: + mage.arcane_surge → magic-vuln stack consumed for burst
                "icon":  "🔍",
                "max_rank":  2,
                "requires":  "rogue.backstab",
                "stats_per_rank": {"crit_chance": 0.12, "attack_bonus": 1},
                "tier":  2,
                "pos":   (1, 1),
            },
            {
                "id":    "shadow_step",
                "name":  "Shadow Step",
                "desc":  "Teleport to target enemy's blind spot (behind them). "
                         "Requires Shadow Cloak armor to unlock.",
                "icon":  "🌑",
                "max_rank":  1,
                "requires":  "rogue.phantom_step",
                "stats_per_rank": {"flank_bonus": 0.5},
                "tier":  4,
                "pos":   (2, 3),
            },
        ],
    },

    # ── MAGE ──────────────────────────────────────────────────────────────────
    "mage": {
        "name": "Mage",
        "color": (80, 120, 220),
        "icon": "🔮",
        "desc": "Harness elemental forces for ranged combat and battlefield control.",
        "skills": [
            {
                "id":    "arcane_knowledge",
                "name":  "Arcane Knowledge",
                "desc":  "Boosts magic weapon damage. Amplified further by Mage Robes.",
                "icon":  "📖",
                "max_rank":  3,
                "requires":  None,
                "stats_per_rank": {"magic_amp": 0.2},
                "tier":  1,
                "pos":   (1, 0),
            },
            {
                "id":    "frost_slow",
                "name":  "Frost Slow",
                "desc":  "Ice attacks slow enemies for 1.5 seconds (stacks with Backstab crit synergy).",
                # SYNERGY NOTE: + rogue.backstab → guaranteed crit on slowed enemies
                "icon":  "❄",
                "max_rank":  2,
                "requires":  None,
                "stats_per_rank": {"magic_amp": 0.1},
                "tier":  1,
                "pos":   (3, 0),
            },
            {
                "id":    "fire_imbue",
                "name":  "Fire Imbue",
                "desc":  "Melee/fire attacks set enemies ablaze for 3 ticks of 1 damage.",
                # SYNERGY NOTE: + warrior.power_strike → AoE burn on heavy attacks
                "icon":  "🔥",
                "max_rank":  2,
                "requires":  "mage.arcane_knowledge",
                "stats_per_rank": {"magic_amp": 0.15, "attack_bonus": 1},
                "tier":  2,
                "pos":   (1, 1),
            },
            {
                "id":    "arcane_surge",
                "name":  "Arcane Surge",
                "desc":  "After 3 magic hits, next hit deals double damage.",
                # SYNERGY NOTE: + rogue.exploit_weakness → magic-vuln consumed for burst
                "icon":  "⚡",
                "max_rank":  2,
                "requires":  "mage.fire_imbue",
                "stats_per_rank": {"magic_amp": 0.25, "crit_chance": 0.08},
                "tier":  3,
                "pos":   (1, 2),
            },
            {
                "id":    "mana_shield",
                "name":  "Mana Shield",
                "desc":  "Once per room, absorb one hit that would kill you, leaving 1 HP.",
                "icon":  "🔵",
                "max_rank":  1,
                "requires":  "mage.arcane_surge",
                "stats_per_rank": {"defense": 1},
                "tier":  4,
                "pos":   (2, 3),
            },
        ],
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def get_skill(tree_id: str, skill_id: str) -> Optional[dict]:
    """Return skill definition dict or None."""
    tree = SKILL_TREES.get(tree_id)
    if not tree:
        return None
    for skill in tree["skills"]:
        if skill["id"] == skill_id:
            return skill
    return None


def get_all_skills_flat() -> list[dict]:
    """Return all skills from all trees with tree_id injected."""
    result = []
    for tree_id, tree in SKILL_TREES.items():
        for skill in tree["skills"]:
            entry = dict(skill)
            entry["tree_id"] = tree_id
            entry["tree_name"] = tree["name"]
            entry["tree_color"] = tree["color"]
            result.append(entry)
    return result


def build_skill_display(progression) -> list[dict]:
    """
    Build a structured list for the skill screen renderer.
    Each entry includes current rank and unlock state.
    """
    result = []
    for tree_id, tree in SKILL_TREES.items():
        for skill in tree["skills"]:
            current_rank = progression.get_skill_rank(tree_id, skill["id"])
            # Check if prereq is met
            prereq_met = True
            if skill.get("requires"):
                p_tree, p_skill = skill["requires"].split(".")
                prereq_met = progression.get_skill_rank(p_tree, p_skill) >= 1
            result.append({
                "tree_id":      tree_id,
                "tree_name":    tree["name"],
                "tree_color":   tree["color"],
                "skill_id":     skill["id"],
                "name":         skill["name"],
                "desc":         skill["desc"],
                "icon":         skill["icon"],
                "max_rank":     skill["max_rank"],
                "current_rank": current_rank,
                "is_maxed":     current_rank >= skill["max_rank"],
                "prereq_met":   prereq_met,
                "can_invest":   prereq_met and current_rank < skill["max_rank"],
                "tier":         skill.get("tier", 1),
                "pos":          skill.get("pos", (0, 0)),
            })
    return result
