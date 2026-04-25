#pragma once

#include "states/state.h"

struct TitleState : State {
    int menu_idx = 0;
    float anim_timer = 0.0f;

    void enter(App& app) override;
    void update(App& app, float dt) override;
    void render(App& app, float alpha) override;
};
