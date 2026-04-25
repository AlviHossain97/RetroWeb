"""
Stage 3 content registry — Mythic Sanctum arc (true finale).

NPC_DEFS, CHEST_DEFS, GROUND_ITEM_DEFS, ENEMY_SPAWN_DEFS, BOSS_DEFS,
ENV_DEFS, FAST_TRAVEL_HINTS, LORE_ITEM_DEFS, BGM_MAP  for sanctum_halls
and throne_room.

Loaded by gameplay when world_stage == 3.
"""

from rewards import make_currency_reward, make_key_item_reward


NPC_DEFS = {
    "sanctum_halls": [
        {
            "spawn_key": "ascended_guide",
            "npc_id":    "ascended_guide",
            "name":      "Seer Lorn",
            "dialogue_stages": {
                "default": [
                    "You have come far, champion.",
                    "The Mythic Sovereign commands this citadel.",
                    "He has three phases of power. Do not falter in the third.",
                    "Your form has transcended mortal limits. Trust it."
                ]
            },
            "body_color": (200, 180, 255),
            "hair_color": (240, 220, 255),
            "facing":     "down",
        }
    ],
    "throne_room": [],
}


CHEST_DEFS = {
    "sanctum_halls": [
        {
            "id":     "sanctum_halls_chest_west",
            "tile_x": 14, "tile_y": 14,
            "reward": make_key_item_reward("void_shard"),
            "label":  "Crystal Vault",
        },
        {
            "id":     "sanctum_halls_chest_east",
            "tile_x": 36, "tile_y": 14,
            "reward": make_key_item_reward("ascended_aegis"),
            "label":  "Champion's Coffer",
        },
    ],
    "throne_room": [
        {
            "id":     "throne_room_mythic_chest_1",
            "tile_x": 44, "tile_y": 6,
            "reward": make_key_item_reward("mythblade"),
            "label":  "The Sovereign's Armory",
        },
        {
            "id":     "throne_room_mythic_chest_2",
            "tile_x": 44, "tile_y": 29,
            "reward": make_key_item_reward("sovereign_crown"),
            "label":  "Crown Vault",
        },
    ],
}


GROUND_ITEM_DEFS = {
    "sanctum_halls": [
        {"id": "sanctum_halls_shard_1", "tile_x": 8,  "tile_y": 18,
         "reward": make_key_item_reward("void_shard")},
        {"id": "sanctum_halls_shard_2", "tile_x": 50, "tile_y": 14,
         "reward": make_key_item_reward("void_shard")},
        {"id": "sanctum_halls_coins",   "tile_x": 28, "tile_y": 20,
         "reward": make_currency_reward(25, "coins")},
    ],
    "throne_room": [
        {"id": "throne_room_mythic_core", "tile_x": 38, "tile_y": 17,
         "reward": make_key_item_reward("mythic_core")},
    ],
}


ENEMY_SPAWN_DEFS = {
    "sanctum_halls": [
        {"id": "sh_void_01",     "type": "void_shade",       "x":  8,  "y": 18},
        {"id": "sh_void_02",     "type": "void_shade",       "x": 12,  "y": 22},
        {"id": "sh_void_03",     "type": "void_shade",       "x": 30,  "y": 14},
        {"id": "sh_crystal_01",  "type": "crystal_colossus", "x": 28,  "y": 20},
        {"id": "sh_crystal_02",  "type": "crystal_colossus", "x": 32,  "y": 20},
        {"id": "sh_sentinel_01", "type": "mythic_sentinel",  "x": 50,  "y": 14},
        {"id": "sh_sentinel_02", "type": "mythic_sentinel",  "x": 50,  "y": 26},
        {"id": "sh_awraith_01",  "type": "ascended_wraith",  "x": 34,  "y": 14},
        {"id": "sh_awraith_02",  "type": "ascended_wraith",  "x": 34,  "y": 26},
    ],
    "throne_room": [
        {"id": "tr_sentinel_01", "type": "mythic_sentinel",  "x": 12, "y": 12},
        {"id": "tr_sentinel_02", "type": "mythic_sentinel",  "x": 12, "y": 23},
        {"id": "tr_void_01",     "type": "void_shade",       "x": 28, "y": 10},
        {"id": "tr_void_02",     "type": "void_shade",       "x": 28, "y": 25},
    ],
}


BOSS_DEFS = {
    "sanctum_halls": None,
    "throne_room":   {"id": "mythic_sovereign", "x": 42, "y": 17},
}


BGM_MAP = {
    "sanctum_halls": "sanctum",
    "throne_room":   "sanctum_boss",
}


ENV_DEFS = {
    "sanctum_halls": {
        "freezable": [],
        "conductive": [
            {"tx": 24, "ty": 14},
            {"tx": 25, "ty": 14},
            {"tx": 24, "ty": 26},
            {"tx": 25, "ty": 26},
        ],
        "destructibles": [
            {"tx": 8,  "ty": 16, "type": "crystal", "id": "sh_crystal_01"},
            {"tx": 50, "ty": 12, "type": "crystal", "id": "sh_crystal_02"},
        ],
    },
    "throne_room": {
        "freezable": [],
        "conductive": [
            {"tx": 20, "ty": 8},
            {"tx": 20, "ty": 27},
            {"tx": 35, "ty": 8},
            {"tx": 35, "ty": 27},
        ],
        "destructibles": [],
    },
}


FAST_TRAVEL_HINTS = {
    "sanctum_halls": "A rift stone pulses with energy. (fast travel unlocked)",
    "throne_room":   None,
}


LORE_ITEM_DEFS = {
    "sanctum_halls": [
        {
            "id":       "lore_sovereign_origin",
            "tile_x":   8, "tile_y": 16,
            "lore_key": "mythic_sovereign_origin",
            "text":     "A floating inscription:\n'The Sovereign was the last mythic king.\nHe refused death and shattered the world.'",
        },
        {
            "id":       "lore_sanctum_purpose",
            "tile_x":   50, "tile_y": 20,
            "lore_key": "sanctum_purpose",
            "text":     "Energy glyphs read:\n'This citadel feeds on the living.\nDestroy the Sovereign and it crumbles.'",
        },
    ],
    "throne_room": [
        {
            "id":       "lore_final_warning",
            "tile_x":   6, "tile_y": 17,
            "lore_key": "final_warning",
            "text":     "Etched in the throne dais:\n'Many champions have fallen here.\nYou are the last hope of the mortal realm.'",
        },
    ],
}
