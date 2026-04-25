#include "hal/sdl2_audio.h"

#include <algorithm>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>

namespace {

void audio_log(const char* msg) {
    std::ofstream out("bastion_startup.log", std::ios::app);
    if (out.is_open()) {
        out << msg << '\n';
    }
}

const char* sfx_name(SfxId id) {
    switch (id) {
    case SfxId::Place:      return "place";
    case SfxId::Shoot:      return "shoot";
    case SfxId::Hit:        return "hit";
    case SfxId::EnemyDeath: return "enemy_death";
    case SfxId::WaveStart:  return "wave_start";
    case SfxId::WaveClear:  return "wave_clear";
    case SfxId::BossSpawn:  return "boss_spawn";
    case SfxId::BaseHit:    return "base_hit";
    case SfxId::Upgrade:    return "upgrade";
    case SfxId::Sell:       return "sell";
    case SfxId::MenuMove:   return "menu_move";
    case SfxId::MenuSelect: return "menu_select";
    case SfxId::GameOver:   return "game_over";
    case SfxId::Victory:    return "victory";
    default:                return nullptr;
    }
}

const char* bgm_name(BgmId id) {
    switch (id) {
    case BgmId::Title: return "bgm_title";
    case BgmId::Build: return "bgm_build";
    case BgmId::Wave:  return "bgm_wave";
    case BgmId::Boss:  return "bgm_boss";
    default:           return nullptr;
    }
}

void audio_callback(void* userdata, Uint8* stream, int len) {
    auto* audio = static_cast<SDL2Audio*>(userdata);
    // Start silent (u8 mono silence = 128).
    std::memset(stream, 128, static_cast<size_t>(len));
    if (audio->voice_mtx != nullptr) {
        SDL_LockMutex(audio->voice_mtx);
    }
    for (auto& v : audio->voices) {
        if (! v.active || v.data == nullptr) {
            continue;
        }
        for (int i = 0; i < len; ++i) {
            if (v.position >= v.length) {
                if (v.loop) {
                    v.position = 0;
                } else {
                    v.active = false;
                    break;
                }
            }
            const int raw = static_cast<int>(v.data[v.position++]) - 128;
            const int scaled = static_cast<int>(static_cast<float>(raw) * v.volume);
            const int current = static_cast<int>(stream[i]) - 128;
            int mixed = current + scaled;
            if (mixed > 127) mixed = 127;
            if (mixed < -128) mixed = -128;
            stream[i] = static_cast<Uint8>(mixed + 128);
        }
    }
    if (audio->voice_mtx != nullptr) {
        SDL_UnlockMutex(audio->voice_mtx);
    }
}

// Load a .wav file, convert to device format (u8 mono 22050 Hz), and store
// an owned PCM buffer in `out`.
bool load_clip(const char* path, SDL2Audio::Clip& out,
               SDL_AudioSpec& device_spec) {
    SDL_AudioSpec wav_spec;
    Uint8* wav_buffer = nullptr;
    Uint32 wav_length = 0;
    if (SDL_LoadWAV(path, &wav_spec, &wav_buffer, &wav_length) == nullptr) {
        return false;
    }
    // Convert to device format if needed.
    SDL_AudioCVT cvt;
    const int build = SDL_BuildAudioCVT(&cvt,
                                        wav_spec.format, wav_spec.channels, wav_spec.freq,
                                        device_spec.format, device_spec.channels, device_spec.freq);
    if (build < 0) {
        SDL_FreeWAV(wav_buffer);
        return false;
    }
    if (build == 0) {
        // Matching format — copy direct.
        out.length = wav_length;
        out.data = static_cast<Uint8*>(std::malloc(wav_length));
        if (out.data == nullptr) {
            SDL_FreeWAV(wav_buffer);
            return false;
        }
        std::memcpy(out.data, wav_buffer, wav_length);
        SDL_FreeWAV(wav_buffer);
        return true;
    }
    // Needs conversion.
    const int cap = wav_length * cvt.len_mult;
    cvt.buf = static_cast<Uint8*>(std::malloc(cap));
    if (cvt.buf == nullptr) {
        SDL_FreeWAV(wav_buffer);
        return false;
    }
    cvt.len = static_cast<int>(wav_length);
    std::memcpy(cvt.buf, wav_buffer, wav_length);
    SDL_FreeWAV(wav_buffer);
    if (SDL_ConvertAudio(&cvt) < 0) {
        std::free(cvt.buf);
        return false;
    }
    out.length = static_cast<Uint32>(cvt.len_cvt);
    out.data = cvt.buf; // transfer ownership
    return true;
}

} // namespace

