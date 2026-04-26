#include "states/gameplay_state.h"

#include "core/math_utils.h"

#include <cstdio>
#include <cstring>

namespace {

const char* speed_text(SpeedMode mode) {
    switch (mode) {
    case SpeedMode::Fast2x:
        return ">>";
    case SpeedMode::Fast3x:
        return ">>>";
    default:
        return ">";
    }
}

SpriteId tower_body_sprite(TowerType type, int level) {
    if (level < 1) {
        level = 1;
    } else if (level > 3) {
        level = 3;
    }

    switch (type) {
    case TowerType::Arrow:
        return level == 1 ? SpriteId::TowerArrow1 : (level == 2 ? SpriteId::TowerArrow2 : SpriteId::TowerArrow3);
    case TowerType::Cannon:
        return level == 1 ? SpriteId::TowerCannon1 : (level == 2 ? SpriteId::TowerCannon2 : SpriteId::TowerCannon3);
    case TowerType::Ice:
        return level == 1 ? SpriteId::TowerIce1 : (level == 2 ? SpriteId::TowerIce2 : SpriteId::TowerIce3);
    case TowerType::Lightning:
        return level == 1 ? SpriteId::TowerLightning1 : (level == 2 ? SpriteId::TowerLightning2 : SpriteId::TowerLightning3);
    case TowerType::Flame:
        return level == 1 ? SpriteId::TowerFlame1 : (level == 2 ? SpriteId::TowerFlame2 : SpriteId::TowerFlame3);
    default:
        return SpriteId::TowerArrow1;
    }
}

int compute_fleet_cost(const GameSim& sim) {
    int missing_cost = 0;
    for (const auto& t : sim.towers.towers) {
        if (t.active && t.type == sim.fleet_selected_type && t.level < sim.fleet_target_level) {
            missing_cost += t.missing_upgrade_cost_to_level(sim.fleet_target_level);
        }
    }
    if (missing_cost == 0) {
        return 0;
    }
    return Economy::fleet_upgrade_cost(1, missing_cost);
}

void update_best_stats(App& app, int wave_reached) {
    if (wave_reached > app.best_wave) {
        app.best_wave = wave_reached;
    }
    if (app.sim.economy.gold > app.best_score) {
        app.best_score = app.sim.economy.gold;
    }
    ++app.games_played;
}

} // namespace

void GameplayState::enter(App& app) {
    if (app.previous_id == StateId::Pause) {
        return;
    }

    app.sim.new_game();
    cursor_x = cfg::GRID_W / 2;
    cursor_y = cfg::GRID_H / 2;
    selected_tower_idx = 0;
    sell_hold_timer = 0.0f;
    show_upgrade = false;
    show_fleet_menu = false;
    fleet_type_idx = 0;
    fast_forward_held = false;
    notification_timer = 0.0f;
    notification[0] = '\0';
    app.audio->play_bgm(BgmId::Build);
}

void GameplayState::show_notification(const char* msg) {
    std::snprintf(notification, sizeof(notification), "%s", msg);
    notification_timer = 2.0f;
}

