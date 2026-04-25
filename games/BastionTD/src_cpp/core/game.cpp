#include "core/game.h"

#include "core/math_utils.h"

#ifdef BASTION_GBA
namespace {

MapData gba_map_scratch __attribute__((section(".sbss")));

}
#endif

void GameSim::new_game(uint32_t seed) {
#ifdef BASTION_GBA
    generate_map(seed, gba_map_scratch);
    const MapData& map = gba_map_scratch;
#else
    const MapData map = generate_map(seed);
#endif
    grid = map.grid;
    for (int i = 0; i < map.path_count; ++i) {
        paths[i] = map.paths[i];
    }
    path_count = map.path_count;

    enemies.init();
    towers.init();
    projectiles.init();
    wave_mgr.init();
    economy.reset();
    effects.init();
    speed_mode = SpeedMode::Normal;
    event_count = 0;
    fleet_available = false;
    fleet_selected_type = TowerType::Arrow;
    fleet_target_level = 2;
    titan_idx = -1;
    titan_announced = false;
}

void GameSim::emit_event(GameEventType type, Vec2 pos, int data) {
    if (event_count < 64) {
        events[event_count++] = {type, pos, data};
    }
}

float GameSim::speed_multiplier() const {
    switch (speed_mode) {
    case SpeedMode::Fast2x:
        return 2.0f;
    case SpeedMode::Fast3x:
        return 3.0f;
    default:
        return 1.0f;
    }
}

int GameSim::speed_steps() const {
    switch (speed_mode) {
    case SpeedMode::Fast2x:
        return 2;
    case SpeedMode::Fast3x:
        return 3;
    default:
        return 1;
    }
}

void GameSim::cycle_speed() {
    switch (speed_mode) {
    case SpeedMode::Normal:
        speed_mode = SpeedMode::Fast2x;
        break;
    case SpeedMode::Fast2x:
        speed_mode = SpeedMode::Fast3x;
        break;
    case SpeedMode::Fast3x:
        speed_mode = SpeedMode::Normal;
        break;
    }
}

void GameSim::tick(float dt) {
    event_count = 0;

    if (wave_mgr.phase != GamePhase::Wave) {
        return;
    }

    wave_mgr.update(dt, enemies, paths, path_count);

    enemies.begin_tick();
    enemies.tick_status_all(dt);
    enemies.heal_pass();
    enemies.move_all(dt);

    titan_idx = -1;
    for (int i = 0; i < cfg::MAX_ENEMIES; ++i) {
        auto& e = enemies.enemies[i];
        if (e.reached_base) {
            economy.lose_lives(e.lives_cost);
            emit_event(GameEventType::EnemyLeaked, e.pos, e.lives_cost);
            emit_event(GameEventType::BaseHit, grid.base_pos, e.lives_cost);
            effects.shake.trigger(0.3f, 2.0f);
            e.reached_base = false;
        }

        if (e.active && !e.dying && e.type == EnemyType::Titan) {
            titan_idx = i;
        }
    }

    if (titan_idx >= 0 && !titan_announced) {
        titan_announced = true;
        emit_event(GameEventType::TitanSpawned, enemies.enemies[titan_idx].pos);
        effects.shake.trigger(0.5f, 3.0f);
    }

    if (economy.is_game_over()) {
        wave_mgr.phase = GamePhase::DefeatPending;
        emit_event(GameEventType::Defeat);
        return;
    }

    for (auto& t : towers.towers) {
        if (!t.active) {
            continue;
        }
        t.update(dt, enemies);
        if (t.ready_to_fire()) {
            const Vec2 start = {static_cast<float>(t.tile_x), static_cast<float>(t.tile_y)};
            if (projectiles.spawn(start, t.target_enemy_idx, t.damage,
                                  t.type, t.color,
                                  t.splash_radius, t.slow_factor, t.slow_duration,
                                  t.chain_count, t.chain_range,
                                  t.dot_damage, t.dot_duration,
                                  enemies) != nullptr) {
                t.cooldown_timer = t.cooldown;
                t.firing_anim = true;
                t.firing_anim_timer = 0.1f;
                emit_event(GameEventType::TowerFired, start);
            }
        }
    }

    projectiles.update_all(dt, enemies);

    for (auto& e : enemies.enemies) {
        if (e.dying && !e.reward_given) {
            economy.earn(e.gold_value);
            emit_event(GameEventType::EnemyKilled, e.pos, e.gold_value);
            effects.emit_burst(e.pos, cfg::ENEMY_DEFS[static_cast<int>(e.type)].color, 6);
            effects.add_dmg_number(e.pos, static_cast<float>(e.gold_value), cfg::colors::GOLD);
            e.reward_given = true;
        }
    }

    if (wave_mgr.is_wave_complete(enemies)) {
        const int bonus = economy.had_leak_this_wave ? 0 : cfg::WAVE_CLEAR_BONUS;
        economy.wave_clear_bonus();
        emit_event(GameEventType::WaveComplete, {}, bonus);

        wave_mgr.phase = GamePhase::Build;
        ++wave_mgr.current_wave;
        speed_mode = SpeedMode::Normal;
        titan_idx = -1;
        titan_announced = false;

        if (wave_mgr.all_waves_done()) {
            emit_event(GameEventType::Victory);
        } else {
            const int waves_done = wave_mgr.current_wave;
            fleet_available = cfg::fleet_upgrade_unlocked(waves_done);
            fleet_target_level = cfg::fleet_upgrade_max_level(waves_done);
        }
    }
}

