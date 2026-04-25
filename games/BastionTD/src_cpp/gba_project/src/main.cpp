// Butano entry point for BastionTD. The game state/update/render flow is the
// same C++ state layer used by the SDL build; this file only adapts the HAL to
// GBA hardware.

#include "bn_bg_palettes.h"
#include "bn_bg_tiles.h"
#include "bn_colors.h"
#include "bn_core.h"
#include "bn_fixed.h"
#include "bn_keypad.h"
#include "bn_optional.h"
#include "bn_regular_bg_item.h"
#include "bn_regular_bg_map_cell_info.h"
#include "bn_regular_bg_map_ptr.h"
#include "bn_regular_bg_ptr.h"
#include "bn_sprite_items_characters.h"
#include "bn_sprite_items_cursor.h"
#include "bn_sprite_items_effects.h"
#include "bn_sprite_items_outline.h"
#include "bn_sprite_items_projectile.h"
#include "bn_sprite_items_props.h"
#include "bn_sprite_items_range_dot.h"
#include "bn_sprite_items_terrain.h"
#include "bn_sprite_items_towers.h"

#include "bn_sound.h"
#include "bn_sound_items.h"
#include "bn_affine_mat_attributes.h"
#include "bn_sprite_affine_mat_ptr.h"
#include "bn_sprite_ptr.h"
#include "bn_sprite_text_generator.h"
#include "bn_vector.h"
#include "common_fixed_8x8_sprite_font.h"

#include "core/config.h"
#include "hal/hal.h"
#include "states/game_over_state.h"
#include "states/gameplay_state.h"
#include "states/instructions_state.h"
#include "states/pause_state.h"
#include "states/settings_state.h"
#include "states/state.h"
#include "states/title_state.h"
#include "states/victory_state.h"

#include <cstring>

namespace {

#define BASTION_EWRAM_DATA __attribute__((section(".ewram")))

constexpr int kScreenCenterX = 120;
constexpr int kScreenCenterY = 80;
constexpr int kSpriteHardwareLimit = 128;
constexpr int kSpriteSafetyMargin = 4;
constexpr int kSpriteBudget = kSpriteHardwareLimit - kSpriteSafetyMargin;
constexpr int kObjectSpriteCapacity = 124;
constexpr int kTextSpriteCapacity = 124;

constexpr int kBgMapColumns = 32;
constexpr int kBgMapRows = 32;
constexpr int kScreenMapX = 1;
constexpr int kScreenMapY = 6;
constexpr int kBlankTerrainTile = 0;
constexpr int kFirstTerrainTile = 1;
constexpr int kTerrainTileCount = 9;

int gba_x_from_left(int x, int width) {
    return x + width / 2 - kScreenCenterX;
}

int gba_y_from_top(int y, int height) {
    return y + height / 2 - kScreenCenterY;
}

int text_x_from_left(int x) {
    return x - kScreenCenterX;
}

int text_y_from_top(int y) {
    return y - kScreenCenterY;
}

bn::color to_bn_color(Color color) {
    return bn::color(color.r >> 3, color.g >> 3, color.b >> 3);
}

bool terrain_tile_index(SpriteId id, int& tile_index) {
    switch (id) {
    case SpriteId::TileGrass:
        tile_index = kFirstTerrainTile + 0;
        return true;
    case SpriteId::TileGrassAlt:
        tile_index = kFirstTerrainTile + 1;
        return true;
    case SpriteId::TilePath:
        tile_index = kFirstTerrainTile + 2;
        return true;
    case SpriteId::TilePathAlt:
        tile_index = kFirstTerrainTile + 3;
        return true;
    case SpriteId::TileWater:
        tile_index = kFirstTerrainTile + 4;
        return true;
    case SpriteId::TileSpawn:
        tile_index = kFirstTerrainTile + 5;
        return true;
    case SpriteId::TileBase:
        tile_index = kFirstTerrainTile + 6;
        return true;
    case SpriteId::TileTowerBase:
        tile_index = kFirstTerrainTile + 7;
        return true;
    default:
        return false;
    }
}

bool character_frame(SpriteId id, int& frame) {
    switch (id) {
    case SpriteId::Char0:
        frame = 0;
        return true;
    case SpriteId::Char1:
        frame = 1;
        return true;
    case SpriteId::Char2:
        frame = 2;
        return true;
    case SpriteId::Char3:
        frame = 3;
        return true;
    case SpriteId::Char4:
        frame = 4;
        return true;
    default:
        return false;
    }
}

bool prop_frame(SpriteId id, int& frame) {
    switch (id) {
    case SpriteId::PropTreeLarge:
        frame = 0;
        return true;
    case SpriteId::PropTreeSmall:
        frame = 1;
        return true;
    case SpriteId::PropBush:
        frame = 2;
        return true;
    case SpriteId::PropRockLarge:
        frame = 3;
        return true;
    case SpriteId::PropRockSmall:
        frame = 4;
        return true;
    case SpriteId::PropLog:
        frame = 5;
        return true;
    default:
        return false;
    }
}

bool tower_frame(SpriteId id, int& frame) {
    switch (id) {
    case SpriteId::TowerArrow1:
        frame = 0;
        return true;
    case SpriteId::TowerArrow2:
        frame = 1;
        return true;
    case SpriteId::TowerArrow3:
        frame = 2;
        return true;
    case SpriteId::TowerCannon1:
    case SpriteId::TowerLightning1:
        frame = 3;
        return true;
    case SpriteId::TowerCannon2:
    case SpriteId::TowerLightning2:
        frame = 4;
        return true;
    case SpriteId::TowerCannon3:
    case SpriteId::TowerLightning3:
        frame = 5;
        return true;
    case SpriteId::TowerIce1:
    case SpriteId::TowerFlame1:
        frame = 6;
        return true;
    case SpriteId::TowerIce2:
    case SpriteId::TowerFlame2:
        frame = 7;
        return true;
    case SpriteId::TowerIce3:
    case SpriteId::TowerFlame3:
        frame = 8;
        return true;
    default:
        return false;
    }
}

struct TerrainLayer {
    alignas(int) bn::regular_bg_map_cell cells[kBgMapColumns * kBgMapRows];
    alignas(int) bn::tile tiles[kTerrainTileCount];
    bn::optional<bn::regular_bg_ptr> bg;

