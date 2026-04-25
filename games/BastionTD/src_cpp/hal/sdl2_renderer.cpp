#include "hal/sdl2_renderer.h"

#include "core/config.h"

#include <algorithm>
#include <cstdint>
#include <fstream>

namespace {

void renderer_log(const char* message) {
    std::ofstream out("bastion_startup.log", std::ios::app);
    if (out.is_open()) {
        out << message << '\n';
    }
}

// 5x7 pixel font. One row per uint8, bits 0..4 = columns left→right (LSB = col 0).
// Covers A-Z, 0-9, and common punctuation. Missing glyphs fall back to blank.
struct Glyph5x7 {
    uint8_t rows[7];
};

const Glyph5x7& glyph_for(char ch) {
    static const Glyph5x7 BLANK = {{0, 0, 0, 0, 0, 0, 0}};
#define G(a, b, c, d, e, f, g) Glyph5x7{{a, b, c, d, e, f, g}}
    if (ch >= 'a' && ch <= 'z') {
        ch = static_cast<char>(ch - 'a' + 'A');
    }
    switch (ch) {
    case 'A': { static const auto g = G(0b01110, 0b10001, 0b10001, 0b11111, 0b10001, 0b10001, 0b10001); return g; }
    case 'B': { static const auto g = G(0b11110, 0b10001, 0b10001, 0b11110, 0b10001, 0b10001, 0b11110); return g; }
    case 'C': { static const auto g = G(0b01111, 0b10000, 0b10000, 0b10000, 0b10000, 0b10000, 0b01111); return g; }
    case 'D': { static const auto g = G(0b11110, 0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b11110); return g; }
    case 'E': { static const auto g = G(0b11111, 0b10000, 0b10000, 0b11110, 0b10000, 0b10000, 0b11111); return g; }
    case 'F': { static const auto g = G(0b11111, 0b10000, 0b10000, 0b11110, 0b10000, 0b10000, 0b10000); return g; }
    case 'G': { static const auto g = G(0b01111, 0b10000, 0b10000, 0b10111, 0b10001, 0b10001, 0b01111); return g; }
    case 'H': { static const auto g = G(0b10001, 0b10001, 0b10001, 0b11111, 0b10001, 0b10001, 0b10001); return g; }
    case 'I': { static const auto g = G(0b11111, 0b00100, 0b00100, 0b00100, 0b00100, 0b00100, 0b11111); return g; }
    case 'J': { static const auto g = G(0b00111, 0b00010, 0b00010, 0b00010, 0b00010, 0b10010, 0b01100); return g; }
    case 'K': { static const auto g = G(0b10001, 0b10010, 0b10100, 0b11000, 0b10100, 0b10010, 0b10001); return g; }
    case 'L': { static const auto g = G(0b10000, 0b10000, 0b10000, 0b10000, 0b10000, 0b10000, 0b11111); return g; }
    case 'M': { static const auto g = G(0b10001, 0b11011, 0b10101, 0b10101, 0b10001, 0b10001, 0b10001); return g; }
    case 'N': { static const auto g = G(0b10001, 0b11001, 0b10101, 0b10011, 0b10001, 0b10001, 0b10001); return g; }
    case 'O': { static const auto g = G(0b01110, 0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b01110); return g; }
    case 'P': { static const auto g = G(0b11110, 0b10001, 0b10001, 0b11110, 0b10000, 0b10000, 0b10000); return g; }
    case 'Q': { static const auto g = G(0b01110, 0b10001, 0b10001, 0b10001, 0b10101, 0b10010, 0b01101); return g; }
    case 'R': { static const auto g = G(0b11110, 0b10001, 0b10001, 0b11110, 0b10100, 0b10010, 0b10001); return g; }
    case 'S': { static const auto g = G(0b01111, 0b10000, 0b10000, 0b01110, 0b00001, 0b00001, 0b11110); return g; }
    case 'T': { static const auto g = G(0b11111, 0b00100, 0b00100, 0b00100, 0b00100, 0b00100, 0b00100); return g; }
    case 'U': { static const auto g = G(0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b01110); return g; }
    case 'V': { static const auto g = G(0b10001, 0b10001, 0b10001, 0b10001, 0b10001, 0b01010, 0b00100); return g; }
    case 'W': { static const auto g = G(0b10001, 0b10001, 0b10001, 0b10101, 0b10101, 0b11011, 0b10001); return g; }
    case 'X': { static const auto g = G(0b10001, 0b10001, 0b01010, 0b00100, 0b01010, 0b10001, 0b10001); return g; }
    case 'Y': { static const auto g = G(0b10001, 0b10001, 0b01010, 0b00100, 0b00100, 0b00100, 0b00100); return g; }
    case 'Z': { static const auto g = G(0b11111, 0b00001, 0b00010, 0b00100, 0b01000, 0b10000, 0b11111); return g; }
    case '0': { static const auto g = G(0b01110, 0b10001, 0b10011, 0b10101, 0b11001, 0b10001, 0b01110); return g; }
    case '1': { static const auto g = G(0b00100, 0b01100, 0b00100, 0b00100, 0b00100, 0b00100, 0b01110); return g; }
    case '2': { static const auto g = G(0b01110, 0b10001, 0b00001, 0b00010, 0b00100, 0b01000, 0b11111); return g; }
    case '3': { static const auto g = G(0b11110, 0b00001, 0b00001, 0b01110, 0b00001, 0b00001, 0b11110); return g; }
    case '4': { static const auto g = G(0b00010, 0b00110, 0b01010, 0b10010, 0b11111, 0b00010, 0b00010); return g; }
    case '5': { static const auto g = G(0b11111, 0b10000, 0b11110, 0b00001, 0b00001, 0b10001, 0b01110); return g; }
    case '6': { static const auto g = G(0b00110, 0b01000, 0b10000, 0b11110, 0b10001, 0b10001, 0b01110); return g; }
    case '7': { static const auto g = G(0b11111, 0b00001, 0b00010, 0b00100, 0b01000, 0b01000, 0b01000); return g; }
    case '8': { static const auto g = G(0b01110, 0b10001, 0b10001, 0b01110, 0b10001, 0b10001, 0b01110); return g; }
    case '9': { static const auto g = G(0b01110, 0b10001, 0b10001, 0b01111, 0b00001, 0b00010, 0b01100); return g; }
    case ':': { static const auto g = G(0b00000, 0b00100, 0b00000, 0b00000, 0b00000, 0b00100, 0b00000); return g; }
    case '.': { static const auto g = G(0b00000, 0b00000, 0b00000, 0b00000, 0b00000, 0b00000, 0b00100); return g; }
    case ',': { static const auto g = G(0b00000, 0b00000, 0b00000, 0b00000, 0b00000, 0b00100, 0b01000); return g; }
    case '!': { static const auto g = G(0b00100, 0b00100, 0b00100, 0b00100, 0b00100, 0b00000, 0b00100); return g; }
    case '?': { static const auto g = G(0b01110, 0b10001, 0b00001, 0b00010, 0b00100, 0b00000, 0b00100); return g; }
    case '-': { static const auto g = G(0b00000, 0b00000, 0b00000, 0b01110, 0b00000, 0b00000, 0b00000); return g; }
    case '+': { static const auto g = G(0b00000, 0b00100, 0b00100, 0b11111, 0b00100, 0b00100, 0b00000); return g; }
    case '/': { static const auto g = G(0b00001, 0b00010, 0b00010, 0b00100, 0b01000, 0b01000, 0b10000); return g; }
    case '>': { static const auto g = G(0b00000, 0b01000, 0b00100, 0b00010, 0b00100, 0b01000, 0b00000); return g; }
    case '<': { static const auto g = G(0b00000, 0b00010, 0b00100, 0b01000, 0b00100, 0b00010, 0b00000); return g; }
    case '(': { static const auto g = G(0b00010, 0b00100, 0b01000, 0b01000, 0b01000, 0b00100, 0b00010); return g; }
    case ')': { static const auto g = G(0b01000, 0b00100, 0b00010, 0b00010, 0b00010, 0b00100, 0b01000); return g; }
    case '\'': { static const auto g = G(0b00100, 0b00100, 0b00000, 0b00000, 0b00000, 0b00000, 0b00000); return g; }
    case '"': { static const auto g = G(0b01010, 0b01010, 0b00000, 0b00000, 0b00000, 0b00000, 0b00000); return g; }
    case '%': { static const auto g = G(0b11001, 0b11010, 0b00100, 0b00100, 0b01000, 0b01011, 0b10011); return g; }
    case '*': { static const auto g = G(0b00000, 0b01010, 0b00100, 0b11111, 0b00100, 0b01010, 0b00000); return g; }
    default: return BLANK;
    }
#undef G
}

void set_color(SDL_Renderer* renderer, Color c) {
    SDL_SetRenderDrawBlendMode(renderer, c.a < 255 ? SDL_BLENDMODE_BLEND : SDL_BLENDMODE_NONE);
    SDL_SetRenderDrawColor(renderer, c.r, c.g, c.b, c.a);
}

// Sprite tint overlays for tower variants that share base art (python parity).
bool sprite_tint(SpriteId id, Color& out) {
    switch (id) {
    case SpriteId::TowerLightning1:
    case SpriteId::TowerLightning2:
    case SpriteId::TowerLightning3:
        out = {200, 200, 60, 255};
        return true;
    case SpriteId::TowerFlame1:
    case SpriteId::TowerFlame2:
    case SpriteId::TowerFlame3:
        out = {220, 100, 40, 255};
        return true;
    case SpriteId::TileSpawn:
        out = {200, 50, 50, 200};
        return true;
    case SpriteId::TileBase:
        out = {50, 80, 220, 200};
        return true;
    default:
        return false;
    }
}

void draw_procedural_char(SDL_Renderer* renderer, SpriteId id, int x, int y, int size, int unit) {
    Color main = cfg::colors::MAGENTA;
    Color accent = cfg::colors::WHITE;
    switch (id) {
    case SpriteId::Char0: main = {145, 72, 72, 255};   accent = {230, 215, 215, 255}; break;
    case SpriteId::Char1: main = {155, 130, 70, 255};  accent = {235, 220, 160, 255}; break;
    case SpriteId::Char2: main = {80, 170, 120, 255};  accent = {220, 240, 220, 255}; break;
    case SpriteId::Char3: main = {120, 150, 220, 255}; accent = {225, 235, 255, 255}; break;
    case SpriteId::Char4: main = {210, 185, 90, 255};  accent = {255, 240, 200, 255}; break;
    default:
        set_color(renderer, cfg::colors::MAGENTA);
        SDL_Rect r{x, y, size, size};
        SDL_RenderFillRect(renderer, &r);
        return;
    }
    set_color(renderer, main);
    SDL_Rect body{x + unit, y + unit, size - unit * 2, size - unit * 2};
    SDL_RenderFillRect(renderer, &body);
    set_color(renderer, accent);
    SDL_Rect top{x + unit * 2, y, size - unit * 4, unit * 2};
    SDL_RenderFillRect(renderer, &top);
    SDL_Rect bot{x + unit * 2, y + size - unit * 2, size - unit * 4, unit};
    SDL_RenderFillRect(renderer, &bot);
}

} // namespace

