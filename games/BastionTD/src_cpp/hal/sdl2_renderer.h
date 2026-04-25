#pragma once

#include "hal/hal.h"
#include "hal/sdl2_assets.h"

#if __has_include(<SDL.h>)
#include <SDL.h>
#else
#include <SDL2/SDL.h>
#endif

struct SDL2Renderer : IRenderer {
    SDL_Window* window = nullptr;
    SDL_Renderer* sdl_renderer = nullptr;
    SDL2AssetManager assets;
    int vw = 0;
    int vh = 0;

    bool init(const char* title, int virtual_w, int virtual_h, int scale);
    void shutdown();

    void clear(Color c) override;
    void draw_rect(int x, int y, int w, int h, Color c) override;
    void draw_rect_outline(int x, int y, int w, int h, Color c) override;
    void draw_sprite(SpriteId id, int x, int y, float scale = 1.0f, bool flip_h = false) override;
    void draw_sprite_rect(SpriteId id, int x, int y, int w, int h, bool flip_h = false) override;
    void draw_text(const char* str, int x, int y, Color c = {240, 235, 220, 255}) override;
    void draw_circle(int cx, int cy, int r, Color c) override;
    void draw_line(int x1, int y1, int x2, int y2, Color c) override;
    void present() override;
    int screen_w() const override;
    int screen_h() const override;
};
