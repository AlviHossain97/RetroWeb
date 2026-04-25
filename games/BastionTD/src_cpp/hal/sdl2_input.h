#pragma once

#include "hal/hal.h"

#if __has_include(<SDL.h>)
#include <SDL.h>
#else
#include <SDL2/SDL.h>
#endif

struct SDL2Input : IInput {
    bool cur[static_cast<int>(InputButton::COUNT)] = {};
    bool prev[static_cast<int>(InputButton::COUNT)] = {};
    bool pressed_now[static_cast<int>(InputButton::COUNT)] = {};
    bool released_now[static_cast<int>(InputButton::COUNT)] = {};
    bool pending_press[static_cast<int>(InputButton::COUNT)] = {};
    bool pending_release[static_cast<int>(InputButton::COUNT)] = {};
    float hold_time[static_cast<int>(InputButton::COUNT)] = {};
    bool quit = false;
    float dt = 0.0f;

    SDL_GameController* controller = nullptr;

    void update() override;
    void advance_frame();
    void set_dt(float d) { dt = d; }
    bool pressed(InputButton btn) const override;
    bool held(InputButton btn) const override;
    bool released(InputButton btn) const override;
    bool quit_requested() const override;
    float held_duration(InputButton btn) const override;
};
