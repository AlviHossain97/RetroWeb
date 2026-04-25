# Red Racer — Asset Notice

This file records the visual-asset provenance for Red Racer and the
deliberate scope decisions made before academic submission.

## Visual assets — TMD Studios *Cars* pack (itch.io)

The 14 car sprite sets baked into `gba_project/assets.h`
(`car_<name>_normal/left/right`, 192 × `u16` each, 16×24 at 8bpp)
are sourced from **TMD Studios — [Cars](https://tmd-studios.itch.io/cars)**
on itch.io.

**Licence**, per the creator's stated terms:

> "Feel free to use them in any of your projects (with or without
> modifications). I just ask that you link to my website
> tmdstudios.wordpress.com"
> — TMD Studios

Credit links:

- **Asset page**: <https://tmd-studios.itch.io/cars>
- **Creator website** (linked per licence): <https://tmdstudios.wordpress.com>

The sprites are used as-supplied without modification; the build
pipeline only re-encodes them into 8bpp paletted GBA tile format
and bakes them into C arrays in `assets.h`.

## Car names — project-original

The C source's `car_defs[NUM_CARS]` array, the per-sprite array
identifiers in `assets.h`, and the corresponding Python prototype
(`src/python_game/cars.py` etc.) all use **project-original
fictional names** for the 14 cars: Felucia, Suprex, Aurion,
Corveda, Lotrix, P11, Astor, Merren, Vyrex, Lumbra, Marlon, Zondra,
CXR, Vexa.

These names were chosen deliberately to avoid any trademark question
that real-world car brand names would raise, independent of the
visual asset licence. The TMD Studios sprite pack does not constrain
the in-game labels; the renaming is a precaution on the project
author's side.

## Audio — removed

The Python prototype originally referenced two third-party audio
files (commercial soundtrack tracks ripped from a download site).
Those files were removed during the IP cleanup pass and are not
distributed in this repository; the path constants in
`src/python_game/settings.py` that referenced them have been nulled.
The shipped GBA build has no audio system implementation
(`gba_project/README.md` documents this as a deliberate deferral),
so the GBA artefact is silent regardless.

This aligns with the corpus-wide silent-audio policy across all
three PiStation original games (Red Racer, Mythical, Bastion TD).

## Net legal position

- Visual assets: third-party, properly licensed under TMD Studios's
  free-with-link terms, with the creator's website link present in
  this file, in the per-game README, and in the cross-game
  licensing summary.
- Names and code: project-original.
- Audio: not present.

A future revision may swap or extend the visual assets; if it does,
this file and the per-game README are the audit trail to update.
