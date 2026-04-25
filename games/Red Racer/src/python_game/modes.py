"""
modes.py — Centralized game mode definitions.

Each mode has:
- Display name and short name
- Rule mutations (scoring, fuel, health, spawning, time limits)
- Mission configuration
- Boost/risk tuning overrides

GBA Portability: MUST PORT LATER (maps directly to ModeRules struct)
"""

import time
import hashlib


# ---------------------------------------------------------------------------
# Mode Definitions
# ---------------------------------------------------------------------------

MODE_ROSTER = {
    "CLASSIC_ENDLESS": {
        "name": "Classic Endless",
        "short": "CLASSIC",
        "description": "Standard experience. Score from distance + risk. Survive as long as you can.",
        "color": (200, 200, 200),
        "icon": "🏁",

        # Rule mutations (False/None = no change from baseline)
        "use_fuel": True,
        "use_health": True,       # Only active on Easy difficulty
        "one_hit_kill": False,
        "time_limit": None,       # None = no time limit (seconds)
        "score_formula": "base+risk",     # "base+risk", "risk_only", "base_only"
        "risk_multiplier": 1.0,
        "fuel_drain_mult": 1.0,
        "spawn_rate_mult": 1.0,
        "nitro_spawn_mult": 1.0,
        "nitro_refill_mult": 1.0,
        "collectibles": True,
        "repair_kits": True,
        "mission_count": 2,
    },
    "HIGH_RISK": {
        "name": "High Risk",
        "short": "HIGH-RISK",
        "description": "Pure risk scoring. Distance doesn't count. Combo chains are everything.",
        "color": (255, 80, 80),
        "icon": "🔥",

        "use_fuel": True,
        "use_health": True,
        "one_hit_kill": False,
        "time_limit": None,
        "score_formula": "risk_only",
        "risk_multiplier": 1.35,
        "fuel_drain_mult": 1.0,
        "spawn_rate_mult": 0.85,
        "nitro_spawn_mult": 1.35,
        "nitro_refill_mult": 1.20,
        "collectibles": False,
        "repair_kits": True,
        "mission_count": 2,
    },
    "TIME_ATTACK": {
        "name": "Time Attack",
        "short": "TIME ATTACK",
        "description": "90-second sprint. Fixed traffic seed. Deterministic challenge.",
        "color": (255, 220, 50),
        "icon": "⏱",

        "use_fuel": True,
        "use_health": True,
        "one_hit_kill": False,
        "time_limit": 90.0,
        "score_formula": "base+risk",
        "risk_multiplier": 1.0,
        "fuel_drain_mult": 0.8,
        "spawn_rate_mult": 0.78,
        "nitro_spawn_mult": 1.10,
        "nitro_refill_mult": 1.10,
        "collectibles": True,
        "repair_kits": False,
        "mission_count": 2,
    },
    "ONE_LIFE_HARDCORE": {
        "name": "Hardcore",
        "short": "HARDCORE",
        "description": "One hit kills. No repair kits. No nitro. Pure survival skill.",
        "color": (180, 30, 30),
        "icon": "💀",

        "use_fuel": False,
        "use_health": False,
        "one_hit_kill": True,
        "time_limit": None,
        "score_formula": "base+risk",
        "risk_multiplier": 1.5,
        "fuel_drain_mult": 0.0,
        "spawn_rate_mult": 0.85,
        "nitro_spawn_mult": 0.0,
        "nitro_refill_mult": 0.0,
        "collectibles": False,
        "repair_kits": False,
        "mission_count": 1,
    },
    "DAILY_RUN": {
        "name": "Daily Run",
        "short": "DAILY RUN",
        "description": "Seeded traffic for today. Everyone plays the same road. One best per day.",
        "color": (100, 200, 255),
        "icon": "📅",

        "use_fuel": True,
        "use_health": True,
        "one_hit_kill": False,
        "time_limit": None,
        "score_formula": "base+risk",
        "risk_multiplier": 1.0,
        "fuel_drain_mult": 1.0,
        "spawn_rate_mult": 1.0,
        "nitro_spawn_mult": 1.0,
        "nitro_refill_mult": 1.0,
        "collectibles": True,
        "repair_kits": True,
        "mission_count": 2,
    },
    "ZEN": {
        "name": "Zen",
        "short": "ZEN",
        "description": "No pressure. Infinite fuel. No real damage. Just drive and vibe.",
        "color": (100, 220, 180),
        "icon": "🧘",

        "use_fuel": False,
        "use_health": False,
        "one_hit_kill": False,
        "time_limit": None,
        "score_formula": "base_only",
        "risk_multiplier": 0.5,
        "fuel_drain_mult": 0.0,
        "spawn_rate_mult": 1.25,
        "nitro_spawn_mult": 0.0,
        "nitro_refill_mult": 0.0,
        "collectibles": True,
        "repair_kits": False,
        "mission_count": 3,
    },
    "FUEL_CRISIS": {
        "name": "Fuel Crisis",
        "short": "FUEL CRISIS",
        "description": "Start with low fuel. Fuel pickups are critical. Route choice matters.",
        "color": (80, 200, 80),
        "icon": "⛽",

        "use_fuel": True,
        "use_health": True,
        "one_hit_kill": False,
        "time_limit": None,
        "score_formula": "base+risk",
        "risk_multiplier": 1.1,
        "fuel_drain_mult": 1.6,
        "spawn_rate_mult": 1.0,
        "nitro_spawn_mult": 0.5,
        "nitro_refill_mult": 0.8,
        "collectibles": True,
        "repair_kits": True,
        "mission_count": 2,
        "start_fuel": 40,
    },
    "BOOST_RUSH": {
        "name": "Boost Rush",
        "short": "BOOST RUSH",
        "description": "Boost charges faster. Speed is higher. Risk rewards are amplified.",
        "color": (150, 80, 255),
        "icon": "🚀",

        "use_fuel": True,
        "use_health": True,
        "one_hit_kill": False,
        "time_limit": None,
        "score_formula": "base+risk",
        "risk_multiplier": 1.4,
        "fuel_drain_mult": 1.1,
        "spawn_rate_mult": 0.9,
        "nitro_spawn_mult": 1.5,
        "nitro_refill_mult": 1.5,
        "collectibles": True,
        "repair_kits": True,
        "mission_count": 2,
        "boost_gain_global": 1.8,
    },
    "ENDURANCE": {
        "name": "Endurance",
        "short": "ENDURANCE",
        "description": "Fewer pickups. Resources are scarce. Every decision matters.",
        "color": (180, 140, 60),
        "icon": "🏋",

        "use_fuel": True,
        "use_health": True,
        "one_hit_kill": False,
        "time_limit": None,
        "score_formula": "base+risk",
        "risk_multiplier": 1.2,
        "fuel_drain_mult": 1.3,
        "spawn_rate_mult": 1.0,
        "nitro_spawn_mult": 0.3,
        "nitro_refill_mult": 0.6,
        "collectibles": True,
        "repair_kits": True,
        "mission_count": 2,
        "pickup_rate_mult": 0.5,
    },
}

