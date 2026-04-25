"""Load and merge external AI and difficulty configuration files."""
from __future__ import annotations

import copy
import json
import os
from functools import lru_cache


ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT_DIR, "data")


def _read_json(filename: str) -> dict:
    path = os.path.join(DATA_DIR, filename)
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def _deep_merge(base: dict, override: dict) -> dict:
    merged = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = copy.deepcopy(value)
    return merged


@lru_cache(maxsize=1)
def load_difficulty_data() -> dict:
    return _read_json("difficulty_configs.json")


@lru_cache(maxsize=1)
def load_enemy_ai_data() -> dict:
    return _read_json("enemy_ai_configs.json")


@lru_cache(maxsize=1)
def load_boss_ai_data() -> dict:
    return _read_json("boss_ai_configs.json")


@lru_cache(maxsize=1)
def load_stage_data() -> dict:
    return _read_json("stage_configs.json")


def clear_config_cache():
    load_difficulty_data.cache_clear()
    load_enemy_ai_data.cache_clear()
    load_boss_ai_data.cache_clear()
    load_stage_data.cache_clear()


def get_default_difficulty() -> str:
    data = load_difficulty_data()
    return data.get("default", "normal")


def get_difficulty_modes() -> list[str]:
    data = load_difficulty_data()
    return list(data.get("modes", {}).keys())


def normalize_difficulty(mode: str | None) -> str:
    data = load_difficulty_data()
    modes = data.get("modes", {})
    if mode in modes:
        return str(mode)
    return get_default_difficulty()


def get_difficulty_config(mode: str | None) -> dict:
    data = load_difficulty_data()
    normalized = normalize_difficulty(mode)
    return copy.deepcopy(data["modes"][normalized])


def describe_difficulty(mode: str | None) -> str:
    config = get_difficulty_config(mode)
    return f"{config.get('label', normalize_difficulty(mode)).upper()}: {config.get('description', '')}"


def get_enemy_config(enemy_type: str, difficulty_mode: str | None) -> dict:
    data = load_enemy_ai_data()
    if enemy_type not in data:
        raise KeyError(f"Unknown enemy type: {enemy_type}")
    entry = data[enemy_type]
    merged = copy.deepcopy(entry["base"])
    difficulty_block = entry.get("difficulty", {}).get(normalize_difficulty(difficulty_mode), {})
    if difficulty_block:
        merged = _deep_merge(merged, difficulty_block)
    return merged


def get_boss_config(boss_id: str, difficulty_mode: str | None) -> dict:
    data = load_boss_ai_data()
    if boss_id not in data:
        raise KeyError(f"Unknown boss id: {boss_id}")
    entry = data[boss_id]
    merged = copy.deepcopy(entry["base"])
    difficulty_block = entry.get("difficulty", {}).get(normalize_difficulty(difficulty_mode), {})
    if difficulty_block:
        merged = _deep_merge(merged, difficulty_block)
    return merged


def get_stage_difficulty_override(stage: int | str, difficulty_mode: str | None) -> dict:
    data = load_stage_data()
    stage_key = str(stage)
    difficulty_key = normalize_difficulty(difficulty_mode)
    return copy.deepcopy(
        data.get("stage_difficulty_matrix", {}).get(stage_key, {}).get(difficulty_key, {})
    )


def get_stage_player_hp_bonus(stage: int | str, fallback: int = 0) -> int:
    data = load_stage_data()
    stage_key = str(stage)
    value = data.get("stage_player_hp_bonus", {}).get(stage_key)
    if value is None:
        return int(fallback)
    return int(value)


def get_stage_boss_xp(stage: int | str, boss_id: str, default: int = 100) -> int:
    data = load_stage_data()
    stage_key = str(stage)
    rewards = data.get("stage_xp_rewards", {}).get(stage_key, {})
    return int(rewards.get(boss_id, default))


def get_stage_boss_loot(boss_id: str) -> list[dict]:
    data = load_stage_data()
    return copy.deepcopy(data.get("boss_loot", {}).get(boss_id, []))
