#include "states/game_over_state.h"

#include "core/config.h"

#include <cstdio>

void GameOverState::enter(App& app) {
    menu_idx = 0;
    app.audio->stop_bgm();
    app.audio->play_sfx(SfxId::GameOver);

    const int reached = app.sim.wave_mgr.current_wave + 1;
    if (reached > app.best_wave) {
        app.best_wave = reached;
    }
    const int score = app.sim.economy.gold;
    if (score > app.best_score) {
        app.best_score = score;
    }
    SaveData data;
    data.best_wave = app.best_wave;
    data.best_score = app.best_score;
    data.games_played = app.games_played;
    app.save_mgr.save(data);
}

void GameOverState::update(App& app, float /*dt*/) {
    if (app.input->pressed(InputButton::Up)) {
        menu_idx = 0;
        app.audio->play_sfx(SfxId::MenuMove);
    }
    if (app.input->pressed(InputButton::Down)) {
        menu_idx = 1;
        app.audio->play_sfx(SfxId::MenuMove);
    }
    if (app.input->pressed(InputButton::A)) {
        app.audio->play_sfx(SfxId::MenuSelect);
        if (menu_idx == 0) {
            app.change_state(StateId::Gameplay);
        } else {
            app.change_state(StateId::Title);
        }
    }
}

void GameOverState::render(App& app, float /*alpha*/) {
    auto* r = app.renderer;
    r->clear(cfg::colors::BG);
    r->draw_text("GAME OVER", 84, 18, cfg::colors::HEALTH);

    char buf[48];
    std::snprintf(buf, sizeof(buf), "WAVE %d", app.sim.wave_mgr.current_wave + 1);
    r->draw_text(buf, 92, 42, cfg::colors::WHITE);
    std::snprintf(buf, sizeof(buf), "GOLD %d", app.sim.economy.gold);
    r->draw_text(buf, 92, 54, cfg::colors::GOLD);

    r->draw_text(menu_idx == 0 ? "> RETRY" : "  RETRY", 88, 80, menu_idx == 0 ? cfg::colors::ACCENT : cfg::colors::WHITE);
    r->draw_text(menu_idx == 1 ? "> TITLE" : "  TITLE", 88, 92, menu_idx == 1 ? cfg::colors::ACCENT : cfg::colors::WHITE);
}