bool GameSim::try_place_tower(TowerType type, int tx, int ty) {
    if (wave_mgr.phase != GamePhase::Build || !grid.is_buildable(tx, ty)) {
        return false;
    }
    const int cost = cfg::TOWER_DEFS[static_cast<int>(type)].cost;
    if (!economy.can_afford(cost)) {
        return false;
    }
    if (towers.place(type, tx, ty) == nullptr) {
        return false;
    }
    economy.spend(cost);
    grid.set(tx, ty, Terrain::Tower);
    emit_event(GameEventType::TowerPlaced, {static_cast<float>(tx), static_cast<float>(ty)}, cost);
    return true;
}

bool GameSim::try_upgrade_tower(int tx, int ty) {
    if (wave_mgr.phase != GamePhase::Build) {
        return false;
    }
    Tower* tower = towers.get_at(tx, ty);
    if (tower == nullptr) {
        return false;
    }
    const int cost = tower->upgrade_cost();
    if (cost < 0 || !economy.can_afford(cost)) {
        return false;
    }
    economy.spend(cost);
    tower->upgrade();
    emit_event(GameEventType::TowerUpgraded, {static_cast<float>(tx), static_cast<float>(ty)}, cost);
    return true;
}

int GameSim::try_sell_tower(int tx, int ty) {
    if (wave_mgr.phase != GamePhase::Build) {
        return 0;
    }
    Tower* tower = towers.get_at(tx, ty);
    if (tower == nullptr) {
        return 0;
    }
    const int value = tower->sell_value();
    economy.earn(value);
    grid.set(tx, ty, Terrain::Empty);
    towers.remove(tx, ty);
    emit_event(GameEventType::TowerSold, {static_cast<float>(tx), static_cast<float>(ty)}, value);
    return value;
}

bool GameSim::try_fleet_upgrade() {
    if (wave_mgr.phase != GamePhase::Build || !fleet_available) {
        return false;
    }

    int missing_cost = 0;
    int affected = 0;
    for (const auto& t : towers.towers) {
        if (t.active && t.type == fleet_selected_type && t.level < fleet_target_level) {
            missing_cost += t.missing_upgrade_cost_to_level(fleet_target_level);
            ++affected;
        }
    }
    if (affected == 0 || missing_cost == 0) {
        return false;
    }

    const int total_cost = Economy::fleet_upgrade_cost(1, missing_cost);
    if (!economy.can_afford(total_cost)) {
        return false;
    }

    economy.spend(total_cost);
    towers.upgrade_all_type(fleet_selected_type, fleet_target_level);
    emit_event(GameEventType::FleetUpgraded, {}, total_cost);
    return true;
}

int GameSim::fleet_upgrade_all_cost() const {
    if (wave_mgr.phase != GamePhase::Build || !fleet_available) {
        return 0;
    }
    int missing_cost = 0;
    for (const auto& t : towers.towers) {
        if (t.active && t.level < fleet_target_level) {
            missing_cost += t.missing_upgrade_cost_to_level(fleet_target_level);
        }
    }
    if (missing_cost == 0) {
        return 0;
    }
    return Economy::fleet_upgrade_cost(1, missing_cost);
}

bool GameSim::try_fleet_upgrade_all() {
    if (wave_mgr.phase != GamePhase::Build || !fleet_available) {
        return false;
    }

    const int total_cost = fleet_upgrade_all_cost();
    if (total_cost == 0) {
        return false;
    }
    if (!economy.can_afford(total_cost)) {
        return false;
    }

    economy.spend(total_cost);
    for (int i = 0; i < static_cast<int>(TowerType::COUNT); ++i) {
        towers.upgrade_all_type(static_cast<TowerType>(i), fleet_target_level);
    }
    emit_event(GameEventType::FleetUpgraded, {}, total_cost);
    return true;
}

void GameSim::start_next_wave() {
    if (wave_mgr.start_wave(path_count)) {
        economy.had_leak_this_wave = false;
        titan_announced = false;
        emit_event(GameEventType::WaveStart, {}, wave_mgr.current_wave + 1);
    }
}
