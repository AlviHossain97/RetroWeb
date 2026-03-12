# RetroWeb (PiStation) — Application Architecture

## Table of Contents

- [Overview](#overview)
- [Services & Runtime](#services--runtime)
- [Frontend Architecture](#frontend-architecture)
  - [Routing & Navigation](#routing--navigation)
  - [App Shell](#app-shell)
  - [State Management](#state-management)
- [Emulation Engine](#emulation-engine)
  - [Core Loading Pipeline](#core-loading-pipeline)
  - [ROM Normalization](#rom-normalization)
  - [System Detection](#system-detection)
  - [BIOS Management](#bios-management)
  - [Save System](#save-system)
- [AI Voice Assistant](#ai-voice-assistant)
  - [Chat Pipeline](#chat-pipeline)
  - [Voice Pipeline (STT → LLM → TTS)](#voice-pipeline-stt--llm--tts)
  - [Whisper STT Server](#whisper-stt-server)
  - [Kokoro TTS Server](#kokoro-tts-server)
- [Data Layer](#data-layer)
  - [IndexedDB Schema (Dexie)](#indexeddb-schema-dexie)
  - [LocalStorage Keys](#localstorage-keys)
  - [SessionStorage Keys](#sessionstorage-keys)
- [Theming System](#theming-system)
- [Networking](#networking)
  - [Netplay (WebRTC P2P)](#netplay-webrtc-p2p)
  - [Cover Art Scraping](#cover-art-scraping)
  - [Vite Proxy Configuration](#vite-proxy-configuration)
- [Input System](#input-system)
- [PWA & Service Worker](#pwa--service-worker)
- [Internationalization](#internationalization)
- [Achievement System](#achievement-system)
- [Notification System](#notification-system)
- [Easter Eggs](#easter-eggs)
- [Security & Isolation](#security--isolation)
- [Supported Systems](#supported-systems)

---

## Overview

RetroWeb is a **fully client-side, browser-based retro game emulator** built as a Progressive Web App (PWA). It runs RetroArch/libretro cores compiled to WebAssembly entirely within the browser. There is **no backend server** for the core application — all game data, saves, BIOS files, and user preferences are stored locally in the browser via IndexedDB and localStorage.

The application is supplemented by **three optional local AI services** (Ollama, Kokoro TTS, Whisper STT) that run on the user's machine to power the AI voice assistant. These are not required for emulation.

**Tech Stack:**
- React 19 + TypeScript (strict) + Vite 7
- Tailwind CSS v4 + shadcn/ui (new-york variant)
- Dexie (IndexedDB wrapper) for persistence
- Nostalgist (RetroArch WASM wrapper) for emulation
- Zustand for global stores
- react-router v7 for routing

---

## Services & Runtime

The application runs with up to 4 concurrent services, managed by `start.mjs`:

| Service | Port | Technology | Purpose |
|---------|------|------------|---------|
| **Vite Dev Server** | 5173 | Node.js / Vite 7 | Serves the React SPA with HMR, COOP/COEP headers, and proxy routes |
| **Ollama** | 11434 | Go binary | Local LLM inference (llava, qwen, phi4, etc.) for AI chat |
| **Kokoro TTS** | 8787 | Python / FastAPI | Text-to-speech using Kokoro ONNX model (GPU-accelerated) |
| **Whisper STT** | 8786 | Python / FastAPI | Speech-to-text using faster-whisper (GPU-accelerated with CUDA) |

`start.mjs` spawns all four as child processes, pipes their stdout/stderr with `[ServiceName]` prefixes, and handles graceful shutdown on SIGINT/SIGTERM.

**Important:** The Vite dev server proxies all AI service requests through same-origin paths to avoid COEP (`Cross-Origin-Embedder-Policy: require-corp`) blocking cross-origin fetches:

| Proxy Path | Target |
|------------|--------|
| `/api/ollama/*` | `http://localhost:11434/*` |
| `/api/whisper/*` | `http://localhost:8786/*` |
| `/api/kokoro/*` | `http://localhost:8787/*` |

---

## Frontend Architecture

### Routing & Navigation

All routes are **lazy-loaded** via `React.lazy()` and wrapped in `<Suspense>` with a spinner fallback. Routes are defined in `src/main.tsx`:

| Path | Component | Description |
|------|-----------|-------------|
| `/login` | `Login` | Session gate (standalone, outside App shell) |
| `/` | `Home` | Landing page with feature cards + continue-playing |
| `/library` | `Library` | ROM management, upload, grid browsing |
| `/play` | `Play` | Emulator player — full-screen Nostalgist canvas |
| `/systems` | `Systems` | Supported systems browser |
| `/bios` | `BiosVault` | BIOS file management |
| `/saves` | `SavesVault` | Save state management |
| `/controller` | `ControllerTest` | Gamepad testing/visualization |
| `/chat` | `Chat` | AI chat assistant with voice mode |
| `/achievements` | `AchievementsPage` | Achievement tracking |
| `/stats` | `StatsPage` | Gameplay statistics |
| `/romhacks` | `RomHacksPage` | ROM hack discovery |
| `/settings` | `Settings` | User preferences |

The router uses `BrowserRouter` from react-router v7. The `/login` route sits outside the `<App />` layout; all other routes are nested children of `<App />` which provides the navigation shell.

### App Shell

`src/App.tsx` is the main application shell. It handles:

1. **Authentication gate** — Checks `sessionStorage.getItem("retroweb.loggedIn")`. If not `"true"`, redirects to `/login`. This is a simple session gate with no real authentication.

2. **Theme initialization** — On mount, reads `localStorage["retroweb.settings.v1"]` and applies `data-theme` attribute and accessibility CSS classes (`a11y-high-contrast`, `a11y-large-text`, `a11y-reduced-motion`).

3. **PWA install prompt** — Listens for `beforeinstallprompt` and shows an install banner.

4. **PWA auto-update** — Monitors `serviceWorker.controllerchange` and `updatefound` events to notify users of new versions.

5. **Global drag-and-drop BIOS installation** — Any file dragged onto the app (outside the emulator) is validated as a BIOS file via `validateBiosFilename()`. If valid, it's MD5-hashed, stored in Dexie, and the user gets a toast notification.

6. **Navigation** — Two navigation modes:
   - **Desktop** (`md:` breakpoint and up): Floating side navigation bar at top-left using animated link components. 8 navigation items.
   - **Mobile**: Fixed bottom tab bar with 5 items (Home, Library, Chat, Saves, Settings).
   - Both are hidden when on the `/play` route (emulator goes full-screen).

7. **Offline indicator** — Listens for `online`/`offline` window events and shows a red banner when offline.

8. **Lazy-loaded shell components**: `LegalModal`, `CookieConsent`, `OnboardingTutorial`, `PacmanGhostEasterEgg`, `PongBackground`, `NotificationCenter` are all lazy-loaded and not on the critical render path.

### State Management

- **Zustand** — Used for cross-component global stores (minimal usage)
- **React hooks** — `useState`, `useRef`, `useCallback`, `useMemo` for all local component state
- **Dexie** — All persistent data (games, saves, BIOS, chat history, achievements)
- **localStorage** — Settings, notifications, language preference
- **sessionStorage** — Login state, screenshot transfer between routes, last played game name

---

## Emulation Engine

### Core Loading Pipeline

The emulation lifecycle is managed in `src/routes/play.tsx` and uses the **Nostalgist** library, which wraps RetroArch compiled to WebAssembly.

**Boot sequence:**

```
1. User clicks "Play" on a game in the Library
2. Navigate to /play with route state: { romFile, coreId, filename, gameId, autoLoadSlot }
3. ROM Normalization: Extract from ZIP if needed, detect system
4. Resolve core: Match coreId → system → core path from coreMap.json
5. Load previous SRAM save from Dexie (if exists)
6. Load required BIOS files from Dexie
7. Check core cache (Cache API) — skip download if cached
8. Call Nostalgist.launch() with: core, rom, sram, bios, canvas, retroarchConfig
9. 20-second timeout race — abort if boot takes too long
10. Focus canvas for keyboard input
11. Start autosave timer (every 60s by default)
12. If autoLoadSlot specified, immediately load that save state
```

**Core binaries** are served from `/cores/{coreName}/{version}/{coreName}_libretro.js` and `.wasm`. The JavaScript glue code and WASM binary are resolved via `resolveCoreJs` and `resolveCoreWasm` callbacks.

**RetroArch config** passed at launch:
```js
retroarchConfig: {
  menu_driver: "null",                            // No RetroArch menu overlay
  network_buildbot_auto_extract_archive: "false",  // Don't fetch from buildbot
}
```

### ROM Normalization

`src/lib/emulation/rom-normalizer.ts` handles the complexity of getting a user's ROM file into a format the emulator can consume:

1. **Extension check** — Determine if the file is a cartridge ROM (`.nes`, `.smc`, `.gb`, `.gba`, `.md`, etc.), disc image (`.chd`, `.pbp`), or ZIP archive.

2. **ZIP handling** — Uses `@zip.js/zip.js` to:
   - List all entries in the archive
   - Filter out non-ROM files (`.txt`, `.nfo`, `.jpg`, etc.)
   - If single ROM found: extract it automatically
   - If multiple ROMs found: throw `NormalizeError` with `zip_multiple_roms` code and the list of candidates for user selection
   - If specific `selectedZipEntry` is provided: extract only that file

3. **System detection** — Map the ROM's file extension to a system ID (NES, SNES, GB, Genesis, PS1)

4. **`.bin` ambiguity** — Files with `.bin` extension under 16MB are treated as Genesis cartridges; larger `.bin` files are rejected as ambiguous.

5. **Disc format validation** — `.cue` and `.iso` files are rejected with a user-friendly message directing to CHD format.

6. **Output** — Returns a `NormalizedROM` with: `blob`, `filename`, `detectedSystem`, `systemId`, `systemLabel`, `detectionSource`.

### System Detection

`src/lib/detection/auto-detect.ts` provides `detectSystemByExtension()`:

- Iterates through `coreMap.json` entries and matches the file extension to a system
- Returns `{ systemId, coreId }` on match
- Special handling for `.chd` files (requires manual system selection)
- Returns an error message for unknown extensions

### BIOS Management

BIOS files are critical for systems like PS1. The BIOS subsystem in `src/lib/storage/db.ts` provides:

1. **Validation** — `validateBiosFilename()` normalizes the filename (lowercase, strip path), and checks against known BIOS files across all systems.

2. **PS1 BIOS variants** — Accepts `scph5501.bin`, `scph5500.bin`, `scph5502.bin`, `scph1001.bin` with known MD5 hashes and expected sizes (512KB each).

3. **MD5 verification** — Uses `src/lib/hash/md5.ts` to hash BIOS files and compare against known-good hashes. Results stored as `verifiedHash` boolean.

4. **Size warnings** — Compares file size against expected size; warns if mismatched.

5. **Storage** — BIOS files are stored in the `bios` table in Dexie, keyed by `filename` (lowercase canonical name).

6. **Loading at boot** — When launching a game, `loadBIOS(biosName)` retrieves the binary data from Dexie and converts it to a `File` object for Nostalgist.

### Save System

Two types of saves are managed:

**SRAM (battery saves):**
- Continuous game progress (like original cartridge battery saves)
- Auto-saved periodically (default: every 60 seconds) and on unmount
- Stored per-game by filename in the `saves` table with `type: "sram"`
- Loaded automatically at boot and passed to Nostalgist

**Save States (snapshots):**
- Full emulator state snapshots (CPU, RAM, VRAM — everything)
- Multiple slots per game (user-selectable)
- Include a canvas thumbnail screenshot (JPEG, 320px wide)
- Keyboard shortcuts: F1 = save slot 0, F4 = load slot 0

Both are stored as `Uint8Array` in IndexedDB via Dexie.

**Gameplay session tracking:**
- `sessionStartedAtRef` tracks when the current session began
- `recordGameplaySession()` updates the game's `playtime` and `lastPlayed` on unmount
- `markGameAutoSaved()` updates `lastAutoSaveAt` timestamp

---

## AI Voice Assistant

### Chat Pipeline

The AI chat (`src/routes/chat.tsx`) integrates with a local Ollama instance for LLM inference:

1. **Health checks** — Every 15 seconds, polls `/api/ollama/api/tags` (for model list) and `/api/kokoro/health` (for TTS availability).

2. **Model selection** — User can pick from available Ollama models. Default is `llava:7b` (vision-capable).

3. **Message flow:**
   ```
   User types message (or voice transcription arrives)
   → Append user message + assistant placeholder to state
   → POST /api/ollama/api/chat with streaming: true
   → Read NDJSON stream, accumulate tokens
   → Update assistant message content in real-time
   → If voice mode: flush text to TTS in sentence-sized chunks
   ```

4. **Image support** — Screenshots from the emulator (captured via `captureThumbnail()`) or uploaded images are sent as base64 in the `images` field of the Ollama API request.

5. **File context** — Text files can be uploaded and their content is appended to the message.

6. **Persona system** — Configurable AI personality.

7. **Walkthrough mode** — Periodic automated queries for game guidance.

8. **Chat persistence** — All messages are saved to Dexie `chatMessages` table and restored on mount.

### Voice Pipeline (STT → LLM → TTS)

The voice assistant implements a continuous listen → transcribe → respond → speak loop:

```
┌──────────────────────────────────────────────────────────┐
│                    VOICE PIPELINE                        │
│                                                          │
│  ┌─────────┐    ┌────────────┐    ┌─────────┐           │
│  │ Browser  │───>│  Whisper   │───>│ Ollama  │           │
│  │ Mic +    │    │  Server    │    │  LLM    │           │
│  │ Silence  │    │ (STT)      │    │         │           │
│  │ Detection│    │ Port 8786  │    │ Port    │           │
│  └─────────┘    └────────────┘    │ 11434   │           │
│                                    └────┬────┘           │
│                                         │                │
│  ┌─────────┐    ┌────────────┐         │                │
│  │ Browser  │<───│  Kokoro    │<────────┘                │
│  │ Audio    │    │  Server    │  (streaming text chunks)  │
│  │ Playback │    │ (TTS)      │                          │
│  └─────────┘    │ Port 8787  │                          │
│       │         └────────────┘                          │
│       │                                                  │
│       └──── When playback finishes, loop restarts ───>   │
└──────────────────────────────────────────────────────────┘
```

**Detailed flow:**

1. **Recording** — `getUserMedia({ audio: true })` acquires the microphone. A `MediaRecorder` captures audio as `audio/webm;codecs=opus`. The mic stream is reused across recordings unless it becomes inactive.

2. **Silence detection** — An `AudioContext` + `AnalyserNode` monitors frequency data at `requestAnimationFrame` rate:
   - `SILENCE_THRESHOLD = 8` — Average frequency below this = silence
   - `SILENCE_DURATION = 1500ms` — Silence after speech triggers stop
   - `MIN_SPEECH_DURATION = 500ms` — Minimum recording before silence detection activates
   - `MAX_DURATION = 30000ms` — Hard cap on recording length
   - Recordings under 1000 bytes are discarded as empty

3. **Transcription** — The audio blob is sent as `FormData` to `POST /api/whisper/v1/audio/transcriptions`. Returns `{ text: string }`.

4. **LLM Response** — The transcribed text is sent to Ollama via `sendMessageDirect()`.

5. **TTS Streaming** — As the LLM streams tokens, text is buffered and flushed to Kokoro TTS at clause/sentence boundaries:
   - Flushes on sentence endings (`.!?`)
   - Flushes on clause boundaries (`,;:—–`) if buffer > 30 chars
   - Hard flush at 120 chars
   - Each chunk fetches audio in parallel; playback is serialized

6. **Loop** — After all TTS audio finishes playing, `startListeningLoop()` is called again to restart recording.

### Whisper STT Server

`scripts/whisper-server.py` — FastAPI server with CORS, running on port 8786:

- **Model:** `faster-whisper` "small" model on CUDA with float16
- **Pre-loading:** Model loaded on startup in a background thread
- **Endpoint:** `POST /v1/audio/transcriptions` (OpenAI-compatible)
- **Processing:** Receives `.webm` audio → ffmpeg converts to 16kHz mono WAV → faster-whisper transcribes → returns `{ text }` JSON
- **Error handling:** All errors caught and returned as `{ text: "", error: "..." }` with HTTP 200 to preserve CORS headers
- **Health:** `GET /health` returns `{ status, model_loaded }`

### Kokoro TTS Server

`scripts/kokoro-tts-server.py` — FastAPI server with CORS, running on port 8787:

- **Model:** Kokoro ONNX v1.0 with voice files (`kokoro-v1.0.onnx`, `voices-v1.0.bin`)
- **Default voice:** `af_heart` at 1.2x speed
- **Endpoints:**
  - `POST /v1/audio/speech` — OpenAI-compatible TTS, returns WAV audio
  - `POST /tts` — Simple TTS endpoint
  - `POST /stt` — Legacy STT endpoint using OpenAI Whisper (separate from the faster-whisper server)
  - `GET /voices` — List available voices
  - `GET /health` — Health check

---

## Data Layer

### IndexedDB Schema (Dexie)

The database (`RetroWebDB`) uses Dexie with versioned migrations. Current schema (v4):

**`games` table:**
```typescript
{
  id: string;              // Unique game identifier
  title: string;           // Original filename-based title
  displayTitle?: string;   // Cleaned display name
  system: string;          // System ID (nes, snes, gb, genesis, ps1)
  core: string;            // Core used to play
  filename: string;        // ROM filename
  size: number;            // ROM file size in bytes
  addedAt: number;         // Timestamp when added
  lastPlayed?: number;     // Last play timestamp
  playtime?: number;       // Total seconds played
  isFavorite: boolean;
  coverUrl?: string;       // LibRetro thumbnail URL
  hasLocalRom: boolean;
  romHash?: string;        // MD5 hash of the ROM
  collectionIds?: string[];
  rating?: number;         // 1-5 stars
  perGameSettings?: Record<string, string>;
  cheats?: string[];
  notes?: string;
  tags?: string[];
  description?: string;    // AI-generated game description
}
```

**`saves` table:**
```typescript
{
  id: number;              // Auto-incremented
  filename: string;        // Game ROM filename (foreign key)
  system: string;
  type: "sram" | "state";  // Battery save vs snapshot
  data: Uint8Array;        // Raw binary save data
  timestamp: Date;
  image?: string;          // Base64 JPEG thumbnail (states only)
  slot?: number;           // Save slot index (states only)
  coreId?: string;
  coreVersion?: string;
}
```

**`bios` table:**
```typescript
{
  filename: string;        // Primary key (canonical lowercase name)
  system: string;
  data: Uint8Array;        // Raw BIOS binary
  sourceFilename?: string; // Original filename before normalization
  hashMd5?: string;
  verifiedHash?: boolean;  // true if hash matches known-good
  expectedSize?: number;
  size: number;
  installedAt: number;     // Timestamp
}
```

**`chatMessages` table:**
```typescript
{
  id: number;              // Auto-incremented
  role: "user" | "assistant";
  content: string;
  images?: string[];       // Base64 image data
  timestamp: number;
}
```

**`collections` table:**
```typescript
{
  id: string;
  name: string;
  description?: string;
  coverUrl?: string;
  createdAt: number;
}
```

**`achievements` table:**
```typescript
{
  id: string;              // Achievement key
  title: string;
  description: string;
  icon: string;            // Emoji icon
  unlockedAt?: number;     // Timestamp (undefined = locked)
}
```

### LocalStorage Keys

| Key | Purpose |
|-----|---------|
| `retroweb.settings.v1` | JSON object with all user settings (theme, audio, display, accessibility) |
| `retroweb.notifications` | JSON array of notification objects (max 50) |
| `retroweb.language` | Language code (`en`, `es`, `fr`, `de`, `ja`, `pt`) |

### SessionStorage Keys

| Key | Purpose |
|-----|---------|
| `retroweb.loggedIn` | `"true"` if user has passed the login gate |
| `retroweb.screenshotForAI` | Base64 screenshot transferred from Play → Chat route |
| `retroweb.lastPlayedGame` | Filename of last played game (for AI context) |

---

## Theming System

Defined in `src/index.css` using CSS custom properties. Themes are applied via `data-theme` attribute on `<html>`.

**Available themes:**

| Theme | `data-theme` | Style |
|-------|-------------|-------|
| Default | *(none)* | Dark with red accents (#cc0000) |
| NES Classic | `nes` | Light gray with red accents |
| Game Boy | `gameboy` | Green-tinted monochrome |
| SNES | `snes` | Dark purple/indigo palette |
| Terminal | `terminal` | Black with green terminal text |

**Core CSS variables:**

| Variable | Purpose |
|----------|---------|
| `--surface-1`, `--surface-2`, `--surface-3` | Layered background surfaces |
| `--text-primary`, `--text-secondary`, `--text-muted` | Text hierarchy |
| `--accent-primary`, `--accent-secondary` | Brand/action colors |
| `--accent-glow` | Glow effect for accent elements |
| `--border-soft`, `--border-strong` | Border variants |
| `--shadow-sm/md/lg/glow` | Elevation shadows |
| `--transition-fast/base/slow` | Timing constants |

**Accessibility classes:**
- `.a11y-high-contrast` — Increased contrast ratios
- `.a11y-large-text` — Larger font sizes
- `.a11y-reduced-motion` — Disables CSS animations/transitions

**Font stack:** `"RoSpritendo"` (custom retro pixel font loaded from `/fonts/RoSpritendo.otf`) → `"Ubuntu"` → `sans-serif`

---

## Networking

### Netplay (WebRTC P2P)

`src/lib/netplay/session.ts` implements serverless peer-to-peer multiplayer:

1. **Host creates offer** — Generates an SDP offer via `RTCPeerConnection`, waits for ICE gathering, encodes to base64
2. **Guest pastes offer** — Creates an answer SDP, encodes to base64
3. **Host pastes answer** — Connection established
4. **Data exchange** — Input frames (frame number + button bitmask) sent over `RTCDataChannel`

Uses Google STUN servers (`stun:stun.l.google.com:19302`) for NAT traversal. No signaling server — SDPs are exchanged manually (copy/paste).

### Cover Art Scraping

`src/lib/metadata/scraper.ts` fetches box art from the **LibRetro Thumbnails** GitHub repository:

- Maps system IDs to LibRetro repo names (e.g., `nes` → `"Nintendo - Nintendo Entertainment System"`)
- Cleans ROM filenames (removes tags, extensions)
- Tries multiple title variants with region tags (`(USA)`, `(Europe)`, etc.)
- Uses `HEAD` requests to check if thumbnail exists before committing
- URLs follow pattern: `https://raw.githubusercontent.com/libretro-thumbnails/{repo}/master/Named_Boxarts/{title}.png`
- Results cached by the service worker

### Vite Proxy Configuration

The Vite dev server (`vite.config.ts`) includes three proxy rules to route AI service requests through same-origin paths. This is **required** because the app sets `Cross-Origin-Embedder-Policy: require-corp` for SharedArrayBuffer support (needed by multi-threaded WASM cores). Without proxying, cross-origin fetch requests to `localhost:8786`/`8787`/`11434` would be blocked by COEP even if the servers return valid CORS headers.

---

## Input System

`src/gamepad/` handles all controller input:

**`types.ts`** — Defines `ControllerButton` union type (a, b, x, y, dpad, shoulders, sticks, etc.), `MappingProfile`, `MappingOverrides`, `RawPadSnapshot`.

**`mapping.ts`** — Maps physical gamepad button indices to logical buttons. Provides a "Standard (Xbox-like)" default profile. Reads raw `Gamepad` API snapshots and converts to `ControllerVisualState`.

**`keyboard-overrides.ts`** — Maps keyboard keys to gamepad buttons for keyboard-only play.

**`overrides.ts`** — Per-user mapping customizations stored in localStorage.

**Keyboard shortcuts during gameplay (Play route):**

| Key | Action |
|-----|--------|
| Escape | Toggle menu overlay / close menu |
| F1 | Quick save to slot 0 |
| F2 | Cycle speed (0.5x → 1x → 2x → 4x) |
| F3 | Toggle FPS counter |
| F4 | Quick load slot 0 / Toggle turbo |
| F5 | Rewind (hold) |
| F6 | Toggle speedrun timer |
| F7 | Record speedrun split |
| F11 | Toggle fullscreen |

**`useGamepadVisualizer` hook** — Polls connected gamepads at `requestAnimationFrame` rate and returns visual state for the controller test page.

---

## PWA & Service Worker

Configured via `vite-plugin-pwa` with Workbox:

- **Registration:** `autoUpdate` mode — new service workers install and activate automatically
- **Precaching:** All `*.{js,css,html,ico,png,svg,wasm,json}` files (up to 50MB per file)
- **Runtime caching:** GitHub thumbnail URLs cached with `CacheFirst` strategy (7-day expiration, 200 entry max)
- **Manifest:** Standalone display, landscape orientation, `RetroWeb Emulator` name
- **Icons:** `pwa-192x192.png` and `pwa-512x512.png` (maskable)
- **Update notifications:** When a new SW is detected, a toast offers "Refresh" action

---

## Internationalization

`src/lib/i18n/index.ts` provides a lightweight i18n system:

- **Supported languages:** English, Spanish, French, German, Japanese, Portuguese
- **Storage:** Language preference in `localStorage["retroweb.language"]`
- **API:** `useI18n()` hook returns `{ t(key), lang, setLang, LANGUAGE_LABELS }`
- **Translation keys:** Organized by section (`nav.home`, `library.search`, `settings.title`, etc.)

---

## Achievement System

`src/lib/achievements.ts` defines unlockable achievements:

| ID | Title | Trigger |
|----|-------|---------|
| `first_game` | First Steps | Play first game |
| `five_games` | Getting Started | Play 5 different games |
| `ten_games` | Retro Explorer | Play 10 different games |
| `hour_played` | Time Flies | 1 hour total playtime |
| `ten_hours` | Dedicated Gamer | 10 hours total playtime |
| `five_systems` | System Hopper | Play on 5 different systems |
| `first_save` | Safety First | Create first save state |
| `first_favorite` | Collector | Favorite a game |
| `bios_installed` | Power Up | Install a BIOS file |
| `ai_chat` | AI Assistant | Send AI chat message |
| `voice_mode` | Voice Commander | Use voice mode |
| `screenshot_ai` | Show & Tell | Send screenshot to AI |
| `theme_changed` | Style Points | Change theme |
| `speed_demon` | Speed Demon | Use fast forward |

`checkAndUnlock(id)` checks if already unlocked, stores in Dexie if new, shows a toast notification, and pushes to the notification center.

---

## Notification System

`src/lib/notifications.ts` provides an in-app notification center:

- Stored in `localStorage["retroweb.notifications"]` as JSON array (max 50)
- Each notification has: `id`, `title`, `message`, `icon`, `timestamp`, `read`
- `pushNotification()` adds to storage and dispatches a `retroweb:notification` CustomEvent
- `NotificationCenter` component (lazy-loaded in App shell) listens for the event and shows a bell icon with unread count

---

## Easter Eggs

Several delightful easter eggs are built into the shell:

1. **PacmanGhostEasterEgg** — A Pac-Man ghost that appears after rapid clicking (configurable `frightenThreshold`). Enters "frightened" blue mode for a duration.

2. **PongBackground** — An animated Pong game plays behind the main content on non-play pages. Uses `requestAnimationFrame` for smooth rendering.

3. **MarioBrickEasterEgg** — Interactive Mario-style brick blocks that can be hit.

---

## Security & Isolation

**Cross-Origin Isolation:**
- `Cross-Origin-Opener-Policy: same-origin` — Required for `SharedArrayBuffer`
- `Cross-Origin-Embedder-Policy: require-corp` — Required for `SharedArrayBuffer`
- These are set by a custom Vite plugin in both dev and preview servers
- `SharedArrayBuffer` enables multi-threaded WASM cores for better emulation performance

**Capability checking** (`src/lib/capability/capability-check.ts`):
```typescript
getThreadingCapability() → { canUseThreads: boolean, reason: string }
```
Checks for `SharedArrayBuffer` availability and `crossOriginIsolated` status.

**Storage quota** (`src/lib/capability/storage-quota.ts`):
Estimates available browser storage for games and saves.

**Privacy:**
- No external data transmission (except LibRetro thumbnail HEAD requests)
- No analytics or tracking
- All game data, saves, and BIOS files stay in the browser
- AI processing happens on the local machine (Ollama, Whisper, Kokoro)

---

## Supported Systems

Defined in `src/data/coreMap.json` and `src/data/systemBrowserData.ts`:

| System | Core | Extensions | BIOS | Tier |
|--------|------|------------|------|------|
| NES | fceumm (fallback: nestopia) | `.nes`, `.zip` | None | doable |
| SNES | snes9x | `.smc`, `.sfc`, `.zip` | None | doable |
| Game Boy / GBC / GBA | mgba (fallback: gambatte) | `.gb`, `.gbc`, `.gba`, `.zip` | None | doable |
| Sega Genesis | genesis_plus_gx (fallback: picodrive) | `.md`, `.smd`, `.gen`, `.bin`, `.zip` | None | doable |
| PlayStation 1 | pcsx_rearmed (fallback: duckstation) | `.chd` | `scph5501.bin` | doable |

Each system entry includes:
- `tier` — Readiness level (`doable`, `experimental`, `coming_soon`)
- `preferredCore` / `fallbackCores` — Core selection with fallback
- `extensions` — Supported ROM file extensions
- `biosRequired` — List of required BIOS filenames
- `coreVersion` — Version string (currently `1.22.0` for all)
- `corePath` — URL path to core binaries (e.g., `/cores/fceumm/1.22.0/fceumm_libretro`)