    TerrainLayer() {
        init_tiles();
        reset_cells();
    }

    void init_tiles() {
        for (auto& word : tiles[kBlankTerrainTile].data) {
            word = 0;
        }

        for (int index = 0; index < 8; ++index) {
            tiles[kFirstTerrainTile + index] = terrain_bn_gfxTiles[index];
        }
    }

    void reset_cells() {
        for (auto& cell : cells) {
            bn::regular_bg_map_cell_info cell_info;
            cell_info.set_tile_index(kBlankTerrainTile);
            cell = cell_info.cell();
        }
    }

    void set_tile_from_screen(int x, int y, int tile_index) {
        const int map_x = (x / cfg::TILE_SIZE) + kScreenMapX;
        const int map_y = (y / cfg::TILE_SIZE) + kScreenMapY;
        if (map_x < 0 || map_x >= kBgMapColumns || map_y < 0 || map_y >= kBgMapRows) {
            return;
        }

        bn::regular_bg_map_cell_info cell_info;
        cell_info.set_tile_index(tile_index);
        cells[map_y * kBgMapColumns + map_x] = cell_info.cell();
    }

    void sync(bool visible) {
        if (! visible) {
            if (bg.has_value()) {
                bg->set_visible(false);
            }
            return;
        }

        if (! bg.has_value()) {
            bn::bg_tiles::set_allow_offset(false);
            bn::regular_bg_item item(
                bn::span<const bn::tile>(tiles, kTerrainTileCount),
                bn::span<const bn::color>(terrain_bn_gfxPal, 16),
                bn::bpp_mode::BPP_4,
                cells[0],
                bn::size(kBgMapColumns, kBgMapRows));
            bg = item.create_bg(0, 0);
            bg->set_priority(3);
            bn::bg_tiles::set_allow_offset(true);
            return;
        }

        bg->set_visible(true);
        bn::regular_bg_map_ptr map = bg->map();
        map.reload_cells_ref();
    }
};

class GbaRenderer : public IRenderer {
public:
    GbaRenderer() :
        text_generator(common::fixed_8x8_sprite_font) {
        text_generator.set_bg_priority(0);
        text_generator.set_z_order(-100);
    }

