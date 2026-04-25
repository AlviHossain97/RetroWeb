#!/usr/bin/env python3
"""
Generate gameplay tables for the standalone Mythical GBA port.

The desktop Python content remains the source of truth; this script emits
compact C tables for maps, quests, items, NPCs, interactables, enemies,
bosses, and stage metadata so the handheld port can follow the same authored
logic instead of maintaining a second manual content layer.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
GEN_DIR = Path(__file__).resolve().parent / "generated"

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
sys.path.insert(0, str(ROOT_DIR))

from ai.config_loader import get_enemy_config, load_stage_data  # noqa: E402
from animal import ANIMAL_DEFS  # noqa: E402
from animal_spawner import ZONE_DEFS  # noqa: E402
from campaign import STAGE_MAPS, STAGE_NAMES, STAGE_PLAYER_FORMS  # noqa: E402
from crafting import RECIPES  # noqa: E402
from content.stage2_content import (  # noqa: E402
    BOSS_DEFS as _BOSS_DEFS_S2,
    CHEST_DEFS as _CHEST_DEFS_S2,
    ENEMY_SPAWN_DEFS as _ENEMY_DEFS_S2,
    GROUND_ITEM_DEFS as _GROUND_DEFS_S2,
    LORE_ITEM_DEFS as _LORE_DEFS_S2,
    NPC_DEFS as _NPC_DEFS_S2,
)
from content.stage3_content import (  # noqa: E402
    BOSS_DEFS as _BOSS_DEFS_S3,
    CHEST_DEFS as _CHEST_DEFS_S3,
    ENEMY_SPAWN_DEFS as _ENEMY_DEFS_S3,
    GROUND_ITEM_DEFS as _GROUND_DEFS_S3,
    LORE_ITEM_DEFS as _LORE_DEFS_S3,
    NPC_DEFS as _NPC_DEFS_S3,
)
from content_registry import (  # noqa: E402
    BOSS_DEFS as _BOSS_DEFS_S1,
    CHEST_DEFS as _CHEST_DEFS_S1,
    ENEMY_SPAWN_DEFS as _ENEMY_DEFS_S1,
    GROUND_ITEM_DEFS as _GROUND_DEFS_S1,
    LORE_ITEM_DEFS as _LORE_DEFS_S1,
    NPC_DEFS as _NPC_DEFS_S1,
)
from item_system import ITEM_DEFS  # noqa: E402
from maps.dungeon import DUNGEON  # noqa: E402
from maps.ruins import RUINS_APPROACH, RUINS_DEPTHS  # noqa: E402
from maps.sanctum import SANCTUM_HALLS, THRONE_ROOM  # noqa: E402
from maps.village import VILLAGE  # noqa: E402
from quest import QuestManager  # noqa: E402
from rewards import normalize_reward  # noqa: E402


MAP_ORDER = [
    ("village", "Village of Thornhollow", "Village", VILLAGE),
    ("dungeon", "Dark Forest Caverns", "Forest Cave", DUNGEON),
    ("ruins_approach", "Haunted Ruins", "Ruins", RUINS_APPROACH),
    ("ruins_depths", "Ruins Depths", "Deep Ruins", RUINS_DEPTHS),
    ("sanctum_halls", "Sanctum Halls", "Sanctum", SANCTUM_HALLS),
    ("throne_room", "Throne of the Sovereign", "Throne", THRONE_ROOM),
]
MAP_INDEX = {name: idx for idx, (name, _, _, _) in enumerate(MAP_ORDER)}

NPC_DEFS_ALL = {**_NPC_DEFS_S1, **_NPC_DEFS_S2, **_NPC_DEFS_S3}
CHEST_DEFS_ALL = {**_CHEST_DEFS_S1, **_CHEST_DEFS_S2, **_CHEST_DEFS_S3}
GROUND_DEFS_ALL = {**_GROUND_DEFS_S1, **_GROUND_DEFS_S2, **_GROUND_DEFS_S3}
ENEMY_DEFS_ALL = {**_ENEMY_DEFS_S1, **_ENEMY_DEFS_S2, **_ENEMY_DEFS_S3}
BOSS_DEFS_ALL = {**_BOSS_DEFS_S1, **_BOSS_DEFS_S2, **_BOSS_DEFS_S3}
LORE_DEFS_ALL = {**_LORE_DEFS_S1, **_LORE_DEFS_S2, **_LORE_DEFS_S3}

CATEGORY_MAP = {
    "key_item": "GBA_ITEM_KEY_ITEM",
    "weapon": "GBA_ITEM_WEAPON",
    "armor": "GBA_ITEM_ARMOR",
    "accessory": "GBA_ITEM_ACCESSORY",
    "consumable": "GBA_ITEM_CONSUMABLE",
    "material": "GBA_ITEM_MATERIAL",
}
SLOT_MAP = {
    None: "GBA_SLOT_NONE",
    "weapon": "GBA_SLOT_WEAPON",
    "armor": "GBA_SLOT_ARMOR",
    "accessory": "GBA_SLOT_ACCESSORY",
}
FACING_MAP = {
    "down": "0",
    "up": "1",
    "left": "2",
    "right": "3",
}
TRIGGER_MAP = {
    "talk_npc": "GBA_TRIGGER_TALK_NPC",
    "pickup_item": "GBA_TRIGGER_PICKUP_ITEM",
    "map_entered": "GBA_TRIGGER_MAP_ENTERED",
    "boss_defeated": "GBA_TRIGGER_BOSS_DEFEATED",
}
QUEST_STAGE_MAP = {
    "main": 1,
    "main_s2": 2,
    "main_s3": 3,
}
QUEST_BRIEFS = {
    ("main", 0): "Talk to Rowan",
    ("main", 1): "Find Old Sword",
    ("main", 2): "Get Forest Key",
    ("main", 3): "Bring Healing Herb",
    ("main", 4): "Enter cave",
    ("main", 5): "Defeat Dark Golem",
    ("main_s2", 0): "Reach the ruins",
    ("main_s2", 1): "Push deeper",
    ("main_s2", 2): "Defeat Gravewarden",
    ("main_s3", 0): "Enter Sanctum",
    ("main_s3", 1): "Reach Throne",
    ("main_s3", 2): "Defeat Sovereign",
}


ANIMAL_BEHAVIOR_MAP = {
    "flee": 0,
    "territorial": 1,
    "aggressive": 2,
}

ANIMAL_TYPE_ORDER = ["deer", "rabbit", "wolf", "boar", "bear", "fish"]


def _build_animal_spawns() -> list[tuple[int, str, int, int, int]]:
    """Pre-generate fixed animal spawn positions from zone definitions."""
    import random as _rng
    _rng.seed(42)
    spawns: list[tuple[int, str, int, int, int]] = []
    animal_type_index = {atype: idx for idx, atype in enumerate(ANIMAL_TYPE_ORDER)}
    for map_name, _, _, map_data in MAP_ORDER:
        if map_name not in ZONE_DEFS:
            continue
        map_id = MAP_INDEX[map_name]
        w = map_data["width"]
        h = map_data["height"]
        for zone in ZONE_DEFS[map_name]:
            x1, y1, x2, y2 = zone["rect"]
            x1 = max(1, min(x1, w - 2))
            y1 = max(1, min(y1, h - 2))
            x2 = max(x1 + 1, min(x2, w - 1))
            y2 = max(y1 + 1, min(y2, h - 1))
            roster = zone["roster"]
            total_weight = sum(entry["weight"] for entry in roster)
            count = zone["max_count"]
            placed = 0
            for _ in range(count * 4):
                if placed >= count:
                    break
                roll = _rng.randint(0, total_weight - 1)
                chosen = roster[0]["atype"]
                accum = 0
                for entry in roster:
                    accum += entry["weight"]
                    if roll < accum:
                        chosen = entry["atype"]
                        break
                tx = _rng.randint(x1, x2 - 1)
                ty = _rng.randint(y1, y2 - 1)
                if tx < 1 or ty < 1 or tx >= w - 1 or ty >= h - 1:
                    continue
                if map_data["collision"][ty][tx]:
                    continue
                if map_data["collision"][max(0, ty - 1)][tx]:
                    continue
                if map_data["collision"][min(h - 1, ty + 1)][tx]:
                    continue
                spawns.append((map_id, chosen, animal_type_index[chosen], tx, ty))
                placed += 1
    return spawns


def sanitize(name: str) -> str:
    return name.replace("-", "_").replace(" ", "_").replace("'", "").replace("/", "_")


def c_string(value: str | None) -> str:
    if value is None:
        return "0"
    escaped = (
        str(value)
        .replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
    )
    return f'"{escaped}"'


def rgb_to_gba(rgb: tuple[int, int, int] | None) -> int:
    if not rgb:
        return 0
    r, g, b = rgb
    return (r // 8) | ((g // 8) << 5) | ((b // 8) << 10)


def pack_collision(map_data: dict) -> list[int]:
    width = map_data["width"]
    height = map_data["height"]
    packed = [0] * ((width * height + 7) // 8)
    for row in range(height):
        for col in range(width):
            if map_data["collision"][row][col]:
                bit = row * width + col
                packed[bit // 8] |= 1 << (bit % 8)
    return packed


def emit_u8_array(handle, name: str, values: list[int]) -> None:
    handle.write(f"static const u8 {name}[{len(values)}] = {{\n")
    for offset in range(0, len(values), 20):
        chunk = values[offset : offset + 20]
        handle.write("    " + ", ".join(str(value) for value in chunk) + ",\n")
    handle.write("};\n\n")


def stage_for_map(map_name: str) -> int:
    for stage, maps in STAGE_MAPS.items():
        if map_name in maps:
            return int(stage)
    return 1


def stage_hp_bonus(stage: int) -> int:
    data = load_stage_data()
    return int(data.get("stage_player_hp_bonus", {}).get(str(stage), 0))


def parse_heal_amount(item_def: dict) -> int:
    effect = item_def.get("use_effect", "")
    if isinstance(effect, str) and effect.startswith("heal_"):
        try:
            return max(0, int(effect.split("_", 1)[1]))
        except (TypeError, ValueError):
            return 0
    return 0


# GBA use_effect enum — mirrors pygame's use_effect strings so the handheld can
# apply the same consume semantics (raw_meat 2-per-half-heart, cure_poison, etc.).
USE_EFFECT_MAP = {
    "": 0,            # GBA_USE_NONE
    "heal_1": 1,      # GBA_USE_HEAL (generic, 1 heart per use)
    "heal_2": 1,
    "heal_3": 1,
    "cure_poison": 2, # GBA_USE_CURE
    "grant_skill_point": 3,  # GBA_USE_SKILL_POINT
    "eat_raw_meat": 4,       # GBA_USE_EAT_RAW  (2 pieces per half heart)
    "eat_cooked_meat": 5,    # GBA_USE_EAT_COOKED (1 piece per half heart)
}


def parse_use_effect(item_id: str, item_def: dict) -> int:
    # Special-case raw/cooked meat because pygame doesn't tag them with a
    # different use_effect string — the behaviour lives in gameplay.py.
    if item_id == "raw_meat":
        return USE_EFFECT_MAP["eat_raw_meat"]
    if item_id == "cooked_meat":
        return USE_EFFECT_MAP["eat_cooked_meat"]
    effect = item_def.get("use_effect", "")
    if isinstance(effect, str) and effect in USE_EFFECT_MAP:
        return USE_EFFECT_MAP[effect]
    if isinstance(effect, str) and effect.startswith("heal_"):
        return USE_EFFECT_MAP["heal_1"]
    return 0


def emit_reward_literal(reward: dict) -> str:
    normalized = normalize_reward(reward)
    kind = normalized["kind"]
    if kind == "key_item":
        return "{{GBA_REWARD_ITEM, {}, 0, {}}}".format(
            c_string(normalized["item_id"]),
            c_string(normalized.get("label")),
        )
    if kind == "currency":
        return "{{GBA_REWARD_CURRENCY, 0, {}, {}}}".format(
            int(normalized["amount"]),
            c_string(normalized.get("label")),
        )
    return "{{GBA_REWARD_HEAL, 0, {}, {}}}".format(
        int(normalized["amount"]),
        c_string(normalized.get("label")),
    )


def emit_map_tables() -> None:
    header_path = GEN_DIR / "maps.h"
    source_path = GEN_DIR / "maps.c"

    with open(header_path, "w", encoding="utf-8", newline="\n") as header:
        header.write("/* Auto-generated by gba_project/convert_content.py */\n")
        header.write("#ifndef MYTHICAL_GBA_MAPS_H\n#define MYTHICAL_GBA_MAPS_H\n\n")
        header.write('#include "../gba.h"\n\n')
        header.write("typedef struct {\n")
        header.write("    u8 x;\n")
        header.write("    u8 y;\n")
        header.write("    u8 target_map;\n")
        header.write("    u8 target_x;\n")
        header.write("    u8 target_y;\n")
        header.write("} GBAExit;\n\n")
        header.write("typedef struct {\n")
        header.write("    const char *name;\n")
        header.write("    const char *label;\n")
        header.write("    const char *hud_label;\n")
        header.write("    const u8 *ground;\n")
        header.write("    const u8 *decor;\n")
        header.write("    const u8 *collision;\n")
        header.write("    const GBAExit *exits;\n")
        header.write("    u8 width;\n")
        header.write("    u8 height;\n")
        header.write("    u8 spawn_x;\n")
        header.write("    u8 spawn_y;\n")
        header.write("    u8 exit_count;\n")
        header.write("} GBAMap;\n\n")
        for idx, (name, _, _, _) in enumerate(MAP_ORDER):
            header.write(f"#define MAP_{sanitize(name).upper()} {idx}\n")
        header.write(f"#define MAP_COUNT {len(MAP_ORDER)}\n\n")
        header.write("extern const GBAMap gba_maps[MAP_COUNT];\n\n")
        header.write("#endif\n")

    with open(source_path, "w", encoding="utf-8", newline="\n") as source:
        source.write("/* Auto-generated by gba_project/convert_content.py */\n")
        source.write('#include "maps.h"\n\n')

        for name, _, _, map_data in MAP_ORDER:
            safe_name = sanitize(name)
            width = int(map_data["width"])
            height = int(map_data["height"])
            ground = [tile for row in map_data["ground"] for tile in row]
            decor = (
                [tile for row in map_data.get("decor", []) for tile in row]
                if map_data.get("decor")
                else [0] * (width * height)
            )
            collision = pack_collision(map_data)
            exits = []
            for (x, y), exit_info in sorted(map_data.get("exits", {}).items()):
                exits.append(
                    (
                        int(x),
                        int(y),
                        MAP_INDEX[exit_info["map"]],
                        int(exit_info["spawn"][0]),
                        int(exit_info["spawn"][1]),
                    )
                )

            emit_u8_array(source, f"{safe_name}_ground", ground)
            emit_u8_array(source, f"{safe_name}_decor", decor)
            emit_u8_array(source, f"{safe_name}_collision", collision)

            source.write(f"static const GBAExit {safe_name}_exits[{len(exits) or 1}] = {{\n")
            if exits:
                for x, y, target_map, target_x, target_y in exits:
                    source.write(
                        f"    {{{x}, {y}, {target_map}, {target_x}, {target_y}}},\n"
                    )
            else:
                source.write("    {0, 0, 0, 0, 0},\n")
            source.write("};\n\n")

        source.write("const GBAMap gba_maps[MAP_COUNT] = {\n")
        for name, label, hud_label, map_data in MAP_ORDER:
            safe_name = sanitize(name)
            spawn = map_data.get("spawns", {}).get("player", (1, 1))
            exit_count = len(map_data.get("exits", {}))
            source.write(
                f"    {{{c_string(name)}, {c_string(label)}, {c_string(hud_label)}, {safe_name}_ground, {safe_name}_decor, "
                f"{safe_name}_collision, {safe_name}_exits, {map_data['width']}, {map_data['height']}, "
                f"{spawn[0]}, {spawn[1]}, {exit_count}}},\n"
            )
        source.write("};\n")


def emit_content_tables() -> None:
    header_path = GEN_DIR / "content.h"
    source_path = GEN_DIR / "content.c"

    all_items = list(ITEM_DEFS.items())
    quests = list(QuestManager().quests.values())

    enemy_type_ids: list[str] = []
    for map_name, spawns in ENEMY_DEFS_ALL.items():
        if map_name not in MAP_INDEX:
            continue
        for spawn in spawns:
            enemy_type = spawn["type"]
            if enemy_type not in enemy_type_ids:
                enemy_type_ids.append(enemy_type)
    enemy_type_index = {enemy_id: idx for idx, enemy_id in enumerate(enemy_type_ids)}

    npcs = []
    chests = []
    ground_items = []
    lore_items = []
    enemy_spawns = []
    bosses = []
    signs = []

    for map_name, _, _, map_data in MAP_ORDER:
        map_id = MAP_INDEX[map_name]
        for npc in NPC_DEFS_ALL.get(map_name, []):
            spawn = map_data.get("spawns", {}).get(npc["spawn_key"], (0, 0))
            npcs.append((map_id, spawn, npc))
        for chest in CHEST_DEFS_ALL.get(map_name, []):
            chests.append((map_id, chest))
        for ground in GROUND_DEFS_ALL.get(map_name, []):
            ground_items.append((map_id, ground))
        for lore in LORE_DEFS_ALL.get(map_name, []):
            lore_items.append((map_id, lore))
        for enemy in ENEMY_DEFS_ALL.get(map_name, []):
            enemy_spawns.append((map_id, enemy))
        boss = BOSS_DEFS_ALL.get(map_name)
        if boss:
            bosses.append((map_id, map_name, boss))
        for (tile_x, tile_y), text in sorted(map_data.get("signs", {}).items()):
            signs.append((map_id, tile_x, tile_y, text))

    stage_data = load_stage_data()
    boss_loot = stage_data.get("boss_loot", {})

    with open(header_path, "w", encoding="utf-8", newline="\n") as header:
        header.write("/* Auto-generated by gba_project/convert_content.py */\n")
        header.write("#ifndef MYTHICAL_GBA_CONTENT_H\n#define MYTHICAL_GBA_CONTENT_H\n\n")
        header.write('#include "../gba.h"\n')
        header.write('#include "maps.h"\n\n')
        header.write("#define GBA_REWARD_NONE 0\n")
        header.write("#define GBA_REWARD_ITEM 1\n")
        header.write("#define GBA_REWARD_CURRENCY 2\n")
        header.write("#define GBA_REWARD_HEAL 3\n\n")
        header.write("#define GBA_ITEM_KEY_ITEM 0\n")
        header.write("#define GBA_ITEM_WEAPON 1\n")
        header.write("#define GBA_ITEM_ARMOR 2\n")
        header.write("#define GBA_ITEM_ACCESSORY 3\n")
        header.write("#define GBA_ITEM_CONSUMABLE 4\n")
        header.write("#define GBA_ITEM_MATERIAL 5\n\n")
        header.write("#define GBA_SLOT_NONE 0\n")
        header.write("#define GBA_SLOT_WEAPON 1\n")
        header.write("#define GBA_SLOT_ARMOR 2\n")
        header.write("#define GBA_SLOT_ACCESSORY 3\n\n")
        header.write("#define GBA_TRIGGER_NONE 0\n")
        header.write("#define GBA_TRIGGER_TALK_NPC 1\n")
        header.write("#define GBA_TRIGGER_PICKUP_ITEM 2\n")
        header.write("#define GBA_TRIGGER_MAP_ENTERED 3\n")
        header.write("#define GBA_TRIGGER_BOSS_DEFEATED 4\n\n")
        header.write("#define GBA_DIALOG_STAGE_DEFAULT -1\n")
        header.write("#define GBA_DIALOG_STAGE_COMPLETE -2\n\n")
        header.write("typedef struct {\n    u8 kind;\n    const char *item_id;\n    u16 amount;\n    const char *label;\n} GBAReward;\n\n")
        header.write("#define GBA_USE_NONE 0\n")
        header.write("#define GBA_USE_HEAL 1\n")
        header.write("#define GBA_USE_CURE 2\n")
        header.write("#define GBA_USE_SKILL_POINT 3\n")
        header.write("#define GBA_USE_EAT_RAW 4\n")
        header.write("#define GBA_USE_EAT_COOKED 5\n\n")
        header.write("typedef struct {\n    const char *id;\n    const char *name;\n    u8 category;\n    u8 stack_max;\n    u8 equip_slot;\n    s8 attack_bonus;\n    s8 defense_bonus;\n    s16 speed_bonus_q8;\n    u8 heal_amount;\n    u8 use_effect;\n} GBAItemDef;\n\n")
        header.write("typedef struct {\n    s8 stage_key;\n    const char **pages;\n    u8 page_count;\n} GBADialogueVariant;\n\n")
        header.write("typedef struct {\n    const char *npc_id;\n    const char *name;\n    u8 map_id;\n    u8 tile_x;\n    u8 tile_y;\n    u16 body_color;\n    u16 hair_color;\n    u8 facing;\n    const GBADialogueVariant *variants;\n    u8 variant_count;\n    const char *give_item_id;\n    s8 give_stage;\n    const char *take_item_id;\n    s8 take_stage;\n} GBANpcDef;\n\n")
        header.write("typedef struct {\n    const char *id;\n    u8 map_id;\n    u8 tile_x;\n    u8 tile_y;\n    GBAReward reward;\n    const char *label;\n} GBAChestDef;\n\n")
        header.write("typedef struct {\n    const char *id;\n    u8 map_id;\n    u8 tile_x;\n    u8 tile_y;\n    GBAReward reward;\n} GBAGroundItemDef;\n\n")
        header.write("typedef struct {\n    const char *id;\n    u8 map_id;\n    u8 tile_x;\n    u8 tile_y;\n    const char **pages;\n    u8 page_count;\n    const char *lore_key;\n} GBALoreDef;\n\n")
        header.write("typedef struct {\n    const char *id;\n    u8 map_id;\n    u8 tile_x;\n    u8 tile_y;\n    const char **pages;\n    u8 page_count;\n} GBASignDef;\n\n")
        header.write("typedef struct {\n    u8 trigger;\n    const char *target;\n    const char *desc;\n    const char *brief;\n} GBAQuestStage;\n\n")
        header.write("typedef struct {\n    const char *id;\n    const char *name;\n    const GBAQuestStage *stages;\n    u8 stage_count;\n} GBAQuestDef;\n\n")
        header.write("typedef struct {\n    GBAReward reward;\n    u8 chance_pct;\n} GBAEnemyDrop;\n\n")
        header.write("typedef struct {\n    const char *id;\n    u8 max_hp;\n    u8 damage;\n    u16 speed_fp;\n    u8 chase_range_q4;\n    u8 attack_range_q4;\n    u8 attack_cooldown_frames;\n    u8 size_q4;\n    u16 color;\n    const GBAEnemyDrop *drops;\n    u8 drop_count;\n    u8 ranged;\n} GBAEnemyTypeDef;\n\n")
        header.write("typedef struct {\n    const char *id;\n    u8 map_id;\n    u8 tile_x;\n    u8 tile_y;\n    u8 enemy_type_index;\n} GBAEnemySpawnDef;\n\n")
        header.write("typedef struct {\n    const char *item_id;\n    u8 chance_pct;\n} GBABossLootDef;\n\n")
        header.write("typedef struct {\n    const char *id;\n    u8 map_id;\n    u8 tile_x;\n    u8 tile_y;\n    u8 stage;\n    const GBABossLootDef *loot;\n    u8 loot_count;\n} GBABossDef;\n\n")
        header.write("#define GBA_ANIMAL_BEHAVE_FLEE 0\n")
        header.write("#define GBA_ANIMAL_BEHAVE_TERRITORIAL 1\n")
        header.write("#define GBA_ANIMAL_BEHAVE_AGGRESSIVE 2\n\n")
        header.write("typedef struct {\n    const char *id;\n    u8 max_hp;\n    u8 damage;\n    u16 speed_fp;\n    u8 flee_range_q4;\n    u8 aggro_range_q4;\n    u8 behavior;\n    u16 color;\n} GBAAnimalTypeDef;\n\n")
        header.write("typedef struct {\n    u8 map_id;\n    u8 animal_type_index;\n    u8 tile_x;\n    u8 tile_y;\n} GBAAnimalSpawnDef;\n\n")
        header.write("#define GBA_MAX_RECIPE_INGREDIENTS 3\n\n")
        header.write("typedef struct {\n    const char *item_id;\n    u8 qty;\n} GBAIngredient;\n\n")
        header.write("typedef struct {\n    const char *id;\n    const char *output_id;\n    u8 output_qty;\n    GBAIngredient ingredients[GBA_MAX_RECIPE_INGREDIENTS];\n    u8 ingredient_count;\n} GBARecipeDef;\n\n")
        header.write("typedef struct {\n    const char *id;\n    u8 map_id;\n    u8 tile_x;\n    u8 tile_y;\n} GBAWaypointDef;\n\n")
        header.write(f"#define GBA_ITEM_COUNT {len(all_items)}\n")
        header.write(f"#define GBA_QUEST_COUNT {len(quests)}\n")
        header.write(f"#define GBA_NPC_COUNT {len(npcs)}\n")
        header.write(f"#define GBA_CHEST_COUNT {len(chests)}\n")
        header.write(f"#define GBA_GROUND_ITEM_COUNT {len(ground_items)}\n")
        header.write(f"#define GBA_LORE_COUNT {len(lore_items)}\n")
        header.write(f"#define GBA_SIGN_COUNT {len(signs)}\n")
        header.write(f"#define GBA_ENEMY_TYPE_COUNT {len(enemy_type_ids)}\n")
        header.write(f"#define GBA_ENEMY_SPAWN_COUNT {len(enemy_spawns)}\n")
        header.write(f"#define GBA_BOSS_COUNT {len(bosses)}\n")
        animal_spawns = _build_animal_spawns()
        all_recipes = [(rid, rdef) for rid, rdef in RECIPES.items() if len(rdef.get("ingredients", [])) <= 3]
        waypoints = [
            ("village_square", "village", 17, 17),
            ("village_bridge", "village", 38, 17),
            ("dungeon_entrance", "dungeon", 5, 3),
            ("ruins_approach", "ruins_approach", 2, 17),
            ("ruins_depths", "ruins_depths", 2, 19),
            ("sanctum_halls", "sanctum_halls", 2, 19),
        ]
        header.write(f"#define GBA_ANIMAL_TYPE_COUNT {len(ANIMAL_TYPE_ORDER)}\n")
        header.write(f"#define GBA_ANIMAL_SPAWN_COUNT {len(animal_spawns)}\n")
        header.write(f"#define GBA_RECIPE_COUNT {len(all_recipes)}\n")
        header.write(f"#define GBA_WAYPOINT_COUNT {len(waypoints)}\n\n")
        header.write("extern const GBAItemDef gba_items[GBA_ITEM_COUNT];\n")
        header.write("extern const GBAQuestDef gba_quests[GBA_QUEST_COUNT];\n")
        header.write("extern const GBANpcDef gba_npcs[GBA_NPC_COUNT];\n")
        header.write("extern const GBAChestDef gba_chests[GBA_CHEST_COUNT];\n")
        header.write("extern const GBAGroundItemDef gba_ground_items[GBA_GROUND_ITEM_COUNT];\n")
        header.write("extern const GBALoreDef gba_lore_items[GBA_LORE_COUNT];\n")
        header.write("extern const GBASignDef gba_signs[GBA_SIGN_COUNT];\n")
        header.write("extern const GBAEnemyTypeDef gba_enemy_types[GBA_ENEMY_TYPE_COUNT];\n")
        header.write("extern const GBAEnemySpawnDef gba_enemy_spawns[GBA_ENEMY_SPAWN_COUNT];\n")
        header.write("extern const GBABossDef gba_bosses[GBA_BOSS_COUNT];\n")
        header.write("extern const GBAAnimalTypeDef gba_animal_types[GBA_ANIMAL_TYPE_COUNT];\n")
        header.write("extern const GBAAnimalSpawnDef gba_animal_spawns[GBA_ANIMAL_SPAWN_COUNT];\n")
        header.write("extern const GBARecipeDef gba_recipes[GBA_RECIPE_COUNT];\n")
        header.write("extern const GBAWaypointDef gba_waypoints[GBA_WAYPOINT_COUNT];\n")
        header.write("extern const char *gba_stage_names[4];\n")
        header.write("extern const char *gba_stage_forms[4];\n")
        header.write("extern const u8 gba_stage_entry_maps[4];\n")
        header.write("extern const u8 gba_stage_hp_bonus[4];\n")
        header.write("extern const u8 gba_stage_quest_index[4];\n")
        header.write("extern const u8 gba_map_stage[MAP_COUNT];\n\n")
        header.write("#endif\n")

    with open(source_path, "w", encoding="utf-8", newline="\n") as source:
        source.write("/* Auto-generated by gba_project/convert_content.py */\n")
        source.write('#include "content.h"\n\n')

        for npc_index, (_, _, npc) in enumerate(npcs):
            for variant_index, pages in enumerate(npc["dialogue_stages"].values()):
                page_name = f"npc_{npc_index}_variant_{variant_index}_pages"
                source.write(f"static const char *{page_name}[{len(pages)}] = {{\n")
                for page in pages:
                    source.write(f"    {c_string(page)},\n")
                source.write("};\n")
            source.write("\n")

        for lore_index, (_, lore) in enumerate(lore_items):
            pages = [line for line in str(lore["text"]).split("\n") if line.strip()]
            array_name = f"lore_{lore_index}_pages"
            source.write(f"static const char *{array_name}[{len(pages)}] = {{\n")
            for page in pages:
                source.write(f"    {c_string(page)},\n")
            source.write("};\n\n")

        for sign_index, (_, _, _, text) in enumerate(signs):
            pages = [line for line in str(text).split("\n") if line.strip()]
            array_name = f"sign_{sign_index}_pages"
            source.write(f"static const char *{array_name}[{len(pages)}] = {{\n")
            for page in pages:
                source.write(f"    {c_string(page)},\n")
            source.write("};\n\n")

        for quest_index, quest in enumerate(quests):
            array_name = f"quest_{quest_index}_stages"
            source.write(f"static const GBAQuestStage {array_name}[{len(quest.stages)}] = {{\n")
            for stage_index, stage in enumerate(quest.stages):
                brief = QUEST_BRIEFS.get((quest.id, stage_index), stage["desc"])
                source.write(
                    f"    {{{TRIGGER_MAP[stage['trigger']]}, {c_string(stage.get('trigger_data'))}, {c_string(stage['desc'])}, {c_string(brief)}}},\n"
                )
            source.write("};\n\n")

        for enemy_index, enemy_id in enumerate(enemy_type_ids):
            base = get_enemy_config(enemy_id, "normal")
            drops = base.get("drops", [])
            array_name = f"enemy_type_{enemy_index}_drops"
            source.write(f"static const GBAEnemyDrop {array_name}[{len(drops) or 1}] = {{\n")
            if drops:
                for drop in drops:
                    chance_pct = int(round(float(drop.get("chance", 0.0)) * 100.0))
                    source.write(f"    {{{emit_reward_literal(drop)}, {chance_pct}}},\n")
            else:
                source.write("    {{ {GBA_REWARD_NONE, 0, 0, 0}, 0 }},\n")
            source.write("};\n\n")

        for boss_index, (_, _, boss) in enumerate(bosses):
            loot_entries = boss_loot.get(boss["id"], [])
            array_name = f"boss_{boss_index}_loot"
            source.write(f"static const GBABossLootDef {array_name}[{len(loot_entries) or 1}] = {{\n")
            if loot_entries:
                for entry in loot_entries:
                    chance_pct = int(round(float(entry.get("chance", 1.0)) * 100.0))
                    source.write(f"    {{{c_string(entry['item_id'])}, {chance_pct}}},\n")
            else:
                source.write("    {0, 0},\n")
            source.write("};\n\n")

        source.write("const GBAItemDef gba_items[GBA_ITEM_COUNT] = {\n")
        for item_id, item_def in all_items:
            stats = item_def.get("stats", {})
            source.write(
                f"    {{{c_string(item_id)}, {c_string(item_def.get('name', item_id))}, {CATEGORY_MAP[item_def.get('category', 'key_item')]}, "
                f"{int(item_def.get('stack_max', 1))}, {SLOT_MAP[item_def.get('equip_slot')]}, "
                f"{int(round(stats.get('attack', 0)))}, {int(round(stats.get('defense', 0)))}, "
                f"{int(round(float(stats.get('speed', 0.0)) * 256.0))}, {parse_heal_amount(item_def)}, "
                f"{parse_use_effect(item_id, item_def)}}},\n"
            )
        source.write("};\n\n")

        source.write("const GBAQuestDef gba_quests[GBA_QUEST_COUNT] = {\n")
        for quest_index, quest in enumerate(quests):
            source.write(f"    {{{c_string(quest.id)}, {c_string(quest.name)}, quest_{quest_index}_stages, {len(quest.stages)}}},\n")
        source.write("};\n\n")

        for npc_index, (_, _, npc) in enumerate(npcs):
            variant_name = f"npc_{npc_index}_variants"
            source.write(f"static const GBADialogueVariant {variant_name}[{len(npc['dialogue_stages'])}] = {{\n")
            for variant_index, (stage_key, pages) in enumerate(npc["dialogue_stages"].items()):
                if stage_key == "default":
                    stage_literal = "GBA_DIALOG_STAGE_DEFAULT"
                elif stage_key == "complete":
                    stage_literal = "GBA_DIALOG_STAGE_COMPLETE"
                else:
                    stage_literal = str(int(stage_key))
                source.write(f"    {{{stage_literal}, npc_{npc_index}_variant_{variant_index}_pages, {len(pages)}}},\n")
            source.write("};\n\n")

        source.write("const GBANpcDef gba_npcs[GBA_NPC_COUNT] = {\n")
        for npc_index, (map_id, spawn, npc) in enumerate(npcs):
            give_def = npc.get("gives_item")
            take_def = npc.get("takes_item")
            source.write(
                f"    {{{c_string(npc['npc_id'])}, {c_string(npc['name'])}, {map_id}, {spawn[0]}, {spawn[1]}, "
                f"{rgb_to_gba(npc.get('body_color'))}, {rgb_to_gba(npc.get('hair_color') or npc.get('body_color'))}, "
                f"{FACING_MAP[npc.get('facing', 'down')]}, npc_{npc_index}_variants, {len(npc['dialogue_stages'])}, "
                f"{c_string(give_def.get('item_id') if give_def else None)}, {int(give_def.get('quest_stage', -1) if give_def else -1)}, "
                f"{c_string(take_def.get('item_id') if take_def else None)}, {int(take_def.get('quest_stage', -1) if take_def else -1)}}},\n"
            )
        source.write("};\n\n")

        source.write("const GBAChestDef gba_chests[GBA_CHEST_COUNT] = {\n")
        for map_id, chest in chests:
            source.write(f"    {{{c_string(chest['id'])}, {map_id}, {int(chest['tile_x'])}, {int(chest['tile_y'])}, {emit_reward_literal(chest['reward'])}, {c_string(chest.get('label', 'Chest'))}}},\n")
        source.write("};\n\n")

        source.write("const GBAGroundItemDef gba_ground_items[GBA_GROUND_ITEM_COUNT] = {\n")
        for map_id, ground in ground_items:
            source.write(f"    {{{c_string(ground['id'])}, {map_id}, {int(ground['tile_x'])}, {int(ground['tile_y'])}, {emit_reward_literal(ground['reward'])}}},\n")
        source.write("};\n\n")

        source.write("const GBALoreDef gba_lore_items[GBA_LORE_COUNT] = {\n")
        for lore_index, (map_id, lore) in enumerate(lore_items):
            pages = [line for line in str(lore['text']).split('\\n') if line.strip()]
            source.write(f"    {{{c_string(lore['id'])}, {map_id}, {int(lore['tile_x'])}, {int(lore['tile_y'])}, lore_{lore_index}_pages, {len(pages)}, {c_string(lore.get('lore_key'))}}},\n")
        source.write("};\n\n")

        source.write("const GBASignDef gba_signs[GBA_SIGN_COUNT] = {\n")
        for sign_index, (map_id, tile_x, tile_y, text) in enumerate(signs):
            pages = [line for line in str(text).split('\\n') if line.strip()]
            sign_id = f"sign_{map_id}_{tile_x}_{tile_y}"
            source.write(f"    {{{c_string(sign_id)}, {map_id}, {tile_x}, {tile_y}, sign_{sign_index}_pages, {len(pages)}}},\n")
        source.write("};\n\n")

        source.write("const GBAEnemyTypeDef gba_enemy_types[GBA_ENEMY_TYPE_COUNT] = {\n")
        for enemy_index, enemy_id in enumerate(enemy_type_ids):
            base = get_enemy_config(enemy_id, 'normal')
            source.write(
                f"    {{{c_string(enemy_id)}, {int(round(base.get('max_hp', 1)))}, {int(round(base.get('damage', 1)))}, "
                f"{int(round(float(base.get('speed', 1.0)) * 256.0))}, {int(round(float(base.get('chase_range', 1.0)) * 4.0))}, "
                f"{int(round(float(base.get('attack_range', 1.0)) * 4.0))}, {int(round(float(base.get('attack_cd', 1.0)) * 60.0))}, "
                f"{int(round(float(base.get('size', 0.8)) * 4.0))}, {rgb_to_gba(tuple(base.get('color', (255, 255, 255))))}, "
                f"enemy_type_{enemy_index}_drops, {len(base.get('drops', []))}, {1 if float(base.get('attack_range', 1.0)) > 1.5 else 0}}},\n"
            )
        source.write("};\n\n")

        source.write("const GBAEnemySpawnDef gba_enemy_spawns[GBA_ENEMY_SPAWN_COUNT] = {\n")
        for map_id, enemy in enemy_spawns:
            source.write(f"    {{{c_string(enemy['id'])}, {map_id}, {int(enemy['x'])}, {int(enemy['y'])}, {enemy_type_index[enemy['type']]}}},\n")
        source.write("};\n\n")

        source.write("const GBABossDef gba_bosses[GBA_BOSS_COUNT] = {\n")
        for boss_index, (map_id, map_name, boss) in enumerate(bosses):
            source.write(f"    {{{c_string(boss['id'])}, {map_id}, {int(boss['x'])}, {int(boss['y'])}, {stage_for_map(map_name)}, boss_{boss_index}_loot, {len(boss_loot.get(boss['id'], []))}}},\n")
        source.write("};\n\n")

        source.write("const GBAAnimalTypeDef gba_animal_types[GBA_ANIMAL_TYPE_COUNT] = {\n")
        for atype in ANIMAL_TYPE_ORDER:
            adef = ANIMAL_DEFS[atype]
            source.write(
                f"    {{{c_string(atype)}, {int(adef['max_hp'])}, {int(adef.get('attack_damage', 0))}, "
                f"{int(round(float(adef.get('speed', 2.0)) * 256.0))}, "
                f"{int(round(float(adef.get('flee_range', 0.0)) * 4.0))}, "
                f"{int(round(float(adef.get('aggro_range', 0.0)) * 4.0))}, "
                f"{ANIMAL_BEHAVIOR_MAP[adef.get('behavior', 'flee')]}, "
                f"{rgb_to_gba(tuple(adef.get('color', (180, 180, 180))))}}},\n"
            )
        source.write("};\n\n")

        source.write(f"const GBAAnimalSpawnDef gba_animal_spawns[{len(animal_spawns)}] = {{\n")
        for map_id, atype, type_index, tx, ty in animal_spawns:
            source.write(f"    {{{map_id}, {type_index}, {tx}, {ty}}},\n")
        source.write("};\n\n")

        source.write(f"const GBARecipeDef gba_recipes[{len(all_recipes)}] = {{\n")
        for rid, rdef in all_recipes:
            ingredients = rdef.get("ingredients", [])
            out_id = rdef.get("output", rid)
            out_qty = int(rdef.get("output_qty", 1))
            ing_literals = []
            for ing in ingredients[:3]:
                ing_literals.append(f"{{{c_string(ing['item_id'])}, {int(ing['qty'])}}}")
            while len(ing_literals) < 3:
                ing_literals.append("{0, 0}")
            source.write(
                f"    {{{c_string(rid)}, {c_string(out_id)}, {out_qty}, "
                f"{{{', '.join(ing_literals)}}}, {len(ingredients)}}},\n"
            )
        source.write("};\n\n")

        source.write(f"const GBAWaypointDef gba_waypoints[{len(waypoints)}] = {{\n")
        for wp_id, wp_map, wp_x, wp_y in waypoints:
            source.write(f"    {{{c_string(wp_id)}, {MAP_INDEX.get(wp_map, 0)}, {wp_x}, {wp_y}}},\n")
        source.write("};\n\n")

        stage_names = ["", "", "", ""]
        stage_forms = ["", "", "", ""]
        stage_entry_maps = [0, 0, 0, 0]
        stage_quest_index = [0, 0, 0, 0]
        for stage in range(1, 4):
            stage_names[stage] = STAGE_NAMES[stage]
            stage_forms[stage] = STAGE_PLAYER_FORMS[stage]
            stage_entry_maps[stage] = MAP_INDEX[STAGE_MAPS[stage][0]]
            quest_id = next(qid for qid, stage_num in QUEST_STAGE_MAP.items() if stage_num == stage)
            stage_quest_index[stage] = next(idx for idx, quest in enumerate(quests) if quest.id == quest_id)
        map_stage = [stage_for_map(map_name) for map_name, _, _, _ in MAP_ORDER]

        source.write("const char *gba_stage_names[4] = {\n")
        for value in stage_names:
            source.write(f"    {c_string(value)},\n")
        source.write("};\n\n")

        source.write("const char *gba_stage_forms[4] = {\n")
        for value in stage_forms:
            source.write(f"    {c_string(value)},\n")
        source.write("};\n\n")

        source.write("const u8 gba_stage_entry_maps[4] = {\n")
        for value in stage_entry_maps:
            source.write(f"    {value},\n")
        source.write("};\n\n")

        source.write("const u8 gba_stage_hp_bonus[4] = {\n")
        for stage in range(4):
            source.write(f"    {stage_hp_bonus(stage) if stage else 0},\n")
        source.write("};\n\n")

        source.write("const u8 gba_stage_quest_index[4] = {\n")
        for value in stage_quest_index:
            source.write(f"    {value},\n")
        source.write("};\n\n")

        source.write("const u8 gba_map_stage[MAP_COUNT] = {\n")
        for value in map_stage:
            source.write(f"    {value},\n")
        source.write("};\n")


def main() -> None:
    GEN_DIR.mkdir(parents=True, exist_ok=True)
    emit_map_tables()
    emit_content_tables()
    print(f"Wrote {GEN_DIR / 'maps.h'}")
    print(f"Wrote {GEN_DIR / 'maps.c'}")
    print(f"Wrote {GEN_DIR / 'content.h'}")
    print(f"Wrote {GEN_DIR / 'content.c'}")


if __name__ == "__main__":
    main()
