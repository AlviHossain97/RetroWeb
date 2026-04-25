"""
cars.py — Centralized car definitions, archetypes, and stat calculation.

Each car has:
- Real-world inspired specs (display-only flavor)
- Gameplay stats (speed, accel, handling, braking, grip, fuel_eff, boost_gain, weight)
- An archetype that defines its role and playstyle
- Unlock requirements

GBA Portability: MUST PORT LATER (maps directly to CarStats struct arrays)
"""

# ---------------------------------------------------------------------------
# Car Archetypes
# ---------------------------------------------------------------------------
# Each archetype has a description and tendencies that influence how the car
# *feels* beyond raw numbers. This is for UI display and future AI tuning.

ARCHETYPES = {
    "balanced":     {"label": "Balanced",       "color": (180, 180, 180), "desc": "Jack of all trades. Great for learning."},
    "speed":        {"label": "Speed Demon",    "color": (255, 80, 80),   "desc": "Blazing fast, hard to control."},
    "grip":         {"label": "Grip Master",    "color": (80, 200, 120),  "desc": "Precise handling, planted cornering."},
    "endurance":    {"label": "Endurance",       "color": (80, 180, 255),  "desc": "Fuel-efficient. Goes the distance."},
    "boost":        {"label": "Boost Specialist","color": (200, 120, 255), "desc": "Charges boost faster from risky play."},
    "bruiser":      {"label": "Bruiser",         "color": (255, 160, 60),  "desc": "Heavy and resilient to collisions."},
    "precision":    {"label": "Precision",       "color": (100, 255, 200), "desc": "Nimble handling, but fragile at speed."},
    "glass_cannon": {"label": "Glass Cannon",    "color": (255, 50, 50),   "desc": "Extreme speed, extreme risk."},
    "all_rounder":  {"label": "All-Rounder",     "color": (220, 220, 100), "desc": "Reliably good at everything."},
    "exotic":       {"label": "Exotic",          "color": (255, 215, 0),   "desc": "Legendary performance. Earned, not given."},
}


# ---------------------------------------------------------------------------
# Car Roster — Gameplay Stats
# ---------------------------------------------------------------------------
# These are the actual gameplay-affecting stats. Decoupled from display specs.
#
# Stat ranges (0-100 scale unless noted):
#   top_speed   : max MPH the speedometer can reach
#   accel       : how quickly speed builds (0-100)
#   handling    : lateral responsiveness (0-100)
#   braking     : deceleration power (0-100)
#   grip        : traction multiplier (0.80 - 1.20)
#   drag        : air resistance / coast decel (0.85 - 1.10)
#   fuel_eff    : fuel efficiency multiplier (0.80 - 1.20, higher = less drain)
#   boost_gain  : how fast boost charges from risk (0.80 - 1.30)
#   weight      : collision resilience (0-100, higher = more damage absorbed)
#   archetype   : string key into ARCHETYPES