    void clear(Color color) override {
        bn::bg_palettes::set_transparent_color(to_bn_color(color));
        objects.clear();
        text_sprites.clear();
        terrain.reset_cells();
        terrain_visible = false;
        sprites_reserved = 0;
        boss_bar_pending = false;
    }

    void draw_rect(int x, int y, int w, int h, Color color) override {
        // 2x2 projectile square (kept for legacy paths).
        if (w == 2 && h == 2) {
            push_projectile(x + 1, y + 1);
            return;
        }

        // 1x1 particle — pick palette variant based on dominant channel.
        if (w == 1 && h == 1) {
            push_particle(x, y, color);
            return;
        }

        // Enemy HP bar: 8-wide, 1-tall. BG pass is absorbed by the fg frame,
        // which embeds the dark-red strip plus N green pixels.
        if (h == 1 && w >= 0 && w <= 8) {
            const bool is_bg = color.r <= 120 && color.g <= 60 && color.b <= 60;
            if (is_bg) {
                // BG is encoded in fg frames — skip to avoid double draw.
                return;
            }
            push_hp_bar(x, y, w);
            return;
        }

        // Boss HP bar: 3-tall strip >=16 wide. Cache bg call, emit both on fg.
        if (h == 3 && w >= 16) {
            const bool is_bg = color.r <= 120 && color.g <= 60 && color.b <= 60;
            if (is_bg) {
                boss_bar_pending = true;
                boss_bar_x = x;
                boss_bar_y = y;
                boss_bar_w = w;
                return;
            }
            emit_boss_bar(x, y, w);
            return;
        }

        // Slow-effect marker behind an enemy sprite.
        if (w == 6 && h == 6) {
            push_effect_frame(/*frame=*/12, x, y, 8, 8);
            return;
        }

        // Tower level pips (1x1 WHITE at tower bottom). Skip to save sprites —
        // tower sprite frames change per level already.
        // Tower tray item box (10x10), HUD backdrop, notification box —
        // rendered as colored 8x8 stamps if budget allows.
        if (w == 10 && h == 10) {
            push_tray_box(x, y, color);
            return;
        }
    }

    void draw_rect_outline(int x, int y, int w, int h, Color color) override {
        // Build-cursor outline (tile-sized, translucent).
        if (w == cfg::TILE_SIZE && h == cfg::TILE_SIZE && color.a < 255) {
            push_cursor(x, y);
            return;
        }

        // Thin rect outlines (spawn/base tile marks, tray selection, notification).
        // Composed from 4 edge sprites scaled to the rect dimensions.
        emit_rect_outline(x, y, w, h);
    }

    void draw_sprite(SpriteId id, int x, int y, float scale = 1.0f, bool flip_h = false) override {
        int size = static_cast<int>(8.0f * scale);
        if (size < 1) {
            size = 1;
        }
        draw_sprite_rect(id, x, y, size, size, flip_h);
    }

    void draw_sprite_rect(SpriteId id, int x, int y, int w, int h, bool flip_h = false) override {
        (void) flip_h;

        int frame = 0;
        if (terrain_tile_index(id, frame)) {
            terrain.set_tile_from_screen(x, y, frame);
            terrain_visible = true;
            return;
        }

        // Characters, towers and props are authored as 16x16 in their sheets.
        // Shared render code asks for render sizes like 8x8 (characters) or
        // 10x12 (props), so scale = requested / native (16) — never 1.0 for
        // character calls or the knight renders at 2x and overlaps the tower.
        if (character_frame(id, frame)) {
            const bn::fixed scale = bn::fixed(w) / 16;
            push_sprite(bn::sprite_items::characters, frame,
                        gba_x_from_left(x, w), gba_y_from_top(y, h), scale);
            return;
        }

        if (tower_frame(id, frame)) {
            const bn::fixed scale = bn::fixed(w) / 16;
            push_sprite(bn::sprite_items::towers, frame,
                        gba_x_from_left(x, w), gba_y_from_top(y, h), scale);
            return;
        }

        if (prop_frame(id, frame)) {
            const bn::fixed scale = bn::fixed(w) / 16;
            push_sprite(bn::sprite_items::props, frame,
                        gba_x_from_left(x, w), gba_y_from_top(y, h), scale);
        }
    }