bool SDL2Renderer::init(const char* title, int virtual_w, int virtual_h, int scale) {
    vw = virtual_w;
    vh = virtual_h;

    SDL_SetHint(SDL_HINT_RENDER_SCALE_QUALITY, "0");

    window = SDL_CreateWindow(title, SDL_WINDOWPOS_CENTERED, SDL_WINDOWPOS_CENTERED,
                              virtual_w * scale, virtual_h * scale, SDL_WINDOW_SHOWN);
    if (window == nullptr) {
        renderer_log("window creation failed");
        return false;
    }
    renderer_log("window creation ok");

    const Uint32 renderer_flags[] = {
        SDL_RENDERER_ACCELERATED | SDL_RENDERER_PRESENTVSYNC,
        SDL_RENDERER_ACCELERATED,
        SDL_RENDERER_SOFTWARE,
    };

    for (Uint32 flags : renderer_flags) {
        sdl_renderer = SDL_CreateRenderer(window, -1, flags);
        if (sdl_renderer != nullptr) {
            if (flags == (SDL_RENDERER_ACCELERATED | SDL_RENDERER_PRESENTVSYNC)) {
                renderer_log("renderer mode: accelerated+vsync");
            } else if (flags == SDL_RENDERER_ACCELERATED) {
                renderer_log("renderer mode: accelerated");
            } else {
                renderer_log("renderer mode: software");
            }
            break;
        }
    }

    if (sdl_renderer == nullptr) {
        renderer_log("renderer creation failed");
        SDL_DestroyWindow(window);
        window = nullptr;
        return false;
    }

    SDL_RenderSetLogicalSize(sdl_renderer, virtual_w, virtual_h);
    SDL_RenderSetIntegerScale(sdl_renderer, SDL_TRUE);

    assets.load(sdl_renderer);
    renderer_log("assets loaded");
    return true;
}

