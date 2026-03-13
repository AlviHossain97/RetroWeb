# PiStation (RetroWeb) — How It Works

> A comprehensive deep-dive into the architecture, data flow, and inner workings of PiStation — a fully client-side, browser-based retro game emulator PWA.

---

## Table of Contents

1. [High-Level Architecture](#1-high-level-architecture)
2. [Tech Stack](#2-tech-stack)
3. [Application Startup & Entry Point](#3-application-startup--entry-point)
4. [Routing & Navigation](#4-routing--navigation)
5. [The App Shell](#5-the-app-shell)
6. [Theming System](#6-theming-system)
7. [Data Layer (IndexedDB via Dexie)](#7-data-layer-indexeddb-via-dexie)
8. [ROM Import & Normalization Pipeline](#8-rom-import--normalization-pipeline)
9. [System & Core Detection](#9-system--core-detection)
10. [The Emulation Runtime](#10-the-emulation-runtime)
11. [Save System (States, SRAM, Auto-Save)](#11-save-system-states-sram-auto-save)
12. [BIOS Management](#12-bios-management)
13. [Metadata Scraping (Box Art)](#13-metadata-scraping-box-art)
14. [Gamepad & Input System](#14-gamepad--input-system)
15. [Netplay (WebRTC P2P)](#15-netplay-webrtc-p2p)
16. [AI Chat Integration](#16-ai-chat-integration)
17. [PWA & Service Worker](#17-pwa--service-worker)
18. [Internationalization (i18n)](#18-internationalization-i18n)
19. [Accessibility](#19-accessibility)
20. [Achievement System](#20-achievement-system)
21. [Build System & Configuration](#21-build-system--configuration)
22. [Testing](#22-testing)
23. [Page-by-Page Breakdown](#23-page-by-page-breakdown)
24. [Data Flow Diagrams](#24-data-flow-diagrams)

---

## 1. High-Level Architecture

PiStation is a **zero-backend, privacy-first Progressive Web App** that emulates retro game consoles entirely in the browser. There are no servers, no accounts, no cloud storage — everything runs on the user's device.

```
┌─────────────────────────────────────────────────────────┐
│                    Browser (Client)                      │
│                                                         │
│  ┌──────────┐  ┌──────────┐  ┌───────────────────────┐ │
│  │  React   │  │  Zustand  │  │   IndexedDB (Dexie)   │ │
│  │  19 UI   │  │  Stores   │  │  Games, Saves, BIOS   │ │
│  └────┬─────┘  └────┬─────┘  └───────────┬───────────┘ │
│       │              │                    │             │
│  ┌────┴──────────────┴────────────────────┴──────────┐ │
│  │              Nostalgist (Emulator Engine)          │ │
│  │         RetroArch WASM + libretro Cores           │ │
│  └───────────────────┬───────────────────────────────┘ │
│                      │                                  │
│  ┌───────────────────┴───────────────────────────────┐ │
│  │             <canvas> Rendering                    │ │
│  │        + Web Audio API + Gamepad API              │ │
│  └───────────────────────────────────────────────────┘ │
│                                                         │
│  ┌──────────────────┐  ┌──────────────────────────┐    │
│  │   Service Worker  │  │   Origin Private FS      │    │
│  │   (Workbox PWA)   │  │   (ROM Binary Storage)   │    │
│  └──────────────────┘  └──────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
```

**Core principles:**
- All game data (ROMs, saves, BIOS files) is stored in IndexedDB and the Origin Private File System (OPFS)
- Emulation happens via WebAssembly (WASM) libretro cores managed by the Nostalgist library
- The app is installable as a PWA with full offline support
- SharedArrayBuffer is used for multi-threaded emulation cores (requires COOP/COEP headers)

---

## 2. Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Framework** | React 19 | Component-based UI |
| **Language** | TypeScript (strict mode) | Type safety |
| **Build** | Vite 7 | HMR, bundling, dev server |
| **Styling** | Tailwind CSS v4 + shadcn/ui | Utility-first CSS + component library |
| **State** | Zustand | Lightweight global stores |
| **Database** | Dexie (IndexedDB wrapper) | Client-side persistent storage |
| **Emulation** | Nostalgist (RetroArch WASM) | libretro core lifecycle management |
| **Routing** | react-router v7 | SPA routing with lazy-loaded routes |
| **Icons** | lucide-react | Consistent icon set |
| **Toasts** | sonner | User notifications |
| **PWA** | vite-plugin-pwa + Workbox | Service worker, offline caching |
| **Archive** | @zip.js/zip.js | Client-side ZIP extraction |
| **Virtualization** | react-virtuoso | Efficient rendering of large lists |
| **Hashing** | Web Crypto API + custom MD5 | ROM identification, BIOS validation |

---

## 3. Application Startup & Entry Point

### `start.mjs` — Multi-Service Launcher

The startup script orchestrates four parallel services using Node.js `child_process.spawn()`:

1. **Ollama** — Local LLM inference server (`localhost:11434`)
2. **Kokoro TTS** — Text-to-speech server (`localhost:8787`)
3. **Whisper STT** — Speech-to-text server (`localhost:8786`)
4. **Vite dev server** — The application itself (`localhost:5173`)

Each process has prefixed stdout/stderr logging and the script implements graceful shutdown via SIGINT/SIGTERM with a 2-second timeout.

> **Note:** The AI services (Ollama, Kokoro, Whisper) are optional local services. The core emulator works entirely without them.

### `src/main.tsx` — React Entry Point

```
main.tsx
  └─ <BrowserRouter>
       └─ <Suspense fallback={Spinner}>
            └─ <Routes>
                 ├─ /login → LoginPage
                 └─ / → <App> (shell)
                      ├─ /        → Home
                      ├─ /library → Library
                      ├─ /play    → Play (emulator)
                      ├─ /systems → Systems
                      ├─ /settings→ Settings
                      ├─ /bios    → BIOS Vault
                      ├─ /saves   → Save Manager
                      ├─ /controller → Controller Test
                      ├─ /chat    → AI Chat
                      ├─ /achievements → Achievements
                      ├─ /stats   → Statistics
                      └─ /romhacks → ROM Hacks
```

**Key pattern:** Every route is lazy-loaded via `React.lazy()` and wrapped in `<Suspense>`. This means only the code for the current page is downloaded, keeping the initial bundle small. The Suspense fallback renders an animated spinner using the app's theme color (`--accent-primary`).

---

## 4. Routing & Navigation

React Router v7 with `BrowserRouter` handles all navigation. Routes are organized as:

- **`/login`** — Standalone route (outside the App shell)
- **`/` (App shell)** — Parent route containing the navigation UI, with child routes for each page

### Route Lazy Loading

Each route component is imported with `React.lazy()`:

```typescript
const Home = lazy(() => import("./routes/home"));
const Library = lazy(() => import("./routes/index"));
const Play = lazy(() => import("./routes/play"));
// ... etc
```

This means:
- **Initial load** only downloads the shared shell + the current page's code
- **Navigation** triggers on-demand chunk downloads
- **Suspense boundaries** show a spinner during chunk loading

---

## 5. The App Shell

### `src/App.tsx` — The Root Layout

The App component is the persistent shell wrapping all pages. It manages:

#### Authentication Gate
```
sessionStorage["retroweb.loggedIn"] === "true"  →  Show app
Otherwise  →  Redirect to /login
```
This is a simple demo gate — there is no real authentication backend.

#### Dual Navigation

- **Desktop** (hidden on mobile): A fixed left-side nav bar with icon buttons that expand on hover to show labels. Custom CSS animations handle the hover expansion effect.
- **Mobile** (`md:` breakpoint and below): A fixed bottom tab bar with 5 key routes — Home, Library, Chat, Saves, Settings.

When the user is on the `/play` route, both navigation UIs are hidden and the main content area expands to fill the full viewport.

#### Global Drag & Drop (BIOS Upload)

The entire app window is a drop zone for BIOS files. When a file is dragged over (outside the `/play` route), a validation overlay appears. The file is validated against known BIOS filenames and stored in IndexedDB with MD5 hash verification.

#### PWA Installation

The shell listens for the `beforeinstallprompt` browser event and shows an install banner (bottom-left, dismissible). It also monitors the service worker for updates and displays a toast notification when a new version is available.

#### Theme Initialization

On mount, the shell reads settings from `localStorage["retroweb.settings.v1"]` and applies:
- The `data-theme` attribute to `<html>` (controls CSS custom property values)
- Accessibility CSS classes (`a11y-high-contrast`, `a11y-large-text`, `a11y-reduced-motion`)

#### Lazy-Loaded Overlays

Several non-critical UI components are lazy-loaded to avoid bloating the initial bundle:
- `LegalModal` — Terms & conditions popup
- `CookieConsent` — Cookie banner
- `PacmanGhostEasterEgg` — Animated Pac-Man ghost
- `PongBackground` — Animated Pong game background
- `OnboardingTutorial` — First-time user walkthrough
- `NotificationCenter` — Push notification manager

---

## 6. Theming System

### Architecture

PiStation uses **CSS custom properties** (variables) for multi-theme support. Themes are toggled by setting the `data-theme` attribute on the `<html>` element.

### Available Themes

| Theme | Attribute | Aesthetic |
|-------|-----------|-----------|
| **Default (Dark)** | *(none)* | Dark background (#0d0d10), red accent (#cc0000), cyan glows |
| **NES Classic** | `data-theme="nes-classic"` | Light gray (#e0e0e0), red accent, retro pixel feel |
| **Game Boy** | `data-theme="gameboy"` | Green monochrome (#9bbc0f on #0f380f), original DMG colors |
| **SNES Purple** | `data-theme="snes-purple"` | Deep purple (#1a1030), violet accent (#8b5cf6) |
| **Terminal Green** | `data-theme="terminal-green"` | CRT green (#00ff00) on black (#0a0a0a) |

### Core CSS Variables

Defined in `src/index.css`:

```css
:root {
  --surface-1: #0d0d10;        /* Primary background */
  --surface-2: #1a1a2e;        /* Elevated surfaces */
  --border-soft: #2a2a3e;      /* Subtle borders */
  --accent-primary: #cc0000;   /* Brand/action color */
  --accent-secondary: #00e5ff; /* Secondary accent */
  --text-primary: #e0e0e0;     /* Main text */
  --text-muted: #888;          /* De-emphasized text */
}
```

Each theme overrides these variables via `[data-theme="..."]` selectors.

### Animations

Custom CSS keyframe animations support the retro aesthetic:
- **`flicker`** — Cyan border flicker with shadow glow (CRT effect)
- **`shimmer`** — Background position animation
- **`carousel-rotate`** — 3D perspective card rotation
- **`glow-pulse`** — Expanding glow effect for neon elements

### Typography

- **Primary font:** "RoSpritendo" — A retro pixel-style OTF font loaded from `/public/fonts/`
- **Fallback:** Ubuntu, then system sans-serif
- Font weight 600, applied globally via `@font-face`

### Tailwind CSS v4 Integration

Tailwind v4 is configured via the `@tailwindcss/vite` plugin (no separate `tailwind.config.js`). The theme is defined inline in CSS using `@theme inline` blocks. shadcn/ui components are imported from `@/components/ui/` using the new-york variant.

---

## 7. Data Layer (IndexedDB via Dexie)

### Database: `RetroWebDB`

All persistent data is stored client-side in IndexedDB, accessed through Dexie (a typed IndexedDB wrapper). The database has 4 schema versions with incremental migrations.

### Tables & Entities

#### `games` — Game Metadata

```typescript
interface Game {
  id: string;              // Unique identifier
  title: string;           // Cleaned display name
  filename: string;        // Original ROM filename
  system: string;          // System ID (nes, snes, gb, etc.)
  coreId: string;          // libretro core used
  romHash: string;         // SHA-256 hash for dedup
  addedAt: number;         // Timestamp
  lastPlayed?: number;     // Last play timestamp
  playtimeSeconds: number; // Accumulated playtime
  isFavorite: boolean;
  coverUrl?: string;       // LibRetro thumbnail URL
  collections: string[];   // Collection IDs
  rating?: number;         // 1-5 stars
  cheats?: string;         // User cheat codes
  notes?: string;          // User notes
  tags?: string[];         // Custom tags
}
```

Indexes: `id`, `title`, `system`, `addedAt`, `lastPlayed`, `isFavorite`, `romHash`

#### `saves` — Save States & SRAM

```typescript
interface SaveData {
  id: string;              // Composite: [filename+type]
  filename: string;        // Associated game filename
  type: "sram" | "state";  // SRAM (battery save) or save state
  data: Uint8Array;        // Binary save data
  coreId: string;          // Core that created it
  timestamp: number;
  slot?: number;           // Save state slot index
  image?: Blob;            // Screenshot thumbnail
}
```

#### `bios` — BIOS Firmware Files

```typescript
interface BIOSFile {
  filename: string;        // e.g., "scph5501.bin"
  data: Uint8Array;        // Binary content
  system: string;          // Target system
  variant?: string;        // Regional variant
  md5?: string;            // Hash for verification
  size: number;
  expectedSize?: number;
  source?: string;         // Upload method
  addedAt: number;
}
```

#### `chatMessages` — AI Chat History
#### `collections` — Custom Game Collections
#### `achievements` — Unlocked Achievement Tracking

### ROM Binary Storage (OPFS)

ROM files themselves are too large for IndexedDB in some browsers, so they use the **Origin Private File System (OPFS)**:

```
OPFS: /roms/{gameId} → ROM binary data
```

Functions: `saveRomToOPFS()`, `loadRomFromOPFS()`, `removeRomFromOPFS()`

### Key Database Operations

| Function | Purpose |
|----------|---------|
| `saveGameMetadata(game)` | Persist full game record |
| `getAllGames()` | Retrieve all games (reverse chronological) |
| `recordGameplaySession(id, start, end)` | Accumulate playtime |
| `markGameAutoSaved(id)` | Timestamp auto-save |
| `updateGameMetadata(id, partial)` | Partial updates |
| `saveSRAM(filename, core, data)` | Store SRAM data |
| `loadSRAM(filename)` | Retrieve SRAM for game |
| `saveState(filename, core, data, image, slot)` | Store save state with thumbnail |
| `loadState(filename, slot)` | Retrieve save state |
| `saveBIOS(filename, data, system, variant)` | Store with MD5 validation |
| `loadBIOS(filename)` | Retrieve BIOS (with family fallback) |

---

## 8. ROM Import & Normalization Pipeline

### `src/lib/emulation/rom-normalizer.ts`

When a user uploads a ROM file, it goes through a multi-stage normalization pipeline:

```
User drops file
      │
      ▼
┌─────────────────┐
│ Extension Check  │ ─── Ignored extension? (.txt, .jpg, etc.) → Reject
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  ZIP Archive?    │ ─── Yes → Extract & filter ROM candidates
└────────┬────────┘         │
         │                  ├── 0 ROMs found → Error: zip_no_rom
         │                  ├── 1 ROM found  → Continue with extracted ROM
         │                  └── N ROMs found → Error: zip_multiple_roms (with candidates)
         │
         ▼
┌─────────────────┐
│ Header Detection │ ─── Read first bytes to identify system:
└────────┬────────┘     • NES: bytes 0-3 = 4E 45 53 1A
         │              • GBA: bytes 0-3 = 2E 00 00 EA
         │              • Genesis: "SEGA" at offset 0x100
         │              • Game Boy: CE ED at offset 0x0104
         │              • SNES: Map mode check at 0x7fc0 or 0xffc0
         │              • N64: 80 37 12 40 (or byte-swapped variants)
         │
         ▼
┌─────────────────┐
│ Extension Fallback│ ─── If no header match, use file extension
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Disc Detection   │ ─── .chd/.pbp = disc format (PS1)
└────────┬────────┘     .cue/.iso = discouraged (need CHD conversion)
         │              .bin > 16MB = treated as disc, not cartridge
         ▼
  NormalizedROM {
    data: Blob,
    system: DetectedSystemKind,
    detectedBy: "header" | "extension" | "fallback"
  }
```

### Supported Extension Mappings

- **Cartridge formats (22+):** `.nes`, `.smc`, `.sfc`, `.gb`, `.gbc`, `.gba`, `.md`, `.smd`, `.gen`, `.bin`, `.n64`, `.z64`, `.v64`, `.nds`, `.pce`, `.ngp`, `.ngc`, `.ws`, `.wsc`, `.a26`, `.a78`, `.lnx`, `.jag`, `.col`, `.sg`, `.sms`, `.gg`
- **Disc formats (preferred):** `.chd`, `.pbp`
- **Disc formats (discouraged):** `.cue`, `.iso` (browser can't handle multi-file disc images)
- **Ignored:** `.txt`, `.nfo`, `.jpg`, `.png`, `.xml`, `.dat`, and 10+ other metadata formats

### Error Handling

The pipeline uses a custom `NormalizeError` class with specific error codes:

| Code | Meaning |
|------|---------|
| `unsupported_format` | Unknown file extension |
| `disc_format_requires_chd` | .cue/.iso needs conversion to .chd |
| `zip_no_rom` | ZIP contains no valid ROM files |
| `zip_multiple_roms` | ZIP contains multiple ROMs (user must choose) |
| `zip_entry_not_found` | Selected entry missing from ZIP |
| `zip_extract_failed` | Extraction error |

---

## 9. System & Core Detection

### `src/lib/detection/auto-detect.ts`

After ROM normalization identifies the system, the auto-detection module maps it to a specific emulator core:

```typescript
detectSystemByExtension(filename: string): DetectionResult | null
```

This function:
1. Extracts the file extension via regex
2. Special-cases `.chd` files (requires manual system selection since CHD is used by multiple systems)
3. Searches `coreMap.json` entries for a matching extension
4. Returns `{ systemId, coreId }` or an error message

### `src/data/coreMap.json` — System Definitions

| System | Preferred Core | Fallback Cores | Extensions | BIOS Required | Core Version |
|--------|---------------|----------------|------------|---------------|-------------|
| **NES** | fceumm | nestopia | `.nes`, `.zip` | No | 1.22.0 |
| **SNES** | snes9x | — | `.smc`, `.sfc`, `.zip` | No | 1.22.0 |
| **Game Boy / GBC / GBA** | mgba | gambatte | `.gb`, `.gbc`, `.gba`, `.zip` | No | 1.22.0 |
| **Sega Genesis** | genesis_plus_gx | picodrive | `.md`, `.smd`, `.gen`, `.bin`, `.zip` | No | 1.22.0 |
| **PlayStation 1** | pcsx_rearmed | duckstation | `.chd` | Yes (`scph5501.bin`) | 1.22.0 |

Core binaries are stored at: `/cores/{coreName}/{version}/{coreName}_libretro`

Each core consists of two files:
- `{coreName}_libretro.js` — JavaScript glue code
- `{coreName}_libretro.wasm` — Compiled WebAssembly binary

### `src/data/systemBrowserData.ts` — Display Metadata

Provides human-readable metadata for the Systems browser page:

```typescript
interface SystemInfo {
  id: string;
  name: string;               // "Nintendo Entertainment System"
  manufacturer: string;       // "Nintendo" | "Sega" | "Sony"
  era: string;                // "1983 · 8-bit"
  tier: "doable" | "experimental" | "coming_soon";
  extensions: string[];
  bios: string[];
  iconUrl?: string;
}
```

Six systems are defined: NES, SNES, Game Boy, Genesis, PS1, and N64 (experimental).

---

## 10. The Emulation Runtime

### `src/routes/play.tsx` — The Heart of PiStation

This is the most complex file in the codebase (~764 lines). It manages the complete emulator lifecycle.

### Boot Sequence

```
User clicks "Play" on a game
        │
        ▼
┌───────────────────┐
│ 1. Load ROM data   │  Read from OPFS or memory
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│ 2. Normalize ROM   │  ZIP extraction, header detection
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│ 3. Resolve core    │  system → coreMap → preferred core + fallbacks
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│ 4. Mount BIOS      │  Load required BIOS from IndexedDB (PS1 needs scph5501.bin)
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│ 5. Restore SRAM    │  Load previous SRAM data from IndexedDB
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│ 6. Cache check     │  Check Cache API for WASM core binary
└────────┬──────────┘  Download from /cores/ if not cached
         │
         ▼
┌───────────────────┐
│ 7. Nostalgist.launch() │  Initialize RetroArch WASM with:
└────────┬──────────┘     • Canvas element ref
         │                • ROM blob
         │                • SRAM blob (if exists)
         │                • BIOS files (if required)
         │
         ▼
┌───────────────────┐
│ 8. Auto-load state │  If autoLoadSlot specified, load save state
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│ 9. Start timers    │  • Auto-save interval (every 45s)
└────────┬──────────┘  • Visibility change listener
         │             • Window unload listener
         ▼
    🎮 PLAYING
```

### Nostalgist Integration

[Nostalgist](https://github.com/nicx/nostalgist) is a JavaScript library that wraps RetroArch compiled to WebAssembly. PiStation uses it to:

- **Initialize** a RetroArch instance attached to an HTML `<canvas>` element
- **Load ROMs** as Blob objects with optional SRAM and BIOS data
- **Save/load states** — `emulator.saveState()` returns `{ state: Blob, thumbnail?: Blob }`
- **Save/load SRAM** — `emulator.saveSRAM()` returns the battery save Blob
- **Send commands** — `emulator.sendCommand("SET fastforward_ratio 2")` for speed control
- **Exit** — `emulator.exit({ removeCanvas: false })` for cleanup

### In-Game Controls

| Key | Action |
|-----|--------|
| **F1** | Quick save to slot 0 |
| **F4** | Quick load from slot 0 |
| **F11** | Toggle fullscreen |
| **F2** | Cycle speed (0.5x → 1x → 2x → 4x) |
| **F3** | Toggle FPS counter |
| **F5** | Activate rewind (hold) |
| **F6** | Toggle speedrun timer |
| **F7** | Record speedrun split time |
| **ESC** | Toggle in-game menu/overlay |

### Speed Control

Speed cycles through `[0.5, 1, 2, 4]x` multipliers. Applied via RetroArch command:
```
emulator.sendCommand("SET fastforward_ratio {multiplier}")
```
Using speeds above 1x unlocks the "speed_demon" achievement.

### FPS Counter

Uses `requestAnimationFrame` to count rendered frames per second. A counter increments on each frame and resets every 1000ms, displaying the count as the FPS value.

### Picture-in-Picture

The canvas stream is captured at 30fps via `canvas.captureStream(30)`, fed into a `<video>` element, and then `requestPictureInPicture()` is called to float the game in a system-level PiP window.

### iOS Safari Handling

iPads and iPhones require a user gesture to start audio playback (autoplay policy). The emulator detects Safari/iOS and shows a "Tap to Start" overlay. On tap, it resumes the `AudioContext`.

### PSX Disc Swapping

For multi-disc PS1 games, the emulator sends RetroArch commands in sequence:
```
DISK_EJECT_TOGGLE → (200ms delay) → DISK_NEXT → (200ms delay) → DISK_EJECT_TOGGLE
```

### Cleanup

When leaving the play route:
1. Flush a final auto-save (reason: "unmount")
2. Record the gameplay session duration via `recordGameplaySession()`
3. Call `emulator.exit()` to shut down the WASM instance
4. Clear all intervals and event listeners

---

## 11. Save System (States, SRAM, Auto-Save)

PiStation has a comprehensive save system with three layers:

### Save States (Manual)

- **Save:** `emulator.saveState()` → captures the complete emulator state as a binary Blob
- **Thumbnail:** `captureThumbnail()` scales the canvas to 320px width and exports as JPEG (quality 0.62)
- **Storage:** `saveState(filename, coreId, stateData, thumbnailBlob, slotIndex)` writes to IndexedDB
- **Load:** `loadState(filename, slotIndex)` → retrieves the Blob → `emulator.loadState(blob)` restores it
- **Slots:** Multiple save slots per game (referenced by index)

### SRAM (Battery Saves)

- **Save:** `emulator.saveSRAM()` → extracts the in-game battery save (e.g., Pokémon save file)
- **Storage:** `saveSRAM(filename, coreId, sramData)` writes to IndexedDB
- **Restore:** On boot, `loadSRAM(filename)` retrieves previous SRAM and passes it to Nostalgist

### Auto-Save

A three-trigger auto-save system ensures saves are never lost:

1. **Interval timer** — Every 45 seconds, `flushAutoSave("interval")` fires
2. **Visibility change** — When the user switches tabs (`document.visibilityState === "hidden"`)
3. **Page unload** — When the browser window closes or navigates away
4. **Component unmount** — When leaving the `/play` route

Each auto-save:
- Calls `emulator.saveSRAM()` to get the latest SRAM
- Stores it via `saveSRAM()`
- Marks the game as auto-saved via `markGameAutoSaved(gameId)`
- Shows a visual pulse indicator (1.8s animation)

---

## 12. BIOS Management

### Why BIOS Files Are Needed

Some emulated systems (notably PlayStation 1) require original firmware (BIOS) files to boot. These files are copyrighted and cannot be distributed with the app — users must provide their own.

### BIOS Validation Pipeline

```
User uploads BIOS file (drag & drop or file picker)
        │
        ▼
┌───────────────────────┐
│ Filename Validation    │  Is this a known BIOS filename?
└────────┬──────────────┘  e.g., scph5501.bin → PS1
         │
         ▼
┌───────────────────────┐
│ MD5 Hash Computation   │  Compute MD5 of file contents
└────────┬──────────────┘
         │
         ▼
┌───────────────────────┐
│ Hash Verification      │  Compare against known-good MD5 hashes
└────────┬──────────────┘  PS1 scph5501.bin → expected: 924e392ed05558ffdb115408c263dccf
         │
         ▼
┌───────────────────────┐
│ Size Verification      │  Check file size (±15% tolerance)
└────────┬──────────────┘  PS1 BIOS expected: 524,288 bytes (512KB)
         │
         ▼
  Status: ✅ Verified | ⚠️ Size Warning | ⚠️ Unverified | ❌ Failed
```

### PS1 BIOS Variants

Four PS1 BIOS variants are recognized (all 512KB):

| Filename | Region | Known MD5 |
|----------|--------|-----------|
| `scph5501.bin` | North America | `924e392ed05558ffdb115408c263dccf` |
| `scph5500.bin` | Japan | *(tracked)* |
| `scph5502.bin` | Europe | *(tracked)* |
| `scph1001.bin` | Legacy NA | *(tracked)* |

### BIOS Loading with Family Fallback

When loading a BIOS file for a game, the system first tries the exact filename, then falls back to "family" variants. For example, if `scph5501.bin` is missing but `scph5502.bin` is available, it will use the European variant.

---

## 13. Metadata Scraping (Box Art)

### `src/lib/metadata/scraper.ts`

PiStation fetches game cover art from the **LibRetro thumbnails repository** on GitHub.

### How It Works

1. **Clean the title:** Strip file extension, brackets, parentheses → clean game name
2. **Generate variants:** Create 9+ title variations with region tags (USA, Europe, Japan, World)
3. **Try each variant:** Send HTTP HEAD requests to:
   ```
   https://raw.githubusercontent.com/libretro-thumbnails/{repo}/master/Named_Boxarts/{title}.png
   ```
4. **First 200 OK wins:** The first variant that returns a successful response becomes the cover URL
5. **Store the URL:** `updateGameMetadata(game.id, { coverUrl: url })` persists to IndexedDB

### System-to-Repository Mapping

| System ID | LibRetro Repository |
|-----------|-------------------|
| `nes` | "Nintendo - Nintendo Entertainment System" |
| `snes` | "Nintendo - Super Nintendo Entertainment System" |
| `gb` | "Nintendo - Game Boy" |
| `gbc` | "Nintendo - Game Boy Color" |
| `gba` | "Nintendo - Game Boy Advance" |
| `genesis` | "Sega - Mega Drive - Genesis" |
| `ps1` | "Sony - PlayStation" |
| `n64` | "Nintendo - Nintendo 64" |

### Batch Scraping

`scrapeAllMissingMetadata(games[], onProgress?)` iterates through all games without a `coverUrl`, attempts to scrape each one, and reports progress via callback.

---

## 14. Gamepad & Input System

### Architecture

```
src/gamepad/
├── types.ts              # Type definitions
├── mapping.ts            # Profile detection & state building
├── keyboard-overrides.ts # Keyboard-to-button mapping
└── overrides.ts          # Gamepad button remapping persistence
```

### Controller Profile Detection

When a gamepad is connected, `detectProfile()` examines the device ID string to select a mapping profile:

| Profile | Detection | Button Swap |
|---------|-----------|-------------|
| **Standard (Xbox)** | Default / "xinput" / "xbox" | None |
| **Nintendo** | "nintendo" / "pro controller" | A↔B, X↔Y |
| **PlayStation** | "playstation" / "dualshock" / "dualsense" | A↔B, X↔Y |
| **Generic** | Everything else | None |

### Gamepad Polling

The `useGamepadVisualizer()` hook:
1. Polls `navigator.getGamepads()` at 60fps via `requestAnimationFrame`
2. Converts raw gamepad data to `RawPadSnapshot`
3. Applies axis deadzone (0.12) and clamping
4. Applies button threshold (0.45 for digital state)
5. Merges user overrides from localStorage
6. Outputs a `ControllerVisualState` for UI rendering

### Keyboard Controls

Default keyboard mappings:

| Key | Button |
|-----|--------|
| X | A |
| Z | B |
| S | X |
| A | Y |
| Arrow keys | D-pad |
| Q / W | LB / RB |
| 1 / 2 | LT / RT |
| Shift | Select/Minus |
| Enter | Start/Plus |
| Escape | Home |

Users can remap both keyboard and gamepad buttons through the Controller Test page. Overrides persist in `localStorage["retroweb_keyboard_overrides"]` and `localStorage["retroweb_gamepad_overrides"]`.

---

## 15. Netplay (WebRTC P2P)

### `src/lib/netplay/session.ts`

PiStation supports peer-to-peer multiplayer via WebRTC DataChannels — **no central server required**.

### Connection Flow (Manual SDP Exchange)

```
        HOST                                GUEST
         │                                    │
    createOffer()                             │
    ──── base64 SDP offer ──────────────>     │
         │                              acceptOffer(offer)
         │                                    │
         │     <──── base64 SDP answer ──────────
    acceptAnswer(answer)                      │
         │                                    │
         ╔════════════════════════════════════╗
         ║      DATA CHANNEL OPEN            ║
         ║   sendInput() ◄──► sendInput()    ║
         ╚════════════════════════════════════╝
```

Users manually exchange base64-encoded SDP strings (via clipboard, messaging, etc.) to establish the connection. No signaling server is used.

### Input Encoding

Button states are encoded as a 16-bit bitmask:

| Bit | Button | Bit | Button |
|-----|--------|-----|--------|
| 0 | A | 8 | LB |
| 1 | B | 9 | RB |
| 2 | X | 10 | LT |
| 3 | Y | 11 | RT |
| 4 | D-Up | 12 | Minus |
| 5 | D-Down | 13 | Plus |
| 6 | D-Left | 14 | L3 |
| 7 | D-Right | 15 | R3 |

Each frame, the local player's button mask is sent as JSON: `{ frame: number, buttons: number }`.

### STUN Configuration

NAT traversal uses Google's public STUN servers:
- `stun:stun.l.google.com:19302`
- `stun:stun1.l.google.com:19302`

---

## 16. AI Chat Integration

### `src/routes/chat.tsx`

PiStation includes an AI chat assistant that runs entirely locally via [Ollama](https://ollama.com).

### Architecture

```
┌──────────┐    /api/ollama     ┌──────────┐
│  Chat UI  │ ──────────────>   │  Ollama   │  (localhost:11434)
│           │ <──────────────   │  (LLM)    │
└──────────┘                    └──────────┘

┌──────────┐    /api/whisper    ┌──────────┐
│  Voice    │ ──────────────>   │  Whisper  │  (localhost:8786)
│  Input    │ <──────────────   │  (STT)    │
└──────────┘                    └──────────┘

┌──────────┐    /api/kokoro     ┌──────────┐
│  Voice    │ ──────────────>   │  Kokoro   │  (localhost:8787)
│  Output   │ <──────────────   │  (TTS)    │
└──────────┘                    └──────────┘
```

### Features

- **Text chat:** Send messages to local LLM, receive responses
- **Image analysis:** Attach screenshots or images for the LLM to analyze
- **Voice input:** Record speech → Whisper STT → text → LLM
- **Voice output:** LLM response → Kokoro TTS → audio playback
- **Screenshot sharing:** From the emulator, press the AI button to capture a screenshot and auto-navigate to chat
- **Persistence:** All chat messages are stored in IndexedDB and restored across sessions

### API Proxies (in `vite.config.ts`)

| Route | Target | Service |
|-------|--------|---------|
| `/api/ollama` | `localhost:11434` | Ollama LLM |
| `/api/whisper` | `localhost:8786` | Whisper STT |
| `/api/kokoro` | `localhost:8787` | Kokoro TTS |

> **Note:** These AI services are optional. The emulator works perfectly without them.

---

## 17. PWA & Service Worker

### Configuration (`vite.config.ts`)

PiStation uses `vite-plugin-pwa` with Workbox for full PWA support.

### Service Worker Strategy

| Aspect | Configuration |
|--------|--------------|
| **Register type** | `autoUpdate` — automatically activates new SW versions |
| **Pre-cached assets** | `**/*.{js,css,html,ico,png,svg,wasm,json}` |
| **Max file size** | 50MB per cached entry (for large WASM emulator cores) |
| **Runtime caching** | GitHub raw content (LibRetro thumbnails) — CacheFirst strategy, 7-day max age, 200 entry limit |

### PWA Manifest

```json
{
  "name": "RetroWeb Emulator",
  "short_name": "RetroWeb",
  "display": "standalone",
  "orientation": "landscape",
  "background_color": "#09090b",
  "theme_color": "#09090b",
  "icons": [
    { "src": "pwa-192x192.png", "sizes": "192x192", "type": "image/png" },
    { "src": "pwa-512x512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable" }
  ]
}
```

### Offline Capabilities

Once installed, the app works fully offline:
- All JavaScript, CSS, and HTML are pre-cached
- WASM emulator cores are cached on first load
- Game thumbnails are cached as they're fetched
- ROMs, saves, and BIOS data are all in IndexedDB

### Update Flow

1. Service worker detects a new version via `updatefound` event
2. App shell displays a toast notification: "New version available"
3. On next page load, the new service worker activates automatically
4. The `controllerchange` event triggers a page reload

### COOP/COEP Headers

For SharedArrayBuffer support (required by multi-threaded WASM cores):

```
Cross-Origin-Opener-Policy: same-origin
Cross-Origin-Embedder-Policy: require-corp
```

These headers are configured for both the dev server and preview server in `vite.config.ts`.

---

## 18. Internationalization (i18n)

### `src/lib/i18n/index.ts`

PiStation supports 6 languages:

| Code | Language |
|------|----------|
| `en` | English |
| `es` | Spanish (Español) |
| `fr` | French (Français) |
| `de` | German (Deutsch) |
| `ja` | Japanese (日本語) |
| `pt` | Portuguese (Português) |

### Translation System

Translations are organized as a nested key-value structure with 45+ keys across categories:

- **`nav.*`** — Navigation labels (home, library, settings, chat, controller, saves)
- **`home.*`** — Landing page text
- **`library.*`** — Library page text (search, upload, empty states)
- **`settings.*`** — Settings section labels
- **`chat.*`** — Chat interface text
- **`common.*`** — Shared actions (cancel, save, delete, close, play, favorite)

### Usage

```typescript
const { t, lang, setLang } = useI18n();

return <h1>{t("nav.home")}</h1>;  // "Home" in English, "Inicio" in Spanish
```

### Language Detection

1. Check `localStorage["retroweb.lang"]` for stored preference
2. Fall back to `navigator.language` browser detection
3. Default to English if no match

Language changes dispatch a `"retroweb:langchange"` custom event so all components update simultaneously.

---

## 19. Accessibility

PiStation implements three accessibility modes, toggled in Settings and applied as CSS classes on `<html>`:

### High Contrast Mode (`a11y-high-contrast`)
- Forces white text (`#ffffff`)
- Gray borders for maximum visibility
- Overrides all theme colors for WCAG compliance

### Large Text Mode (`a11y-large-text`)
- Forces minimum 18px font size on all elements
- Applied via `* { font-size: 18px !important }`

### Reduced Motion Mode (`a11y-reduced-motion`)
- Disables all CSS animations and transitions
- Sets `animation-duration: 0.01ms !important`
- Sets `transition-duration: 0.01ms !important`
- Respects users who experience motion sickness or vestibular disorders

These settings persist in `localStorage["retroweb.settings.v1"]` and are applied on every page load.

---

## 20. Achievement System

### `src/lib/achievements.ts`

PiStation tracks 14 achievements with emoji icons:

| ID | Title | Icon | Trigger |
|----|-------|------|---------|
| `first_game` | First Game Played | 🎮 | Play any game |
| `five_games` | Five Games | 🕹️ | Play 5 different games |
| `ten_games` | Explorer | 🗺️ | Play 10 different games |
| `hour_played` | Hour Played | ⏰ | 1 hour total playtime |
| `ten_hours` | Dedicated | 🏆 | 10 hours total playtime |
| `five_systems` | Multi-System | 📺 | Play on 5 different systems |
| `first_save` | First Save | 💾 | Create first save state |
| `first_favorite` | Favorited | ⭐ | Favorite a game |
| `bios_installed` | BIOS Ready | 🔌 | Install any BIOS file |
| `ai_chat` | AI Assistant | 🤖 | Send first chat message |
| `voice_mode` | Voice Mode | 🎤 | Use voice input |
| `screenshot_ai` | Screenshot AI | 📸 | Share screenshot with AI |
| `theme_changed` | Themed | 🎨 | Change app theme |
| `speed_demon` | Speed Demon | ⚡ | Use speed multiplier >1x |

### Unlock Flow

```typescript
checkAndUnlock(achievementId: string): Promise<boolean>
```

1. Check if already unlocked in IndexedDB
2. If new, store `{ id, unlockedAt: Date.now() }` in the `achievements` table
3. Show a toast notification
4. Trigger a push notification (if permitted)
5. Return `true` if newly unlocked

---

## 21. Build System & Configuration

### TypeScript Configuration

```
tsconfig.json (root)
├── tsconfig.app.json  → Source code (src/)
└── tsconfig.node.json → Build scripts, Vite config
```

**Key settings:**
- **Target:** ES2022 (modern browsers only)
- **Module:** ESNext with bundler resolution
- **Strict mode:** All strict flags enabled (`noUnusedLocals`, `noUnusedParameters`, `noFallthroughCases`)
- **Path alias:** `@/*` → `./src/*`
- **JSX:** `react-jsx` (automatic runtime — no `React` import needed)

### Vite Build Optimization

**Manual chunk splitting** keeps bundle sizes manageable:

| Chunk | Contents |
|-------|----------|
| `vendor-react` | React, React DOM, React Router |
| `vendor-ui` | Radix UI, Lucide icons, shadcn utilities |
| `vendor-data` | Dexie, Zustand, date-fns |
| `vendor-zip` | @zip.js/zip.js |
| `vendor-emulator` | Nostalgist |

**Build target:** `esnext` (no downleveling, tree-shaking enabled)

### ESLint Configuration

Flat config (ESLint v9+) with:
- `typescript-eslint` — TypeScript-aware linting
- `react-hooks` — Hook rules enforcement
- `react-refresh` — Fast Refresh compatibility

### Scripts

| Script | Command | Purpose |
|--------|---------|---------|
| `npm start` | `node start.mjs` | Launch all services |
| `npm run dev` | `vite` | Dev server with HMR |
| `npm run build` | `tsc -b && vite build` | Type-check + production build |
| `npm run lint` | `eslint .` | Run linter |
| `npm run preview` | `vite preview` | Preview production build |
| `npm test` | `node --test tests/*.test.mjs` | Run test suite |

---

## 22. Testing

### Framework

PiStation uses the **Node.js native test runner** (`node --test`) with ESM test files.

### Test File: `tests/rom-normalizer.test.mjs`

8 tests covering the ROM normalization pipeline:

| Test | Validates |
|------|-----------|
| GBA file detection | Bare `.gba` file maps to `gb` system |
| ZIP with GBA | Extracts GBA ROM from ZIP, detects system |
| ZIP with ROM + text | Ignores non-ROM files, loads only ROM |
| ZIP multiple ROMs | Throws `zip_multiple_roms` with candidates list |
| ZIP no ROM | Throws `zip_no_rom` when no valid ROM found |
| Unsupported format | Rejects `.exe` and invalid extensions |
| GBA header detection | Validates ARM branch opcode signature (8 bytes) |
| NES header detection | Validates iNES magic bytes (`4E 45 53 1A`) |

---

## 23. Page-by-Page Breakdown

### Home (`/`)
The landing page featuring a hero section with animated gradient title, a "Continue Playing" carousel of the 6 most recent games, an 8-card feature grid, and a 3-step quick start guide. Data is loaded from `getRecentGames(6)`.

### Library (`/library`)
The main ROM management hub. Supports drag-and-drop ROM upload with auto-detection, three view modes (grid/list/carousel with 3D rotation), persistent sort and search with 200ms debounce, game details drawer (rating, collections, notes, cheats, tags), and batch metadata scraping. ROM storage uses OPFS with quota monitoring.

### Play (`/play`)
The emulator runtime (see [Section 10](#10-the-emulation-runtime) for full details). Renders a `<canvas>` element where RetroArch WASM draws frames. Full-screen layout with in-game menu overlay for save/load, speed control, FPS, fullscreen, PiP, and AI screenshot sharing.

### Systems (`/systems`)
A browsable directory of supported emulation systems. Cards show system name, manufacturer, era, tier badge, BIOS status checklist, and game count. Filterable by readiness status (Ready to Play / Needs Setup) and searchable. Tabbed view separating fully supported from experimental systems.

### Settings (`/settings`)
Comprehensive preferences page with searchable sections: Storage Usage (visual quota bar), Performance & Compatibility (thread/WASM status), Display (shader, aspect ratio, FPS), Audio (volume, latency), Input (touch controls), Saves (auto-save interval), Data Management (export/import backup, clear data), Accessibility (contrast, text size, motion), and About/Debug info.

### BIOS Vault (`/bios`)
BIOS firmware management with drag-and-drop upload, MD5 hash verification, size validation, and per-system readiness tracking. Shows global readiness percentage, installed vs. missing counts, and per-BIOS verification status (Verified / Size Warning / Unverified / Failed).

### Saves (`/saves`)
Save state and SRAM management with filter tabs (All/SRAM/States), stats chips, virtualized list with thumbnails, and import/export functionality. Each save shows type icon, filename, slot, timestamp, and size.

### Controller Test (`/controller`)
Gamepad diagnostics with live polling at 60fps. Shows connected controllers, real-time stick/trigger/button visualization, and supports gamepad button remapping and keyboard remapping — all persisted to localStorage.

### AI Chat (`/chat`)
Local Ollama-powered chat with text, image, and voice support. Messages persist in IndexedDB. Features voice-to-text (Whisper), text-to-speech (Kokoro), and screenshot sharing from the emulator.

### Achievements (`/achievements`)
Trophy-style achievement grid showing 14 trackable achievements with emoji icons, unlock dates, and an overall progress bar. Locked achievements appear at 50% opacity with grayscale.

### Stats (`/stats`)
Analytics dashboard with summary cards (total games, playtime, games played, average rating), playtime-by-system bar chart, top 10 most played games, activity-by-day bar chart, and a GitHub-style play calendar heatmap (52 weeks of activity).

### ROM Hacks (`/romhacks`)
Curated directory of 12 notable ROM hacks with search and type filter (Overhaul/Translation/Improvement/Difficulty). Each entry links to external download sources like romhacking.net.

### Login (`/login`)
Demo authentication page with username/password fields. Sets `sessionStorage["retroweb.loggedIn"]` = `"true"` on submit. No actual backend authentication — purely a UI gate with animated glow backgrounds.

---

## 24. Data Flow Diagrams

### ROM Upload to Play

```
                              ┌─────────────────┐
  Drag & Drop ROM ──────────> │  rom-normalizer  │
  or File Picker              │  ZIP extract     │
                              │  Header detect   │
                              └────────┬────────┘
                                       │
                              ┌────────▼────────┐
                              │  auto-detect     │
                              │  extension→core  │
                              └────────┬────────┘
                                       │
                    ┌──────────────────┬┴──────────────────┐
                    │                  │                    │
           ┌────────▼──────┐  ┌───────▼───────┐  ┌───────▼──────┐
           │ hashROMInWorker│  │ saveGameMeta  │  │ saveRomToOPFS│
           │ (Web Worker)   │  │ (IndexedDB)   │  │ (OPFS)       │
           └────────┬──────┘  └───────┬───────┘  └───────┬──────┘
                    │                 │                    │
                    └─────────────────┴────────────────────┘
                                      │
                              ┌───────▼───────┐
                              │  Navigate to   │
                              │  /play?file=   │
                              └───────┬───────┘
                                      │
                              ┌───────▼───────┐
                              │  Nostalgist    │
                              │  .launch()     │
                              │  WASM + Canvas │
                              └───────────────┘
```

### Save State Lifecycle

```
    ┌──────────┐     saveState()      ┌─────────────┐
    │ Emulator │ ──────────────────>  │  IndexedDB   │
    │ (WASM)   │  state blob +        │  saves table │
    │          │  thumbnail JPEG      │              │
    └──────────┘                      └──────┬──────┘
         ▲                                   │
         │          loadState()              │
         └───────────────────────────────────┘
              blob → emulator.loadState()

    ┌──────────┐     saveSRAM()       ┌─────────────┐
    │ Emulator │ ──────────────────>  │  IndexedDB   │
    │ (WASM)   │  every 45s +         │  saves table │
    │          │  on exit/tab-hide    │              │
    └──────────┘                      └──────┬──────┘
         ▲                                   │
         │          loadSRAM()               │
         └───────────────────────────────────┘
              restore on boot
```

### Settings Persistence

```
  Settings Page                     localStorage
  ┌──────────┐     save              ┌──────────────────────┐
  │  Theme   │ ──────────────>       │ retroweb.settings.v1 │
  │  Audio   │                       │ {                    │
  │  Display │                       │   theme: "gameboy",  │
  │  A11y    │     load on mount     │   volume: 0.8,      │
  │  Input   │ <──────────────       │   highContrast: true │
  └──────────┘                       │ }                    │
                                     └──────────────────────┘

  Gamepad Overrides                  localStorage
  ┌──────────┐     save              ┌────────────────────────────┐
  │ Remap UI │ ──────────────>       │ retroweb_gamepad_overrides │
  └──────────┘     load              │ retroweb_keyboard_overrides│
               <──────────────       └────────────────────────────┘
```

---

*This document describes PiStation as of its current implementation. The application is under active development and new features may be added.*