    void draw_text(const char* str, int x, int y, Color color = {240, 235, 220, 255}) override {
        (void) color;

        if (str == nullptr || *str == '\0') {
            return;
        }

        const int available = kSpriteBudget - sprites_reserved;
        if (available <= 0) {
            return;
        }

        char truncated[64];
        int copied = 0;
        while (str[copied] != '\0' && copied < available && copied < int(sizeof(truncated)) - 1) {
            truncated[copied] = str[copied];
            ++copied;
        }
        truncated[copied] = '\0';
        if (copied == 0) {
            return;
        }

        sprites_reserved += copied;
        text_generator.generate(text_x_from_left(x), text_y_from_top(y), truncated, text_sprites);
    }

    void draw_circle(int cx, int cy, int r, Color color) override {
        (void) color;
        // Emit up to 16 dot sprites on the circumference as a range preview.
        // Heavier radii use more dots; small radii skip to keep sprite count down.
        if (r < 6) {
            return;
        }
        constexpr int kDots = 16;
        // cos/sin table (16 entries, values in units of 256).
        static const int kCos[kDots] = { 256,  236,  181,   97,    0,  -97, -181, -236,
                                        -256, -236, -181,  -97,    0,   97,  181,  236 };
        static const int kSin[kDots] = {   0,   97,  181,  236,  256,  236,  181,   97,
                                           0,  -97, -181, -236, -256, -236, -181,  -97 };
        for (int i = 0; i < kDots; ++i) {
            const int dx = (kCos[i] * r) / 256;
            const int dy = (kSin[i] * r) / 256;
            push_range_dot(cx + dx, cy + dy);
        }
    }

    void draw_line(int /*x1*/, int /*y1*/, int /*x2*/, int /*y2*/, Color /*color*/) override {
        // Only called in non-sprite fallback; unused on GBA (use_sprites=true).
    }

    void present() override {
        // If the shared code issued a boss bar bg without matching fg, still emit it.
        if (boss_bar_pending) {
            // No fg — fill the whole bar with bg tiles.
            const int tiles = boss_bar_w / 8;
            for (int i = 0; i < tiles; ++i) {
                push_effect_frame(/*frame=*/9, boss_bar_x + i * 8, boss_bar_y, 8, 8);
            }
            boss_bar_pending = false;
        }
        terrain.sync(terrain_visible);
    }

    int screen_w() const override {
        return cfg::SCREEN_W;
    }

    int screen_h() const override {
        return cfg::SCREEN_H;
    }

private:
    TerrainLayer terrain;
    bn::sprite_text_generator text_generator;
    bn::vector<bn::sprite_ptr, kObjectSpriteCapacity> objects;
    bn::vector<bn::sprite_ptr, kTextSpriteCapacity> text_sprites;
    bool terrain_visible = false;
    int sprites_reserved = 0;

    // Boss-bar pairing: the shared renderer issues bg rect then fg rect. We
    // cache the bg so we can draw only the empty-right portion as bg after
    // seeing the fg fill width.
    bool boss_bar_pending = false;
    int boss_bar_x = 0;
    int boss_bar_y = 0;
    int boss_bar_w = 0;

    bool reserve_sprite(int count = 1) {
        if (sprites_reserved + count > kSpriteBudget) {
            return false;
        }

        sprites_reserved += count;
        return true;
    }

    void release_sprite_reservation() {
        if (sprites_reserved > 0) {
            --sprites_reserved;
        }
    }

    // Shared affine-matrix pool. Each unique scale value allocates at most one
    // matrix, reused across all sprites at that scale for the rest of the run.
    // GBA hardware exposes only 32 affine slots, and per-sprite set_scale()
    // burns one slot each — which exhausts the pool once many enemies/props
    // are on screen. Sharing keeps the usage bounded by the number of distinct
    // scales the game actually uses (~8 in practice).
    static constexpr int kSharedMatPoolSize = 16;
    struct SharedMatEntry {
        bn::fixed scale = bn::fixed(0);
        bn::optional<bn::sprite_affine_mat_ptr> mat;
    };
    SharedMatEntry shared_mats[kSharedMatPoolSize];

