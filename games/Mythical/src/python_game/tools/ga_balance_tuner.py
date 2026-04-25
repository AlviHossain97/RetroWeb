"""Offline genetic tuner for MYTHICAL difficulty configs.

This tool never runs in-game. It mutates difficulty configuration values,
evaluates them against deterministic encounter simulations, and exports
generated config files that can be reviewed or applied manually.
"""
from __future__ import annotations

import argparse
import copy
import json
import math
import os
import random
import statistics


ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT_DIR, "data")


ENCOUNTER_TEMPLATES = [
    {"name": "slime_duo", "enemies": [("slime", 2)]},
    {"name": "bat_pair", "enemies": [("bat", 2)]},
    {"name": "skeleton_duel", "enemies": [("skeleton", 2)]},
    {"name": "golem_guard", "enemies": [("golem", 1)]},
    {"name": "mixed_pack", "enemies": [("slime", 2), ("bat", 1), ("skeleton", 1)]},
    {"name": "boss", "boss": True},
]


TARGETS = {
    "easy": {"damage": 1.8, "duration": 6.5, "win_rate": 0.95, "pressure": 0.34},
    "normal": {"damage": 3.1, "duration": 8.0, "win_rate": 0.8, "pressure": 0.55},
    "hard": {"damage": 4.9, "duration": 9.8, "win_rate": 0.62, "pressure": 0.76},
}


GENE_SPECS = {
    "player_damage_taken_mult": (0.75, 1.2),
    "player_attack_damage_mult": (0.9, 1.2),
    "map_transition_heal": (0.0, 2.0),
    "respawn_hp_ratio": (0.55, 1.0),
    "checkpoint_heal_bonus": (0.0, 3.0),
    "drop_heal_chance_bonus": (-0.08, 0.2),
    "enemy_hp_mult": (0.8, 1.25),
    "enemy_damage_mult": (0.75, 1.25),
    "enemy_speed_mult": (0.9, 1.12),
    "enemy_attack_cd_mult": (0.85, 1.15),
    "enemy_chase_mult": (0.9, 1.12),
    "boss_hp_mult": (0.85, 1.25),
    "boss_damage_mult": (0.8, 1.28),
    "boss_speed_mult": (0.9, 1.15),
    "boss_cooldown_mult": (0.8, 1.15),
    "boss_phase2_threshold": (0.45, 0.7),
    "ai_tactical_quality": (0.5, 1.35),
    "ai_pressure_scale": (0.7, 1.3),
    "ai_retreat_bias": (0.82, 1.35),
    "ai_flank_bias": (0.75, 1.25),
}


def _load_json(filename: str) -> dict:
    path = os.path.join(DATA_DIR, filename)
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def _write_json(path: str, data: dict):
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2)


def encode_mode(mode_cfg: dict) -> dict:
    return {
        "player_damage_taken_mult": mode_cfg["player_damage_taken_mult"],
        "player_attack_damage_mult": mode_cfg["player_attack_damage_mult"],
        "map_transition_heal": float(mode_cfg["map_transition_heal"]),
        "respawn_hp_ratio": mode_cfg["respawn_hp_ratio"],
        "checkpoint_heal_bonus": float(mode_cfg["checkpoint_heal_bonus"]),
        "drop_heal_chance_bonus": mode_cfg["drop_heal_chance_bonus"],
        "enemy_hp_mult": mode_cfg["enemy_stat_mults"]["hp"],
        "enemy_damage_mult": mode_cfg["enemy_stat_mults"]["damage"],
        "enemy_speed_mult": mode_cfg["enemy_stat_mults"]["speed"],
        "enemy_attack_cd_mult": mode_cfg["enemy_stat_mults"]["attack_cd"],
        "enemy_chase_mult": mode_cfg["enemy_stat_mults"]["chase_range"],
        "boss_hp_mult": mode_cfg["boss_stat_mults"]["hp"],
        "boss_damage_mult": mode_cfg["boss_stat_mults"]["damage"],
        "boss_speed_mult": mode_cfg["boss_stat_mults"]["speed"],
        "boss_cooldown_mult": mode_cfg["boss_stat_mults"]["cooldown"],
        "boss_phase2_threshold": mode_cfg["boss_stat_mults"]["phase2_threshold"],
        "ai_tactical_quality": mode_cfg["ai"]["tactical_quality"],
        "ai_pressure_scale": mode_cfg["ai"]["pressure_scale"],
        "ai_retreat_bias": mode_cfg["ai"]["retreat_bias"],
        "ai_flank_bias": mode_cfg["ai"]["flank_bias"],
    }


