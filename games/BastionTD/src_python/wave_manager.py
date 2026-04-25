"""
wave_manager.py - Wave definitions, spawn queue, timing, phase control.
"""
from __future__ import annotations

from typing import TYPE_CHECKING
from settings import *
from enemy import Enemy

if TYPE_CHECKING:
    pass  # grid.Grid type hint if needed


class WaveManager:
    """Manages wave progression, enemy spawning, and build/wave phase transitions."""

    def __init__(self) -> None:
        self.waves: list = generate_waves()
        self.current_wave: int = 0          # 0-indexed
        self.phase: str = "build"           # "build" or "wave"
        self.spawn_queue: list[tuple[str, float]] = []  # [(enemy_type, delay)]
        self.active_enemies: list[Enemy] = []
        self.spawn_timer: float = 0.0

    # ------------------------------------------------------------------
    # Start wave
    # ------------------------------------------------------------------
    def start_wave(self) -> None:
        if self.current_wave >= len(self.waves):
            return
        self.phase = "wave"
        wave_def = self.waves[self.current_wave]
        self.spawn_queue = []

        # Build spawn queue: groups spawn sequentially.
        # Each group is (enemy_type, count, spawn_delay).
        # Titan always last (already guaranteed by generate_waves ordering).
        for enemy_type, count, delay in wave_def:
            for i in range(count):
                # First enemy in a group spawns immediately (0 delay), rest use spawn_delay
                entry_delay = 0.0 if i == 0 else delay
                self.spawn_queue.append((enemy_type, entry_delay))

        self.spawn_timer = 0.0

    # ------------------------------------------------------------------
    # Update -- returns list of event dicts
    # ------------------------------------------------------------------
    def update(self, dt: float, grid) -> list[dict]:
        events: list[dict] = []

        if self.phase != "wave":
            return events

        # 1. Spawn enemies from queue -----------------------------------
        if self.spawn_queue:
            self.spawn_timer -= dt
            if self.spawn_timer <= 0:
                enemy_type, delay = self.spawn_queue.pop(0)

                # Pick a path from the grid -- use first available spawn
                path = None
                if grid.paths:
                    # Use the first spawn path (or round-robin for multi-spawn)
                    spawn_keys = list(grid.paths.keys())
                    spawn_key = spawn_keys[len(self.active_enemies) % len(spawn_keys)]
                    path = grid.paths[spawn_key]

                if path:
                    enemy = Enemy(enemy_type, path, spawn_index=0)
                    self.active_enemies.append(enemy)
                    # Boss spawn event
                    if enemy_type == "titan":
                        events.append({
                            "type": "boss_spawn",
                            "enemy": enemy,
                        })

                # Set timer for next spawn
                if self.spawn_queue:
                    _, next_delay = self.spawn_queue[0]
                    self.spawn_timer = next_delay
                else:
                    self.spawn_timer = 0.0

        # 2. Update all active enemies -----------------------------------
        for enemy in self.active_enemies:
            enemy.update(dt, self.active_enemies)

        # 3. Process dead and base-reaching enemies ----------------------
        still_active: list[Enemy] = []
        for enemy in self.active_enemies:
            if enemy.reached_base:
                events.append({
                    "type": "lives_lost",
                    "amount": enemy.lives_cost,
                    "enemy_type": enemy.type,
                })
            elif not enemy.alive:
                # Enemy died (not from reaching base) -- award gold
                if enemy.death_timer <= 0:
                    events.append({
                        "type": "gold_earned",
                        "amount": enemy.gold,
                        "enemy_type": enemy.type,
                        "x": enemy.x,
                        "y": enemy.y,
                    })
                else:
                    # Still in death animation
                    still_active.append(enemy)
            else:
                still_active.append(enemy)

        self.active_enemies = still_active

        # 4. Check wave complete -----------------------------------------
        if not self.spawn_queue and not self.active_enemies:
            events.append({"type": "wave_complete", "wave": self.current_wave})
            self.current_wave += 1
            self.phase = "build"

        return events

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------
    def is_wave_active(self) -> bool:
        return self.phase == "wave"

    def enemies_remaining(self) -> int:
        return len(self.spawn_queue) + len(self.active_enemies)
