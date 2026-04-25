#include "states/settings_state.h"

#include "core/config.h"

#include <cstdio>

namespace {

constexpr int kItemCount = 5;

const char* label_for(int i) {
    switch (i) {
    case 0: return "SPRITES";
    case 1: return "SFX";
    case 2: return "MUSIC";
    case 3: return "FPS";
    case 4: return "BACK";
    default: return "";
    }
}

bool value_for(const App& app, int i) {
    switch (i) {
    case 0: return app.use_sprites;
    case 1: return app.sfx_enabled;
    case 2: return app.bgm_enabled;
    case 3: return app.show_fps;
    default: return false;
    }
}

} // namespace

void SettingsState::enter(App& /*app*/) {
    cursor_idx = 0;
}

void SettingsState::update(App& app, float /*dt*/) {
    if (app.input->pressed(InputButton::Up)) {
        cursor_idx = (cursor_idx - 1 + kItemCount) % kItemCount;
        app.audio->play_sfx(SfxId::MenuMove);
    }
    if (app.input->pressed(InputButton::Down)) {
        cursor_idx = (cursor_idx + 1) % kItemCount;
        app.audio->play_sfx(SfxId::MenuMove);
    }
    if (app.input->pressed(InputButton::A)) {
        app.audio->play_sfx(SfxId::MenuSelect);
        switch (cursor_idx) {
        case 0: app.use_sprites = !app.use_sprites; break;
        case 1:
            app.sfx_enabled = !app.sfx_enabled;
            app.audio->set_sfx_volume(app.sfx_enabled ? 1.0f : 0.0f);
            break;
        case 2:
            app.bgm_enabled = !app.bgm_enabled;
            if (app.bgm_enabled) {
                app.audio->set_bgm_volume(1.0f);
                app.audio->play_bgm(BgmId::Title);
            } else {
                app.audio->set_bgm_volume(0.0f);
                app.audio->stop_bgm();
            }
            break;
        case 3: app.show_fps = !app.show_fps; break;
        case 4: app.change_state(StateId::Title); break;
        }
    }
    if (app.input->pressed(InputButton::B) || app.input->pressed(InputButton::Start)) {
        app.change_state(StateId::Title);
    }
}

void SettingsState::render(App& app, float /*alpha*/) {
    auto* r = app.renderer;
    r->clear(cfg::colors::HUD_BG);

    r->draw_text("SETTINGS", 96, 8, cfg::colors::GOLD);

    const int start_y = 30;
    const int row_h = 12;
    for (int i = 0; i < kItemCount; ++i) {
        const bool sel = (i == cursor_idx);
        const Color name_c = sel ? cfg::colors::ACCENT : cfg::colors::WHITE;
        const Color val_c  = sel ? cfg::colors::GOLD   : Color{160, 160, 160, 255};

        const int y = start_y + i * row_h;
        if (sel) {
            r->draw_text(">", 20, y, name_c);
        }
        r->draw_text(label_for(i), 30, y, name_c);
        if (i < 4) {
            r->draw_text(value_for(app, i) ? "ON" : "OFF", 160, y, val_c);
        }
    }

    r->draw_text("A=TOGGLE  B=BACK", 64, cfg::SCREEN_H - 10, {180, 180, 180, 255});
}