void SDL2Renderer::shutdown() {
    assets.unload();
    if (sdl_renderer != nullptr) {
        SDL_DestroyRenderer(sdl_renderer);
        sdl_renderer = nullptr;
    }
    if (window != nullptr) {
        SDL_DestroyWindow(window);
        window = nullptr;
    }
}

void SDL2Renderer::clear(Color c) {
    set_color(sdl_renderer, c);
    SDL_RenderClear(sdl_renderer);
}

void SDL2Renderer::draw_rect(int x, int y, int w, int h, Color c) {
    set_color(sdl_renderer, c);
    const SDL_Rect rect{x, y, w, h};
    SDL_RenderFillRect(sdl_renderer, &rect);
}

void SDL2Renderer::draw_rect_outline(int x, int y, int w, int h, Color c) {
    set_color(sdl_renderer, c);
    const SDL_Rect rect{x, y, w, h};
    SDL_RenderDrawRect(sdl_renderer, &rect);
}

void SDL2Renderer::draw_sprite(SpriteId id, int x, int y, float scale, bool flip_h) {
    const int size = std::max(1, static_cast<int>(8.0f * scale));
    draw_sprite_rect(id, x, y, size, size, flip_h);
}

void SDL2Renderer::draw_sprite_rect(SpriteId id, int x, int y, int w, int h, bool flip_h) {
    const SpriteEntry& entry = assets.get(id);

    if (entry.tex != nullptr) {
        SDL_Rect dst{x, y, w, h};
        Color tint{};
        const bool has_tint = sprite_tint(id, tint);
        if (has_tint) {
            SDL_SetTextureColorMod(entry.tex, tint.r, tint.g, tint.b);
        } else {
            SDL_SetTextureColorMod(entry.tex, 255, 255, 255);
        }
        SDL_SetTextureAlphaMod(entry.tex, 255);
        const SDL_RendererFlip flip = flip_h ? SDL_FLIP_HORIZONTAL : SDL_FLIP_NONE;
        SDL_RenderCopyEx(sdl_renderer, entry.tex, nullptr, &dst, 0.0, nullptr, flip);
        if (has_tint && tint.a < 255) {
            set_color(sdl_renderer, tint);
            SDL_Rect overlay{x, y, w, h};
            SDL_RenderFillRect(sdl_renderer, &overlay);
        }
        return;
    }

    const int size = std::min(w, h);
    const int unit = std::max(1, size / 8);
    draw_procedural_char(sdl_renderer, id, x, y, size, unit);
}

