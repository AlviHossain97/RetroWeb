# RetroWeb — Fixes & Roadmap Plan v3 (Complete)

> **Current state:** v0.1.0 · Vite + React + TS · localhost:5173
> **Date:** February 28, 2026
> **Blocker:** ZIP extraction fails in RetroArch WASM — games don't load

---

## Current State Assessment (from screenshots, Feb 28 afternoon)

### What's Working Well (big progress since this morning)

- **Sidebar** is polished: "RetroWeb" branding, 5 nav items (Library, Supported Systems, BIOS Vault, Saves Vault, Settings), version footer
- **Dark theme is now cohesive** — content area matches sidebar (the gray background issue from earlier is fixed)
- **Library page** has real structure: "Game Library" header, search bar, Mode toggle (Add to Library / Memory Only), grid/list view toggle, "All Games" section with a game card for "Super Mario Advance 4 - Super..." with NES badge, "Never played" status, favorite star, settings gear
- **Supported Systems** is populated: search + filter bar, "Fully Supported (5)" / "Experimental (1)" tabs, system cards for Game Boy Series, NES, Sega Genesis, Super Nintendo, PlayStation 1 — each showing accepted formats, BIOS status, game count. PS1 card shows "BIOS Missing" with yellow Upload button
- **BIOS Vault** is functional: Global Readiness (0%), Vault Status (0 installed / 1 missing), Storage Used (0 Bytes), batch upload drop zone, Required Firmware List showing PS1 as missing
- **Saves Vault** has structure: Total SRAM Used / Total States Used cards, "Import Saves" button, empty state with "No Saves Found — Play some games to generate SRAM and Save States"
- **Settings** has two sections: Storage Usage (3 MB / 2048 MB with progress bar) and Performance & Compatibility (Multi-threading WASM Threads: Enabled, green badge, "Cross-Origin Isolation is active")
- **Player view** exists: shows game title in header, "Menu (Esc)" button, X close button, black canvas area, status line "Playing: Super Mario Advance 4..."

### What's Broken (the blocker)

The final screenshot tells the whole story:

```
Saved config to "/home/web_user/retroarch/userdata/retroarch.cfg".
Failed to extract content from compressed file:
"/home/web_user/retroarch/userdata/content/data10.zip"
```

**Root cause:** The file is being passed to RetroArch as a `.zip`. The Emscripten/WASM build of RetroArch doesn't have working archive extraction (zlib/libarchive isn't compiled in or doesn't work at runtime). RetroArch tries to extract it, fails, and shows this error on a black screen.

**The fix is simple:** Never pass a `.zip` to RetroArch. Extract the ROM in JavaScript first, then pass the uncompressed ROM blob.

### What Needs Fixing / Improving (beyond the blocker)

1. **Game card misdetection:** The card shows "Super Mario Advance 4" (a GBA game) with an "NES" badge. The system detection is wrong — SMA4 is a `.gba` file, not `.nes`. This suggests the detection is guessing based on something other than extension or header.
2. **Player shows sidebar:** When playing a game, the sidebar is still visible. The player should go fullscreen (or at least hide the sidebar) for immersion.
3. **Player canvas is just black:** Even before the ZIP error, the canvas shows nothing — no loading spinner, no progress indicator, no "Extracting ROM..." feedback. User sees black and waits.
4. **No error surfacing in the UI:** The ZIP extraction error only appears in the RetroArch console (which the user may not even see). There's no toast or modal telling the user what went wrong.
5. **Settings page is sparse:** Only 2 sections with minimal content. No display settings, audio settings, input settings, or data management.
6. **BIOS Vault "Total SRAM Used" card shows no value** — the left card in the stats row is blank (no "0 Bytes" like the right card).
7. **No loading/progress states:** Dropping a ROM → launching shows no intermediate feedback. The user just sees the player page with a black screen.
8. **Library card cover art area is plain black** — no placeholder illustration or system-colored gradient. It looks like a broken image.

---

## Phase 0 — Kill the ZIP Error Forever (Day 1)

**This is the single blocker preventing the app from working. Fix it first, test it, then move on.**

### A) Implement the ROM Normalizer

Create one function that every launch path calls. It handles ZIP extraction, format validation, and system detection in JavaScript — before anything touches RetroArch.

