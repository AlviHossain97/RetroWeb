"""Map-scoped content definitions extracted from the gameplay state."""

from rewards import make_currency_reward, make_key_item_reward


NPC_DEFS = {
    "village": [
        {
            "spawn_key": "elder_npc",
            "npc_id": "elder",
            "name": "Elder Rowan",
            "dialogue_stages": {
                0: [
                    "Welcome, traveller. Strange creatures lurk beyond the river.",
                    "Find a weapon first -- check the garden chest south of the square."
                ],
                1: ["Check the garden chest, south of the village square."],
                2: ["Good, you're armed! Get the Forest Key from Merchant Lira."],
                3: ["Gardener Fenn needs a Healing Herb. Ask Healer Elara near the riverbank."],
                4: ["Cross the bridge east. The cave entrance lies beyond the trees."],
                "complete": ["Thank you for everything, hero. Rest well."],
                "default": ["The village thanks you."]
            },
            "body_color": (140, 80, 50),
            "hair_color": (180, 180, 180),
            "facing": "down"
        },
        {
            "spawn_key": "shop_npc",
            "npc_id": "merchant",
            "name": "Merchant Lira",
            "dialogue_stages": {
                2: ["The Elder sent you? Take this Forest Key. Be careful!"],
                "default": ["Welcome! Stock coming soon."]
            },
            "body_color": (60, 140, 90),
            "hair_color": (50, 30, 20),
            "facing": "down",
            "gives_item": {"quest_stage": 2, "item_id": "forest_key"}
        },
        {
            "spawn_key": "healer_npc",
            "npc_id": "healer",
            "name": "Healer Elara",
            "dialogue_stages": {
                3: ["Gardener Fenn needs a Healing Herb? Here, take this one I gathered."],
                "default": ["I study the properties of the local flora."]
            },
            "body_color": (200, 150, 150),
            "hair_color": (220, 200, 80),
            "facing": "left",
            "gives_item": {"quest_stage": 3, "item_id": "herb"}
        },
        {
            "spawn_key": "garden_npc",
            "npc_id": "gardener",
            "name": "Gardener Fenn",
            "dialogue_stages": {
                3: ["You brought a Healing Herb! Here, take this Glowing Mushroom."],
                "default": ["Flowers blooming beautifully! Strange noises from the graveyard..."]
            },
            "body_color": (100, 140, 60),
            "hair_color": (80, 50, 30),
            "facing": "up",
            "gives_item": {"quest_stage": 3, "item_id": "mushroom"},
            "takes_item": {"quest_stage": 3, "item_id": "herb"}
        }
    ],
    "dungeon": [
        {
            "spawn_key": "guard_npc",
            "npc_id": "scout",
            "name": "Scout Mira",
            "dialogue_stages": {
                "default": ["Cave is dangerous. South holds puzzles, east holds the Dark Golem. Good luck."]
            },
            "body_color": (160, 80, 80),
            "hair_color": (40, 30, 50),
            "facing": "right"
        }
    ]
}


CHEST_DEFS = {
    "village": [
        {"id": "village_garden_chest", "tile_x": 20, "tile_y": 31, "reward": make_key_item_reward("old_sword"), "label": "Garden Chest"},
        {"id": "village_elder_chest", "tile_x": 6, "tile_y": 8, "reward": make_key_item_reward("letter"), "label": "Elder's Chest"}
    ],
    "dungeon": [
        {"id": "dungeon_supply_crate", "tile_x": 22, "tile_y": 5, "reward": make_key_item_reward("cave_map"), "label": "Supply Crate"},
        {"id": "dungeon_ancient_chest", "tile_x": 14, "tile_y": 22, "reward": make_key_item_reward("boss_key"), "label": "Ancient Chest"}
    ]
}


GROUND_ITEM_DEFS = {
    "village": [
        {"id": "village_river_herb", "tile_x": 34, "tile_y": 20, "reward": make_key_item_reward("herb")},
        {"id": "village_coin_pouch", "tile_x": 18, "tile_y": 18, "reward": make_currency_reward(5, "coins")}
    ],
    "dungeon": [
        {"id": "dungeon_dark_crystal", "tile_x": 34, "tile_y": 8, "reward": make_key_item_reward("crystal")}
    ]
}