bool SDL2Audio::init() {
    if (SDL_InitSubSystem(SDL_INIT_AUDIO) < 0) {
        audio_log("audio subsystem init failed");
        return false;
    }

    voice_mtx = SDL_CreateMutex();

    SDL_AudioSpec want = {};
    want.freq = 22050;
    want.format = AUDIO_U8;
    want.channels = 1;
    want.samples = 1024;
    want.callback = audio_callback;
    want.userdata = this;

    SDL_AudioSpec got = {};
    device = SDL_OpenAudioDevice(nullptr, 0, &want, &got, 0);
    if (device == 0) {
        audio_log("SDL_OpenAudioDevice failed");
        return false;
    }

    for (int i = 0; i < kSfxCount; ++i) {
        const char* name = sfx_name(static_cast<SfxId>(i));
        if (name == nullptr) {
            continue;
        }
        char path[128];
        std::snprintf(path, sizeof(path), "assets/audio/%s.wav", name);
        load_clip(path, sfx[i], got);
    }
    for (int i = 0; i < kBgmCount; ++i) {
        const char* name = bgm_name(static_cast<BgmId>(i));
        if (name == nullptr) {
            continue;
        }
        char path[128];
        std::snprintf(path, sizeof(path), "assets/audio/%s.wav", name);
        load_clip(path, bgm[i], got);
    }

    SDL_PauseAudioDevice(device, 0); // start playback
    initialized = true;
    audio_log("SDL audio ready");
    return true;
}

void SDL2Audio::shutdown() {
    if (! initialized) {
        return;
    }
    if (device != 0) {
        SDL_PauseAudioDevice(device, 1);
        SDL_CloseAudioDevice(device);
        device = 0;
    }
    for (auto& c : sfx) {
        if (c.data != nullptr) {
            std::free(c.data);
            c.data = nullptr;
        }
    }
    for (auto& c : bgm) {
        if (c.data != nullptr) {
            std::free(c.data);
            c.data = nullptr;
        }
    }
    if (voice_mtx != nullptr) {
        SDL_DestroyMutex(voice_mtx);
        voice_mtx = nullptr;
    }
    SDL_QuitSubSystem(SDL_INIT_AUDIO);
    initialized = false;
}

void SDL2Audio::play_sfx(SfxId id) {
    if (! initialized) {
        return;
    }
    const int i = static_cast<int>(id);
    if (i < 0 || i >= kSfxCount) {
        return;
    }
    const Clip& clip = sfx[i];
    if (clip.data == nullptr || clip.length == 0) {
        return;
    }
    if (voice_mtx != nullptr) {
        SDL_LockMutex(voice_mtx);
    }
    // Find a free voice slot (skip slot 0, reserved for BGM).
    for (int v = 1; v < kMaxVoices; ++v) {
        if (! voices[v].active) {
            voices[v].data = clip.data;
            voices[v].length = clip.length;
            voices[v].position = 0;
            voices[v].volume = std::max(0.0f, std::min(1.0f, sfx_volume));
            voices[v].loop = false;
            voices[v].active = true;
            break;
        }
    }
    if (voice_mtx != nullptr) {
        SDL_UnlockMutex(voice_mtx);
    }
}

void SDL2Audio::play_bgm(BgmId id) {
    if (! initialized) {
        return;
    }
    if (current_bgm == id && voices[0].active) {
        return;
    }
    const int i = static_cast<int>(id);
    if (i < 0 || i >= kBgmCount) {
        return;
    }
    const Clip& clip = bgm[i];
    if (clip.data == nullptr || clip.length == 0) {
        return;
    }
    if (voice_mtx != nullptr) {
        SDL_LockMutex(voice_mtx);
    }
    voices[0].data = clip.data;
    voices[0].length = clip.length;
    voices[0].position = 0;
    voices[0].volume = std::max(0.0f, std::min(1.0f, bgm_volume));
    voices[0].loop = true;
    voices[0].active = true;
    current_bgm = id;
    if (voice_mtx != nullptr) {
        SDL_UnlockMutex(voice_mtx);
    }
}

void SDL2Audio::stop_bgm() {
    if (! initialized) {
        return;
    }
    if (voice_mtx != nullptr) {
        SDL_LockMutex(voice_mtx);
    }
    voices[0].active = false;
    voices[0].data = nullptr;
    current_bgm = BgmId::COUNT;
    if (voice_mtx != nullptr) {
        SDL_UnlockMutex(voice_mtx);
    }
}

void SDL2Audio::set_sfx_volume(float v) {
    sfx_volume = std::max(0.0f, std::min(1.0f, v));
}

void SDL2Audio::set_bgm_volume(float v) {
    bgm_volume = std::max(0.0f, std::min(1.0f, v));
    if (voice_mtx != nullptr) {
        SDL_LockMutex(voice_mtx);
    }
    voices[0].volume = bgm_volume;
    if (voice_mtx != nullptr) {
        SDL_UnlockMutex(voice_mtx);
    }
}
