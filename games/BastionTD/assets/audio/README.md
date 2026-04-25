# Bastion TD Desktop Sim — Audio Assets

This directory is intentionally empty. The desktop simulator's audio
infrastructure (`SDL2Audio` implementation in
`../../src_cpp/hal/sdl2_audio.{h,cpp}`, `app.audio->play_sfx()` /
`play_bgm()` calls in the state classes) remains in the source code but
is a no-op in the shipped silent build — `SDL2Audio`'s playback methods
are gated behind `ENABLE_AUDIO` which is undefined by default.

See `../../README.md` for the corpus-wide audio policy.