```typescript
// rom-normalizer.ts

import { BlobReader, BlobWriter, ZipReader } from '@zip.js/zip.js';

interface NormalizedROM {
  blob: Blob;
  filename: string;         // e.g., "Super Mario Advance 4.gba"
  systemId: string;         // e.g., "gba"
  originalFilename: string; // e.g., "Super Mario Advance 4 (En,Fr,De,Es,It).zip"
}

// Extensions that are valid ROM files (not metadata, not disc images)
const CARTRIDGE_EXTENSIONS = new Set([
  '.nes', '.smc', '.sfc', '.gb', '.gbc', '.gba',
  '.md', '.smd', '.gen', '.bin', '.n64', '.z64', '.v64',
  '.nds', '.pce', '.ngp', '.ngc', '.ws', '.wsc',
  '.a26', '.a78', '.lnx', '.jag', '.col', '.sg',
  '.sms', '.gg',
]);

const DISC_EXTENSIONS = new Set(['.chd', '.pbp']);

// Files to ignore inside ZIPs
const IGNORE_EXTENSIONS = new Set([
  '.txt', '.nfo', '.jpg', '.jpeg', '.png', '.gif',
  '.bmp', '.pdf', '.url', '.htm', '.html', '.xml',
  '.srm', '.sav', '.db',
]);

export async function normalizeROM(file: File): Promise<NormalizedROM> {
  const ext = getExtension(file.name);

  // Case 1: Already an uncompressed ROM
  if (CARTRIDGE_EXTENSIONS.has(ext) || DISC_EXTENSIONS.has(ext)) {
    return {
      blob: file,
      filename: file.name,
      systemId: detectSystem(file.name, ext),
      originalFilename: file.name,
    };
  }

  // Case 2: ZIP file — extract in JS, never pass to RetroArch
  if (ext === '.zip') {
    return await extractROMFromZip(file);
  }

  // Case 3: Unknown format
  throw new NormalizeError(
    'unsupported_format',
    `"${ext}" is not a supported ROM format. Accepted formats: .nes, .gba, .smc, .chd, .zip, etc.`
  );
}

async function extractROMFromZip(file: File): Promise<NormalizedROM> {
  const reader = new ZipReader(new BlobReader(file));
  const entries = await reader.getEntries();

  // Filter to ROM candidates only
  const candidates = entries.filter(entry => {
    if (entry.directory) return false;
    const ext = getExtension(entry.filename);
    if (IGNORE_EXTENSIONS.has(ext)) return false;
    return CARTRIDGE_EXTENSIONS.has(ext) || DISC_EXTENSIONS.has(ext);
  });

  if (candidates.length === 0) {
    await reader.close();
    throw new NormalizeError(
      'zip_no_rom',
      'This ZIP file doesn\'t contain any recognized ROM files.'
    );
  }

  let selected: typeof candidates[0];

  if (candidates.length === 1) {
    // Auto-select the only candidate
    selected = candidates[0];
  } else {
    // Multiple ROMs — let the UI handle selection
    // (throw a special error that the UI catches to show a picker modal)
    await reader.close();
    throw new NormalizeError(
      'zip_multiple_roms',
      'Multiple ROM files found in ZIP',
      candidates.map(c => ({ filename: c.filename, size: c.uncompressedSize }))
    );
  }

  // Extract the selected ROM
  const blob = await selected.getData!(new BlobWriter());
  await reader.close();

  const ext = getExtension(selected.filename);
  return {
    blob,
    filename: selected.filename,
    systemId: detectSystem(selected.filename, ext),
    originalFilename: file.name,
  };
}

// Also: add header magic byte detection for ambiguous cases
function detectSystem(filename: string, ext: string): string {
  const systemMap: Record<string, string> = {
    '.nes': 'nes', '.smc': 'snes', '.sfc': 'snes',
    '.gb': 'gb', '.gbc': 'gbc', '.gba': 'gba',
    '.md': 'genesis', '.smd': 'genesis', '.gen': 'genesis',
    '.chd': 'ps1', '.pbp': 'psp',
    '.n64': 'n64', '.z64': 'n64', '.v64': 'n64',
    // ... etc for all systems
  };
  return systemMap[ext] ?? 'unknown';
}
```

### B) Wire It Into Every Launch Path

Every place in the app that launches a game must go through `normalizeROM()` first:

```typescript
// In your launch handler (Library card click, drag-drop, etc.)
async function handleLaunchGame(file: File) {
  try {
    showLoadingOverlay('Preparing ROM...');

    const normalized = await normalizeROM(file);

    updateLoadingOverlay(`Loading ${normalized.systemId.toUpperCase()} core...`);

    // Now pass the UNCOMPRESSED blob to the emulator
    await launchEmulator({
      core: getCoreForSystem(normalized.systemId),
      rom: { filename: normalized.filename, content: normalized.blob },
      bios: await getBiosForSystem(normalized.systemId),
    });

    hideLoadingOverlay();
  } catch (error) {
    hideLoadingOverlay();

    if (error instanceof NormalizeError) {
      if (error.code === 'zip_multiple_roms') {
        showROMPickerModal(error.candidates, file);
      } else {
        showErrorToast(error.userMessage);
      }
    } else {
      showErrorToast('Failed to launch game. Check console for details.');
      console.error('Launch error:', error);
    }
  }
}
```

### C) Defensively Disable RetroArch Archive Handling

Even after the normalizer, tell RetroArch to never try extracting archives itself:

```typescript
retroarchConfig: {
  // ...your existing config
  'network_buildbot_auto_extract_archive': 'false',
  'menu_driver': 'null',
}
```

Or if your wrapper exposes it: set `archive_mode = "off"` equivalent.

### D) Success Criteria

- [ ] Upload `.zip` containing `.gba` → game boots instantly (no "Failed to extract" error ever again)
- [ ] Upload bare `.gba` → game boots instantly
- [ ] Upload `.zip` with multiple ROMs → selection modal appears
- [ ] Upload `.zip` with no ROMs (just `.txt`/`.nfo`) → friendly error toast
- [ ] Upload `.chd` for PS1 → accepted (after BIOS is present)
- [ ] Upload `.bin`/`.cue` → rejected with "Please convert to CHD" message
- [ ] The string "Failed to extract content from compressed file" never appears again

