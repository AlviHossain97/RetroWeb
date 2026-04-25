#pragma once

#include "states/state.h"

struct GameplayState : State {
    int cursor_x = 0;
    int cursor_y = 0;
    int selected_tower_idx = 0;
    float sell_hold_timer = 0.0f;
    bool show_upgrade = false;
    bool show_fleet_menu = false;
    int fleet_type_idx = 0;
    bool fast_forward_held = false;

    float notification_timer = 0.0f;
    char notification[64] = {};

    void enter(App& app) override;
    void update(App& app, float dt) override;
    void render(App& app, float alpha) override;

    void render_grid(App& app);
    void render_enemies(App& app, float alpha);
    void render_towers(App& app);
    void render_projectiles(App& app, float alpha);
    void render_cursor(App& app);
    void render_effects(App& app);
    void render_hud(App& app);
    void show_notification(const char* msg);
};
