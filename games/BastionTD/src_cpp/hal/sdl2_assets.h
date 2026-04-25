#pragma once

#include "core/types.h"

#if __has_include(<SDL.h>)
#include <SDL.h>
#else
#include <SDL2/SDL.h>
#endif

struct SpriteEntry {
    SDL_Texture* tex = nullptr;
    int w = 0;
    int h = 0;
};

struct SDL2AssetManager {
    SpriteEntry sprites[static_cast<int>(SpriteId::COUNT)] = {};

    bool load(SDL_Renderer* renderer);
    void unload();
    const SpriteEntry& get(SpriteId id) const;
};
