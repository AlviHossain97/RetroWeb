#pragma once

#include "core/config.h"
#include "core/enemy.h"
#include "core/pathfinding.h"
#include "core/types.h"

struct SpawnEntry {
    EnemyType type = EnemyType::Goblin;
    int path_idx = 0;
    float delay = 0.0f;
};

struct WaveManager {
    cfg::WaveDef wave_defs[cfg::TOTAL_WAVES];
    int current_wave = 0;
    GamePhase phase = GamePhase::Build;

    SpawnEntry spawn_queue[256];
    int queue_size = 0;
    int queue_head = 0;
    float spawn_timer = 0.0f;

    void init();
    bool start_wave(int spawn_count);
    void update(float dt, EnemyPool& enemies, const Path paths[], int path_count);
    bool is_wave_complete(const EnemyPool& enemies) const;
    int enemies_remaining(const EnemyPool& enemies) const;
    bool all_waves_done() const;
};
