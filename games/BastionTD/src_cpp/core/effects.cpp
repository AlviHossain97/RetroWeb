#include "core/effects.h"

#include <cmath>
#include <cstdlib>

void ScreenShake::trigger(float dur, float intens) {
    duration = dur;
    intensity = intens;
}

void ScreenShake::update(float dt) {
    if (duration > 0.0f) {
        duration -= dt;
        const float fraction = duration > 0.0f ? duration / 0.3f : 0.0f;
        offset_x = static_cast<float>((std::rand() % 3) - 1) * intensity * fraction;
        offset_y = static_cast<float>((std::rand() % 3) - 1) * intensity * fraction;
    } else {
        offset_x = 0.0f;
        offset_y = 0.0f;
    }
}

void Effects::init() {
    for (auto& p : particles) {
        p.active = false;
    }
    for (auto& d : dmg_numbers) {
        d.active = false;
    }
    shake = {};
}

void Effects::emit_burst(Vec2 pos, Color color, int count) {
    for (int i = 0; i < count; ++i) {
        for (auto& p : particles) {
            if (!p.active) {
                p.active = true;
                p.pos = pos;
                const float angle = static_cast<float>(std::rand() % 360) * 3.1415926f / 180.0f;
                const float speed = 1.0f + static_cast<float>(std::rand() % 30) / 10.0f;
                p.vel = {std::cos(angle) * speed, std::sin(angle) * speed};
                p.color = color;
                p.max_life = 0.3f + static_cast<float>(std::rand() % 20) / 100.0f;
                p.life = p.max_life;
                break;
            }
        }
    }
}

void Effects::add_dmg_number(Vec2 pos, float value, Color color) {
    for (auto& d : dmg_numbers) {
        if (!d.active) {
            d.active = true;
            d.pos = pos;
            d.value = value;
            d.life = 0.8f;
            d.color = color;
            return;
        }
    }
}

void Effects::update(float dt) {
    for (auto& p : particles) {
        if (!p.active) {
            continue;
        }
        p.pos.x += p.vel.x * dt;
        p.pos.y += p.vel.y * dt;
        p.life -= dt;
        if (p.life <= 0.0f) {
            p.active = false;
        }
    }

    for (auto& d : dmg_numbers) {
        if (!d.active) {
            continue;
        }
        d.pos.y -= 2.0f * dt;
        d.life -= dt;
        if (d.life <= 0.0f) {
            d.active = false;
        }
    }

    shake.update(dt);
}