    bn::optional<bn::sprite_affine_mat_ptr> get_shared_mat(bn::fixed scale) {
        for (auto& s : shared_mats) {
            if (s.mat.has_value() && s.scale == scale) {
                return s.mat;
            }
        }
        for (auto& s : shared_mats) {
            if (! s.mat.has_value()) {
                bn::affine_mat_attributes attrs;
                attrs.set_scale(scale);
                bn::optional<bn::sprite_affine_mat_ptr> made =
                    bn::sprite_affine_mat_ptr::create_optional(attrs);
                if (! made.has_value()) {
                    return bn::optional<bn::sprite_affine_mat_ptr>();
                }
                s.scale = scale;
                s.mat = bn::move(made);
                return s.mat;
            }
        }
        // Pool full: reuse slot 0 for the new scale (worst-case scale that
        // hasn't been seen all run).
        bn::affine_mat_attributes attrs;
        attrs.set_scale(scale);
        bn::optional<bn::sprite_affine_mat_ptr> made =
            bn::sprite_affine_mat_ptr::create_optional(attrs);
        if (! made.has_value()) {
            return bn::optional<bn::sprite_affine_mat_ptr>();
        }
        shared_mats[0].scale = scale;
        shared_mats[0].mat = bn::move(made);
        return shared_mats[0].mat;
    }

    void push_sprite(const bn::sprite_item& item, int frame, int x, int y, bn::fixed scale) {
        if (! reserve_sprite() || objects.full()) {
            release_sprite_reservation();
            return;
        }

        bn::optional<bn::sprite_ptr> sprite = item.create_sprite_optional(x, y, frame);
        if (! sprite.has_value()) {
            release_sprite_reservation();
            return;
        }

        if (scale != bn::fixed(1)) {
            bn::optional<bn::sprite_affine_mat_ptr> mat = get_shared_mat(scale);
            if (mat.has_value()) {
                sprite->set_affine_mat(*mat);
            }
        }
        objects.push_back(bn::move(*sprite));
    }

    void push_projectile(int center_x, int center_y) {
        if (! reserve_sprite() || objects.full()) {
            release_sprite_reservation();
            return;
        }

        bn::optional<bn::sprite_ptr> sprite = bn::sprite_items::projectile.create_sprite_optional(
            center_x - kScreenCenterX, center_y - kScreenCenterY);
        if (! sprite.has_value()) {
            release_sprite_reservation();
            return;
        }

        objects.push_back(bn::move(*sprite));
    }

    void push_cursor(int x, int y) {
        if (! reserve_sprite() || objects.full()) {
            release_sprite_reservation();
            return;
        }

        bn::optional<bn::sprite_ptr> sprite = bn::sprite_items::cursor.create_sprite_optional(
            gba_x_from_left(x, cfg::TILE_SIZE), gba_y_from_top(y, cfg::TILE_SIZE));
        if (! sprite.has_value()) {
            release_sprite_reservation();
            return;
        }

        objects.push_back(bn::move(*sprite));
    }

    // Draw an 8x8 frame from the effects sprite sheet at shared-screen (x, y).
    void push_effect_frame(int frame, int x, int y, int w, int h) {
        push_sprite(bn::sprite_items::effects, frame,
                    gba_x_from_left(x, w), gba_y_from_top(y, h), bn::fixed(1));
    }

    // Pick a particle palette variant by dominant color channel.
    void push_particle(int x, int y, Color color) {
        int frame = 13; // white default
        if (color.r > 150 && color.g > 150 && color.b < 100) {
            frame = 14; // gold-ish
        } else if (color.r > 150 && color.g < 120) {
            frame = 15; // red
        }
        push_effect_frame(frame, x, y, 8, 8);
    }

    // Enemy HP bar: fg frame N shows dark-red bg row + N green pixels overlay.
    void push_hp_bar(int x, int y, int fill_w) {
        if (fill_w < 0) {
            fill_w = 0;
        }
        if (fill_w > 8) {
            fill_w = 8;
        }
        // Centre the 8x8 sprite so its top row coincides with the 8x1 bar row.
        push_effect_frame(fill_w, x, y, 8, 8);
    }