CAR_ROSTER = {
    "Felucia": {
        "display_name": "Felucia",
        "archetype": "balanced",
        "top_speed": 211, "accel": 82, "handling": 78, "braking": 75,
        "grip": 1.02, "drag": 0.95, "fuel_eff": 0.95, "boost_gain": 1.00, "weight": 50,
        "specs": {"bhp": 789, "torque": 718, "zero_sixty": 2.9, "engine": "6.5L NA V12", "drive": "RWD"},
        "tier": 1,
    },
    "Suprex": {
        "display_name": "Suprex",
        "archetype": "grip",
        "top_speed": 155, "accel": 55, "handling": 85, "braking": 80,
        "grip": 1.10, "drag": 1.05, "fuel_eff": 1.15, "boost_gain": 0.95, "weight": 55,
        "specs": {"bhp": 320, "torque": 500, "zero_sixty": 4.6, "engine": "3.0L Turbo I6", "drive": "RWD"},
        "tier": 1,
    },
    "Corveda": {
        "display_name": "Corveda",
        "archetype": "all_rounder",
        "top_speed": 194, "accel": 72, "handling": 70, "braking": 72,
        "grip": 0.98, "drag": 0.98, "fuel_eff": 1.05, "boost_gain": 1.00, "weight": 60,
        "specs": {"bhp": 670, "torque": 624, "zero_sixty": 2.9, "engine": "5.5L NA V8", "drive": "RWD"},
        "tier": 2,
    },
    "Aurion": {
        "display_name": "Aurion",
        "archetype": "endurance",
        "top_speed": 205, "accel": 70, "handling": 82, "braking": 78,
        "grip": 1.06, "drag": 0.96, "fuel_eff": 1.10, "boost_gain": 0.95, "weight": 58,
        "specs": {"bhp": 602, "torque": 800, "zero_sixty": 3.1, "engine": "5.2L NA V10", "drive": "AWD"},
        "tier": 2,
    },
    "Lotrix": {
        "display_name": "Lotrix",
        "archetype": "precision",
        "top_speed": 180, "accel": 65, "handling": 95, "braking": 88,
        "grip": 1.15, "drag": 0.99, "fuel_eff": 1.08, "boost_gain": 1.05, "weight": 35,
        "specs": {"bhp": 400, "torque": 420, "zero_sixty": 4.1, "engine": "3.5L SC V6", "drive": "RWD"},
        "tier": 2,
    },
    "Merren": {
        "display_name": "Merren",
        "archetype": "bruiser",
        "top_speed": 202, "accel": 75, "handling": 68, "braking": 70,
        "grip": 1.00, "drag": 0.97, "fuel_eff": 0.95, "boost_gain": 1.00, "weight": 72,
        "specs": {"bhp": 720, "torque": 800, "zero_sixty": 3.0, "engine": "5.4L SC V8", "drive": "RWD"},
        "tier": 3,
    },
    "Astor": {
        "display_name": "Astor",
        "archetype": "all_rounder",
        "top_speed": 211, "accel": 78, "handling": 75, "braking": 74,
        "grip": 1.02, "drag": 0.96, "fuel_eff": 0.98, "boost_gain": 1.02, "weight": 55,
        "specs": {"bhp": 715, "torque": 753, "zero_sixty": 3.3, "engine": "5.2L TT V12", "drive": "RWD"},
        "tier": 3,
    },
    "P11": {
        "display_name": "P11",
        "archetype": "precision",
        "top_speed": 205, "accel": 85, "handling": 92, "braking": 90,
        "grip": 1.12, "drag": 0.95, "fuel_eff": 0.92, "boost_gain": 1.08, "weight": 42,
        "specs": {"bhp": 640, "torque": 800, "zero_sixty": 2.6, "engine": "3.8L TT F6", "drive": "AWD"},
        "tier": 3,
    },
    "Vyrex": {
        "display_name": "Vyrex",
        "archetype": "bruiser",
        "top_speed": 206, "accel": 80, "handling": 58, "braking": 62,
        "grip": 0.92, "drag": 0.98, "fuel_eff": 0.85, "boost_gain": 1.10, "weight": 78,
        "specs": {"bhp": 645, "torque": 813, "zero_sixty": 3.3, "engine": "8.4L NA V10", "drive": "RWD"},
        "tier": 3,
    },
    "Marlon": {
        "display_name": "Marlon",
        "archetype": "speed",
        "top_speed": 208, "accel": 88, "handling": 80, "braking": 82,
        "grip": 1.02, "drag": 0.93, "fuel_eff": 0.90, "boost_gain": 1.05, "weight": 40,
        "specs": {"bhp": 755, "torque": 800, "zero_sixty": 2.7, "engine": "4.0L TT V8", "drive": "RWD"},
        "tier": 4,
    },
    "Lumbra": {
        "display_name": "Lumbra",
        "archetype": "boost",
        "top_speed": 211, "accel": 86, "handling": 76, "braking": 72,
        "grip": 1.08, "drag": 0.94, "fuel_eff": 0.88, "boost_gain": 1.25, "weight": 52,
        "specs": {"bhp": 770, "torque": 720, "zero_sixty": 2.8, "engine": "6.5L NA V12", "drive": "AWD"},
        "tier": 4,
    },
    "Zondra": {
        "display_name": "Zondra",
        "archetype": "glass_cannon",
        "top_speed": 217, "accel": 84, "handling": 82, "braking": 78,
        "grip": 1.04, "drag": 0.94, "fuel_eff": 0.85, "boost_gain": 1.15, "weight": 32,
        "specs": {"bhp": 760, "torque": 780, "zero_sixty": 3.0, "engine": "7.3L NA V12", "drive": "RWD"},
        "tier": 4,
    },
    "CXR": {
        "display_name": "CXR",
        "archetype": "glass_cannon",
        "top_speed": 245, "accel": 90, "handling": 65, "braking": 68,
        "grip": 0.95, "drag": 0.92, "fuel_eff": 0.82, "boost_gain": 1.20, "weight": 30,
        "specs": {"bhp": 806, "torque": 920, "zero_sixty": 3.1, "engine": "4.7L TS V8", "drive": "RWD"},
        "tier": 5,
    },
    "Vexa": {
        "display_name": "Vexa",
        "archetype": "exotic",
        "top_speed": 253, "accel": 95, "handling": 60, "braking": 65,
        "grip": 1.10, "drag": 0.90, "fuel_eff": 0.75, "boost_gain": 1.10, "weight": 80,
        "specs": {"bhp": 1001, "torque": 1250, "zero_sixty": 2.5, "engine": "8.0L QT W16", "drive": "AWD"},
        "tier": 5,
    },
}

