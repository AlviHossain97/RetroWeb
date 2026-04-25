#include "hal/sdl2_assets.h"

#include "baked_sprites.h"

#include <cstring>
#include <string>
#include <unordered_map>

namespace {

int name_to_sprite_id(const char* name) {
    // Keep this table aligned with the SpriteId enum. Sprites not in the table
    // stay unassigned (draw code falls back to a primitive).
    struct Pair { const char* name; SpriteId id; };
    static const Pair pairs[] = {
        {"Char0", SpriteId::Char0},
        {"Char1", SpriteId::Char1},
        {"Char2", SpriteId::Char2},
        {"Char3", SpriteId::Char3},
        {"Char4", SpriteId::Char4},
        {"TowerArrow1",     SpriteId::TowerArrow1},
        {"TowerArrow2",     SpriteId::TowerArrow2},
        {"TowerArrow3",     SpriteId::TowerArrow3},
        {"TowerCannon1",    SpriteId::TowerCannon1},
        {"TowerCannon2",    SpriteId::TowerCannon2},
        {"TowerCannon3",    SpriteId::TowerCannon3},
        {"TowerIce1",       SpriteId::TowerIce1},
        {"TowerIce2",       SpriteId::TowerIce2},
        {"TowerIce3",       SpriteId::TowerIce3},
        {"TowerLightning1", SpriteId::TowerLightning1},
        {"TowerLightning2", SpriteId::TowerLightning2},
        {"TowerLightning3", SpriteId::TowerLightning3},
        {"TowerFlame1",     SpriteId::TowerFlame1},
        {"TowerFlame2",     SpriteId::TowerFlame2},
        {"TowerFlame3",     SpriteId::TowerFlame3},
        {"TileGrass",     SpriteId::TileGrass},
        {"TileGrassAlt",  SpriteId::TileGrassAlt},
        {"TilePath",      SpriteId::TilePath},
        {"TilePathAlt",   SpriteId::TilePathAlt},
        {"TileRock",      SpriteId::TileRock},
        {"TileWater",     SpriteId::TileWater},
        {"TileTree",      SpriteId::TileTree},
        {"TileSpawn",     SpriteId::TileSpawn},
        {"TileBase",      SpriteId::TileBase},
        {"TileTowerBase", SpriteId::TileTowerBase},
        {"PropTreeLarge", SpriteId::PropTreeLarge},
        {"PropTreeSmall", SpriteId::PropTreeSmall},
        {"PropBush",      SpriteId::PropBush},
        {"PropRockLarge", SpriteId::PropRockLarge},
        {"PropRockSmall", SpriteId::PropRockSmall},
        {"PropLog",       SpriteId::PropLog},
    };
    for (const auto& p : pairs) {
        if (std::strcmp(p.name, name) == 0) {
            return static_cast<int>(p.id);
        }
    }
    return -1;
}

SDL_Texture* make_texture(SDL_Renderer* renderer, int w, int h, const unsigned char* rgba) {
    SDL_Surface* surf = SDL_CreateRGBSurfaceWithFormatFrom(
        const_cast<unsigned char*>(rgba), w, h, 32, w * 4, SDL_PIXELFORMAT_RGBA32);
    if (surf == nullptr) {
        return nullptr;
    }
    SDL_Texture* tex = SDL_CreateTextureFromSurface(renderer, surf);
    SDL_FreeSurface(surf);
    if (tex != nullptr) {
        SDL_SetTextureScaleMode(tex, SDL_ScaleModeNearest);
    }
    return tex;
}

} // namespace

bool SDL2AssetManager::load(SDL_Renderer* renderer) {
    for (int i = 0; i < BAKED_SPRITE_COUNT; ++i) {
        const BakedSprite& b = BAKED_SPRITES[i];
        int slot = name_to_sprite_id(b.name);
        if (slot < 0) {
            continue;
        }
        SDL_Texture* tex = make_texture(renderer, b.w, b.h, BAKED_PIXELS + b.pixel_offset);
        if (tex == nullptr) {
            continue;
        }
        sprites[slot].tex = tex;
        sprites[slot].w = b.w;
        sprites[slot].h = b.h;
    }
    return true;
}

void SDL2AssetManager::unload() {
    for (auto& s : sprites) {
        if (s.tex != nullptr) {
            SDL_DestroyTexture(s.tex);
            s.tex = nullptr;
        }
    }
}

const SpriteEntry& SDL2AssetManager::get(SpriteId id) const {
    return sprites[static_cast<int>(id)];
}
