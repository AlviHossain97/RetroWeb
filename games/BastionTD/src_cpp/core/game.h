#pragma once

#include "core/economy.h"
#include "core/effects.h"
#include "core/enemy.h"
#include "core/grid.h"
#include "core/map_generator.h"
#include "core/pathfinding.h"
#include "core/projectile.h"
#include "core/tower.h"
#include "core/types.h"
#include "core/wave_manager.h"

#include <cstdint>

enum class GameEventType : uint8_t {
    EnemyKilled = 0,
    EnemyLeaked,
    TowerFired,
    WaveComplete,
    WaveStart,
    TitanSpawned,
    BaseHit,
    TowerPlaced,
    TowerSold,
    TowerUpgraded,
    FleetUpgraded,
    Victory,
    Defeat,
};

struct GameEvent {
    GameEventType type = GameEventType::WaveStart;
    Vec2 pos = {0.0f, 0.0f};
    int data = 0;
};

struct GameSim {
    Grid grid;
    Path paths[cfg::MAX_SPAWNS];
    int path_count = 0;
    EnemyPool enemies;
    TowerArray towers;
    ProjectilePool projectiles;
    WaveManager wave_mgr;
    Economy economy;
    Effects effects;
    SpeedMode speed_mode = SpeedMode::Normal;

    GameEvent events[64];
    int event_count = 0;

    bool fleet_available = false;
    TowerType fleet_selected_type = TowerType::Arrow;
    int fleet_target_level = 2;

    int titan_idx = -1;
    bool titan_announced = false;

    void new_game(uint32_t seed = 0);
    void tick(float dt);
    void emit_event(GameEventType type, Vec2 pos = {}, int data = 0);

    bool try_place_tower(TowerType type, int tx, int ty);
    bool try_upgrade_tower(int tx, int ty);
    int try_sell_tower(int tx, int ty);
    bool try_fleet_upgrade();
    bool try_fleet_upgrade_all();
    int  fleet_upgrade_all_cost() const;
    void start_next_wave();
    void cycle_speed();

    float speed_multiplier() const;
    int speed_steps() const;
};
