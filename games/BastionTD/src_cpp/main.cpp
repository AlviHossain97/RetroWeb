#if __has_include(<SDL.h>)
#include <SDL.h>
#else
#include <SDL2/SDL.h>
#endif

#include "core/config.h"
#include "hal/sdl2_audio.h"
#include "hal/sdl2_input.h"
#include "hal/sdl2_renderer.h"
#include "states/game_over_state.h"
#include "states/gameplay_state.h"
#include "states/instructions_state.h"
#include "states/pause_state.h"
#include "states/settings_state.h"
#include "states/state.h"
#include "states/title_state.h"
#include "states/victory_state.h"

#include <cstdio>
#include <fstream>

namespace {

void startup_log(const char* message) {
    std::ofstream out("bastion_startup.log", std::ios::app);
    if (out.is_open()) {
        out << message << '\n';
    }
}

void startup_log_sdl_error(const char* prefix) {
    std::ofstream out("bastion_startup.log", std::ios::app);
    if (out.is_open()) {
        out << prefix << ": " << SDL_GetError() << '\n';
    }
}

} // namespace

void App::change_state(StateId id) {
    previous_id = current_id;
    if (current_state != nullptr) {
        current_state->exit(*this);
    }
    current_id = id;
    current_state = states[static_cast<int>(id)];
    if (current_state != nullptr) {
        current_state->enter(*this);
    }
}

int main(int /*argc*/, char** /*argv*/) {
    startup_log("launch begin");

    if (SDL_Init(SDL_INIT_VIDEO | SDL_INIT_TIMER | SDL_INIT_GAMECONTROLLER) < 0) {
        startup_log_sdl_error("SDL_Init failed");
        SDL_ShowSimpleMessageBox(SDL_MESSAGEBOX_ERROR, "BASTION TD", SDL_GetError(), nullptr);
        return 1;
    }
    startup_log("SDL_Init ok");

    SDL2Renderer renderer;
    if (!renderer.init("BASTION TD", cfg::SCREEN_W, cfg::SCREEN_H, cfg::WINDOW_SCALE)) {
        startup_log_sdl_error("renderer init failed");
        SDL_ShowSimpleMessageBox(SDL_MESSAGEBOX_ERROR, "BASTION TD", SDL_GetError(), nullptr);
        SDL_Quit();
        return 1;
    }
    startup_log("renderer init ok");

    SDL2Input input;
    SDL2Audio audio;
    audio.init();
    startup_log("audio init ok");

    App app;
    app.renderer = &renderer;
    app.input = &input;
    app.audio = &audio;

    TitleState title_state;
    GameplayState gameplay_state;
    PauseState pause_state;
    GameOverState game_over_state;
    VictoryState victory_state;
    InstructionsState instructions_state;
    SettingsState settings_state;

    app.states[static_cast<int>(StateId::Title)] = &title_state;
    app.states[static_cast<int>(StateId::Gameplay)] = &gameplay_state;
    app.states[static_cast<int>(StateId::Pause)] = &pause_state;
    app.states[static_cast<int>(StateId::GameOver)] = &game_over_state;
    app.states[static_cast<int>(StateId::Victory)] = &victory_state;
    app.states[static_cast<int>(StateId::Instructions)] = &instructions_state;
    app.states[static_cast<int>(StateId::Settings)] = &settings_state;

    SaveData saved = app.save_mgr.load();
    app.best_wave = saved.best_wave;
    app.best_score = saved.best_score;
    app.games_played = saved.games_played;

    app.current_state = nullptr;
    app.current_id = StateId::Title;
    app.previous_id = StateId::Title;
    app.change_state(StateId::Title);
    startup_log("entered title state");

    const Uint64 freq = SDL_GetPerformanceFrequency();
    Uint64 last = SDL_GetPerformanceCounter();
    float accumulator = 0.0f;

    while (app.running) {
        const Uint64 now = SDL_GetPerformanceCounter();
        float frame_dt = static_cast<float>(now - last) / static_cast<float>(freq);
        last = now;
        if (frame_dt > cfg::MAX_DT) {
            frame_dt = cfg::MAX_DT;
        }

        input.set_dt(cfg::SIM_DT);
        input.update();
        audio.tick();
        if (input.quit_requested()) {
            break;
        }

        accumulator += frame_dt;
        while (accumulator >= cfg::SIM_DT && app.running) {
            input.advance_frame();
            if (app.current_state != nullptr) {
                app.current_state->update(app, cfg::SIM_DT);
            }
            accumulator -= cfg::SIM_DT;
        }

        if (app.current_state != nullptr) {
            const float alpha = accumulator / cfg::SIM_DT;
            app.current_state->render(app, alpha);
            renderer.present();
        }
    }

    audio.shutdown();
    renderer.shutdown();
    SDL_Quit();
    return 0;
}
