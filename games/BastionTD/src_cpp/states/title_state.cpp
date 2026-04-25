#include "states/title_state.h"

#include "core/config.h"

#include <cstdio>

namespace {

constexpr int kMenuCount = 4;

const char* kMenuItems[kMenuCount] = {
    "NEW GAME",
    "INSTRUCTIONS",
    "SETTINGS",
    "QUIT",
};

} // namespace

void TitleState::enter(App& app) {
    menu_idx = 0;
    anim_timer = 0.0f;
    app.audio->play_bgm(BgmId::Title);
}

void TitleState::update(App& app, float dt) {
    anim_timer += dt;

    if (app.input->pressed(InputButton::Up)) {
        menu_idx = (menu_idx - 1 + kMenuCount) % kMenuCount;
        app.audio->play_sfx(SfxId::MenuMove);
    }
    if (app.input->pressed(InputButton::Down)) {
        menu_idx = (menu_idx + 1) % kMenuCount;
        app.audio->play_sfx(SfxId::MenuMove);
    }
    if (app.input->pressed(InputButton::A)) {
        app.audio->play_sfx(SfxId::MenuSelect);
        switch (menu_idx) {
        case 0: app.change_state(StateId::Gameplay);     break;
        case 1: app.change_state(StateId::Instructions); break;
        case 2: app.change_state(StateId::Settings);     break;
        case 3: app.running = false;                     break;
        }
    }
}

void TitleState::render(App& app, float /*alpha*/) {
    auto* r = app.renderer;
    r->clear(cfg::colors::BG);

    for (int x = 0; x < cfg::SCREEN_W; x += 12) {
        const int y = 16 + ((x / 12) % 2 == 0 ? 0 : 2);
        r->draw_line(x, y, x + 20, y, {30, 60, 35, 255});
    }

    r->draw_text("BASTION TD", 90, 6, cfg::colors::GOLD);
#ifdef BASTION_GBA
    r->draw_text("GBA PORT", 98, 18, cfg::colors::WHITE);
#else
    r->draw_text("SDL2 PORT", 96, 18, cfg::colors::WHITE);
#endif

    const int menu_x = 78;
    const int menu_y = 42;
    const int row_h = 10;
    for (int i = 0; i < kMenuCount; ++i) {
        const Color color = (i == menu_idx) ? cfg::colors::ACCENT : cfg::colors::WHITE;
        const int y = menu_y + i * row_h;
        if (i == menu_idx) {
            r->draw_text(">", menu_x - 10, y, color);
        }
        r->draw_text(kMenuItems[i], menu_x, y, color);
    }

    if (app.best_wave > 0) {
        char buf[48];
        std::snprintf(buf, sizeof(buf), "BEST WAVE %d", app.best_wave);
        r->draw_text(buf, 84, cfg::SCREEN_H - 20, cfg::colors::GOLD);
    }
    if (app.games_played > 0) {
        char buf[48];
        std::snprintf(buf, sizeof(buf), "GAMES %d", app.games_played);
        r->draw_text(buf, 96, cfg::SCREEN_H - 10, {180, 180, 180, 255});
    }
}