def decode_mode(base_mode: dict, genes: dict) -> dict:
    mode_cfg = copy.deepcopy(base_mode)
    mode_cfg["player_damage_taken_mult"] = genes["player_damage_taken_mult"]
    mode_cfg["player_attack_damage_mult"] = genes["player_attack_damage_mult"]
    mode_cfg["map_transition_heal"] = int(round(genes["map_transition_heal"]))
    mode_cfg["respawn_hp_ratio"] = genes["respawn_hp_ratio"]
    mode_cfg["checkpoint_heal_bonus"] = int(round(genes["checkpoint_heal_bonus"]))
    mode_cfg["drop_heal_chance_bonus"] = genes["drop_heal_chance_bonus"]
    mode_cfg["enemy_stat_mults"]["hp"] = genes["enemy_hp_mult"]
    mode_cfg["enemy_stat_mults"]["damage"] = genes["enemy_damage_mult"]
    mode_cfg["enemy_stat_mults"]["speed"] = genes["enemy_speed_mult"]
    mode_cfg["enemy_stat_mults"]["attack_cd"] = genes["enemy_attack_cd_mult"]
    mode_cfg["enemy_stat_mults"]["chase_range"] = genes["enemy_chase_mult"]
    mode_cfg["boss_stat_mults"]["hp"] = genes["boss_hp_mult"]
    mode_cfg["boss_stat_mults"]["damage"] = genes["boss_damage_mult"]
    mode_cfg["boss_stat_mults"]["speed"] = genes["boss_speed_mult"]
    mode_cfg["boss_stat_mults"]["cooldown"] = genes["boss_cooldown_mult"]
    mode_cfg["boss_stat_mults"]["phase2_threshold"] = genes["boss_phase2_threshold"]
    mode_cfg["ai"]["tactical_quality"] = genes["ai_tactical_quality"]
    mode_cfg["ai"]["pressure_scale"] = genes["ai_pressure_scale"]
    mode_cfg["ai"]["retreat_bias"] = genes["ai_retreat_bias"]
    mode_cfg["ai"]["flank_bias"] = genes["ai_flank_bias"]
    return mode_cfg


def clamp_genes(genes: dict) -> dict:
    clamped = {}
    for key, value in genes.items():
        low, high = GENE_SPECS[key]
        clamped[key] = max(low, min(high, value))
    return clamped


def mutate(genes: dict, rng: random.Random, rate: float = 0.28) -> dict:
    mutated = dict(genes)
    for key, (low, high) in GENE_SPECS.items():
        if rng.random() < rate:
            span = high - low
            mutated[key] += rng.gauss(0.0, span * 0.08)
    return clamp_genes(mutated)


def crossover(a: dict, b: dict, rng: random.Random) -> dict:
    child = {}
    for key in GENE_SPECS:
        if rng.random() < 0.5:
            child[key] = (a[key] + b[key]) / 2.0
        else:
            child[key] = a[key] if rng.random() < 0.5 else b[key]
    return clamp_genes(child)


def _effective_enemy_stats(enemy_base: dict, mode_cfg: dict) -> dict:
    enemy_mults = mode_cfg["enemy_stat_mults"]
    ai_cfg = mode_cfg["ai"]
    return {
        "hp": enemy_base["max_hp"] * enemy_mults["hp"],
        "damage": enemy_base["damage"] * enemy_mults["damage"],
        "speed": enemy_base["speed"] * enemy_mults["speed"],
        "attack_cd": enemy_base["attack_cd"] * enemy_mults["attack_cd"],
        "chase": enemy_base["chase_range"] * enemy_mults["chase_range"],
        "pressure": enemy_base["ai"]["pressure_bias"] * ai_cfg["pressure_scale"],
        "flank": enemy_base["ai"]["flank_bias"] * ai_cfg["flank_bias"],
        "tactics": enemy_base["ai"]["tactical_enabled"],
        "retreat": enemy_base["ai"]["retreat_hp_ratio"] * ai_cfg["retreat_bias"],
        "quality": ai_cfg["tactical_quality"],
        "aggro": enemy_base["ai"]["aggro_confidence"] * mode_cfg["enemy_stat_mults"]["aggro_confidence"],
    }