void GameplayState::update(App& app, float dt) {
    auto& sim = app.sim;
    auto* input = app.input;

    if (input->pressed(InputButton::Start)) {
        app.change_state(StateId::Pause);
        return;
    }

    if (notification_timer > 0.0f) {
        notification_timer -= dt;
    }

    if (sim.wave_mgr.phase == GamePhase::Build) {
        fast_forward_held = false;
        sim.effects.update(dt);

        if (input->pressed(InputButton::FleetUpgrade) && sim.fleet_available) {
            show_fleet_menu = !show_fleet_menu;
            fleet_type_idx = static_cast<int>(sim.fleet_selected_type);
        }

        if (show_fleet_menu) {
            // Menu entries: 0..4 = per-type upgrade, 5 = ALL types at once.
            constexpr int kFleetOptions = 6;
            if (input->pressed(InputButton::L)) {
                fleet_type_idx = (fleet_type_idx - 1 + kFleetOptions) % kFleetOptions;
                app.audio->play_sfx(SfxId::MenuMove);
            }
            if (input->pressed(InputButton::R)) {
                fleet_type_idx = (fleet_type_idx + 1) % kFleetOptions;
                app.audio->play_sfx(SfxId::MenuMove);
            }
            if (fleet_type_idx < 5) {
                sim.fleet_selected_type = static_cast<TowerType>(fleet_type_idx);
            }
            if (input->pressed(InputButton::A)) {
                const bool ok = (fleet_type_idx == 5) ? sim.try_fleet_upgrade_all()
                                                       : sim.try_fleet_upgrade();
                if (ok) {
                    app.audio->play_sfx(SfxId::Upgrade);
                    show_notification(fleet_type_idx == 5 ? "ALL FLEETS UPGRADED"
                                                          : "FLEET UPGRADED");
                    show_fleet_menu = false;
                }
            }
            if (input->pressed(InputButton::B)) {
                show_fleet_menu = false;
            }
            return;
        }

        if (input->pressed(InputButton::Up)) {
            cursor_y = sim_to_int(sim_max(0.0f, static_cast<float>(cursor_y - 1)));
        }
        if (input->pressed(InputButton::Down)) {
            cursor_y = sim_to_int(sim_min(static_cast<float>(cfg::GRID_H - 1), static_cast<float>(cursor_y + 1)));
        }
        if (input->pressed(InputButton::Left)) {
            cursor_x = sim_to_int(sim_max(0.0f, static_cast<float>(cursor_x - 1)));
        }
        if (input->pressed(InputButton::Right)) {
            cursor_x = sim_to_int(sim_min(static_cast<float>(cfg::GRID_W - 1), static_cast<float>(cursor_x + 1)));
        }

        if (input->pressed(InputButton::L)) {
            selected_tower_idx = (selected_tower_idx - 1 + 5) % 5;
            app.audio->play_sfx(SfxId::MenuMove);
        }
        if (input->pressed(InputButton::R)) {
            selected_tower_idx = (selected_tower_idx + 1) % 5;
            app.audio->play_sfx(SfxId::MenuMove);
        }

        Tower* tower_under = sim.towers.get_at(cursor_x, cursor_y);
        if (tower_under != nullptr) {
            if (input->held(InputButton::B)) {
                sell_hold_timer += dt;
                if (sell_hold_timer >= 1.0f) {
                    const int refund = sim.try_sell_tower(cursor_x, cursor_y);
                    if (refund > 0) {
                        app.audio->play_sfx(SfxId::Sell);
                        show_notification("TOWER SOLD");
                    }
                    sell_hold_timer = 0.0f;
                    show_upgrade = false;
                }
            } else {
                if (input->released(InputButton::B) && sell_hold_timer < 1.0f) {
                    show_upgrade = !show_upgrade;
                }
                sell_hold_timer = 0.0f;
            }

            if (show_upgrade && input->pressed(InputButton::A)) {
                if (sim.try_upgrade_tower(cursor_x, cursor_y)) {
                    app.audio->play_sfx(SfxId::Upgrade);
                    show_notification("TOWER UPGRADED");
                    show_upgrade = false;
                }
            }
        } else {
            sell_hold_timer = 0.0f;
            show_upgrade = false;

            if (input->pressed(InputButton::A)) {
                const TowerType selected = static_cast<TowerType>(selected_tower_idx);
                if (sim.grid.is_buildable(cursor_x, cursor_y)) {
                    if (sim.try_place_tower(selected, cursor_x, cursor_y)) {
                        app.audio->play_sfx(SfxId::Place);
                        show_notification("TOWER PLACED");
                    }
                } else {
                    sim.start_next_wave();
                    if (sim.wave_mgr.phase == GamePhase::Wave) {
                        app.audio->play_sfx(SfxId::WaveStart);
                        show_notification(cfg::is_boss_wave(sim.wave_mgr.current_wave + 1) ? "BOSS WAVE" : "WAVE START");
                        app.audio->play_bgm(cfg::is_boss_wave(sim.wave_mgr.current_wave + 1) ? BgmId::Boss : BgmId::Wave);
                    }
                }
            }
        }

        return;
    }

    fast_forward_held = input->held(InputButton::FastForward);

    if (!fast_forward_held && input->pressed(InputButton::Select)) {
        sim.cycle_speed();
    }

    const int sim_steps = fast_forward_held ? 3 : sim.speed_steps();
    for (int step = 0; step < sim_steps; ++step) {
        sim.tick(cfg::SIM_DT);
        sim.effects.update(cfg::SIM_DT);

        for (int i = 0; i < sim.event_count; ++i) {
            const GameEvent& ev = sim.events[i];
            switch (ev.type) {
            case GameEventType::EnemyKilled:
                app.audio->play_sfx(SfxId::EnemyDeath);
                break;
            case GameEventType::TowerFired:
                app.audio->play_sfx(SfxId::Shoot);
                break;
            case GameEventType::BaseHit:
                app.audio->play_sfx(SfxId::BaseHit);
                show_notification("BASE HIT");
                break;
            case GameEventType::TitanSpawned:
                app.audio->play_sfx(SfxId::BossSpawn);
                app.audio->play_bgm(BgmId::Boss);
                show_notification("TITAN INCOMING");
                break;
            case GameEventType::WaveComplete:
                app.audio->play_sfx(SfxId::WaveClear);
                app.audio->play_bgm(BgmId::Build);
                show_notification(ev.data > 0 ? "WAVE CLEAR +25G" : "WAVE CLEAR");
                break;
            case GameEventType::Victory:
                update_best_stats(app, cfg::TOTAL_WAVES);
                app.change_state(StateId::Victory);
                return;
            case GameEventType::Defeat:
                update_best_stats(app, sim.wave_mgr.current_wave + 1);
                app.change_state(StateId::GameOver);
                return;
            default:
                break;
            }
        }
    }
}