MODE_ORDER = [
    "CLASSIC_ENDLESS",
    "HIGH_RISK",
    "TIME_ATTACK",
    "ONE_LIFE_HARDCORE",
    "FUEL_CRISIS",
    "BOOST_RUSH",
    "ENDURANCE",
    "DAILY_RUN",
    "ZEN",
]


def next_mode(current):
    """Cycle to the next mode."""
    if current not in MODE_ORDER:
        return MODE_ORDER[0]
    idx = (MODE_ORDER.index(current) + 1) % len(MODE_ORDER)
    return MODE_ORDER[idx]


def short_name(mode):
    """Get the short display name for a mode."""
    m = MODE_ROSTER.get(mode)
    return m["short"] if m else mode


def get_mode_rules(mode):
    """Get the full rule set for a mode. Returns a copy."""
    return dict(MODE_ROSTER.get(mode, MODE_ROSTER["CLASSIC_ENDLESS"]))


def get_mode_display(mode):
    """Get display metadata for a mode."""
    m = MODE_ROSTER.get(mode, MODE_ROSTER["CLASSIC_ENDLESS"])
    return {
        "name": m["name"],
        "short": m["short"],
        "description": m["description"],
        "color": m["color"],
        "icon": m["icon"],
    }


# ---------------------------------------------------------------------------
# Seeding
# ---------------------------------------------------------------------------

def deterministic_seed_for_mode(mode_name, config=None):
    """Return a deterministic seed for modes that need one, or None."""
    if mode_name == "TIME_ATTACK":
        return 13371337
    if mode_name == "DAILY_RUN":
        day_key = time.strftime("%Y-%m-%d")
        salt = "red-racer-daily"
        if config:
            salt = config.get("modes", {}).get("daily_seed_salt", salt)
        raw = f"{salt}-{day_key}".encode("utf-8")
        digest = hashlib.sha256(raw).hexdigest()[:8]
        return int(digest, 16)
    if config and config.get("features", {}).get("deterministic_mode", False):
        return 20260209
    return None
