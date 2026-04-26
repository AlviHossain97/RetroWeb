#include "states/instructions_state.h"

#include "core/config.h"

#include <cstdio>

void InstructionsState::enter(App& /*app*/) {}

void InstructionsState::update(App& app, float /*dt*/) {
    if (app.input->pressed(InputButton::A) || app.input->pressed(InputButton::B) ||
        app.input->pressed(InputButton::Start)) {
        app.audio->play_sfx(SfxId::MenuSelect);
        app.change_state(StateId::Title);
    }
}

void InstructionsState::render(App& app, float /*alpha*/) {
    auto* r = app.renderer;
    r->clear(cfg::colors::HUD_BG);

    r->draw_text("HOW TO PLAY", 88, 4, cfg::colors::GOLD);

    int y = 18;
    const int left = 6;

    r->draw_text("ACTION      KEY       GBA", left, y, cfg::colors::GOLD);
    y += 9;
    r->draw_text("MOVE        WASD      DPAD", left, y, cfg::colors::WHITE);  y += 8;
    r->draw_text("PLACE       Z/ENTER   A",    left, y, cfg::colors::WHITE);  y += 8;
    r->draw_text("UPGRADE     X         B",    left, y, cfg::colors::WHITE);  y += 8;
    r->draw_text("PREV TOWER  Q         L",    left, y, cfg::colors::WHITE);  y += 8;
    r->draw_text("NEXT TOWER  E         R",    left, y, cfg::colors::WHITE);  y += 8;
    r->draw_text("PAUSE       ESC/BKSP  START",left, y, cfg::colors::WHITE); y += 8;
    r->draw_text("SPEED       SHIFT     SELECT",left,y, cfg::colors::WHITE); y += 8;
    r->draw_text("FLEET UP    F         L+R",   left, y, cfg::colors::WHITE); y += 11;

    r->draw_text("DEFEND THE BASE FROM WAVES",  left, y, cfg::colors::ACCENT); y += 8;
    r->draw_text("HOLD B FOR 1S TO SELL",       left, y, cfg::colors::WHITE);  y += 8;
    r->draw_text("SURVIVE 20 WAVES TO WIN",     left, y, cfg::colors::WHITE);  y += 11;

    r->draw_text("PRESS A TO RETURN", 60, cfg::SCREEN_H - 10, cfg::colors::ACCENT);
}
