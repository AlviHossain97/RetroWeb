"""
Stage 2 content registry — Haunted Ruins arc.

NPC_DEFS, CHEST_DEFS, GROUND_ITEM_DEFS, ENEMY_SPAWN_DEFS, BOSS_DEFS,
ENV_DEFS, FAST_TRAVEL_HINTS, LORE_ITEM_DEFS, BGM_MAP  for ruins_approach
and ruins_depths.

Loaded by gameplay when world_stage == 2.
"""

from rewards import make_currency_reward, make_key_item_reward


NPC_DEFS = {
    "ruins_approach": [
        {
            "spawn_key": "guide_npc",
            "npc_id":    "ruins_guide",
            "name":      "Wanderer Sera",
            "dialogue_stages": {
                "default": [
                    "You survived the Golem? Impressive.",
                    "The Gravewarden lies deep in the ruins.",
                    "Find the Runic Crystal — it weakens him."
                ]
            },
            "body_color": (100, 80, 120),
            "hair_color": (60, 40, 80),
            "facing":     "right",
        }
    ],
    "ruins_depths": [
        {
            "spawn_key": "ruins_scout_npc",
            "npc_id":    "ruins_scout",
            "name":      "Scout Aldren",
            "dialogue_stages": {
                "default": [
                    "Watch the bone archers — they keep their distance.",
                    "The Gravewarden has two forms. Break his guard first.",
                    "Runic gear from these ruins hurts him more."
                ]
            },
            "body_color": (120, 100, 80),
            "hair_color": (80, 60, 40),
            "facing":     "right",
        }
    ],
}


CHEST_DEFS = {
    "ruins_approach": [
        {
            "id":     "ruins_approach_chest_north",
            "tile_x": 38, "tile_y": 8,
            "reward": make_key_item_reward("runic_crystal"),
            "label":  "Weathered Chest",
        },
        {
            "id":     "ruins_approach_chest_hidden",
            "tile_x": 42, "tile_y": 26,
            "reward": make_currency_reward(15, "coins"),
            "label":  "Buried Cache",
        },
    ],
    "ruins_depths": [
        {
            "id":     "ruins_depths_supply_chest",
            "tile_x": 6, "tile_y": 22,
            "reward": make_key_item_reward("bone_arrow"),
            "label":  "Supply Chest",
        },
        {
            "id":     "ruins_depths_boss_chest",
            "tile_x": 56, "tile_y": 10,
            "reward": make_key_item_reward("revenant_core"),
            "label":  "Gravewarden's Vault",
        },
    ],
}


GROUND_ITEM_DEFS = {
    "ruins_approach": [
        {"id": "ruins_approach_crystal",  "tile_x": 33, "tile_y": 18,
         "reward": make_key_item_reward("runic_crystal")},
        {"id": "ruins_approach_coins",    "tile_x": 15, "tile_y": 5,
         "reward": make_currency_reward(8, "coins")},
    ],
    "ruins_depths": [
        {"id": "ruins_depths_crystal",    "tile_x": 12, "tile_y": 14,
         "reward": make_key_item_reward("runic_crystal")},
        {"id": "ruins_depths_bone_arrow", "tile_x": 26, "tile_y": 20,
         "reward": make_key_item_reward("bone_arrow")},
    ],
}


ENEMY_SPAWN_DEFS = {
    "ruins_approach": [
        {"id": "ra_wraith_01",   "type": "wraith",           "x": 14, "y":  8},
        {"id": "ra_wraith_02",   "type": "wraith",           "x": 22, "y": 12},
        {"id": "ra_archer_01",   "type": "bone_archer",      "x": 30, "y":  7},
        {"id": "ra_archer_02",   "type": "bone_archer",      "x": 40, "y": 28},
        {"id": "ra_knight_01",   "type": "corrupted_knight", "x": 36, "y": 15},
        {"id": "ra_revenant_01", "type": "revenant",         "x": 44, "y": 22},
    ],
    "ruins_depths": [
        {"id": "rd_wraith_01",   "type": "wraith",           "x":  8, "y": 15},
        {"id": "rd_wraith_02",   "type": "wraith",           "x": 10, "y": 22},
        {"id": "rd_archer_01",   "type": "bone_archer",      "x": 26, "y": 12},
        {"id": "rd_archer_02",   "type": "bone_archer",      "x": 26, "y": 26},
        {"id": "rd_knight_01",   "type": "corrupted_knight", "x": 30, "y": 18},
        {"id": "rd_knight_02",   "type": "corrupted_knight", "x": 34, "y": 22},
        {"id": "rd_revenant_01", "type": "revenant",         "x": 32, "y": 14},
        {"id": "rd_revenant_02", "type": "revenant",         "x": 36, "y": 26},
    ],
}


BOSS_DEFS = {
    "ruins_approach": None,
    "ruins_depths": {"id": "gravewarden", "x": 52, "y": 20},
}


BGM_MAP = {
    "ruins_approach": "ruins",
    "ruins_depths":   "ruins_boss",
}


ENV_DEFS = {
    "ruins_approach": {
        "freezable": [
            {"tx": 20, "ty": 5},
            {"tx": 21, "ty": 5},
            {"tx": 30, "ty": 25},
            {"tx": 31, "ty": 25},
        ],
        "conductive": [
            {"tx": 35, "ty": 10},
            {"tx": 36, "ty": 10},
        ],
        "destructibles": [
            {"tx": 12, "ty": 16, "type": "barrel",  "id": "ra_barrel_01"},
            {"tx": 13, "ty": 16, "type": "barrel",  "id": "ra_barrel_02"},
            {"tx": 38, "ty": 18, "type": "boulder", "id": "ra_boulder_01"},
        ],
    },
    "ruins_depths": {
        "freezable": [
            {"tx": 24, "ty": 12},
            {"tx": 25, "ty": 12},
            {"tx": 26, "ty": 31},
        ],
        "conductive": [
            {"tx": 28, "ty": 8},
            {"tx": 29, "ty": 8},
            {"tx": 28, "ty": 28},
        ],
        "destructibles": [
            {"tx": 5,  "ty": 15, "type": "barrel",  "id": "rd_barrel_01"},
            {"tx": 5,  "ty": 22, "type": "barrel",  "id": "rd_barrel_02"},
            {"tx": 23, "ty": 12, "type": "crate",   "id": "rd_crate_01"},
            {"tx": 30, "ty": 24, "type": "boulder", "id": "rd_boulder_01"},
        ],
    },
}


FAST_TRAVEL_HINTS = {
    "ruins_approach": "A shattered waystone hums faintly. (fast travel unlocked)",
    "ruins_depths":   "An old campfire still glows in the corner. (fast travel unlocked)",
}


LORE_ITEM_DEFS = {
    "ruins_approach": [
        {
            "id":       "lore_ruins_marker",
            "tile_x":   38, "tile_y": 7,
            "lore_key": "ashen_ridge_battle",
            "text":     "The marker reads: 'Here the army of Morthane\nwas consumed by the Corruption.'",
        },
    ],
    "ruins_depths": [
        {
            "id":       "lore_gravewarden_origin",
            "tile_x":   20, "tile_y": 16,
            "lore_key": "gravewarden_creation",
            "text":     "A slab: 'The Gravewarden was once a general.\nThe ruins twisted him into something eternal.'",
        },
        {
            "id":       "lore_ruins_warning",
            "tile_x":   10, "tile_y": 24,
            "lore_key": "ruins_warning",
            "text":     "Scratched into the wall: 'Do not let him\nregenerate. Strike fast or flee.'",
        },
    ],
}