void SDL2Renderer::draw_text(const char* str, int x, int y, Color c) {
    set_color(sdl_renderer, c);
    const int col_w = 5;
    const int row_h = 7;
    const int advance = col_w + 1; // 6 px per glyph
    const int line_h = row_h + 2;  // 9 px per line
    int cursor_x = x;
    int cursor_y = y;
    while (*str != '\0') {
        const char ch = *str++;
        if (ch == '\n') {
            cursor_x = x;
            cursor_y += line_h;
            continue;
        }
        if (ch == ' ') {
            cursor_x += advance;
            continue;
        }
        const Glyph5x7& glyph = glyph_for(ch);
        for (int gy = 0; gy < row_h; ++gy) {
            uint8_t row_bits = glyph.rows[gy];
            if (row_bits == 0) {
                continue;
            }
            for (int gx = 0; gx < col_w; ++gx) {
                if (((row_bits >> (col_w - 1 - gx)) & 1U) != 0U) {
                    SDL_RenderDrawPoint(sdl_renderer, cursor_x + gx, cursor_y + gy);
                }
            }
        }
        cursor_x += advance;
    }
}

void SDL2Renderer::draw_circle(int cx, int cy, int r, Color c) {
    set_color(sdl_renderer, c);
    int x = r;
    int y = 0;
    int err = 1 - r;
    while (x >= y) {
        SDL_RenderDrawPoint(sdl_renderer, cx + x, cy + y);
        SDL_RenderDrawPoint(sdl_renderer, cx + y, cy + x);
        SDL_RenderDrawPoint(sdl_renderer, cx - y, cy + x);
        SDL_RenderDrawPoint(sdl_renderer, cx - x, cy + y);
        SDL_RenderDrawPoint(sdl_renderer, cx - x, cy - y);
        SDL_RenderDrawPoint(sdl_renderer, cx - y, cy - x);
        SDL_RenderDrawPoint(sdl_renderer, cx + y, cy - x);
        SDL_RenderDrawPoint(sdl_renderer, cx + x, cy - y);
        ++y;
        if (err < 0) {
            err += 2 * y + 1;
        } else {
            --x;
            err += 2 * (y - x) + 1;
        }
    }
}

void SDL2Renderer::draw_line(int x1, int y1, int x2, int y2, Color c) {
    set_color(sdl_renderer, c);
    SDL_RenderDrawLine(sdl_renderer, x1, y1, x2, y2);
}

void SDL2Renderer::present() {
    SDL_RenderPresent(sdl_renderer);
}

int SDL2Renderer::screen_w() const {
    return vw;
}

int SDL2Renderer::screen_h() const {
    return vh;
}
