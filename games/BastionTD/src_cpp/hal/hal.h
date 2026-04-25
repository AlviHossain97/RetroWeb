#pragma once

#include "core/types.h"

struct IRenderer {
    virtual ~IRenderer() = default;
    virtual void clear(Color c) = 0;
    virtual void draw_rect(int x, int y, int w, int h, Color c) = 0;
    virtual void draw_rect_outline(int x, int y, int w, int h, Color c) = 0;
    virtual void draw_sprite(SpriteId id, int x, int y, float scale = 1.0f, bool flip_h = false) = 0;
    virtual void draw_sprite_rect(SpriteId id, int x, int y, int w, int h, bool flip_h = false) = 0;
    virtual void draw_text(const char* str, int x, int y, Color c = {240, 235, 220, 255}) = 0;
    virtual void draw_circle(int cx, int cy, int r, Color c) = 0;
    virtual void draw_line(int x1, int y1, int x2, int y2, Color c) = 0;
    virtual void present() = 0;
    virtual int screen_w() const = 0;
    virtual int screen_h() const = 0;
};

struct IInput {
    virtual ~IInput() = default;
    virtual void update() = 0;
    virtual bool pressed(InputButton btn) const = 0;
    virtual bool held(InputButton btn) const = 0;
    virtual bool released(InputButton btn) const = 0;
    virtual bool quit_requested() const = 0;
    virtual float held_duration(InputButton btn) const = 0;
};

struct IAudio {
    virtual ~IAudio() = default;
    virtual void play_sfx(SfxId id) = 0;
    virtual void play_bgm(BgmId id) = 0;
    virtual void stop_bgm() = 0;
    virtual void set_sfx_volume(float v) = 0;
    virtual void set_bgm_volume(float v) = 0;
    // Called once per frame. Platforms that need to manually re-trigger looped
    // BGM (e.g. GBA maxmod WAV playback) override this; default is a no-op.
    virtual void tick() {}
};
