#pragma once

#include "core/config.h"
#include "core/types.h"

struct Particle {
    bool active = false;
    Vec2 pos = {0.0f, 0.0f};
    Vec2 vel = {0.0f, 0.0f};
    Color color = {};
    float life = 0.0f;
    float max_life = 0.0f;
};

struct DamageNumber {
    bool active = false;
    Vec2 pos = {0.0f, 0.0f};
    float value = 0.0f;
    float life = 0.0f;
    Color color = {};
};

struct ScreenShake {
    float duration = 0.0f;
    float intensity = 0.0f;
    float offset_x = 0.0f;
    float offset_y = 0.0f;

    void trigger(float dur, float intens);
    void update(float dt);
};

struct Effects {
    Particle particles[cfg::MAX_PARTICLES];
    DamageNumber dmg_numbers[cfg::MAX_DMG_NUMBERS];
    ScreenShake shake;

    void init();
    void emit_burst(Vec2 pos, Color color, int count);
    void add_dmg_number(Vec2 pos, float value, Color color);
    void update(float dt);
};