    // Boss bar fg arrives after bg was cached. Emit fg tiles for the filled
    // portion and bg tiles for the remaining right portion.
    void emit_boss_bar(int fg_x, int fg_y, int fg_w) {
        if (! boss_bar_pending) {
            // Unexpected order; treat fg as standalone fill.
            boss_bar_x = fg_x;
            boss_bar_y = fg_y;
            boss_bar_w = fg_w;
        }
        const int total_tiles = boss_bar_w / 8;
        int fg_tiles = fg_w / 8;
        if (fg_tiles > total_tiles) {
            fg_tiles = total_tiles;
        }
        if (fg_tiles < 0) {
            fg_tiles = 0;
        }
        for (int i = 0; i < fg_tiles; ++i) {
            // Frame 10: boss-bar fg strip 8x3.
            push_effect_frame(10, boss_bar_x + i * 8, boss_bar_y, 8, 8);
        }
        for (int i = fg_tiles; i < total_tiles; ++i) {
            // Frame 9: boss-bar bg strip 8x3.
            push_effect_frame(9, boss_bar_x + i * 8, boss_bar_y, 8, 8);
        }
        boss_bar_pending = false;
    }

    // Small 10x10 tower-tray box: stamp a particle-tile as a 1-pixel marker
    // hint. Keeps the tray readable without burning sprites on a full box.
    void push_tray_box(int x, int y, Color /*color*/) {
        // Use the white particle frame as a decorative pip in the tray box.
        push_effect_frame(13, x + 1, y + 1, 8, 8);
    }

    void push_range_dot(int cx, int cy) {
        push_sprite(bn::sprite_items::range_dot, 0,
                    gba_x_from_left(cx - 4, 8), gba_y_from_top(cy - 4, 8), bn::fixed(1));
    }

    void emit_rect_outline(int x, int y, int w, int h) {
        // Budget guard: skip if rect is tiny or too large (outline readability
        // is marginal in either case).
        if (w < 8 || h < 8 || w > 200 || h > 96) {
            return;
        }
        // Top and bottom edges: tile 8x8 "top edge" and "bottom edge" sprites
        // across the width. Left/right edges: tile vertical edge sprites across
        // the height.
        const int edges_x = (w + 7) / 8;
        const int edges_y = (h + 7) / 8;
        // Top (frame 0)
        for (int i = 0; i < edges_x; ++i) {
            push_sprite(bn::sprite_items::outline, 0,
                        gba_x_from_left(x + i * 8, 8),
                        gba_y_from_top(y, 8), bn::fixed(1));
        }
        // Bottom (frame 1)
        for (int i = 0; i < edges_x; ++i) {
            push_sprite(bn::sprite_items::outline, 1,
                        gba_x_from_left(x + i * 8, 8),
                        gba_y_from_top(y + h - 8, 8), bn::fixed(1));
        }
        // Left/right: skip for short rects to save sprites, main visual cue
        // comes from top/bottom strokes.
        if (h >= 16) {
            for (int i = 1; i < edges_y - 1; ++i) {
                push_sprite(bn::sprite_items::outline, 2,
                            gba_x_from_left(x, 8),
                            gba_y_from_top(y + i * 8, 8), bn::fixed(1));
                push_sprite(bn::sprite_items::outline, 3,
                            gba_x_from_left(x + w - 8, 8),
                            gba_y_from_top(y + i * 8, 8), bn::fixed(1));
            }
        }
    }
};

class GbaInput : public IInput {
public:
    void update() override {
        set(InputButton::Up, bn::keypad::up_pressed(), bn::keypad::up_held());
        set(InputButton::Down, bn::keypad::down_pressed(), bn::keypad::down_held());
        set(InputButton::Left, bn::keypad::left_pressed(), bn::keypad::left_held());
        set(InputButton::Right, bn::keypad::right_pressed(), bn::keypad::right_held());
        set(InputButton::A, bn::keypad::a_pressed(), bn::keypad::a_held());
        set(InputButton::B, bn::keypad::b_pressed(), bn::keypad::b_held());
        set(InputButton::L, bn::keypad::l_pressed(), bn::keypad::l_held());
        set(InputButton::R, bn::keypad::r_pressed(), bn::keypad::r_held());
        set(InputButton::Start, bn::keypad::start_pressed(), bn::keypad::start_held());
        set(InputButton::Select, bn::keypad::select_pressed(), bn::keypad::select_held());
        set(InputButton::FastForward, bn::keypad::r_pressed(), bn::keypad::r_held());
        set(InputButton::FleetUpgrade,
            bn::keypad::l_held() && bn::keypad::r_pressed(),
            bn::keypad::l_held() && bn::keypad::r_held());
    }

