"""
roads.py — Centralized road/environment definitions.

Each road has:
- Display metadata (name, description, visual mood)
- Gameplay modifiers (traffic, grip, fuel drain, risk, reward)
- Traffic profile (density, speed, behavioral weighting)
- Environmental effects (visibility, weather feel)

GBA Portability: MUST PORT LATER (maps to RoadConfig struct array)
"""


# ---------------------------------------------------------------------------
# Road Roster
# ---------------------------------------------------------------------------

ROAD_ROSTER = {
    "Road.png": {
        "name": "City Express",
        "description": "Balanced urban highway. Great training ground.",
        "biome": "city",
        "traffic_profile": "balanced",
        "mood_color": (60, 80, 120),

        # Gameplay modifiers (1.0 = neutral baseline)
        "spawn_threshold_mult": 1.00,
        "enemy_speed_mult": 1.00,
        "fuel_drain_mult": 1.00,
        "grip_mult": 1.00,
        "risk_mult": 1.00,
        "reward_mult": 1.00,
        "cap_bonus": 0.0,

        # Traffic behavioral weights (added to base pool)
        "traffic_weights": {
            "normal": 10, "lane_drifter": 0, "sudden_braker": 0,
            "speeder": 0, "weaver": 0, "chaos": 0,
        },
        # Display info
        "traffic_label": "Balanced",
        "risk_label": "Medium",
        "surface_label": "Dry Asphalt",
        "visibility_label": "High",
        "note": "Great all-round training road.",
    },
    "Road2.png": {
        "name": "Industrial Route",
        "description": "Tight lanes, dense traffic, precision rewarded.",
        "biome": "industrial",
        "traffic_profile": "dense",
        "mood_color": (100, 80, 60),

        "spawn_threshold_mult": 0.84,
        "enemy_speed_mult": 0.95,
        "fuel_drain_mult": 1.12,
        "grip_mult": 0.97,
        "risk_mult": 1.10,
        "reward_mult": 1.08,
        "cap_bonus": -0.3,

        "traffic_weights": {
            "normal": 5, "lane_drifter": 6, "sudden_braker": 8,
            "speeder": 0, "weaver": 2, "chaos": 0,
        },
        "traffic_label": "Dense",
        "risk_label": "High",
        "surface_label": "Worn Asphalt",
        "visibility_label": "Medium",
        "note": "Tighter lanes reward precision passes.",
    },
    "Road3.png": {
        "name": "Coastal Run",
        "description": "High-speed highway along the coast. Fast traffic.",
        "biome": "coastal",
        "traffic_profile": "flowing",
        "mood_color": (60, 140, 180),

        "spawn_threshold_mult": 0.94,
        "enemy_speed_mult": 1.10,
        "fuel_drain_mult": 1.02,
        "grip_mult": 1.03,
        "risk_mult": 1.06,
        "reward_mult": 1.10,
        "cap_bonus": 0.8,

        "traffic_weights": {
            "normal": 5, "lane_drifter": 2, "sudden_braker": 0,
            "speeder": 8, "weaver": 4, "chaos": 0,
        },
        "traffic_label": "Flowing",
        "risk_label": "Medium-High",
        "surface_label": "Fast Tarmac",
        "visibility_label": "High",
        "note": "High-speed overtakes and long reads.",
    },
    "Road4.png": {
        "name": "Night Circuit",
        "description": "Dark, fast, chaotic. Maximum risk, maximum reward.",
        "biome": "night",
        "traffic_profile": "chaotic",
        "mood_color": (30, 20, 60),

        "spawn_threshold_mult": 0.88,
        "enemy_speed_mult": 1.15,
        "fuel_drain_mult": 1.20,
        "grip_mult": 0.92,
        "risk_mult": 1.20,
        "reward_mult": 1.18,
        "cap_bonus": 1.2,

        "traffic_weights": {
            "normal": 0, "lane_drifter": 4, "sudden_braker": 5,
            "speeder": 5, "weaver": 6, "chaos": 8,
        },
        "traffic_label": "Unpredictable",
        "risk_label": "Extreme",
        "surface_label": "Patchy Asphalt",
        "visibility_label": "Low",
        "note": "Best for hardcore risk combo runs.",
    },
}

ROAD_ORDER = list(ROAD_ROSTER.keys())


def get_road_effects(road_key):
    """Return the gameplay modifier dict for a road."""
    road = ROAD_ROSTER.get(road_key, ROAD_ROSTER.get("Road.png"))
    return {
        "spawn_threshold_mult": road["spawn_threshold_mult"],
        "enemy_speed_mult": road["enemy_speed_mult"],
        "fuel_drain_mult": road["fuel_drain_mult"],
        "grip_mult": road["grip_mult"],
        "risk_mult": road["risk_mult"],
        "reward_mult": road["reward_mult"],
        "cap_bonus": road["cap_bonus"],
    }


def get_road_traffic_weights(road_key):
    """Return extra traffic behavior weights for this road."""
    road = ROAD_ROSTER.get(road_key, ROAD_ROSTER.get("Road.png"))
    return dict(road.get("traffic_weights", {}))


def get_road_display(road_key):
    """Return display info for UI."""
    road = ROAD_ROSTER.get(road_key, ROAD_ROSTER.get("Road.png"))
    return {
        "name": road["name"],
        "description": road["description"],
        "biome": road["biome"],
        "mood_color": road["mood_color"],
        "traffic": road["traffic_label"],
        "risk": road["risk_label"],
        "surface": road["surface_label"],
        "visibility": road["visibility_label"],
        "note": road["note"],
    }
