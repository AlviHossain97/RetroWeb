#pragma once

#include "core/types.h"

#include <cstdint>

// ----------------------------------------------------------------------------
// Audio compile-time gate
// ----------------------------------------------------------------------------
// The shipped Bastion TD build is silent. Audio infrastructure (IAudio
// interface, SDL2Audio + GbaAudio implementations, SfxId / BgmId enums,
// app.audio->play_sfx() / play_bgm() call sites) remains in the source as
// documented engineering work, but the actual playback bodies are gated
// behind ENABLE_AUDIO which is undefined by default. To re-enable audio
// (post-submission, with properly-attributed assets), uncomment the
// definition below, drop WAV files into gba_project/audio/ and assets/audio/,
// and rebuild.
//
// #define ENABLE_AUDIO

namespace cfg {

constexpr int TILE_SIZE = 8;
constexpr int GRID_W = 30;
constexpr int GRID_H = 12;
constexpr int HUD_ROWS = 2;
constexpr int TRAY_ROWS = 2;
constexpr int TOTAL_ROWS = HUD_ROWS + GRID_H + TRAY_ROWS;
constexpr int SCREEN_W = TILE_SIZE * GRID_W;
constexpr int SCREEN_H = TILE_SIZE * TOTAL_ROWS;
constexpr int WINDOW_SCALE = 4;
constexpr int GRID_OFFSET_Y = HUD_ROWS * TILE_SIZE;

constexpr float SIM_DT = 1.0f / 60.0f;
constexpr float MAX_DT = 0.1f;
constexpr int TARGET_FPS = 60;

constexpr int START_GOLD = 200;
constexpr int START_LIVES = 20;
constexpr int WAVE_CLEAR_BONUS = 25;
constexpr int TOTAL_WAVES = 20;
constexpr float FLEET_UPGRADE_PREMIUM = 1.10f;

constexpr float PROJECTILE_SPEED = 12.0f;
constexpr float PROJECTILE_HIT_DIST = 0.3f;

struct TowerDef {
    const char* name;
    int cost;
    float range;
    float damage;
    float cooldown;
    Color color;
    float splash_radius;
    float slow_factor;
    float slow_duration;
    int chain_count;
    float chain_range;
    float dot_damage;
    float dot_duration;

    struct Upgrade {
        int cost;
        float damage;
        float range;
        float splash_radius;
        float slow_factor;
        int chain_count;
        float dot_damage;
        float dot_duration;
    };

