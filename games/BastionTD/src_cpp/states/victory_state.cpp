#include "states/victory_state.h"

#include "core/config.h"

#include <cstdio>

void VictoryState::enter(App& app) {
    menu_idx = 0;
    app.audio->stop_bgm();
    app.audio->play_sfx(SfxId::Victory);

    if (cfg::TOTAL_WAVES > app.best_wave) {
        app.best_wave = cfg::TOTAL_WAVES;
    }
    if (app.sim.economy.gold > app.best_score) {
        app.best_score = app.sim.economy.gold;
    }
    SaveData data;
    data.best_wave = app.best_wave;
    data.best_score = app.best_score;
    data.games_played = app.games_played;
    app.save_mgr.save(data);
}

void VictoryState::update(App& app, float /*dt*/) {
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

void VictoryState::render(App& app, float /*alpha*/) {
    auto* r = app.renderer;
    r->clear(cfg::colors::BG);
    r->draw_text("VICTORY", 90, 18, cfg::colors::GOLD);
    r->draw_text("ALL 20 WAVES CLEARED", 48, 42, cfg::colors::ACCENT);

    char buf[48];
    std::snprintf(buf, sizeof(buf), "FINAL GOLD %d", app.sim.economy.gold);
    r->draw_text(buf, 68, 58, cfg::colors::WHITE);

    r->draw_text(menu_idx == 0 ? "> PLAY AGAIN" : "  PLAY AGAIN", 64, 82, menu_idx == 0 ? cfg::colors::ACCENT : cfg::colors::WHITE);
    r->draw_text(menu_idx == 1 ? "> TITLE" : "  TITLE", 86, 94, menu_idx == 1 ? cfg::colors::ACCENT : cfg::colors::WHITE);
}