def _effective_boss_stats(boss_base: dict, mode_cfg: dict) -> dict:
    boss_mults = mode_cfg["boss_stat_mults"]
    ai_cfg = mode_cfg["ai"]
    return {
        "hp": boss_base["max_hp"] * boss_mults["hp"],
        "damage": boss_base["damage"] * boss_mults["damage"],
        "speed": boss_base["speed"] * boss_mults["speed"],
        "cooldown": boss_base["attack_cooldown"] * boss_mults["cooldown"],
        "pressure": boss_base["pressure_bias"] * boss_mults["pressure"] * ai_cfg["pressure_scale"],
        "phase2": boss_base["phase2_threshold"] * boss_mults["phase2_threshold"],
        "search": boss_base["search_radius"] * ai_cfg["tactical_quality"],
        "range1": boss_base["preferred_range_phase1"],
        "range2": boss_base["preferred_range_phase2"],
    }


def simulate_template(template: dict, mode_cfg: dict, enemy_data: dict, boss_data: dict, seed: int) -> dict:
    rng = random.Random(seed)
    player_hp = 6.0 + mode_cfg["checkpoint_heal_bonus"] * 0.2
    player_dps = 2.2 * mode_cfg["player_attack_damage_mult"]
    healing_support = mode_cfg["drop_heal_chance_bonus"] * 2.1 + mode_cfg["map_transition_heal"] * 0.3
    reaction_noise = 0.92 + rng.random() * 0.16

    if template.get("boss"):
        boss = _effective_boss_stats(boss_data["dark_golem"]["base"], mode_cfg)
        duration = (boss["hp"] / max(0.6, player_dps * 0.78)) * (1.1 + boss["pressure"] * 0.08) * reaction_noise
        hit_rate = (boss["damage"] / max(0.3, boss["cooldown"])) * (0.45 + boss["pressure"] * 0.12)
        damage_taken = duration * hit_rate * mode_cfg["player_damage_taken_mult"] * 0.22
        pressure = min(1.0, 0.45 + boss["pressure"] * 0.18 + (1.0 - boss["cooldown"]) * 0.22)
    else:
        total_hp = 0.0
        aggregate_pressure = 0.0
        aggregate_dps = 0.0
        for enemy_type, count in template["enemies"]:
            stats = _effective_enemy_stats(enemy_data[enemy_type]["base"], mode_cfg)
            total_hp += stats["hp"] * count
            tactical_tax = 0.08 * stats["quality"] if stats["tactics"] else 0.0
            aggregate_pressure += count * (0.24 + stats["pressure"] * 0.12 + stats["flank"] * 0.08 + tactical_tax)
            aggregate_dps += count * (stats["damage"] / max(0.3, stats["attack_cd"])) * (0.75 + stats["speed"] * 0.08 + stats["aggro"] * 0.05)
        player_accuracy = max(0.45, 0.88 - aggregate_pressure * 0.08) * reaction_noise
        duration = total_hp / max(0.75, player_dps * player_accuracy)
        damage_taken = duration * aggregate_dps * mode_cfg["player_damage_taken_mult"] * 0.19
        pressure = min(1.0, aggregate_pressure / max(1.0, len(template["enemies"]) * 1.8))

    net_damage = max(0.0, damage_taken - healing_support)
    survival_ratio = player_hp / max(player_hp, net_damage)
    survival_time = duration * min(1.0, survival_ratio)
    win = 1.0 if net_damage < player_hp else 0.0
    return {
        "survival_time": survival_time,
        "damage_taken": net_damage,
        "duration": duration,
        "win": win,
        "pressure": pressure,
        "enemy_hit_frequency": damage_taken / max(0.5, duration),
    }