void GameplayState::render(App& app, float alpha) {
    auto* r = app.renderer;
    r->clear(cfg::colors::BG);
    render_grid(app);
    render_towers(app);
    render_enemies(app, alpha);
    render_projectiles(app, alpha);
    render_cursor(app);
    render_effects(app);
    render_hud(app);
}

void GameplayState::render_grid(App& app) {
    auto* r = app.renderer;
    auto& g = app.sim.grid;
    const int ts = cfg::TILE_SIZE;

    // Pass 1: base tiles. Alternating variants give the grass and path a
    // checker pattern that reads as real terrain instead of a flat colour.
    for (int ty = 0; ty < cfg::GRID_H; ++ty) {
        for (int tx = 0; tx < cfg::GRID_W; ++tx) {
            const int px = tx * ts;
            const int py = cfg::GRID_OFFSET_Y + ty * ts;
            const Terrain t = g.get(tx, ty);
            const bool odd = ((tx + ty) & 1) != 0;

            Color fill = cfg::colors::GRASS;
            SpriteId sprite = odd ? SpriteId::TileGrassAlt : SpriteId::TileGrass;
            switch (t) {
            case Terrain::Path:
                fill = cfg::colors::PATH;
                sprite = odd ? SpriteId::TilePathAlt : SpriteId::TilePath;
                break;
            case Terrain::Water:
                fill = cfg::colors::WATER;
                sprite = SpriteId::TileWater;
                break;
            case Terrain::Spawn:
                fill = cfg::colors::SPAWN;
                sprite = SpriteId::TileSpawn;
                break;
            case Terrain::Base:
                fill = cfg::colors::BASE;
                sprite = SpriteId::TileBase;
                break;
            case Terrain::Rock:
            case Terrain::Tree:
            case Terrain::Tower:
            case Terrain::Empty:
            default:
                fill = cfg::colors::GRASS;
                sprite = odd ? SpriteId::TileGrassAlt : SpriteId::TileGrass;
                break;
            }

            if (app.use_sprites) {
                r->draw_sprite(sprite, px, py, 1.0f);
            } else {
                r->draw_rect(px, py, ts, ts, fill);
            }

            if (t == Terrain::Spawn || t == Terrain::Base) {
                r->draw_rect_outline(px, py, ts, ts, cfg::colors::WHITE);
            }
        }
    }

    // Pass 2: props (trees, rocks) overlaid on top so they can overflow
    // vertically without being covered by the next row's grass.
    if (app.use_sprites) {
        for (int ty = 0; ty < cfg::GRID_H; ++ty) {
            for (int tx = 0; tx < cfg::GRID_W; ++tx) {
                const int px = tx * ts;
                const int py = cfg::GRID_OFFSET_Y + ty * ts;
                const Terrain t = g.get(tx, ty);
                const bool odd = ((tx + ty) & 1) != 0;
                if (t == Terrain::Tree) {
                    const SpriteId prop = odd ? SpriteId::PropTreeSmall : SpriteId::PropTreeLarge;
                    // Render 10x12, anchored so the trunk sits in the tile.
                    r->draw_sprite_rect(prop, px - 1, py - 4, 10, 12);
                } else if (t == Terrain::Rock) {
                    const SpriteId prop = odd ? SpriteId::PropRockSmall : SpriteId::PropRockLarge;
                    r->draw_sprite_rect(prop, px, py + 1, ts, ts - 2);
                }
            }
        }
    } else {
        for (int ty = 0; ty < cfg::GRID_H; ++ty) {
            for (int tx = 0; tx < cfg::GRID_W; ++tx) {
                const int px = tx * ts;
                const int py = cfg::GRID_OFFSET_Y + ty * ts;
                const Terrain t = g.get(tx, ty);
                if (t == Terrain::Rock) {
                    r->draw_rect(px + 2, py + 2, ts - 4, ts - 4, cfg::colors::ROCK);
                } else if (t == Terrain::Tree) {
                    r->draw_rect(px + 3, py + 1, 2, ts - 2, cfg::colors::TREE_COL);
                } else if (t == Terrain::Path) {
                    r->draw_line(px + 1, py + ts / 2, px + ts - 2, py + ts / 2, {170, 150, 100, 255});
                }
            }
        }
    }
}