# Ordered list for UI display (tier, then alphabetical)
CAR_ORDER = sorted(CAR_ROSTER.keys(), key=lambda k: (CAR_ROSTER[k]["tier"], k))


# ---------------------------------------------------------------------------
# Unlock Thresholds (cumulative high score required)
# ---------------------------------------------------------------------------
CAR_UNLOCK_THRESHOLDS = {
    "Felucia": 0,
    "Suprex": 0,
    "Corveda": 500,
    "Aurion": 1500,
    "Lotrix": 3000,
    "Merren": 5000,
    "Astor": 8000,
    "P11": 12000,
    "Vyrex": 18000,
    "Marlon": 25000,
    "Lumbra": 35000,
    "Zondra": 50000,
    "CXR": 70000,
    "Vexa": 99000,
}


# ---------------------------------------------------------------------------
# Gameplay Effects Builder
# ---------------------------------------------------------------------------

def _clamp(value, lo, hi):
    return max(lo, min(hi, value))


def build_car_effects(car_key):
    """
    Convert a car's raw stats into gameplay multipliers used by the game loop.
    Returns a dict of multipliers.
    """
    car = CAR_ROSTER.get(car_key, CAR_ROSTER.get("Felucia"))

    top_speed = car["top_speed"]
    accel = car["accel"]
    handling = car["handling"]
    braking = car["braking"]
    grip = car["grip"]
    drag = car["drag"]
    fuel_eff = car["fuel_eff"]
    boost_gain = car["boost_gain"]
    weight = car["weight"]

    # Normalize to multipliers centered around 1.0
    speed_mult = _clamp(top_speed / 205.0, 0.75, 1.25)
    accel_mult = _clamp(accel / 75.0, 0.70, 1.30)
    handling_mult = _clamp(handling / 78.0, 0.70, 1.30)
    braking_mult = _clamp(braking / 75.0, 0.70, 1.30)

    return {
        "speed_mult": speed_mult,
        "accel_mult": accel_mult,
        "handling_mult": handling_mult,
        "braking_mult": braking_mult,
        "grip": grip,
        "drag": drag,
        "fuel_eff": fuel_eff,
        "boost_gain_mult": boost_gain,
        "weight": weight,
        "top_speed": top_speed,
        "archetype": car.get("archetype", "balanced"),
    }


def get_car_display_stats(car_key):
    """Return a list of (label, value_str) tuples for UI display."""
    car = CAR_ROSTER.get(car_key, CAR_ROSTER.get("Felucia"))
    arch = ARCHETYPES.get(car.get("archetype", "balanced"), ARCHETYPES["balanced"])
    return {
        "display_name": car.get("display_name", car_key),
        "archetype": arch["label"],
        "archetype_color": arch["color"],
        "archetype_desc": arch["desc"],
        "tier": car.get("tier", 1),
        "stats": [
            ("Top Speed", f"{car['top_speed']} mph"),
            ("Accel", f"{car['accel']}/100"),
            ("Handling", f"{car['handling']}/100"),
            ("Braking", f"{car['braking']}/100"),
            ("Grip", f"{car['grip']:.2f}"),
            ("Fuel Eff.", f"{car['fuel_eff']:.2f}"),
            ("Boost Gain", f"{car['boost_gain']:.2f}"),
            ("Weight", f"{car['weight']}/100"),
        ],
        "specs": car.get("specs", {}),
    }