def evaluate_mode(mode_name: str, genes: dict, base_mode: dict, enemy_data: dict, boss_data: dict) -> tuple[float, dict]:
    mode_cfg = decode_mode(base_mode, genes)
    samples = []
    for template in ENCOUNTER_TEMPLATES:
        for seed in range(6):
            metric = simulate_template(template, mode_cfg, enemy_data, boss_data, seed + 17)
            samples.append(metric)

    aggregate = {
        "damage": statistics.mean(sample["damage_taken"] for sample in samples),
        "duration": statistics.mean(sample["duration"] for sample in samples),
        "win_rate": statistics.mean(sample["win"] for sample in samples),
        "pressure": statistics.mean(sample["pressure"] for sample in samples),
        "survival_time": statistics.mean(sample["survival_time"] for sample in samples),
        "hit_frequency": statistics.mean(sample["enemy_hit_frequency"] for sample in samples),
        "variance": statistics.pvariance(sample["damage_taken"] for sample in samples),
    }

    target = TARGETS[mode_name]
    penalty = 0.0
    penalty += abs(aggregate["damage"] - target["damage"]) * 1.5
    penalty += abs(aggregate["duration"] - target["duration"]) * 0.45
    penalty += abs(aggregate["win_rate"] - target["win_rate"]) * 8.0
    penalty += abs(aggregate["pressure"] - target["pressure"]) * 4.2
    penalty += aggregate["variance"] * 0.35
    if mode_name == "easy" and aggregate["win_rate"] < 0.88:
        penalty += 12.0
    if mode_name == "hard" and aggregate["pressure"] < 0.65:
        penalty += 5.0
    return -penalty, aggregate


def tune_mode(mode_name: str, base_mode: dict, enemy_data: dict, boss_data: dict, generations: int, population: int, seed: int):
    rng = random.Random(seed)
    base_genes = encode_mode(base_mode)
    population_genes = [base_genes]
    while len(population_genes) < population:
        population_genes.append(mutate(base_genes, rng, rate=0.75))

    best_score = -1_000_000.0
    best_genes = base_genes
    best_metrics = {}

    for _ in range(generations):
        scored = []
        for genes in population_genes:
            score, metrics = evaluate_mode(mode_name, genes, base_mode, enemy_data, boss_data)
            scored.append((score, genes, metrics))
            if score > best_score:
                best_score = score
                best_genes = dict(genes)
                best_metrics = dict(metrics)
        scored.sort(key=lambda item: item[0], reverse=True)
        elites = [dict(item[1]) for item in scored[: max(2, population // 4)]]
        next_population = elites[:]
        while len(next_population) < population:
            parent_a = rng.choice(elites)
            parent_b = rng.choice(elites)
            child = crossover(parent_a, parent_b, rng)
            child = mutate(child, rng, rate=0.4)
            next_population.append(child)
        population_genes = next_population

    return decode_mode(base_mode, best_genes), best_metrics, best_score


def export_bundle(tuned_difficulties: dict, apply_live: bool = False):
    difficulty_data = _load_json("difficulty_configs.json")
    enemy_data = _load_json("enemy_ai_configs.json")
    boss_data = _load_json("boss_ai_configs.json")
    for mode_name, mode_cfg in tuned_difficulties.items():
        difficulty_data["modes"][mode_name] = mode_cfg

    output_dir = DATA_DIR
    _write_json(os.path.join(output_dir, "generated_difficulty_configs.json"), difficulty_data)
    _write_json(os.path.join(output_dir, "generated_enemy_ai_configs.json"), enemy_data)
    _write_json(os.path.join(output_dir, "generated_boss_ai_configs.json"), boss_data)

    if apply_live:
        _write_json(os.path.join(output_dir, "difficulty_configs.json"), difficulty_data)


def main():
    parser = argparse.ArgumentParser(description="Offline GA tuner for MYTHICAL difficulty configs.")
    parser.add_argument("--generations", type=int, default=10, help="Number of GA generations per difficulty.")
    parser.add_argument("--population", type=int, default=18, help="Population size per difficulty.")
    parser.add_argument("--apply", action="store_true", help="Overwrite live difficulty_configs.json with tuned output.")
    args = parser.parse_args()

    difficulty_data = _load_json("difficulty_configs.json")
    enemy_data = _load_json("enemy_ai_configs.json")
    boss_data = _load_json("boss_ai_configs.json")

    tuned = {}
    for index, mode_name in enumerate(("easy", "normal", "hard")):
        tuned_mode, metrics, score = tune_mode(
            mode_name,
            difficulty_data["modes"][mode_name],
            enemy_data,
            boss_data,
            generations=args.generations,
            population=args.population,
            seed=1337 + index * 101,
        )
        tuned[mode_name] = tuned_mode
        print(f"{mode_name.upper()} score={score:.3f} damage={metrics['damage']:.2f} duration={metrics['duration']:.2f} win={metrics['win_rate']:.2f} pressure={metrics['pressure']:.2f}")

    export_bundle(tuned, apply_live=args.apply)
    print("Exported generated config bundle to data/generated_*.json")
    if args.apply:
        print("Applied tuned difficulty configs to data/difficulty_configs.json")


if __name__ == "__main__":
    main()
