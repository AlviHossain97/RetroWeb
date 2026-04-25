#pragma once

#include "core/game.h"
#include "core/save_manager.h"
#include "hal/hal.h"

#include <cstdint>

struct App;

struct State {
    virtual ~State() = default;
    virtual void enter(App& app) {}
    virtual void exit(App& app) {}
    virtual void update(App& app, float dt) = 0;
    virtual void render(App& app, float alpha) = 0;
};

enum class StateId : uint8_t {
    Title = 0,
    Gameplay,
    Pause,
    GameOver,
    Victory,
    Instructions,
    Settings,
    COUNT,
};

struct App {
    IRenderer* renderer = nullptr;
    IInput* input = nullptr;
    IAudio* audio = nullptr;
    GameSim sim;
    SaveManager save_mgr;
    State* states[static_cast<int>(StateId::COUNT)] = {};
    State* current_state = nullptr;
    StateId current_id = StateId::Title;
    StateId previous_id = StateId::Title;
    bool running = true;

    int best_wave = 0;
    int best_score = 0;
    int games_played = 0;

    bool use_sprites = true;
    bool sfx_enabled = true;
    bool bgm_enabled = true;
    bool show_fps = false;

    void change_state(StateId id);
};
