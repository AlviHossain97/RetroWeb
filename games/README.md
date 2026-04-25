# Original GBA homebrew

Three Game Boy Advance homebrew titles, written from scratch for this
project so the test corpus is **IP-safe**: no commercial ROMs are
distributed in this repository, and the games are themselves part of
the artefact rather than third-party content used to demonstrate it.

| Game | GBA build language | Origin | Asset sourcing | Folder |
|---|---|---|---|---|
| **Red Racer** | C | Python prototype → C port | itch.io car sprites by **TMD Studios** (free with creator-link); names + code project-original | [Red Racer/](Red%20Racer/) |
| **Mythical** | C++ | Python prototype → C++ port | 100% project-original | [Mythical/](Mythical/) |
| **Bastion Tower Defence** | C++ (Butano engine) | Python+SDL2 prototype → Butano port | itch.io sprites by **pixel.iwao** (credit-only licence); audio TBD; code original | [BastionTD/](BastionTD/) |

All three run **natively on the Raspberry Pi 3 via RetroArch's `lr-mgba`
core** — they are not browser-emulated. The compiled `.gba` ROMs ship
in each game's folder; the Pi loads them through EmulationStation
(see [pi/README.md](../pi/README.md)).

---

## The Python-to-GBA-native prototyping pattern

Every game in this corpus followed the same pipeline:

```
Python prototype on the laptop  →  GBA-native C/C++ port that runs on the Pi
(rapid iteration on gameplay)        (the actual artefact)
```

The Python prototype is a **disposable design tool**: pygame/pygame-ce
on the laptop, with no concern for memory budgets or render budgets.
Lane logic, fuel/repair pickups, score progression, enemy waves,
tower placement — all of it is iterated in Python where a
print-statement-and-rerun loop is cheap.

Once the gameplay design is locked, the entire codebase is rewritten
for the GBA in either C or C++. This is **not transpilation** — the
two implementations share no source. What carries across is the
*design*: which entities exist, how they collide, what the win
condition is. The GBA implementation has to satisfy hard constraints
the Python prototype never had to think about:

- **Fixed-point math.** No FPU on the GBA's ARM7TDMI. Distances, velocities, and angles are 16.16 fixed-point integers; trigonometry comes from precomputed tables.
- **240×160 framebuffer.** The Python prototype runs at whatever the laptop's window is. The GBA build commits to a 240×160 design from the start, with sprite sizes (8×8, 16×16, 32×32) chosen to fit the OAM budget (128 sprites max).
- **No dynamic allocation in hot paths.** Object pools are statically sized at ROM time; there is no `new`/`malloc` per frame.
- **Sprite memory layout.** Tile data lives in VRAM at fixed addresses; palettes are 16 colours (4bpp) or 256 colours (8bpp); animation is sprite-sheet flipping by source-tile-pointer mutation, not blitting.
- **ROM mapping.** Constant data (sprite tiles, level layouts, audio) is laid out in the ROM image and accessed by pointer; the linker script (`gba_cart.ld`) controls placement.

This is genuine systems-level work and is documented for each game in
its own folder.

---

## Asset Licensing Summary

| Game | Visual Assets | Audio Assets | Code |
|---|---|---|---|
| Red Racer | itch.io: [Cars](https://tmd-studios.itch.io/cars) by **TMD Studios** — free use with link to [tmdstudios.wordpress.com](https://tmdstudios.wordpress.com), per the creator's stated terms | Silent (see [README](Red%20Racer/README.md)) | Project-original |
| Mythical | Project-original | Silent (see [README](Mythical/README.md)) | Project-original |
| Bastion Tower Defence | itch.io: [Tiny Tower Defense Assets](https://ilustramundogames.itch.io/tiny-tower-defense-assets) by **pixel.iwao** (ilustramundogames) — free for personal and commercial use with creator credit, per the creator's confirmed terms | Silent (see [README](BastionTD/README.md)) | Project-original |

**Audio policy:** All three games ship with silent GBA builds. Audio
infrastructure code is preserved in the source where it exists (Bastion TD
and the Python prototypes) as documented engineering work, but no audio
playback occurs at runtime. This deliberate scope decision keeps the
homebrew corpus uniformly licence-clean and eliminates third-party audio
attribution complexity. A future post-submission revision may re-introduce
audio with properly-attributed assets.

This corpus was deliberately curated to minimise third-party
licensing complexity. **Mythical is 100% project-original.** Red
Racer and Bastion TD each use one third-party sprite pack from
itch.io, both under explicit creator-link / creator-credit licences:

- Red Racer: TMD Studios — [Cars](https://tmd-studios.itch.io/cars),
  free with link to <https://tmdstudios.wordpress.com>
- Bastion TD: pixel.iwao (ilustramundogames) —
  [Tiny Tower Defense Assets](https://ilustramundogames.itch.io/tiny-tower-defense-assets),
  free with creator credit

Full attribution is provided in each game's per-game README and (for
Bastion TD) at runtime on the title screen.

### Policy

- **Anything not original to this project must be attributed in the per-game README** with the licence name, source URL, and (where applicable) author credit.
- **Anything that cannot be redistributed under a clear licence is not committed to this repository.** It may have been used during prototyping on the laptop; in that case the prototype's asset folder is replaced with a README explaining the situation. See `Red Racer/assets/python_game/README.md` and [`Red Racer/ASSET_NOTICE.md`](Red%20Racer/ASSET_NOTICE.md) for the worked example.
- **The shipped `.gba` ROMs are the artefact.** The marker should not need to run any non-redistributable code or assets to assess the work; everything in the runnable artefact is either project-original or covered by a clear creator-credit licence.

---

## Building from source

The shipped `.gba` files are committed; rebuilding is optional.

- **Mythical** and **Red Racer** use plain devkitARM + a small Makefile in `gba_project/`. Install devkitPro from <https://devkitpro.org/wiki/Getting_Started>, then `make` in the game's `gba_project/` directory.
- **Bastion Tower Defence** uses the [Butano](https://github.com/GValiente/butano) C++23 engine on top of devkitARM, plus CMake + SDL2 for the desktop simulator build. The full setup (toolchain locations, third-party paths) is documented in [BastionTD/setup.md](BastionTD/setup.md).

The build artefacts (`.elf`, `.o`, `.d`, `.sav`, `build/` directories,
toolchain copies) are excluded from version control via `.gitignore`
and live in a local build cache outside the repository tree on the
development machine. See the project root [README](../README.md) for
the cache layout.
