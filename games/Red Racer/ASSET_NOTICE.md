# Red Racer — Asset Notice

All car sprites previously sourced from Game Dev Market have been removed from
this repository. The current build uses neutral placeholder graphics generated
programmatically by the project author.

This decision was made to keep Red Racer's asset corpus 100% project-original
for academic submission purposes, eliminating any third-party licensing
considerations.

Engine sprites, UI elements, fonts, and audio (if any) are project-original.

## What was removed

- Car sprites from Game Dev Market — *Pixel Art Top View Super Cars*
- Any associated colour-variant or animation-frame derivatives (left-turn,
  right-turn variants per car slot — 14 cars × 3 directions = 42 sprite arrays)
- Same assets from the Python prototype (which preceded the GBA C port),
  including the prototype's manufacturer-named car PNGs and reference audio

## What remains

- **Procedurally generated placeholder car graphics** for all 14 car slots
  (16×24 each, distinct flat colour per slot via palette indices 2–15;
  baked into `gba_project/assets.h` as `car_<name>_<direction>[192]` arrays).
- **Branded car names renamed** to project-original equivalents (14 cars
  total) in C source, Python prototype, and documentation. The full
  rename mapping is in this commit's diff and in the project's git
  history. None of the new names reference any real-world car
  manufacturer or model.
- **All gameplay logic, physics, track rendering, HUD, save system,
  achievement system, mission system, and game-state code** written by the
  project author. The C source under `gba_project/` and the Python
  prototype under `src/python_game/` are project-original.

## Net legal position

Zero third-party visual assets in the live build. Zero attribution required.
Zero residual licence risk.