    Upgrade upgrades[2];
    SpriteId char_sprite;
};

constexpr TowerDef TOWER_DEFS[static_cast<int>(TowerType::COUNT)] = {
    {"Arrow", 50, 3.5f, 1.0f, 0.6f, {160, 130, 60, 255}, 0.0f, 0.0f, 0.0f, 0, 0.0f, 0.0f, 0.0f,
        {{30, 2.0f, 4.0f, 0.0f, 0.0f, 0, 0.0f, 0.0f}, {50, 3.0f, 4.5f, 0.0f, 0.0f, 0, 0.0f, 0.0f}},
        SpriteId::Char2},
    {"Cannon", 100, 2.5f, 3.0f, 1.5f, {120, 80, 60, 255}, 1.2f, 0.0f, 0.0f, 0, 0.0f, 0.0f, 0.0f,
        {{60, 5.0f, 3.0f, 1.2f, 0.0f, 0, 0.0f, 0.0f}, {90, 8.0f, 3.5f, 1.5f, 0.0f, 0, 0.0f, 0.0f}},
        SpriteId::Char3},
    {"Ice", 75, 3.0f, 0.5f, 0.8f, {100, 180, 220, 255}, 0.0f, 0.4f, 2.0f, 0, 0.0f, 0.0f, 0.0f,
        {{45, 1.0f, 3.0f, 0.0f, 0.3f, 0, 0.0f, 0.0f}, {70, 1.5f, 3.5f, 0.0f, 0.2f, 0, 0.0f, 0.0f}},
        SpriteId::Char2},
    {"Lightning", 150, 4.0f, 2.0f, 1.0f, {200, 200, 60, 255}, 0.0f, 0.0f, 0.0f, 2, 1.5f, 0.0f, 0.0f,
        {{90, 3.0f, 4.0f, 0.0f, 0.0f, 3, 0.0f, 0.0f}, {130, 4.0f, 4.5f, 0.0f, 0.0f, 4, 0.0f, 0.0f}},
        SpriteId::Char4},
    {"Flame", 125, 2.0f, 1.0f, 0.2f, {220, 100, 40, 255}, 0.0f, 0.0f, 0.0f, 0, 0.0f, 0.5f, 2.0f,
        {{75, 1.5f, 2.0f, 0.0f, 0.0f, 0, 1.0f, 2.0f}, {110, 2.0f, 2.5f, 0.0f, 0.0f, 0, 1.5f, 3.0f}},
        SpriteId::Char3},
};

struct EnemyDef {
    const char* name;
    float hp;
    float speed;
    int armor;
    int gold;
    Color color;
    float size;
    int lives_cost;
    float heal_rate;
    float heal_range;
    SpriteId sprite;
    float sprite_scale;
};

constexpr EnemyDef ENEMY_DEFS[static_cast<int>(EnemyType::COUNT)] = {
    {"Goblin", 3.0f, 2.0f, 0, 5, {60, 160, 60, 255}, 0.5f, 1, 0.0f, 0.0f, SpriteId::Char0, 1.0f},
    {"Wolf", 2.0f, 3.5f, 0, 8, {140, 120, 100, 255}, 0.5f, 1, 0.0f, 0.0f, SpriteId::Char1, 1.0f},
    {"Knight", 8.0f, 1.2f, 2, 15, {180, 180, 200, 255}, 0.7f, 1, 0.0f, 0.0f, SpriteId::Char2, 1.0f},
    {"Healer", 4.0f, 2.0f, 0, 12, {60, 200, 60, 255}, 0.5f, 1, 1.0f, 2.0f, SpriteId::Char3, 1.0f},
    {"Swarm", 1.0f, 3.0f, 0, 2, {180, 180, 50, 255}, 0.35f, 1, 0.0f, 0.0f, SpriteId::Char1, 0.7f},
    {"Titan", 50.0f, 0.8f, 3, 100, {160, 80, 80, 255}, 1.0f, 5, 0.0f, 0.0f, SpriteId::Char4, 2.0f},
};

struct WaveEntry {
    EnemyType type;
    int count;
    float spawn_delay;
};

constexpr int MAX_WAVE_ENTRIES = 6;

struct WaveDef {
    WaveEntry entries[MAX_WAVE_ENTRIES];
    int entry_count;
    bool has_titan;
};

inline void generate_waves(WaveDef waves[TOTAL_WAVES]) {
    for (int w = 1; w <= TOTAL_WAVES; ++w) {
        WaveDef& wd = waves[w - 1];
        wd.entry_count = 0;
        wd.has_titan = false;
        auto add = [&](EnemyType t, int count, float delay) {
            if (wd.entry_count < MAX_WAVE_ENTRIES) {
                wd.entries[wd.entry_count++] = {t, count, delay};
            }
        };

        if (w <= 3) {
            add(EnemyType::Goblin, 4 + w * 2, 0.8f);
        } else if (w <= 6) {
            add(EnemyType::Goblin, 6 + w, 0.7f);
            add(EnemyType::Wolf, w - 2, 0.6f);
        } else if (w <= 10) {
            add(EnemyType::Wolf, 4 + w - 6, 0.6f);
            add(EnemyType::Knight, w - 6, 1.2f);
            if (w >= 9) {
                add(EnemyType::Healer, 1, 1.5f);
            }
        } else if (w <= 15) {
            add(EnemyType::Knight, w - 8, 1.0f);
            add(EnemyType::Healer, (w - 9) / 2 + 1, 1.3f);
            add(EnemyType::Swarm, w * 2, 0.3f);
        } else {
            add(EnemyType::Knight, w - 10, 0.9f);
            add(EnemyType::Wolf, w - 12, 0.5f);
            add(EnemyType::Healer, 2, 1.2f);
            add(EnemyType::Swarm, w * 3, 0.25f);
        }

        if (w == 5 || w == 10 || w == 15) {
            add(EnemyType::Titan, 1, 0.0f);
            wd.has_titan = true;
        }
        if (w == 20) {
            add(EnemyType::Titan, 2, 0.0f);
            wd.has_titan = true;
        }
    }
}

constexpr bool is_boss_wave(int wave_num) {
    return wave_num == 5 || wave_num == 10 || wave_num == 15 || wave_num == 20;
}

constexpr bool fleet_upgrade_unlocked(int waves_completed) {
    return waves_completed >= 5;
}

constexpr int fleet_upgrade_max_level(int waves_completed) {
    if (waves_completed >= 10) {
        return 3;
    }
    if (waves_completed >= 5) {
        return 2;
    }
    return 1;
}

constexpr int MAX_ENEMIES = 64;
constexpr int MAX_TOWERS = 32;
constexpr int MAX_PROJECTILES = 64;
constexpr int MAX_PARTICLES = 128;
constexpr int MAX_DMG_NUMBERS = 32;
constexpr int MAX_PATH_LEN = 256;
constexpr int MAX_SPAWNS = 2;
constexpr int MAX_DOT_STACKS = 3;

namespace colors {
constexpr Color BG = {20, 28, 20, 255};
constexpr Color GRASS = {45, 90, 45, 255};
constexpr Color PATH = {140, 120, 80, 255};
constexpr Color ROCK = {100, 100, 110, 255};
constexpr Color WATER = {40, 70, 150, 255};
constexpr Color TREE_COL = {30, 70, 35, 255};
constexpr Color BASE = {60, 60, 180, 255};
constexpr Color SPAWN = {180, 60, 60, 255};
constexpr Color HUD_BG = {10, 10, 18, 255};
constexpr Color TRAY_BG = {15, 15, 25, 255};
constexpr Color WHITE = {240, 235, 220, 255};
constexpr Color GOLD = {255, 210, 80, 255};
constexpr Color ACCENT = {80, 200, 120, 255};
constexpr Color HEALTH = {220, 50, 50, 255};
constexpr Color CURSOR_OK = {80, 255, 80, 100};
constexpr Color CURSOR_BAD = {255, 80, 80, 100};
constexpr Color MAGENTA = {255, 0, 255, 255};
} // namespace colors

} // namespace cfg