void GameplayState::render_enemies(App& app, float alpha) {
    auto* r = app.renderer;
    for (const auto& e : app.sim.enemies.enemies) {
        if (!e.active) {
            continue;
        }

        const Vec2 rp = lerp(e.prev_pos, e.pos, alpha);
        const int cx = sim_to_int(rp.x * cfg::TILE_SIZE + cfg::TILE_SIZE / 2.0f);
        const int cy = cfg::GRID_OFFSET_Y + sim_to_int(rp.y * cfg::TILE_SIZE + cfg::TILE_SIZE / 2.0f);
        const float scale = e.dying ? sim_clamp(sim_div(e.death_timer, 0.3f), 0.3f, 1.0f) * e.sprite_scale : e.sprite_scale;
        int sprite_size = sim_to_int(8.0f * scale);
        if (sprite_size < 1) {
            sprite_size = 1;
        }
        const int half = sprite_size / 2;

        r->draw_sprite_rect(e.sprite, cx - half, cy - half, sprite_size, sprite_size);

        if (e.slow_timer > 0.0f) {
            r->draw_rect(cx - 3, cy - 3, 6, 6, {80, 140, 220, 90});
        }

        if (!e.dying && e.hp < e.max_hp) {
            const int bw = 8;
            const int bh = 1;
            const int bx = cx - 4;
            const int by = cy - half - 2;
            const float hp_frac = sim_clamp(sim_div(e.hp, e.max_hp), 0.0f, 1.0f);
            r->draw_rect(bx, by, bw, bh, {60, 20, 20, 255});
            r->draw_rect(bx, by, sim_to_int(bw * hp_frac), bh, cfg::colors::ACCENT);
        }
    }
}

void GameplayState::render_towers(App& app) {
    auto* r = app.renderer;
    const int ts = cfg::TILE_SIZE;
    for (const auto& t : app.sim.towers.towers) {
        if (!t.active) {
            continue;
        }
        const int px = t.tile_x * ts;
        const int py = cfg::GRID_OFFSET_Y + t.tile_y * ts;

        if (app.use_sprites) {
            // 50% shrink: tower body 8x8 filling the tile rectangle.
            r->draw_sprite_rect(tower_body_sprite(t.type, t.level), px, py, 8, 8);
        } else {
            r->draw_rect(px + 1, py + 2, ts - 2, ts - 3, {t.color.r, t.color.g, t.color.b, 180});
        }

        // 8x8 char sits on body top (py). Feet end at py. Firing animates 1px up.
        const int char_dy = t.firing_anim ? -9 : -8;
        r->draw_sprite_rect(t.char_sprite, px, py + char_dy, 8, 8);

        for (int i = 0; i < t.level; ++i) {
            r->draw_rect(px + 1 + i * 2, py + ts - 1, 1, 1, cfg::colors::WHITE);
        }
    }
}

void GameplayState::render_projectiles(App& app, float alpha) {
    auto* r = app.renderer;
    for (const auto& p : app.sim.projectiles.projectiles) {
        if (!p.active) {
            continue;
        }
        const Vec2 rp = lerp(p.prev_pos, p.pos, alpha);
        const int px = sim_to_int(rp.x * cfg::TILE_SIZE + cfg::TILE_SIZE / 2.0f);
        const int py = cfg::GRID_OFFSET_Y + sim_to_int(rp.y * cfg::TILE_SIZE + cfg::TILE_SIZE / 2.0f);
        r->draw_rect(px - 1, py - 1, 2, 2, p.color);
    }
}