---

## Phase 0.5 — Fix System Misdetection (Day 1, alongside Phase 0)

### The Problem

The library card shows "Super Mario Advance 4" with an **NES** badge. SMA4 is a GBA game. This means the system detection is either not reading the file extension inside the ZIP, or it's defaulting to NES when unsure.

### The Fix

The `normalizeROM()` function above already solves this — it reads the actual ROM file extension inside the ZIP (`.gba`), not the ZIP filename. But also:

1. **After extraction, validate via header magic bytes** as a second check:
   - GBA ROMs start with `0x2E 0x00 0x00 0xEA` (ARM branch instruction)
   - NES ROMs start with `0x4E 0x45 0x53 0x1A` ("NES" + EOF)
   - SNES ROMs have a header at offset `0x7FC0` or `0xFFC0`
   - Genesis ROMs have "SEGA" at offset `0x100`

2. **If extension and header disagree, trust the header.** Show a toast: "Detected as GBA (file header) — extension said .nes"

3. **Update the library card badge** to reflect the actual detected system from the normalized ROM, not from the original ZIP filename.

```typescript
// header-detection.ts
export async function detectSystemFromHeader(blob: Blob): Promise<string | null> {
  const buffer = await blob.slice(0, 512).arrayBuffer();
  const view = new Uint8Array(buffer);

  // NES: "NES\x1A"
  if (view[0] === 0x4E && view[1] === 0x45 && view[2] === 0x53 && view[3] === 0x1A) {
    return 'nes';
  }

  // GBA: ARM branch at 0x00
  if (view[0] === 0x2E && view[1] === 0x00 && view[2] === 0x00 && view[3] === 0xEA) {
    return 'gba';
  }

  // Check for "SEGA" at offset 0x100 (Genesis/Mega Drive)
  if (view.length >= 0x104) {
    const sega = String.fromCharCode(view[0x100], view[0x101], view[0x102], view[0x103]);
    if (sega === 'SEGA') return 'genesis';
  }

  // GB/GBC: Nintendo logo at 0x0104
  if (view.length >= 0x0134) {
    if (view[0x0104] === 0xCE && view[0x0105] === 0xED) {
      // Check GBC flag at 0x0143
      return view[0x0143] === 0x80 || view[0x0143] === 0xC0 ? 'gbc' : 'gb';
    }
  }

  return null; // Unknown — fall back to extension
}
```

---

## Phase 1 — Player Canvas & Loading Polish (Days 2–3)

**The player currently shows a black canvas with no feedback. Users don't know if it's loading or broken.**

### 1.1 Loading States (kill the black screen experience)

When the user clicks "Play" on a library card, show a progression:

```
[Library card clicked]
  → "Preparing ROM..." (ZIP extraction in progress, show % if possible)
  → "Loading GBA core..." (WASM downloading, show MB progress)
  → "Mounting BIOS..." (if applicable)
  → "Starting game..." (core initializing)
  → [Canvas shows first frame — hide all overlays]
```

Implementation: a centered overlay on top of the (still-black) canvas with a spinner + status text. Use `zip.js` progress callbacks and `fetch` progress for core download.

```typescript
// Example: core download with progress
async function fetchCoreWithProgress(url: string, onProgress: (pct: number) => void) {
  const response = await fetch(url);
  const total = parseInt(response.headers.get('content-length') || '0');
  const reader = response.body!.getReader();
  const chunks: Uint8Array[] = [];
  let received = 0;

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    chunks.push(value);
    received += value.length;
    if (total > 0) onProgress(Math.round((received / total) * 100));
  }

  return new Blob(chunks);
}
```

### 1.2 Player Layout — Hide Sidebar, Go Immersive

**Current problem:** The player view still shows the full sidebar. The game canvas is crammed into the content area alongside navigation.

**Fix:** When the player route is active:
- Hide the sidebar entirely (or collapse it with a small floating "☰" toggle)
- The canvas should fill the entire viewport (or the maximum area with correct aspect ratio)
- Show a thin top bar with: game title (truncated), Menu (Esc), Close (X)
- The canvas itself should be centered with letterboxing if aspect ratio doesn't match

```typescript
// In your layout component
const isPlaying = useLocation().pathname === '/play';

return (
  <div className="flex h-screen">
    {!isPlaying && <Sidebar />}
    <main className={isPlaying ? 'w-full h-full' : 'flex-1 overflow-auto'}>
      <Outlet />
    </main>
  </div>
);
```

### 1.3 Custom Player Overlay (day 1 minimal version)

Even before building the full Phase 6 overlay, ship a minimal version:

- **Top bar:** Game title (left) + "Menu (Esc)" button (right) + Close/X
- **Bottom quick bar** (hidden by default, shown on Esc or hover at bottom edge):
  - Save State (F1)
  - Load State (F4)
  - Reset
  - Fullscreen (F11)
  - Back to Library
- **Escape key** toggles overlay visibility
- **Click/tap canvas** hides overlay + focuses game

