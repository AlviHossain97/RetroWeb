#pragma once

#include "hal/hal.h"

#include <SDL.h>

#include <cstdint>

struct SDL2Audio : IAudio {
    static constexpr int kMaxVoices = 8;
    static constexpr int kSfxCount = static_cast<int>(SfxId::COUNT);
    static constexpr int kBgmCount = static_cast<int>(BgmId::COUNT);

    struct Clip {
        std::uint8_t* data = nullptr;   // owned buffer (u8 mono PCM @ device rate)
        std::uint32_t length = 0;
    };

    struct Voice {
        const std::uint8_t* data = nullptr;
        std::uint32_t length = 0;
        std::uint32_t position = 0;
        float volume = 1.0f;
        bool loop = false;
        bool active = false;
    };

    bool initialized = false;
    float sfx_volume = 1.0f;
    float bgm_volume = 1.0f;
    BgmId current_bgm = BgmId::COUNT;

    SDL_AudioDeviceID device = 0;
    SDL_mutex* voice_mtx = nullptr;

    Clip sfx[kSfxCount] = {};
    Clip bgm[kBgmCount] = {};
    Voice voices[kMaxVoices] = {};

    bool init();
    void shutdown();

    void play_sfx(SfxId id) override;
    void play_bgm(BgmId id) override;
    void stop_bgm() override;
    void set_sfx_volume(float v) override;
    void set_bgm_volume(float v) override;
};
