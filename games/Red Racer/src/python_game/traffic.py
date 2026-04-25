"""
traffic.py — Traffic AI behaviors and entity variety.

Provides:
- Multiple traffic vehicle types with different sizes and score values
- Named AI behaviors with tunable parameters
- Behavior selection based on road profile, mode, and progression

GBA Portability: MUST PORT LATER (behavior enum + simple struct data)
"""

import random


# ---------------------------------------------------------------------------
# Traffic Vehicle Types
# ---------------------------------------------------------------------------
# Each type modifies the base enemy appearance and gameplay interaction.

TRAFFIC_TYPES = {
    "sedan": {
        "label": "Sedan",
        "width_mult": 1.0,    # Relative to base 50px width
        "height_mult": 1.0,   # Relative to base 100px height
        "speed_mult": 1.0,
        "score_value": 10,     # Points when passed
        "collision_severity": 1.0,
        "near_miss_value": 1.0,
        "weight": 60,          # Spawn weight (higher = more common)
    },
    "sports_car": {
        "label": "Sports Car",
        "width_mult": 0.95,
        "height_mult": 0.95,
        "speed_mult": 1.3,
        "score_value": 15,
        "collision_severity": 1.0,
        "near_miss_value": 1.3,
        "weight": 20,
    },
    "truck": {
        "label": "Truck",
        "width_mult": 1.3,
        "height_mult": 1.4,
        "speed_mult": 0.7,
        "score_value": 20,
        "collision_severity": 1.5,
        "near_miss_value": 1.5,
        "weight": 15,
    },
    "van": {
        "label": "Van",
        "width_mult": 1.15,
        "height_mult": 1.2,
        "speed_mult": 0.85,
        "score_value": 12,
        "collision_severity": 1.2,
        "near_miss_value": 1.1,
        "weight": 18,
    },
    "compact": {
        "label": "Compact",
        "width_mult": 0.85,
        "height_mult": 0.85,
        "speed_mult": 1.1,
        "score_value": 8,
        "collision_severity": 0.8,
        "near_miss_value": 0.9,
        "weight": 25,
    },
    "elite": {
        "label": "Elite Racer",
        "width_mult": 0.9,
        "height_mult": 0.95,
        "speed_mult": 1.5,
        "score_value": 30,
        "collision_severity": 1.0,
        "near_miss_value": 2.0,
        "weight": 5,
    },
}


# ---------------------------------------------------------------------------
# AI Behaviors
# ---------------------------------------------------------------------------

BEHAVIORS = {
    "normal": {
        "label": "Normal",
        "speed_multiplier": 1.0,
        "lane_change_chance": 0.8,
        "lateral_speed_min": 1.0,
        "lateral_speed_max": 3.0,
        "brake_chance": 0.0,
        "brake_duration_range": (0, 0),
        "brake_speed_multiplier": 1.0,
        "weave_chance": 0.0,
        "chaos_speed_range": None,
    },
    "lane_drifter": {
        "label": "Lane Drifter",
        "speed_multiplier": 1.0,
        "lane_change_chance": 0.95,
        "lateral_speed_min": 2.6,
        "lateral_speed_max": 4.0,
        "brake_chance": 0.0,
        "brake_duration_range": (0, 0),
        "brake_speed_multiplier": 1.0,
        "weave_chance": 0.0,
        "chaos_speed_range": None,
    },
    "sudden_braker": {
        "label": "Sudden Braker",
        "speed_multiplier": 1.0,
        "lane_change_chance": 0.5,
        "lateral_speed_min": 1.0,
        "lateral_speed_max": 3.0,
        "brake_chance": 0.012,
        "brake_duration_range": (10, 24),
        "brake_speed_multiplier": 0.4,
        "weave_chance": 0.0,
        "chaos_speed_range": None,
    },
    "speeder": {
        "label": "Speeder",
        "speed_multiplier": 1.35,
        "lane_change_chance": 0.5,
        "lateral_speed_min": 1.5,
        "lateral_speed_max": 3.0,
        "brake_chance": 0.0,
        "brake_duration_range": (0, 0),
        "brake_speed_multiplier": 1.0,
        "weave_chance": 0.0,
        "chaos_speed_range": None,
    },
    "weaver": {
        "label": "Weaver",
        "speed_multiplier": 1.0,
        "lane_change_chance": 1.0,
        "lateral_speed_min": 3.3,
        "lateral_speed_max": 5.0,
        "brake_chance": 0.0,
        "brake_duration_range": (0, 0),
        "brake_speed_multiplier": 1.0,
        "weave_chance": 0.05,
        "chaos_speed_range": None,
    },
    "chaos": {
        "label": "Chaos",
        "speed_multiplier": 1.0,
        "lane_change_chance": 1.0,
        "lateral_speed_min": 2.2,
        "lateral_speed_max": 4.6,
        "brake_chance": 0.006,
        "brake_duration_range": (8, 18),
        "brake_speed_multiplier": 0.5,
        "weave_chance": 0.08,
        "chaos_speed_range": (0.7, 1.6),
    },
    "blocker": {
        "label": "Blocker",
        "speed_multiplier": 0.6,
        "lane_change_chance": 0.3,
        "lateral_speed_min": 0.5,
        "lateral_speed_max": 1.5,
        "brake_chance": 0.0,
        "brake_duration_range": (0, 0),
        "brake_speed_multiplier": 1.0,
        "weave_chance": 0.0,
        "chaos_speed_range": None,
    },
}


