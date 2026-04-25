#pragma once

#include "states/state.h"

struct SettingsState : State {
    int cursor_idx = 0;

    void enter(App& app) override;
    void update(App& app, float dt) override;
    void render(App& app, float alpha) override;
};