void GameplayState::render_cursor(App& app) {
    if (app.sim.wave_mgr.phase != GamePhase::Build) {
        return;
    }

    auto* r = app.renderer;
    const int px = cursor_x * cfg::TILE_SIZE;
    const int py = cfg::GRID_OFFSET_Y + cursor_y * cfg::TILE_SIZE;
    const bool buildable = app.sim.grid.is_buildable(cursor_x, cursor_y);
    const Color outline = buildable ? cfg::colors::CURSOR_OK : cfg::colors::CURSOR_BAD;
    r->draw_rect_outline(px, py, cfg::TILE_SIZE, cfg::TILE_SIZE, outline);

    if (buildable) {
        const auto& def = cfg::TOWER_DEFS[selected_tower_idx];
        r->draw_circle(px + cfg::TILE_SIZE / 2, py + cfg::TILE_SIZE / 2, sim_to_int(def.range * cfg::TILE_SIZE), {255, 255, 255, 50});
        if (app.use_sprites) {
            r->draw_sprite_rect(tower_body_sprite(static_cast<TowerType>(selected_tower_idx), 1), px, py, 8, 8);
        } else {
            r->draw_rect(px + 1, py + 2, cfg::TILE_SIZE - 2, cfg::TILE_SIZE - 3, {def.color.r, def.color.g, def.color.b, 90});
        }
        r->draw_sprite_rect(def.char_sprite, px, py - 8, 8, 8);
    }

    const Tower* t = app.sim.towers.get_at(cursor_x, cursor_y);
    if (t != nullptr) {
        r->draw_circle(px + cfg::TILE_SIZE / 2, py + cfg::TILE_SIZE / 2, sim_to_int(t->range * cfg::TILE_SIZE), {255, 255, 255, 70});
        if (show_upgrade && t->upgrade_cost() >= 0) {
            char buf[24];
            std::snprintf(buf, sizeof(buf), "UP %dG", t->upgrade_cost());
            r->draw_text(buf, px, py - 8, cfg::colors::GOLD);
        }
    }
}

void GameplayState::render_effects(App& app) {
    auto* r = app.renderer;
    for (const auto& p : app.sim.effects.particles) {
        if (!p.active) {
            continue;
        }
        const int px = sim_to_int(p.pos.x * cfg::TILE_SIZE + cfg::TILE_SIZE / 2.0f);
        const int py = cfg::GRID_OFFSET_Y + sim_to_int(p.pos.y * cfg::TILE_SIZE + cfg::TILE_SIZE / 2.0f);
        r->draw_rect(px, py, 1, 1, p.color);
    }
    for (const auto& d : app.sim.effects.dmg_numbers) {
        if (!d.active) {
            continue;
        }
        const int px = sim_to_int(d.pos.x * cfg::TILE_SIZE + cfg::TILE_SIZE / 2.0f);
        const int py = cfg::GRID_OFFSET_Y + sim_to_int(d.pos.y * cfg::TILE_SIZE + cfg::TILE_SIZE / 2.0f);
        char buf[16];
        std::snprintf(buf, sizeof(buf), "%d", sim_to_int(d.value));
        r->draw_text(buf, px, py, d.color);
    }
}