    bool pressed(InputButton button) const override {
        return pressed_buttons[static_cast<int>(button)];
    }

    bool held(InputButton button) const override {
        return held_buttons[static_cast<int>(button)];
    }

    bool released(InputButton button) const override {
        return released_buttons[static_cast<int>(button)];
    }

    bool quit_requested() const override {
        return false;
    }

    float held_duration(InputButton button) const override {
        return static_cast<float>(held_frames[static_cast<int>(button)]) * cfg::SIM_DT;
    }

private:
    bool pressed_buttons[static_cast<int>(InputButton::COUNT)] = {};
    bool held_buttons[static_cast<int>(InputButton::COUNT)] = {};
    bool released_buttons[static_cast<int>(InputButton::COUNT)] = {};
    bool previous_held[static_cast<int>(InputButton::COUNT)] = {};
    int held_frames[static_cast<int>(InputButton::COUNT)] = {};

    void set(InputButton button, bool is_pressed, bool is_held) {
        const int index = static_cast<int>(button);
        pressed_buttons[index] = is_pressed;
        held_buttons[index] = is_held;
        released_buttons[index] = previous_held[index] && ! is_held;
        held_frames[index] = is_held ? (previous_held[index] ? held_frames[index] + 1 : 1) : 0;
        previous_held[index] = is_held;
    }
};

class GbaAudio : public IAudio {
public:
    void play_sfx(SfxId id) override {
        if (sfx_volume <= bn::fixed(0)) {
            return;
        }
        const bn::sound_item* item = sfx_item(id);
        if (item != nullptr) {
            bn::sound::play(*item, sfx_volume);
        }
    }

    void play_bgm(BgmId id) override {
        if (current_bgm == id && bgm_frames_remaining > 0) {
            return; // already playing this track
        }
        stop_bgm();
        current_bgm = id;
        restart_bgm();
    }

    void stop_bgm() override {
        current_bgm = BgmId::COUNT;
        bgm_frames_remaining = 0;
        bn::sound::stop_all();
    }

    void set_sfx_volume(float volume) override {
        sfx_volume = bn::fixed(volume);
        if (sfx_volume > bn::fixed(1)) {
            sfx_volume = bn::fixed(1);
        }
        if (sfx_volume < bn::fixed(0)) {
            sfx_volume = bn::fixed(0);
        }
    }

    void set_bgm_volume(float volume) override {
        bgm_volume = bn::fixed(volume);
        if (bgm_volume > bn::fixed(1)) {
            bgm_volume = bn::fixed(1);
        }
        if (bgm_volume < bn::fixed(0)) {
            bgm_volume = bn::fixed(0);
        }
    }

    void tick() override {
        if (current_bgm == BgmId::COUNT) {
            return;
        }
        if (bgm_frames_remaining > 0) {
            --bgm_frames_remaining;
        }
        if (bgm_frames_remaining == 0) {
            restart_bgm();
        }
    }

private:
    bn::fixed sfx_volume = bn::fixed(1);
    bn::fixed bgm_volume = bn::fixed(1);
    BgmId current_bgm = BgmId::COUNT;
    int bgm_frames_remaining = 0;

    static const bn::sound_item* sfx_item(SfxId id) {
        switch (id) {
        case SfxId::Place:       return &bn::sound_items::place;
        case SfxId::Shoot:       return &bn::sound_items::shoot;
        case SfxId::Hit:         return &bn::sound_items::hit;
        case SfxId::EnemyDeath:  return &bn::sound_items::enemy_death;
        case SfxId::WaveStart:   return &bn::sound_items::wave_start;
        case SfxId::WaveClear:   return &bn::sound_items::wave_clear;
        case SfxId::BossSpawn:   return &bn::sound_items::boss_spawn;
        case SfxId::BaseHit:     return &bn::sound_items::base_hit;
        case SfxId::Upgrade:     return &bn::sound_items::upgrade;
        case SfxId::Sell:        return &bn::sound_items::sell;
        case SfxId::MenuMove:    return &bn::sound_items::menu_move;
        case SfxId::MenuSelect:  return &bn::sound_items::menu_select;
        case SfxId::GameOver:    return &bn::sound_items::game_over;
        case SfxId::Victory:     return &bn::sound_items::victory;
        default:                 return nullptr;
        }
    }