### 1.4 iOS/Safari Audio Fix

```typescript
// Show a "Tap to Start" overlay on iOS Safari
const isIOSSafari = /iPad|iPhone/.test(navigator.userAgent) &&
                    !window.MSStream &&
                    /Safari/.test(navigator.userAgent);

// Or more reliably, just check if AudioContext needs user gesture:
const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
if (audioCtx.state === 'suspended') {
  showTapToStartOverlay(); // Full-screen overlay: "Tap to Start"
  // On tap: audioCtx.resume(), then hide overlay
}
```

### 1.5 Error Surfacing in Player

If the emulator errors out (like the ZIP extraction failure), **catch it and show a user-friendly overlay on the canvas area**, not just a console message:

```
┌─────────────────────────────────────┐
│                                     │
│     ⚠️ Game Failed to Load          │
│                                     │
│  "Could not extract ROM from ZIP"   │
│                                     │
│  [Try Again]  [Back to Library]     │
│                                     │
│  ▸ Show technical details           │
│                                     │
└─────────────────────────────────────┘
```

The "Show technical details" expandable gives power users the raw error for bug reports.

---

## Phase 2 — BIOS Vault Production-Ready (Day 3)

**Current state: The BIOS Vault already looks excellent.** The stats cards, batch upload zone, and Required Firmware List are all in place. Just needs small polish.

### Fixes & Additions

- [ ] **Fix the "Total SRAM Used" card:** The left stat card in the BIOS Vault appears to have no value displayed (unlike "Total States Used" which shows "0 Bytes"). Ensure both cards render their values.
- [ ] **Auto-validate common BIOS variants:** PS1 has multiple valid BIOS files (`scph5501.bin`, `scph5500.bin`, `scph5502.bin`, `scph1001.bin`, etc.). Accept any of them, but show which specific file was uploaded.
- [ ] **Hash validation:** After upload, compute MD5 of the file and check against known-good hashes. Show ✅ Verified / ⚠️ Unrecognized Hash (still allow use, but flag it).
- [ ] **BIOS filename case normalization:** If user uploads `SCPH5501.BIN` → rename internally to `scph5501.bin` and accept it. Don't reject over capitalization.
- [ ] **"Test BIOS" button** (dev/power-user): Loads a tiny test payload to verify the BIOS file actually works with the core, without needing a full game.
- [ ] **Live recalculation:** Global Readiness % should update instantly when a BIOS is uploaded (no page refresh needed).
- [ ] **Success feedback:** After successful BIOS upload, show a toast: "✅ PlayStation 1 BIOS installed — PS1 games are now playable!"
- [ ] **BIOS Vault ↔ System Browser link:** Clicking "Upload" on the PS1 card in System Browser should deep-link to BIOS Vault, or open an inline upload modal.

### 🆕 My Additions

- [ ] **BIOS file size pre-check:** Before even hashing, check file size. PS1 BIOS should be ~512KB. If someone uploads a 50MB file named `scph5501.bin`, warn immediately: "This file is much larger than expected for a PS1 BIOS (expected ~512KB, got 50MB)."
- [ ] **Multi-BIOS systems awareness:** Some systems need multiple BIOS files (e.g., Saturn needs 3). The Vault should show all required files for each system, not just one. Group them under the system heading.
- [ ] **BIOS drag-to-system:** If user drags a BIOS file onto a system card in System Browser, detect it's a BIOS (by filename match) and offer to store it.

---

## Phase 3 — Library Becomes the Heart (Days 4–5)

**Current state: The Library has real structure** — search bar, mode toggle, grid/list views, game card with system badge. It just needs the "delight" layer and the fix for misdetected systems.

### Fixes & Additions