void GameplayState::render_hud(App& app) {
    auto* r = app.renderer;
    auto& sim = app.sim;

    r->draw_rect(0, 0, cfg::SCREEN_W, cfg::GRID_OFFSET_Y, cfg::colors::HUD_BG);
    r->draw_rect(0, cfg::GRID_OFFSET_Y + cfg::GRID_H * cfg::TILE_SIZE,
                 cfg::SCREEN_W, cfg::TRAY_ROWS * cfg::TILE_SIZE, cfg::colors::TRAY_BG);

    char buf[48];
    int display_wave = sim.wave_mgr.current_wave + 1;
    if (display_wave > cfg::TOTAL_WAVES) {
        display_wave = cfg::TOTAL_WAVES;
    }
    std::snprintf(buf, sizeof(buf), "W %d/%d", display_wave, cfg::TOTAL_WAVES);
    r->draw_text(buf, 2, 2, cfg::colors::WHITE);

    std::snprintf(buf, sizeof(buf), "G %d", sim.economy.gold);
    r->draw_text(buf, 56, 2, cfg::colors::GOLD);

    std::snprintf(buf, sizeof(buf), "L %d", sim.economy.lives);
    r->draw_text(buf, 108, 2, cfg::colors::HEALTH);

    r->draw_text(speed_text(fast_forward_held ? SpeedMode::Fast3x : sim.speed_mode), 218, 2, cfg::colors::ACCENT);

    if (sim.wave_mgr.phase == GamePhase::Build) {
        r->draw_text("BUILD", 2, 10, cfg::colors::ACCENT);
    } else {
        std::snprintf(buf, sizeof(buf), "EN %d", sim.wave_mgr.enemies_remaining(sim.enemies));
        r->draw_text(buf, 2, 10, cfg::colors::WHITE);
    }

    if (sim.titan_idx >= 0 && sim.enemies.enemies[sim.titan_idx].active && !sim.enemies.enemies[sim.titan_idx].dying) {
        const auto& titan = sim.enemies.enemies[sim.titan_idx];
        const int bx = 20;
        const int by = cfg::GRID_OFFSET_Y + cfg::GRID_H * cfg::TILE_SIZE - 4;
        const int bw = cfg::SCREEN_W - 40;
        const float hp_frac = sim_clamp(sim_div(titan.hp, titan.max_hp), 0.0f, 1.0f);
        r->draw_rect(bx, by, bw, 3, {60, 20, 20, 255});
        r->draw_rect(bx, by, sim_to_int(bw * hp_frac), 3, cfg::colors::HEALTH);
        r->draw_text("TITAN", bx, by - 6, cfg::colors::HEALTH);
    }

    const int tray_y = cfg::GRID_OFFSET_Y + cfg::GRID_H * cfg::TILE_SIZE;
    for (int i = 0; i < 5; ++i) {
        const auto& def = cfg::TOWER_DEFS[i];
        const int tx = 2 + i * 47;
        const int ty = tray_y + 2;
        const bool selected = (i == selected_tower_idx);
        const bool affordable = sim.economy.can_afford(def.cost);
        const Color box_color = affordable ? def.color : Color{60, 60, 60, 255};
        r->draw_rect(tx, ty, 10, 10, box_color);
        r->draw_sprite(def.char_sprite, tx + 1, ty + 1);
        if (selected) {
            r->draw_rect_outline(tx - 1, ty - 1, 44, 12, cfg::colors::ACCENT);
        }
        std::snprintf(buf, sizeof(buf), "%d", def.cost);
        r->draw_text(buf, tx + 12, ty + 2, affordable ? cfg::colors::GOLD : Color{100, 100, 100, 255});
    }

    if (sim.fleet_available && sim.wave_mgr.phase == GamePhase::Build) {
        r->draw_text("F FLEET", 2, tray_y + 10, cfg::colors::GOLD);
    }

    if (notification_timer > 0.0f) {
        r->draw_text(notification, 72, cfg::GRID_OFFSET_Y + 6, cfg::colors::WHITE);
    }

    if (show_fleet_menu) {
        const bool all_mode = (fleet_type_idx == 5);
        const int cost = all_mode ? sim.fleet_upgrade_all_cost() : compute_fleet_cost(sim);
        r->draw_rect(40, 38, 160, 40, {0, 0, 0, 200});
        r->draw_rect_outline(40, 38, 160, 40, cfg::colors::ACCENT);

        if (all_mode) {
            std::snprintf(buf, sizeof(buf), "FLEET ALL L%d", sim.fleet_target_level);
        } else {
            std::snprintf(buf, sizeof(buf), "FLEET %s L%d",
                cfg::TOWER_DEFS[fleet_type_idx].name, sim.fleet_target_level);
        }
        r->draw_text(buf, 48, 44, cfg::colors::ACCENT);
        std::snprintf(buf, sizeof(buf), "COST %dG", cost);
        r->draw_text(buf, 48, 54, cost > 0 && sim.economy.can_afford(cost)
                        ? cfg::colors::GOLD
                        : Color{200, 80, 80, 255});
        r->draw_text("L/R PICK  A BUY  B BACK", 48, 66, {180, 180, 180, 255});
    }
}
