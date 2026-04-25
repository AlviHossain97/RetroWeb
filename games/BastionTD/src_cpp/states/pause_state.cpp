#include "states/pause_state.h"

#include "core/config.h"
#include "states/gameplay_state.h"

void PauseState::enter(App& /*app*/) {
    menu_idx = 0;
}

void PauseState::update(App& app, float /*dt*/) {
    if (app.input->pressed(InputButton::Up)) {
        menu_idx = 0;
        app.audio->play_sfx(SfxId::MenuMove);
    }
    if (app.input->pressed(InputButton::Down)) {
        menu_idx = 1;
        app.audio->play_sfx(SfxId::MenuMove);
    }
    if (app.input->pressed(InputButton::Start) || app.input->pressed(InputButton::B)) {
        app.change_state(StateId::Gameplay);
        return;
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

void PauseState::render(App& app, float /*alpha*/) {
    auto* r = app.renderer;

    // Full solid clear so the menu reads cleanly on every platform (the
    // previous translucent-overlay approach did not render on GBA, which
    // lacks an alpha-blended big-rect primitive).
    r->clear(cfg::colors::HUD_BG);

    const int cx = cfg::SCREEN_W / 2;

    r->draw_text("PAUSED", cx - 24, 24, cfg::colors::GOLD);

    const int menu_y = 52;
    const int row_h = 12;

    const Color c_resume = (menu_idx == 0) ? cfg::colors::ACCENT : cfg::colors::WHITE;
    const Color c_title  = (menu_idx == 1) ? cfg::colors::ACCENT : cfg::colors::WHITE;

    r->draw_text(menu_idx == 0 ? ">" : " ", cx - 40, menu_y,          c_resume);
    r->draw_text("RESUME",                  cx - 28, menu_y,          c_resume);
    r->draw_text(menu_idx == 1 ? ">" : " ", cx - 40, menu_y + row_h,  c_title);
    r->draw_text("TITLE",                   cx - 28, menu_y + row_h,  c_title);

    r->draw_text("A=OK  B=RESUME", cx - 56, cfg::SCREEN_H - 16, {180, 180, 180, 255});
}