    static const bn::sound_item* bgm_item(BgmId id) {
        switch (id) {
        case BgmId::Title: return &bn::sound_items::bgm_title;
        case BgmId::Build: return &bn::sound_items::bgm_build;
        case BgmId::Wave:  return &bn::sound_items::bgm_wave;
        case BgmId::Boss:  return &bn::sound_items::bgm_boss;
        default:           return nullptr;
        }
    }

    static int bgm_duration_frames(BgmId id) {
        // Matches gen_audio.py note counts * note duration * 60 fps.
        switch (id) {
        case BgmId::Title: return 180; // 6 notes * 0.5s
        case BgmId::Build: return 150; // 8 notes * 0.3125s
        case BgmId::Wave:  return 150; // 8 notes * 0.3125s
        case BgmId::Boss:  return 120; // 8 notes * 0.25s
        default:           return 0;
        }
    }

    void restart_bgm() {
        const bn::sound_item* item = bgm_item(current_bgm);
        if (item == nullptr) {
            bgm_frames_remaining = 0;
            return;
        }
        bn::sound::play(*item, bgm_volume);
        bgm_frames_remaining = bgm_duration_frames(current_bgm);
    }
};

} // namespace

void App::change_state(StateId id) {
    previous_id = current_id;
    if (current_state != nullptr) {
        current_state->exit(*this);
    }
    current_id = id;
    current_state = states[static_cast<int>(id)];
    if (current_state != nullptr) {
        current_state->enter(*this);
    }
}

int main() {
    bn::core::init();
    bn::bg_palettes::set_transparent_color(bn::color(2, 6, 2));

    static GbaRenderer renderer BASTION_EWRAM_DATA;
    static GbaInput input BASTION_EWRAM_DATA;
    static GbaAudio audio BASTION_EWRAM_DATA;
    static App app BASTION_EWRAM_DATA;

    static TitleState title_state BASTION_EWRAM_DATA;
    static GameplayState gameplay_state BASTION_EWRAM_DATA;
    static PauseState pause_state BASTION_EWRAM_DATA;
    static GameOverState game_over_state BASTION_EWRAM_DATA;
    static VictoryState victory_state BASTION_EWRAM_DATA;
    static InstructionsState instructions_state BASTION_EWRAM_DATA;
    static SettingsState settings_state BASTION_EWRAM_DATA;

    app.renderer = &renderer;
    app.input = &input;
    app.audio = &audio;
    app.states[static_cast<int>(StateId::Title)] = &title_state;
    app.states[static_cast<int>(StateId::Gameplay)] = &gameplay_state;
    app.states[static_cast<int>(StateId::Pause)] = &pause_state;
    app.states[static_cast<int>(StateId::GameOver)] = &game_over_state;
    app.states[static_cast<int>(StateId::Victory)] = &victory_state;
    app.states[static_cast<int>(StateId::Instructions)] = &instructions_state;
    app.states[static_cast<int>(StateId::Settings)] = &settings_state;

    const SaveData saved = app.save_mgr.load();
    app.best_wave = saved.best_wave;
    app.best_score = saved.best_score;
    app.games_played = saved.games_played;

    app.current_id = StateId::Title;
    app.previous_id = StateId::Title;
    app.current_state = nullptr;
    app.change_state(StateId::Title);

    while (app.running) {
        input.update();
        audio.tick();
        if (app.current_state != nullptr) {
            app.current_state->update(app, cfg::SIM_DT);
        }
        if (app.current_state != nullptr) {
            app.current_state->render(app, 1.0f);
            renderer.present();
        }
        bn::core::update();
    }

    while (true) {
        bn::core::update();
    }
}
