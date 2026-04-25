#include "mythical/core/world.hpp"
#include "render.hpp"
#include "save_io.hpp"
#include "terminal.hpp"

#include <cctype>
#include <cstdint>
#include <iostream>
#include <sstream>
#include <string>

using namespace mythical;
using namespace mythical::port;

namespace {

constexpr const char* SAVE_PATH = "mythical_save.bin";

std::uint32_t g_rng_state = 0x12345678u;

int next_roll_0_99() {
    // Simple xorshift; deterministic unless re-seeded.
    g_rng_state ^= g_rng_state << 13;
    g_rng_state ^= g_rng_state >> 17;
    g_rng_state ^= g_rng_state << 5;
    return static_cast<int>(g_rng_state % 100);
}

struct FrameMessage {
    std::string text;
};

void print_title() {
    std::cout << "=========================================\n"
              << "  MYTHICAL  (C++ terminal port, v1)\n"
              << "=========================================\n"
              << "\n"
              << "  [n] New game\n"
              << "  [c] Continue (load " << SAVE_PATH << ")\n"
              << "  [q] Quit\n"
              << "\n"
              << "Controls in-game: wasd to move, f to attack,\n"
              << "i inventory, e enter door, b defeat boss,\n"
              << "s save, l load, q quit.\n"
              << "\n> " << std::flush;
}

SaveState snapshot(const World& w) {
    SaveState st;
    st.campaign    = w.campaign();
    st.current_map = w.current_map();
    st.player_x    = w.player().x();
    st.player_y    = w.player().y();
    st.coins       = w.player().inventory().wallet().coins();
    return st;
}

void apply_snapshot(World& w, const SaveState& st) {
    w.campaign() = st.campaign;
    w.enter_map(st.current_map);
    w.player().set_position(st.player_x, st.player_y);
    w.player().set_form(w.campaign().current_form());
    const int cur = w.player().inventory().wallet().coins();
    if (st.coins > cur) w.player().inventory().wallet().add(st.coins - cur);
}

Direction key_to_dir(int key) {
    switch (std::tolower(key)) {
        case 'w': return Direction::North;
        case 's': return Direction::South;
        case 'a': return Direction::West;
        case 'd': return Direction::East;
        default:  return Direction::None;
    }
}

void render_game(const World& w, const FrameMessage& msg) {
    clear_screen();
    std::cout << render_status(w) << "\n\n"
              << render_frame(w) << "\n"
              << render_inventory(w) << "\n"
              << "Controls: wasd move, f attack, e enter door, b defeat-boss, i inv, s save, l load, q quit\n";
    if (!msg.text.empty()) {
        std::cout << "> " << msg.text << "\n";
    }
    std::cout.flush();
}

void show_inventory(const World& w) {
    clear_screen();
    std::cout << "=== Inventory ===\n\n" << render_inventory(w) << "\n"
              << "Press any key to return.\n";
    read_key();
}

bool handle_boss_defeat(World& w, FrameMessage& msg) {
    // Defeat whichever boss corresponds to the current stage when the player
    // types 'b' — a cheat-ish fast-path so the terminal port can exercise the
    // full campaign arc without grinding.
    std::string boss_id;
    switch (w.campaign().world_stage()) {
        case 1: boss_id = "dark_golem"; break;
        case 2: boss_id = "gravewarden"; break;
        case 3: boss_id = "mythic_sovereign"; break;
        default: boss_id = "dark_golem";
    }
    const auto adv = w.defeat_boss(boss_id);
    w.player().set_form(w.campaign().current_form());
    if (adv.has_value()) {
        std::ostringstream s;
        s << "Boss " << boss_id << " defeated. Stage " << *adv << " unlocked.";
        msg.text = s.str();
    } else {
        msg.text = "Final boss defeated! Campaign complete.";
    }
    return w.campaign().is_final_stage_complete();
}

int game_loop(World& w) {
    FrameMessage msg;
    while (true) {
        render_game(w, msg);
        msg.text.clear();

        int key = read_key();
        if (key < 0) return 0;
        key = std::tolower(key);

        if (key == 'q') {
            return 0;
        }
        if (key == 'i') {
            show_inventory(w);
            continue;
        }
        if (key == 's') {
            const bool ok = save_to_file(snapshot(w), SAVE_PATH);
            msg.text = ok ? "Saved." : "Save failed.";
            continue;
        }
        if (key == 'l') {
            const auto r = load_from_file(SAVE_PATH);
            if (r.has_value()) {
                apply_snapshot(w, r.value());
                msg.text = "Loaded.";
            } else {
                msg.text = "No save found.";
            }
            continue;
        }
        if (key == 'f') {
            const auto res = w.player_attack_front(next_roll_0_99());
            if (res.damage_dealt == 0) {
                msg.text = "Nothing there.";
            } else {
                std::ostringstream s;
                s << "Hit for " << res.damage_dealt;
                if (res.enemy_killed) {
                    s << " [KILL] +" << res.xp_gained << " xp, +" << res.coins_gained << " coins";
                    if (!res.loot_id.empty()) s << ", loot: " << res.loot_id;
                }
                msg.text = s.str();
            }
            const int dmg_taken = w.run_enemy_turn();
            if (dmg_taken > 0) {
                msg.text += "  (enemies hit you for " + std::to_string(dmg_taken) + ")";
            }
            if (!w.player().is_alive()) {
                render_game(w, msg);
                std::cout << "\nYou died. Press any key.\n";
                read_key();
                return 1;
            }
            continue;
        }
        if (key == 'b') {
            if (handle_boss_defeat(w, msg)) {
                render_game(w, msg);
                std::cout << "\n*** VICTORY! Press any key. ***\n";
                read_key();
                return 0;
            }
            continue;
        }
        if (key == 'e') {
            // Try to enter whatever door the player is standing on.
            const auto tile = w.tilemap().at(w.player().x(), w.player().y());
            if (tile != TileKind::Door && tile != TileKind::HouseDoor) {
                msg.text = "No door here.";
                continue;
            }
            // Map-specific door routing.
            std::string target;
            if (w.current_map() == "village") target = "dungeon";
            else if (w.current_map() == "dungeon") target = "village";
            else if (w.current_map() == "ruins_approach") target = "ruins_depths";
            else if (w.current_map() == "ruins_depths") target = "ruins_approach";
            else if (w.current_map() == "sanctum_halls") target = "throne_room";
            else if (w.current_map() == "throne_room") target = "sanctum_halls";
            if (target.empty()) {
                msg.text = "That door leads nowhere yet.";
                continue;
            }
            const auto enter = w.enter_map(target);
            if (!enter.ok) {
                msg.text = "Door is locked (campaign gate).";
            } else {
                msg.text = "Entered " + target + ".";
            }
            continue;
        }

        const Direction d = key_to_dir(key);
        if (d != Direction::None) {
            const auto outcome = w.move_player(d);
            switch (outcome) {
                case StepOutcome::Moved:        break;
                case StepOutcome::Blocked:      msg.text = "Blocked."; break;
                case StepOutcome::MapLocked:    msg.text = "Map locked."; break;
                case StepOutcome::BumpedEnemy:  msg.text = "Enemy in the way. Press f to attack."; break;
                case StepOutcome::ReachedExit:  msg.text = "On a door. Press e to use it."; break;
            }
            w.run_enemy_turn();
            if (!w.player().is_alive()) {
                render_game(w, msg);
                std::cout << "\nYou died. Press any key.\n";
                read_key();
                return 1;
            }
            continue;
        }

        msg.text = "Unknown key.";
    }
}

}  // namespace

int main(int argc, char** argv) {
    (void)argc; (void)argv;
    while (true) {
        clear_screen();
        print_title();
        int key = read_key();
        if (key < 0) return 0;
        key = std::tolower(key);
        if (key == 'q') return 0;

        World w;
        // Give the player a starting loadout so early combat is possible.
        w.player().inventory().add("old_sword", 1);
        w.player().inventory().equip("old_sword");
        w.player().inventory().add("health_potion", 3);

        if (key == 'c') {
            const auto r = load_from_file(SAVE_PATH);
            if (r.has_value()) apply_snapshot(w, r.value());
        }

        if (game_loop(w) != 0) {
            clear_screen();
            std::cout << "Game over. Press any key to return to title.\n";
            read_key();
        }
    }
}