# ---------------------------------------------------------------------------
# Behavior Selection
# ---------------------------------------------------------------------------

def select_behavior(road_traffic_weights, performance_level, game_mode, daily_profile=None):
    """
    Select a behavior name for a new enemy based on context.
    
    road_traffic_weights: dict from roads.get_road_traffic_weights()
    performance_level: float (0.0 = start of run, higher = better performance)
    game_mode: string mode key
    daily_profile: optional string, forced bias for daily run
    """
    # Base weights
    weights = {
        "normal": 50,
        "lane_drifter": 14 + performance_level * 6,
        "sudden_braker": 11 + performance_level * 5,
        "speeder": 8 + performance_level * 6,
        "weaver": 7 + performance_level * 5,
        "chaos": max(1, int(performance_level * 2)),
        "blocker": max(1, int(performance_level * 1.5)),
    }

    # Add road-specific bias
    for behavior, extra in road_traffic_weights.items():
        if behavior in weights:
            weights[behavior] += extra

    # Mode-specific adjustments
    if game_mode == "TIME_ATTACK":
        weights["speeder"] += 12
        weights["weaver"] += 8
        weights["lane_drifter"] += 6
    elif game_mode == "ONE_LIFE_HARDCORE":
        weights["sudden_braker"] += 14
        weights["chaos"] += 12
        weights["weaver"] += 10
    elif game_mode == "BOOST_RUSH":
        weights["speeder"] += 10
        weights["weaver"] += 8
    elif game_mode == "ENDURANCE":
        weights["blocker"] += 10
        weights["sudden_braker"] += 8

    # Daily run bias
    if daily_profile and daily_profile in weights:
        weights[daily_profile] += 25

    # Build weighted bag
    bag = []
    for name, w in weights.items():
        bag.extend([name] * max(1, int(w)))

    return random.choice(bag) if bag else "normal"


def select_traffic_type(performance_level, game_mode):
    """Select a traffic vehicle type for visual/gameplay variety."""
    weights = dict(TRAFFIC_TYPES)
    
    # Build weighted pool
    pool = []
    for type_key, data in weights.items():
        base_w = data["weight"]
        # Elite cars become more common as performance rises
        if type_key == "elite":
            base_w = max(1, int(base_w + performance_level * 3))
        # Trucks more common in endurance
        if type_key == "truck" and game_mode == "ENDURANCE":
            base_w += 10
        pool.extend([type_key] * max(1, base_w))

    return random.choice(pool) if pool else "sedan"
