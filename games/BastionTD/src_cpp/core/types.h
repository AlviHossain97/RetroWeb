#pragma once

#include <cstdint>

struct Vec2 {
    float x = 0.0f;
    float y = 0.0f;
};

struct Color {
    uint8_t r = 0;
    uint8_t g = 0;
    uint8_t b = 0;
    uint8_t a = 255;
};

struct Rect {
    float x = 0.0f;
    float y = 0.0f;
    float w = 0.0f;
    float h = 0.0f;
};

enum class Terrain : uint8_t {
    Empty = 0,
    Path,
    Rock,
    Water,
    Tree,
    Spawn,
    Base,
    Tower,
};

enum class TowerType : uint8_t {
    Arrow = 0,
    Cannon,
    Ice,
    Lightning,
    Flame,
    COUNT,
};

enum class EnemyType : uint8_t {
    Goblin = 0,
    Wolf,
    Knight,
    Healer,
    Swarm,
    Titan,
    COUNT,
};

enum class GamePhase : uint8_t {
    Build = 0,
    Wave,
    WaveCleanup,
    DefeatPending,
};

enum class SpeedMode : uint8_t {
    Normal = 0,
    Fast2x,
    Fast3x,
};

enum class SpriteId : uint8_t {
    Char0 = 0,
    Char1,
    Char2,
    Char3,
    Char4,

    TowerArrow1,
    TowerArrow2,
    TowerArrow3,
    TowerCannon1,
    TowerCannon2,
    TowerCannon3,
    TowerIce1,
    TowerIce2,
    TowerIce3,
    TowerLightning1,
    TowerLightning2,
    TowerLightning3,
    TowerFlame1,
    TowerFlame2,
    TowerFlame3,

    TileGrass,
    TileGrassAlt,
    TilePath,
    TilePathAlt,
    TileRock,
    TileWater,
    TileTree,
    TileSpawn,
    TileBase,
    TileTowerBase,

    PropTreeLarge,
    PropTreeSmall,
    PropBush,
    PropRockLarge,
    PropRockSmall,
    PropLog,

    MagentaFallback,
    COUNT,
};

enum class InputButton : uint8_t {
    Up = 0,
    Down,
    Left,
    Right,
    A,
    B,
    L,
    R,
    Start,
    Select,
    FastForward,
    FleetUpgrade,
    COUNT,
};

enum class SfxId : uint8_t {
    Place = 0,
    Shoot,
    Hit,
    EnemyDeath,
    WaveStart,
    WaveClear,
    BossSpawn,
    BaseHit,
    Upgrade,
    Sell,
    MenuMove,
    MenuSelect,
    GameOver,
    Victory,
    COUNT,
};

enum class BgmId : uint8_t {
    Title = 0,
    Build,
    Wave,
    Boss,
    COUNT,
};
