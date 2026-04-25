#pragma once

#include "states/state.h"

struct GameOverState : State {
    int menu_idx = 0;

    void enter(App& app) override;
    void update(App& app, float dt) override;
    void render(App& app, float alpha) override;
};
