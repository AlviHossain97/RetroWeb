#include "core/wave_manager.h"

void WaveManager::init() {
    cfg::generate_waves(wave_defs);
    current_wave = 0;
    phase = GamePhase::Build;
    queue_size = 0;
    queue_head = 0;
    spawn_timer = 0.0f;
}

bool WaveManager::start_wave(int spawn_count) {
    if (phase != GamePhase::Build || current_wave >= cfg::TOTAL_WAVES) {
        return false;
    }

    phase = GamePhase::Wave;
    queue_size = 0;
    queue_head = 0;
    spawn_timer = 0.0f;

    const auto& wave = wave_defs[current_wave];
    for (int entry_idx = 0; entry_idx < wave.entry_count; ++entry_idx) {
        const auto& entry = wave.entries[entry_idx];
        for (int i = 0; i < entry.count && queue_size < 256; ++i) {
            const float delay = (i == 0) ? 0.0f : entry.spawn_delay;
            const int path_choice = spawn_count > 1 ? (queue_size % spawn_count) : 0;
            spawn_queue[queue_size++] = {entry.type, path_choice, delay};
        }
    }

    return true;
}

void WaveManager::update(float dt, EnemyPool& enemies, const Path paths[], int path_count) {
    if (phase != GamePhase::Wave) {
        return;
    }

    spawn_timer -= dt;
    while (queue_head < queue_size && spawn_timer <= 0.0f) {
        const SpawnEntry entry = spawn_queue[queue_head];
        const int safe_path_idx = (path_count > 0) ? (entry.path_idx % path_count) : 0;
        Enemy* spawned = enemies.spawn(entry.type, &paths[safe_path_idx]);
        if (spawned == nullptr) {
            spawn_timer = 0.0f;
            break;
        }
        ++queue_head;
        if (queue_head < queue_size) {
            spawn_timer += spawn_queue[queue_head].delay;
        }
    }
}

bool WaveManager::is_wave_complete(const EnemyPool& enemies) const {
    return phase == GamePhase::Wave && queue_head >= queue_size && enemies.active_count() == 0;
}

int WaveManager::enemies_remaining(const EnemyPool& enemies) const {
    return (queue_size - queue_head) + enemies.active_count();
}

bool WaveManager::all_waves_done() const {
    return current_wave >= cfg::TOTAL_WAVES;
}
