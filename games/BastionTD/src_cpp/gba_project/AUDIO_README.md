# Bastion TD GBA — Audio Assets

This directory is intentionally empty. Audio was removed from the shipped
build to keep the homebrew corpus consistently silent across all three
PiStation original games.

The audio infrastructure (`SfxId` / `BgmId` enums, `IAudio` interface,
`GbaAudio` implementation in `../src/main.cpp`) remains in the source code
as documented engineering work, with playback gated behind a compile-time
flag (`ENABLE_AUDIO` in `core/config.h`) that is disabled by default.

## Re-enabling audio (post-submission, with attribution)

1. Place properly-attributed WAV files in this directory matching the
   names referenced in `GbaAudio::sfx_item()` and `GbaAudio::bgm_item()`
   in `../src/main.cpp` (`place.wav`, `shoot.wav`, `bgm_title.wav`, etc.).
2. Define `ENABLE_AUDIO` in `core/config.h`.
3. Rebuild — Butano's asset pipeline will auto-generate `bn_sound_items.h`
   from the WAVs, and the gated playback code will compile back in.
4. Update the asset attribution section in `../../../README.md` with the
   audio source and licence.

See `../../../README.md` for the corpus-wide audio policy.
