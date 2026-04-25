# Python prototype — assets withheld

Red Racer began as a Python prototype on the laptop in Q1 2026 to iterate
gameplay (lane logic, fuel/repair pickups, score progression) before the
GBA-native rewrite. The prototype used third-party reference imagery and
audio sourced for internal iteration only; that material is not part of
the project's IP and is not redistributed in this repository.

The shipped artefact is the GBA-native build in `../gba_game/RedRacer_Phys.gba`,
compiled from the C source in `../../src/` and `../../gba_project/`.
All sprites and sound used by the GBA build are project-original or
explicitly licensed (see `../gba_game/LICENSES.md` if present).

If you are reproducing the prototyping pipeline, drop your own placeholder
PNGs and audio into this folder; the Python sources reference filenames
relative to this directory.