- [ ] **Fix system badge accuracy** (from Phase 0.5 — ensure normalizer's `systemId` is used, not a guess)
- [ ] **Play button on card hover:** Hovering over a game card should reveal a centered play button (▶) with a subtle scale-up animation. Clicking it launches immediately.
- [ ] **Card cover art placeholder:** Instead of a plain black rectangle, show a system-colored gradient or a retro pattern with the system's icon watermarked. (e.g., GBA card gets a purple-to-blue gradient with a faint GBA logo)
- [ ] **Cover art upload:** Click the cover area → file picker for a `.jpg`/`.png`. Store in OPFS, display on card.
- [ ] **Game context menu:** Right-click (or long-press mobile) on card:
  - Play
  - View Details
  - Export Save
  - Remove from Library
  - Set Cover Art
- [ ] **"Quick play" from card:** Single-click launches game (don't require navigating to a detail page first)
- [ ] **Sort controls:** Sort by: Name, System, Last Played, Date Added, Playtime
- [ ] **Library sections when populated:** "Recently Played" (top carousel or row), "Favorites" (if any), then "All Games"
- [ ] **Multi-file drop support:** Drop a folder or multiple files → batch-detect → add all valid ROMs → show summary toast: "Added 12 games (3 NES, 5 GBA, 4 SNES)"
- [ ] **Duplicate detection:** If user drops a ROM they already have (by filename or hash), warn: "This game is already in your library" with option to replace or skip.

### 🆕 My Additions

- [ ] **Empty state upgrade:** When the library has 0 games, the current drop zone is fine but add more visual warmth — a retro console illustration, animated dotted border on hover, and the text should say "Drop ROMs here — or click to browse" (make the whole zone clickable for file picker)
- [ ] **Game card title cleanup:** Strip common filename cruft automatically: remove region tags like "(En,Fr,De,Es,It)", "(USA)", "(Europe)", version tags like "[!]", "(Rev A)" — show the clean title on the card, but keep the full filename in the detail view. Example: "Super Mario Advance 4 - Super Mario Bros. 3 (Europe) (En,Fr,De,Es,It).zip" → display as "Super Mario Advance 4 - Super Mario Bros. 3"
- [ ] **Search suggestions:** As user types in search, show matching system names too (typing "nin" suggests "Nintendo Entertainment System" as a filter chip)
- [ ] **Keyboard navigation:** Arrow keys to navigate between cards, Enter to launch, Delete to remove
- [ ] **Virtual grid:** Use `@tanstack/react-virtual` for the game grid from day one. If someone imports 500+ ROMs, rendering all cards will lag.
- [ ] **Persist grid/list preference:** Save the toggle state in Zustand/localStorage so it persists across sessions.

---

## Phase 4 — Saves Vault That Never Loses Progress (Days 5–6)

**Current state: Structure is excellent** — SRAM/States stats cards, Import button, empty state. Now needs to actually fill with data.

### Fixes & Additions

- [ ] **Auto SRAM save** every 45 seconds during gameplay + on `beforeunload` + on `visibilitychange` (tab switch / minimize)
- [ ] **Save-state slots (0–9)** with:
  - Thumbnail (capture canvas screenshot at save time)
  - Timestamp ("Saved 2 min ago" / "Feb 28, 3:42 PM")
  - File size
  - Core version tag
- [ ] **Save-state UI in Saves Vault:** Group by game → expand to see slots → click to view details / export / delete
- [ ] **One-click "Export all saves for this game"** → downloads a `.zip`
- [ ] **"Export All"** → downloads everything (all games' SRAM + states) as one `.zip`
- [ ] **Import via drag-drop** — drop a save `.zip` → auto-match by game filename → confirm → import
- [ ] **Save integrity check:** If a save file write was interrupted (e.g., browser crashed mid-flush), detect the corrupted save and warn instead of silently loading garbage data
- [ ] **Delete with undo:** Deleting a save shows a 10-second undo toast before actually removing from OPFS

### 🆕 My Additions

- [ ] **"Quick Resume" badge on Library cards:** If a game has a recent auto-save (< 24 hours old), show a small "▶ Resume" badge on the library card. Clicking it loads the auto-save state instead of starting fresh.
- [ ] **Auto-save indicator during gameplay:** A small, non-intrusive save icon (💾) flashes briefly in the corner every time an auto-save completes. Never blocks gameplay.
- [ ] **Save versioning:** Tag every save with the core version that created it. If the core is updated, show a one-time warning: "This save was created with fceumm 1.22.0. You're now on 1.23.0. It should still work, but we've kept a backup just in case." Automatically back up the save before first load on a new core version.
- [ ] **Per-game save detail page:** Clicking a game row in Saves Vault shows: all SRAM files, all save state slots (with thumbnails), total size, export/import/delete-all options.
- [ ] **Stats on the Vault page once populated:** "Total saves: 47 across 12 games · 156 MB used" — gives a sense of how much data the user has.

---

## Phase 5 — Input System (Days 6–7)

### Fixes & Additions

- [ ] **Gamepad API auto-detection:** When a controller is connected, show a toast: "🎮 Xbox Controller connected" (or PlayStation, generic, etc. — detect by vendor ID)
- [ ] **Visual remapping UI:** Show an SVG controller diagram. Click a button on the diagram → prompt "Press the button you want to map" → wait for physical input → save.
- [ ] **Per-system defaults:** Ship sensible default mappings:
  - NES: A → Z, B → X, Start → Enter, Select → Shift, D-pad → Arrows
  - SNES: adds Y → A, X → S, L → Q, R → W
  - GBA: similar to SNES
  - PS1: adds analog sticks, triggers
- [ ] **Per-game overrides:** On the game detail page, allow custom mappings that override the system default.
- [ ] **Keyboard shortcut reference:** Press `?` anywhere → modal showing all keyboard shortcuts.
- [ ] **Mobile virtual controls:**
  - Auto-show when touch device is detected during gameplay
  - System-appropriate layout (NES = D-pad + 2 buttons, SNES = D-pad + 4 buttons + L/R, etc.)
  - Configurable opacity + size
  - Draggable positioning (save per system)

### 🆕 My Additions

- [ ] **Analog stick deadzone slider:** Some controllers have drift. Expose a simple deadzone slider in the input settings (default 15%).
- [ ] **"Test input" mode:** A page/modal where the user can press buttons and see which inputs the app detects. Helpful for debugging mapping issues.
- [ ] **Haptic feedback:** Use the Gamepad haptic actuator API for rumble where the core supports it (e.g., N64, PS1 with DualShock).
- [ ] **Save controller profile:** If a user has multiple controllers (Xbox + PS5), let them save named profiles and switch between them.

---

## Phase 6 — Architecture & Emulation Runtime Layer (Day 7 + ongoing)

**This is the foundation that makes everything above clean and maintainable instead of spaghetti.**

### 6.1 Emulation Runtime Service

A single module that owns the entire emulation lifecycle. The UI never touches emulator internals directly.

```typescript
// emulation-runtime.ts

class EmulationRuntime {
  private instance: NostalgistInstance | null = null;

  async launch(options: LaunchOptions): Promise<void> {
    // 1. Normalize ROM (extract ZIP if needed)
    const normalized = await normalizeROM(options.file);

    // 2. Resolve core
    const coreConfig = resolveCoreConfig(normalized.systemId);

    // 3. Check + load BIOS
    const bios = await loadBiosFiles(coreConfig.biosRequired);
    if (!bios.allPresent) {
      throw new MissingBIOSError(bios.missing);
    }

    // 4. Fetch core (with progress callback)
    const coreAssets = await fetchCore(coreConfig, options.onProgress);

    // 5. Launch emulator
    this.instance = await Nostalgist.launch({
      core: coreAssets,
      rom: { filename: normalized.filename, content: normalized.blob },
      bios: bios.files,
      retroarchConfig: this.buildConfig(coreConfig),
    });

    // 6. Start auto-save interval
    this.startAutoSave(normalized);
  }

  async saveState(slot: number): Promise<SaveStateResult> { /* ... */ }
  async loadState(slot: number): Promise<void> { /* ... */ }
  async reset(): Promise<void> { /* ... */ }
  async shutdown(): Promise<void> { /* flush saves, destroy instance */ }

  getScreenshot(): Blob { /* capture canvas */ }
}
```

### 6.2 Capability Matrix

Each system/core declares its capabilities. The UI reads this to show/hide features automatically.

```json
{
  "nes": {
    "cores": {
      "fceumm": {
        "supportsZippedContent": false,
        "requiresBios": false,
        "supportsSaveStates": true,
        "supportsRewind": true,
        "supportsRunAhead": true,
        "supportsThreading": false,
        "maxSaveSlots": 10
      }
    }
  },
  "ps1": {
    "cores": {
      "duckstation": {
        "supportsZippedContent": false,
        "requiresBios": true,
        "supportsSaveStates": true,
        "supportsRewind": false,
        "supportsThreading": true,
        "maxSaveSlots": 10
      }
    }
  }
}
```

**The UI reads this:** If `supportsRewind: false`, the rewind button is hidden/disabled for that system. If `supportsThreading: true` and the environment supports it, show "Performance mode" toggle.

### 6.3 Core Hosting — Same-Origin, Pinned

```
/public/cores/
  fceumm/
    1.22.0/
      fceumm_libretro.js
      fceumm_libretro.wasm
  mgba/
    0.10.3/
      mgba_libretro.js
      mgba_libretro.wasm
  duckstation/
    0.1.7823/
      duckstation_libretro.js
      duckstation_libretro.wasm
```

`coreMap.json` references these paths — never external CDN URLs as primary.

### 6.4 Storage Layer Abstraction

```typescript
// storage.ts — clean API that can swap backends later

interface StorageLayer {
  // ROM storage (optional, only if "Add to Library" is on)
  saveROM(id: string, blob: Blob): Promise<void>;
  loadROM(id: string): Promise<Blob | null>;
  deleteROM(id: string): Promise<void>;

  // BIOS storage
  saveBIOS(filename: string, blob: Blob): Promise<void>;
  loadBIOS(filename: string): Promise<Blob | null>;

  // Save data (SRAM + states)
  saveSRAM(gameId: string, data: ArrayBuffer): Promise<void>;
  loadSRAM(gameId: string): Promise<ArrayBuffer | null>;
  saveState(gameId: string, slot: number, data: ArrayBuffer, screenshot?: Blob): Promise<void>;
  loadState(gameId: string, slot: number): Promise<ArrayBuffer | null>;

  // Metadata (Dexie)
  getLibrary(): Promise<GameEntry[]>;
  updateGame(id: string, updates: Partial<GameEntry>): Promise<void>;

  // Quota
  getUsageEstimate(): Promise<{ usedMB: number; totalMB: number }>;
}
```

---

## Phase 7 — Settings Page Buildout (Day 7)

**Current state: Only 2 sections (Storage Usage + Performance).** Needs to be the app's control center.

### Add These Sections

```
Settings
├── Storage Usage .............. ✅ exists (3 MB / 2048 MB meter)
├── Performance & Compatibility  ✅ exists (threading status)
├── Display .................... 🆕
│   ├── Default shader preset (None / CRT / Scanlines / Sharp)
│   ├── Default aspect ratio (Original / Stretch / Integer)
│   ├── VSync toggle
│   └── FPS counter (Show / Hide)
├── Audio ...................... 🆕
│   ├── Master volume slider (0–150%)
│   ├── Audio latency (Auto / Low / Normal)
│   └── Audio driver info
├── Input ...................... 🆕
│   ├── Connected controllers list
│   ├── Default keyboard mapping
│   ├── "Remap controls" button → opens mapper
│   └── Touch control settings (opacity, size, layout)
├── Saves ...................... 🆕
│   ├── Auto-save interval (30s / 60s / 2min / Off)
│   ├── Auto-save on exit (on/off)
│   ├── Default save slot
│   └── Save versioning (on/off)
├── Data Management ............ 🆕
│   ├── Clear ROM cache (keeps saves)
│   ├── Clear all saves (export first!)
│   ├── Clear BIOS files
│   ├── Clear everything (double confirm)
│   ├── Export full backup (.zip)
│   └── Import backup (.zip)
├── Legal & Privacy ............ 🆕
│   ├── Legal disclaimer (text)
│   ├── Privacy policy (we store nothing remotely)
│   ├── Open source licenses
│   └── Analytics opt-in (off by default)
└── About ...................... 🆕
    ├── Version: v0.1.0
    ├── Environment: Chrome 125 / Windows
    ├── Threading: Enabled ✅
    ├── OPFS: Available ✅
    ├── IndexedDB: Available ✅
    └── GitHub link
```

### 🆕 My Additions

- [ ] **"Copy debug info" button** in About section: copies a formatted text block with version, browser, threading status, storage quota, number of installed BIOS, etc. — perfect for bug reports.
- [ ] **Settings search:** If there are many sections, add a search/filter at the top so users can quickly find what they need.
- [ ] **Reset to defaults:** Each section gets a small "Reset" link that restores factory settings for that category only.

---

## Phase 8 — UI/UX Polish Pass (Pencil Workflow) (Days 8–9)

### Wireframe Every State

Open Pencil and wireframe these specific states:

1. **Library:** Empty state, 1 game, 20+ games (grid and list views), during drag-drop overlay
2. **Library card:** Default, hover (play button visible), playing indicator, has-resume-save badge
3. **Player:** Loading, playing, overlay open, error state, iOS tap-to-start
4. **BIOS Vault:** Empty, partially filled, fully ready
5. **Saves Vault:** Empty, populated with multiple games, per-game expanded view
6. **System Browser:** Fully Supported tab, Experimental tab, system detail expanded
7. **Settings:** Full page with all sections
8. **Modals:** BIOS missing (launch blocker), ZIP multiple ROMs picker, delete confirmation, first-visit legal disclaimer
9. **Mobile:** All pages at 375px width, player in landscape with touch controls

Export all wireframes to `/docs/wireframes/` and commit them as the design spec.

### Visual Polish Checklist

- [ ] **Card hover states:** Subtle lift (`translate-y-[-2px]`) + border glow on hover
- [ ] **Micro-animations:** `framer-motion` for page transitions, modal entrances, card additions to grid
- [ ] **Typography hierarchy:** Ensure headings are visually distinct from body text (weight + size + spacing). Currently some headings feel a bit flat.
- [ ] **Accent color consistency:** The green "Enabled" badge, yellow "Upload" button, and blue "0 Bytes" text use different accent colors. Establish a deliberate accent palette: green = good/success, yellow = warning/action needed, red = error/missing, blue = info/primary.
- [ ] **Card contrast:** The system cards in System Browser are slightly low-contrast (dark cards on dark background). Add a subtle border or slightly lighter card background (`bg-zinc-800` vs `bg-zinc-900`).
- [ ] **Empty state illustrations:** Commission or source simple SVG illustrations for empty states (gamepad, disc, save floppy) instead of just icons.
- [ ] **Sidebar active indicator:** Add a left accent bar (2px, colored) on the active nav item for stronger visual feedback.

---

## Phase 9 — Mobile & PWA (Day 10)

- [ ] **PWA manifest:** app name, icons (192 + 512), theme color matching dark theme, `display: standalone`
- [ ] **Landscape lock** during gameplay (`screen.orientation.lock('landscape')`)
- [ ] **Responsive sidebar:** Collapses to bottom tab bar or hamburger on `< 768px`
- [ ] **Touch targets:** Minimum 44×44px on all interactive elements
- [ ] **Prevent pull-to-refresh during gameplay:** `overscroll-behavior: none` on player route
- [ ] **Wake lock during gameplay:** `navigator.wakeLock.request('screen')` to prevent screen dim
- [ ] **Notch / safe area handling:** `padding: env(safe-area-inset-*)` on player canvas and touch controls
- [ ] **Add-to-homescreen banner** after 2nd visit

---

## Phase 10 — Testing & Regression (Ongoing)

### Automated Tests

```
Playwright E2E:
  ✓ Drop .zip containing .gba → normalizer extracts → core loads → frames render
  ✓ Drop bare .nes → detected as NES → core loads → frames render
  ✓ Drop .zip with no valid ROM → error toast appears
  ✓ Drop .zip with multiple ROMs → picker modal appears
  ✓ PS1 .chd without BIOS → "BIOS Missing" modal blocks launch
  ✓ Upload BIOS → PS1 .chd → game boots
  ✓ Play game → auto-save fires → close tab → reopen → save exists
  ✓ Save state → load state → game resumes at correct point
  ✓ RetroArch console text "Failed to extract" NEVER appears (regression test)
  ✓ RetroArch menu UI NEVER appears (regression test)

Vitest Unit:
  ✓ normalizeROM('.zip' containing '.gba') → returns { systemId: 'gba' }
  ✓ normalizeROM('.zip' containing '.nes' + '.txt') → ignores .txt, returns .nes
  ✓ normalizeROM('.zip' containing 2 ROMs) → throws 'zip_multiple_roms'
  ✓ normalizeROM('.zip' with no ROMs) → throws 'zip_no_rom'
  ✓ normalizeROM('.gba') → passes through as-is
  ✓ normalizeROM('.exe') → throws 'unsupported_format'
  ✓ detectSystemFromHeader(gba_bytes) → 'gba'
  ✓ detectSystemFromHeader(nes_bytes) → 'nes'
  ✓ BIOS hash validation passes for known-good files
  ✓ BIOS hash validation warns for unknown hash
  ✓ Storage layer: write save → read save → matches
```

### CI Pipeline

```
PR → lint + typecheck → Vitest unit → Vite build → Playwright E2E (Chrome) → merge
Release → full cross-browser (Chrome + Firefox + Safari) → deploy staging → smoke test → production
```

---

## Phase 11 — Feature Platform ("1000s of Features" Done Right)

### The Principle

Don't add 1000 random buttons. Build a **modular system** so adding features becomes cheap and safe.

### Module System

Each module is a self-contained feature that plugs into the app:

| Module | Description | Priority |
|---|---|---|
| **Library Tags/Collections** | User-created playlists, custom tags | High |
| **Box Art** | Cover art upload + optional API lookup | High |
| **Shaders Gallery** | Browse + preview + apply shader presets | Medium |
| **Cheats** | Load cheat files, toggle cheats in-game | Medium |
| **Achievements** | RetroAchievements API (user provides token) | Medium |
| **Speedrun Tools** | Timer overlay, splits, save-locking | Low |
| **Replay Recorder** | Record input log, replay later | Low |
| **Netplay** | WebRTC-based multiplayer | Future |
| **Accessibility** | Font scaling, high contrast, colorblind modes | Medium |
| **Themes** | Light mode, custom accent colors, retro themes | Low |

### Per-Game Configuration Overrides

Every setting (shader, aspect ratio, volume, controller mapping, core selection) should be overridable per game:

```json
{
  "gameId": "super-mario-advance-4",
  "overrides": {
    "shader": "crt-royale",
    "aspectRatio": "4:3",
    "volume": 80,
    "controllerProfile": "gba-custom-1",
    "core": "mgba"
  }
}
```

If no override exists, fall back to the system default. If no system default, fall back to global default.

---

## Concrete Next 7-Day Sprint

| Day | Focus | Deliverable |
|---|---|---|
| **Day 1** | **ROM Normalizer** | `normalizeROM()` with zip.js, header detection, wired into launch pipeline. Test with the Super Mario Advance 4 ZIP that's currently failing. |
| **Day 2** | **Player loading + layout** | Loading overlay with progress. Hide sidebar during play. Error overlay (not black screen). First frame visible. |
| **Day 3** | **BIOS Vault polish + PS1** | Hash validation, filename normalization, "Test BIOS" flow. Attempt PS1 boot with BIOS uploaded. |
| **Day 4** | **Library polish** | Play-on-hover, card cover placeholders, title cleanup, sort controls. Fix system badge from normalized data. Pencil wireframes started. |
| **Day 5** | **Save system live** | Auto-SRAM every 45s, save-state slots with thumbnails, Saves Vault populated, export/import. |
| **Day 6** | **Input mapper + overlay** | Gamepad detection, basic visual mapper, player overlay (save/load/reset/fullscreen), keyboard shortcuts. |
| **Day 7** | **Settings + testing + v0.2.0** | Settings page buildout, Playwright tests for normalizer + boot + save, "Copy debug info", ship v0.2.0. |

---

## Priority Summary

| Priority | What | Why | Time |
|---|---|---|---|
| 🔴 **P0 (now)** | ROM Normalizer — extract ZIPs in JS | Games literally don't load without this | 4–6 hours |
| 🔴 **P0 (now)** | Fix system misdetection (NES badge on GBA game) | Users see wrong info, affects core selection | 1–2 hours |
| 🟠 **P1 (today)** | Player loading states + error overlay | Black screen = "is it broken?" | 3–4 hours |
| 🟠 **P1 (today)** | Player layout — hide sidebar during play | Game canvas is cramped | 1 hour |
| 🟡 **P2 (this week)** | BIOS hash validation + PS1 test | Unlocks an entire new system tier | Half day |
| 🟡 **P2 (this week)** | Library play-on-hover + card polish | Makes the Library feel alive | Half day |
| 🟢 **P3 (next week)** | Save system live | Core retention feature | 1–2 days |
| 🟢 **P3 (next week)** | Input mapper | Console-grade feel | 1–2 days |
| ⚪ **P4 (ongoing)** | Settings buildout, PWA, testing, modules | Polish + platform | Ongoing |

The single most impactful thing you can do right now is implement `normalizeROM()` with `@zip.js/zip.js` and test it against that Super Mario Advance 4 ZIP. Once ROMs load, everything else becomes testable and the app becomes usable.