ENEMY_SPAWN_DEFS = {
    "village": [],
    "dungeon": [
        {"id": "dungeon_slime_01", "type": "slime", "x": 5, "y": 7},
        {"id": "dungeon_slime_02", "type": "slime", "x": 8, "y": 11},
        {"id": "dungeon_bat_01", "type": "bat", "x": 12, "y": 6},
        {"id": "dungeon_bat_02", "type": "bat", "x": 17, "y": 10},
        {"id": "dungeon_slime_03", "type": "slime", "x": 24, "y": 8},
        {"id": "dungeon_skeleton_01", "type": "skeleton", "x": 33, "y": 7},
        {"id": "dungeon_skeleton_02", "type": "skeleton", "x": 35, "y": 10},
        {"id": "dungeon_bat_03", "type": "bat", "x": 30, "y": 20},
        {"id": "dungeon_skeleton_03", "type": "skeleton", "x": 28, "y": 24},
        {"id": "dungeon_golem_01", "type": "golem", "x": 32, "y": 25},
        {"id": "dungeon_slime_04", "type": "slime", "x": 15, "y": 24},
        {"id": "dungeon_bat_04", "type": "bat", "x": 12, "y": 26}
    ]
}


BOSS_DEFS = {
    "village": None,
    "dungeon": {"id": "dark_golem", "x": 14, "y": 26}
}


BGM_MAP = {
    "village": "village",
    "dungeon": "dungeon"
}


# ── Environmental object definitions per map ──────────────────────────────────
# Structure expected by EnvironmentalManager.load_for_map():
#   map_name → { "freezable":    [{tx, ty},...],
#                "conductive":   [{tx, ty},...],
#                "destructibles":[{tx, ty, type, id},...] }

ENV_DEFS = {
    "village": {
        "freezable": [
            {"tx": 30, "ty": 20},
            {"tx": 31, "ty": 20},
            {"tx": 32, "ty": 20},
        ],
        "conductive": [],
        "destructibles": [
            {"tx": 15, "ty": 12, "type": "barrel", "id": "v_barrel_01"},
            {"tx": 16, "ty": 12, "type": "barrel", "id": "v_barrel_02"},
            {"tx": 22, "ty": 18, "type": "crate",  "id": "v_crate_01"},
        ],
    },
    "dungeon": {
        "freezable": [
            {"tx": 6,  "ty": 25},
            {"tx": 7,  "ty": 25},
        ],
        "conductive": [
            {"tx": 28, "ty": 8},
            {"tx": 29, "ty": 8},
        ],
        "destructibles": [
            {"tx": 8,  "ty": 6,  "type": "barrel", "id": "d_barrel_01"},
            {"tx": 9,  "ty": 6,  "type": "barrel", "id": "d_barrel_02"},
            {"tx": 20, "ty": 5,  "type": "crate",  "id": "d_crate_01"},
            {"tx": 25, "ty": 15, "type": "boulder", "id": "d_boulder_01"},
        ],
    },
}


# ── Fast-travel waypoint unlock hints per map ─────────────────────────────────
# Displayed when player first enters a map with a locked waypoint nearby.

FAST_TRAVEL_HINTS = {
    "village": "Ancient stones glow near the village square. (fast travel unlocked)",
    "dungeon": "A campfire flickers in the cave entrance. (fast travel unlocked)",
}


# ── Lore item placements ──────────────────────────────────────────────────────
# Placed as ground items that grant lore fragments to ConsequenceState.

LORE_ITEM_DEFS = {
    "village": [
        {"id": "lore_village_stone", "tile_x": 10, "tile_y": 10,
         "lore_key": "village_origin",
         "text": "An inscription reads: 'Founded by the wanderers of the east.'"},
    ],
    "dungeon": [
        {"id": "lore_dungeon_tablet", "tile_x": 18, "tile_y": 20,
         "lore_key": "golem_creation",
         "text": "A cracked tablet: 'The Golem was forged to guard what must not be opened.'"},
        {"id": "lore_dungeon_journal", "tile_x": 7, "tile_y": 14,
         "lore_key": "scout_warning",
         "text": "A scout's journal: 'Electrified floors — don't touch the metal grates.'"},
    ]
}
