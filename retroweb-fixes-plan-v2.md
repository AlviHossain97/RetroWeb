# RetroWeb — Fixes & Roadmap Plan v2

> **Current state:** v0.1.0 · Vite + React + TS on localhost:5173
> **Date:** February 28, 2026

---

## Current State Assessment (from screenshots)

**What exists:**
- Dark sidebar with 3 nav items (Library, Supported Systems, Settings)
- Library page has a centered drop zone ("Drop your ROM here to play") listing NES, SNES, Gameboy, GBA, Genesis, PS1 (CHD)
- Version badge in sidebar footer: "v0.1.0 · WASM Powered"
- Running on Vite dev server (port 5173)

**What's broken or missing:**
- Settings page: completely empty gray void — no content at all
- System Browser page: completely empty gray void — no content at all
- Library page: no game grid, no cards, no sections, no empty-state art — just the drop zone floating in gray space
- No first-visit legal modal
- No toast/error system visible
- No loading states or skeleton loaders
- The entire content area background is a flat gray that feels unfinished and disconnected from the dark sidebar
- No app logo/branding in the sidebar header (there's a small icon but no wordmark)
- Drop zone text is functional but visually plain — no animation, no hover state visible
- No indication of what happens after a ROM is dropped (does it work? does it crash? does RetroArch menu appear?)

---

## Priority #0: Auto-Launch Fix (the #1 blocker — before anything else)

### Root Cause

RetroArch WASM opens its built-in menu when no content is passed at boot time, or when the ROM isn't properly mounted in the VFS before `launch()` is called. This is the single most visible bug — it makes the app feel broken even if everything else works.

### Correct Launch Sequence (enforce every time)

```
1. User drops file → detect system via extension + header magic bytes
2. Pick core from coreMap.json (preferredCore first)
3. Validate + mount BIOS if required (exact filename match)
4. Unzip if needed → mount ROM to VFS path /content/game.<ext>
5. Call launch({ core, rom, bios }) with content pre-mounted
6. Immediately suppress RetroArch UI → show your custom overlay
```

### If Using Nostalgist.js Directly

```typescript
await Nostalgist.launch({
  core: 'fceumm',
  rom: file,                    // Blob or File object
  bios: biosFiles,              // array of { filename, content }
  retroarchConfig: {
    menu_driver: 'null',        // suppress RA menu entirely
    video_fullscreen: 'true',
    // ... your defaults
  },
  // Never call .menu() — ever
});
```

### If Using Koin Deck Player

```typescript
KoinDeckPlayer.launch({
  core: coreMap[detectedSystem].preferredCore,
  rom: { filename: file.name, content: await file.arrayBuffer() },
  bios: biosArray,
  config: { ...yourDefaults },
});
```

### Debug Checklist (2-minute smoke test)

Open DevTools → Console + Network tab:

- [ ] ROM written to VFS? (check for VFS mount log or error)
- [ ] Core `.wasm` fetched successfully? (check Network tab for 200 on .wasm)
- [ ] Any `SharedArrayBuffer` / COEP errors in console?
- [ ] Log the exact launch args before calling launch()
- [ ] After launch: is canvas rendering frames? (check for black screen vs. actual output)

**Fix this before touching anything else.** Once ROMs boot cleanly without the RetroArch menu, everything downstream becomes testable.

---

## Priority #0.5: Content Area Background & Layout Foundation

### The Problem (visible in all 3 screenshots)

The entire content area is a flat `#808080`-ish gray that looks like a missing CSS background, not a design choice. Combined with empty pages (Settings, System Browser), the app currently feels like a broken prototype rather than an early build.

### Fixes

- **Match the content area to the dark theme.** The sidebar is a nice dark charcoal — the content area should be a slightly lighter shade of the same palette (e.g., `bg-zinc-900` or `bg-neutral-900`), not a mid-tone gray that clashes.
- **Add a subtle noise/grain texture or gradient** to the content background so it feels intentional.
- **Ensure the sidebar and content area feel like one cohesive app**, not two separate panels glued together.
- **The drop zone** should have more visual weight — a subtle border glow on hover, a micro-animation on the upload icon, and a pulsing dashed border on drag-over.

This is a 30-minute fix that will transform the entire perceived quality of the app.

---

## Tech Stack Lock-In (confirm today)

| Layer | Choice | Status |
|---|---|---|
| Framework | React 19 + Vite 6 + TypeScript | ✅ Already running |
| Emulator | Koin Deck Player or Nostalgist.js v0.21+ (npm) | 🔧 Install + wire up |
| Storage | Dexie.js + OPFS (`navigator.storage.getDirectory()`) | 🔧 Install |
| UI | shadcn/ui + Tailwind + Radix (keep dark theme) | ✅ Partially in place |
| Cross-origin isolation | `coi-serviceworker` (one-line addition for SAB/threads) | 🔧 Add |
| Core hosting | `/public/cores/` (self-hosted, version-pinned) + jsDelivr fallback | 🔧 Set up |
| State management | Zustand + persist middleware | 🔧 Install |
| Toast/notifications | sonner (shadcn-compatible) or react-hot-toast | 🔧 Install |

---

## Full Roadmap: Phases -1 through 10

---

### Phase -1 — Foundation & Design System (1–2 days)

**The app currently looks like scaffolding. This phase makes it look intentionally designed.**

**Tasks:**

- [ ] **Fix the content background color** — switch from gray to dark theme palette (`bg-zinc-900`/`bg-zinc-950`) so sidebar and content feel unified
- [ ] **Collapsible sidebar** — hamburger menu on mobile, smooth collapse animation on desktop
- [ ] **Design tokens** — establish consistent color palette, spacing scale, border radii, and typography in Tailwind config (don't ad-hoc colors)
- [ ] **Empty-state illustrations** — every empty page (Library with no games, System Browser, Settings) gets a purposeful empty state with an icon, heading, and call-to-action. Examples:
  - Library (empty): controller icon + "Your library is empty" + "Drop a ROM or click to upload" button
  - System Browser: grid of system cards (even before emulation works, this page should show the catalog)
  - Settings: organized settings panels with sensible defaults, even if some aren't wired up yet
- [ ] **Skeleton loaders** — add shimmer skeletons for game cards, system cards, and any async content
- [ ] **Toast system** — install `sonner` or equivalent. Every user action should get feedback (success, error, info)
- [ ] **First-visit legal modal** — "RetroWeb does not host ROMs or BIOS files. You must own the original hardware and software." with "I understand" button. Persistent footer link to legal page.
- [ ] **App branding** — the sidebar header has a tiny icon but no wordmark. Add "RetroWeb" (or your name) as a text logo next to it. Consider a subtle retro-styled logotype.

**Success criteria:** Every page looks intentionally designed, not placeholder-gray. Empty states guide the user. Dark theme is cohesive.

**🆕 My additions to this phase:**

- [ ] **Global drag-and-drop overlay** — when user drags a file *anywhere* over the window (not just the Library drop zone), show a full-screen translucent overlay with "Drop ROM to play" so users don't have to navigate to Library first
- [ ] **Page transition animations** — subtle fade/slide on route changes so navigation feels smooth, not jarring
- [ ] **Sidebar active state polish** — the current active state (slightly lighter background) is functional but could use a left accent bar or subtle gradient to feel more premium
- [ ] **Favicon + meta tags** — add a proper favicon, Open Graph tags, and `<title>` per route so browser tabs aren't generic

---

### Phase 0 — Stabilize Emulator Boot (3–5 days)

**The auto-launch fix from Priority #0, formalized into a phase.**

**Tasks:**

- [ ] **Single `launchGame(file)` pipeline** — one function that handles the entire flow: detect → validate → mount BIOS → unzip → mount ROM → launch core → suppress RA menu → show custom overlay
- [ ] **Robust error UI + toast system:**
  - "BIOS missing: scph5501.bin" (with link to BIOS management)
  - "Unsupported file format" (with list of accepted extensions)
  - "Core failed to load — try refreshing" (with retry button)
  - "This file doesn't look like a ROM" (for non-ROM drops)
- [ ] **Safe-mode fallback** — detect if `SharedArrayBuffer` is unavailable and fall back to single-threaded mode automatically (don't just crash)
- [ ] **Self-host cores** — copy verified `.wasm` + `.js` files to `/public/cores/{core}/{version}/`
- [ ] **Add `coi-serviceworker`** — enables cross-origin isolation for `SharedArrayBuffer` / threads without requiring server header config
- [ ] **Loading state during core download** — show a progress indicator ("Loading NES emulator... 2.3 MB") instead of a blank screen while the .wasm downloads

**Success criteria:** NES, SNES, GBA, Genesis, PS1 boot in ≤3 clicks. Zero RetroArch menu appearances. All errors show user-friendly toasts, not console errors.

**🆕 My additions to this phase:**

- [ ] **Launch arg logging** — in dev mode, log the exact `{ core, rom, bios, config }` object to console before every launch. This is the single most useful debug tool.
- [ ] **Core download caching** — once a core .wasm is fetched, store it in the service worker cache (or IndexedDB) so subsequent launches are instant
- [ ] **"What went wrong?" expandable detail** — on error toasts, add a small "Details" toggle that shows the technical error for power users / bug reports, while keeping the default message friendly
- [ ] **Timeout handling** — if core doesn't produce a frame within 10 seconds of launch, show "The emulator is taking too long. The ROM may be incompatible." instead of hanging forever

---

### Phase 1 — Real Library (not just a drop zone) (4–6 days)

**The Library page currently has nothing except the drop zone. This phase makes it a real game collection.**

**Tasks:**

- [ ] **Dexie + OPFS storage layer** — persist game metadata, covers, and optionally ROM files
- [ ] **"Add to Library" toggle** — default = memory-only (privacy-first). User can opt in to persist ROMs locally.
- [ ] **Game cards** with: filename-derived title, system badge (colored chip), last-played date, playtime counter, favorite star toggle, local cover image upload
- [ ] **Library sections:** Recently Played (top), Favorites, All Games (alphabetical with system grouping)
- [ ] **Drag & drop anywhere on the page** (not just the center zone) — the entire Library page is a drop target
- [ ] **Instant add** — dropped ROM appears in the grid immediately with a loading shimmer, then resolves with detected system info
- [ ] **Multi-file drop** — drop a folder or multiple files at once; batch-detect and add all valid ROMs
- [ ] **Search/filter bar** — filter by system, name, or favorite status

**Success criteria:** Upload → appears in grid instantly → click card → game launches. Library persists across page reloads (if "Add to Library" is on).

**🆕 My additions to this phase:**

- [ ] **Virtualized grid** — use `react-virtuoso` or `@tanstack/react-virtual` for the game grid. If a user has 500+ ROMs, rendering all cards will lag. Virtualize from day one.
- [ ] **Grid/list view toggle** — some users prefer a compact list view (especially on smaller screens). Offer both.
- [ ] **Sort options** — sort by name, system, last played, date added, playtime
- [ ] **Game card context menu** — right-click (or long-press on mobile) for quick actions: Launch, Remove from Library, Export Save, View Details
- [ ] **Duplicate detection** — if user drops the same ROM twice (by filename or hash), warn instead of silently duplicating
- [ ] **Drop zone visual upgrade** — when the Library has games, shrink the drop zone to a small "+" button in the corner or a subtle top bar, so it doesn't dominate the view. Only show the large centered drop zone when the library is empty.

---

### Phase 2 — System Browser (the Truth Dashboard) (3–4 days)

**The Supported Systems page is currently a completely empty gray void. This phase makes it the app's knowledge hub.**

**Tasks:**

- [ ] **Two tabs:** Supported | Experimental (with counts: "12 systems" / "5 systems")
- [ ] **System cards** with:
  - System name + era label (e.g., "1990 · 16-bit")
  - Local SVG icon/logo for each system
  - Accepted file extensions list (e.g., ".nes, .zip")
  - BIOS status indicator: ✅ Ready / ❌ Missing / ➖ Not Required
  - Preferred core name + version
  - Performance badge: Excellent / Playable / Heavy
  - "Upload BIOS" button (inline, if BIOS is missing)
- [ ] **Search + filter** by system name, tier, BIOS status
- [ ] **Expandable detail panel** — click a system card to see: full core list (preferred + fallbacks), known quirks, compatible extensions, expected performance notes
- [ ] **"Quick Launch Test ROM" button** (dev-only, hidden in production) — boots a test ROM for that system to verify the core works

**Success criteria:** Users instantly understand what works, what needs BIOS, and what's experimental. No guessing.

**🆕 My additions to this phase:**

- [ ] **BIOS status summary banner** — at the top of System Browser, show "3 of 5 BIOS files uploaded" with a progress bar. Makes it immediately clear what's needed.
- [ ] **"Ready to play" vs "Needs setup" grouping** — within each tab, systems with all prerequisites met appear first (with a green "Ready" tag), systems needing BIOS appear below with a clear "Upload BIOS to enable" call-to-action
- [ ] **System card link to Library** — show a count of how many games the user has for that system ("4 games in library"), clickable to filter the Library
- [ ] **Responsive grid** — 3-4 columns on desktop, 2 on tablet, 1 on mobile. Cards should be scannable at a glance.

---

### Phase 3 — BIOS Vault (2–3 days)

**Tasks:**

- [ ] **Dedicated BIOS store** in OPFS (separate from ROM storage)
- [ ] **Filename validation** — exact match required (e.g., must be `scph5501.bin`, not `SCPH5501.BIN` or `ps1_bios.bin`)
- [ ] **Optional hash + size validation** — confirm the BIOS file is correct, not just correctly named
- [ ] **Global BIOS status** — shown in System Browser cards AND as a launch-blocker modal when trying to play a game that needs BIOS
- [ ] **BIOS management page** (in Settings or as sub-route of System Browser):
  - List of all systems that need BIOS
  - Upload button per BIOS file
  - Status: ✅ Verified / ⚠️ Wrong hash / ❌ Missing
  - "Remove" button per BIOS file
- [ ] **Clear error when BIOS is wrong:** "You uploaded 'scph5501.bin' but the file hash doesn't match. This may be the wrong version. Expected hash: abc123..."

**Success criteria:** Missing BIOS → clear modal with exact filename + expected hash. BIOS upload → instant status update across all pages.

**🆕 My additions to this phase:**

- [ ] **Drag-and-drop BIOS upload** — same UX as ROM upload. Drop a BIOS file anywhere → auto-detect which system it belongs to by filename → store it
- [ ] **Batch BIOS upload** — user drops a folder of BIOS files → all valid ones are matched and stored in one action
- [ ] **BIOS filename case normalization** — if user uploads `SCPH5501.BIN`, auto-rename to `scph5501.bin` internally and accept it (don't reject over case)

---

### Phase 4 — Saves & States (4 days)

**Tasks:**

- [ ] **Auto SRAM save** every 30 seconds + on `beforeunload` + on `visibilitychange` (tab switch)
- [ ] **Save state slots (0–9)** with thumbnails + timestamps
- [ ] **Save state UI** — accessible from the in-game overlay (Phase 6) and from the game detail page
- [ ] **Export/import per-game** — download a `.zip` of all saves for one game
- [ ] **Export/import full profile** — all saves + settings + controller mappings in one `.zip`
- [ ] **Save integrity check** — if a save file is corrupted (truncated write), warn user instead of silently losing data

**Success criteria:** Close tab mid-game → reopen → game resumes exactly where you left off. Save states have visual thumbnails.

**🆕 My additions to this phase:**

- [ ] **Auto-save indicator** — subtle "Saving..." toast or icon flash every 30s so user knows their progress is safe (don't make it annoying — just a brief icon)
- [ ] **Save versioning by core hash** — tag each save with the core version that created it. If core is updated later, warn: "This save was created with fceumm 1.22.0 — you're now on 1.23.0. It should work, but you can keep a backup."
- [ ] **"Quick Resume" on library cards** — if a game has a recent auto-save, show a "Resume" button directly on the card (in addition to "Play from start")
- [ ] **Undo delete** — if user deletes a save, give a 10-second undo toast before actually deleting from OPFS

---

### Phase 5 — Input System (3–4 days)

**Tasks:**

- [ ] **Gamepad API integration** — detect connected controllers, show them in UI
- [ ] **Visual remapping UI** — show a controller diagram, click a button → press the physical button to map
- [ ] **Per-system defaults** — sensible default mappings for each system (NES A/B, SNES X/Y/A/B, etc.)
- [ ] **Per-game overrides** — save custom mappings per game
- [ ] **In-player overlay** — show connected controllers, "Press button to map" prompt
- [ ] **Keyboard defaults** — arrow keys + WASD + Z/X/A/S common mapping out of the box
- [ ] **Mobile virtual touch controls** — on-screen D-pad + buttons, GPU-accelerated, configurable size/position/opacity

**Success criteria:** Plug in Xbox/PS controller → works instantly with correct default mapping. Remap is visual and intuitive.

**🆕 My additions to this phase:**

- [ ] **Controller haptic feedback** — use the Gamepad API haptic actuator for rumble-supported games (where the core supports it)
- [ ] **"Controller connected" toast** — when a gamepad is plugged in, show a brief "Xbox Controller connected" notification so user knows it was detected
- [ ] **Touch control presets per system** — NES touch layout is different from PSX (fewer buttons). Auto-switch layout based on the running system.
- [ ] **Touch control editor** — let user drag buttons around to reposition the virtual controls to their preference. Save layout per system.

---

### Phase 6 — Player Experience & Custom Overlay (3 days)

**This is a new high-priority phase. The goal: when you're playing, it feels like a native console app, not a web page with an emulator <iframe>.**

**Tasks:**

- [ ] **Fullscreen canvas** — the emulator canvas takes over the entire viewport (no sidebar, no header)
- [ ] **Custom overlay UI** (RetroPie quick-menu style) — slides in from the side or bottom:
  - Save State (to selected slot)
  - Load State (from selected slot, with thumbnail preview)
  - Reset game
  - Screenshot (save to gallery)
  - Shader presets (CRT, scanlines, sharp bilinear, none)
  - Pause / Resume
  - Return to Library
- [ ] **Hide RetroArch menu completely** — via retroarch config: `menu_driver = "null"`
- [ ] **FPS counter** (toggleable) — small overlay in corner
- [ ] **Performance warning** for Experimental systems — "This system is experimental. Performance may vary." banner at top of player
- [ ] **Hotkeys:**
  - `Escape` → open/close overlay
  - `F11` → toggle fullscreen
  - `F1` → quick save
  - `F4` → quick load

**Success criteria:** Playing a game feels immersive and seamless. All controls are accessible through the custom overlay. RetroArch's own UI is never visible.

**🆕 My additions to this phase:**

- [ ] **Overlay backdrop blur** — when the overlay slides in, blur the game canvas behind it (via CSS `backdrop-filter`) for a polished feel
- [ ] **Quick-save notification** — when user hits F1, show a brief screenshot thumbnail that fades in and out (like PlayStation's save notification)
- [ ] **Volume control in overlay** — simple slider. Emulators are often too loud by default.
- [ ] **Aspect ratio options** — original (4:3, varies by system), stretched to fill, integer scaling. Accessible from overlay.
- [ ] **Return-to-library confirmation** — "Save before quitting?" prompt with Save & Quit / Quit Without Saving / Cancel

---

### Phase 7 — Performance, Security & Deployment (3 days)

**Tasks:**

- [ ] **Self-hosted cores** in `/public/cores/` with version-pinned paths
- [ ] **`coi-serviceworker`** for cross-origin isolation
- [ ] **Storage quota meter** in Settings → Storage (progress bar + MB used / available)
- [ ] **Granular clearing:**
  - Clear ROM cache only
  - Clear saves only (with export prompt first)
  - Clear BIOS files
  - Clear everything (double-confirm)
- [ ] **Service worker** — cache app shell + static assets. Pass through core/WASM and OPFS fetches. (See service worker strategy from main plan.)
- [ ] **Strict CSP** — no eval, no inline scripts, no remote execution from ROM data
- [ ] **Filename sanitization** — strip path traversal, null bytes, special chars from all uploaded filenames

**Success criteria:** Works on Chrome, Edge, Firefox, Safari (desktop + mobile). Storage usage is visible and manageable.

**🆕 My additions to this phase:**

- [ ] **Storage warning at 80%** — when OPFS/IndexedDB usage exceeds 80% of estimated quota, show a persistent but dismissible warning in the sidebar or Library page
- [ ] **"Export all saves before clearing" prompt** — any time user tries to clear data, offer to export saves first. This prevents accidental data loss.
- [ ] **Build output optimization** — ensure Vite is code-splitting properly. The initial bundle should be tiny (< 200KB gzipped for the app shell). Cores are lazy-loaded.
- [ ] **Error boundary at the app root** — if the React app crashes entirely, show a recovery page with "Clear data and restart" instead of a white screen

---

### Phase 8 — Mobile & PWA Polish (2–3 days)

**Tasks:**

- [ ] **PWA manifest** — name, icons (192px + 512px), theme color, background color, display: standalone
- [ ] **Service worker** for offline support (app shell cached; previously downloaded cores work offline)
- [ ] **Landscape lock** during gameplay (via Screen Orientation API)
- [ ] **Touch-optimized** everything — 44px minimum touch targets, swipe gestures for sidebar
- [ ] **iOS Safari workarounds:**
  - "Tap to Start Audio" overlay (AudioContext won't auto-play)
  - Memory budget warnings for Experimental systems (iOS has ~700MB limit)
  - Standalone PWA testing (some APIs behave differently in standalone mode)
- [ ] **Responsive layout** — sidebar collapses to bottom tab bar on small screens, or to hamburger menu
- [ ] **Add-to-homescreen prompt** — subtle banner after 2nd visit: "Install RetroWeb for the best experience"

**Success criteria:** Install on Android/iOS → feels like a native app. Touch controls work comfortably. Landscape gameplay is seamless.

**🆕 My additions to this phase:**

- [ ] **Notch/safe-area handling** — on modern phones with notches/dynamic islands, ensure the game canvas and touch controls respect safe area insets (`env(safe-area-inset-*)`)
- [ ] **Prevent pull-to-refresh during gameplay** — CSS `overscroll-behavior: none` on the player page to prevent accidental page refreshes
- [ ] **Wake lock during gameplay** — use the Screen Wake Lock API to prevent the screen from dimming/locking while playing

---

### Phase 9 — Testing & Regression (ongoing)

**Tasks:**

- [ ] **Playwright E2E tests:**
  - Upload ROM → boot → save → reload → verify save persists
  - BIOS missing → modal appears → upload BIOS → launch succeeds
  - Input mapping → remap → verify mapping persists
- [ ] **Vitest unit tests:**
  - ROM detection (extension + header magic bytes)
  - BIOS validation (filename + hash)
  - Core mapping resolution (preferred → fallback)
  - Storage layer (Dexie + OPFS read/write)
- [ ] **Core version pinning** in `/public/cores/vX.Y/`
- [ ] **Regression tests (automated assertions):**
  - "RetroArch menu is never visible" (check for RA menu DOM elements)
  - "BIOS missing blocks launch" (not just warns)
  - "Drop non-ROM file → error toast, no crash"
- [ ] **Compatibility matrix** — updated after every core version bump. Published in `docs/compatibility.md`.
- [ ] **CI pipeline:** PR → lint + typecheck → unit tests → build → E2E (Chrome) → merge

**🆕 My additions to this phase:**

- [ ] **Visual regression tests** — Playwright screenshot comparisons for Library (empty), Library (with games), System Browser, Player overlay. Catch unintended UI changes.
- [ ] **Memory budget test** — automated check that peak memory stays under 700MB for Doable system test ROMs (catches regressions that would crash iOS)
- [ ] **Core load time benchmark** — track .wasm download + compile time per core. Alert if a version bump regresses load time by >20%.

---

### Phase 10 — Final Polish & Launch (1 week)

**Tasks:**

- [ ] **Empty states with illustrations** — every page should feel complete even when empty
- [ ] **Keyboard shortcuts overlay** — press `?` to see all shortcuts
- [ ] **Accessibility:**
  - ARIA labels on all interactive elements
  - Focus traps in modals
  - Reduced-motion support (disable shader transitions, UI animations)
  - Screen reader announcements for state changes
  - Tab navigation through entire UI
- [ ] **Help page** — "Where to find BIOS filenames" (legal links only, no ROM links)
- [ ] **CHD conversion guide** — "How to convert disc images to CHD" with step-by-step `chdman` instructions
- [ ] **Performance audit** — Lighthouse 95+ on all categories
- [ ] **Legal copy review** — lawyer-reviewed disclaimer
- [ ] **Privacy-first launch** — no analytics unless user opts in
- [ ] **Changelog / release notes** — visible in Settings

**🆕 My additions to this phase:**

- [ ] **Onboarding tutorial** — optional 4-step guided walkthrough for first-time users: "Upload a ROM" → "Your Library" → "Managing Saves" → "Keyboard Shortcuts". Dismissible, never shows again.
- [ ] **"About" modal** — credits, open-source licenses, version info, links to GitHub
- [ ] **Performance mode explanation** — in Settings, a clear explanation of what threading/COEP does and when to enable it
- [ ] **Print-ready compatibility page** — `docs/compatibility.md` should also be accessible at `/help/compatibility` in the app itself, so users can check supported systems without leaving the app
- [ ] **Soft launch plan** — deploy to a staging URL, invite 10-20 beta testers, collect feedback for 1 week before public launch

---

## Additional Fixes I Identified from the Screenshots

These are specific issues visible in the current build that aren't explicitly covered in any phase above:

### 1. Content Area Background Mismatch (Critical Visual Issue)

The content area appears to be using a default or unset background color (mid-gray) that clashes with the dark sidebar. This is the single biggest visual issue — it makes every page look broken.

**Fix:** Set the content area to `bg-zinc-900` or `bg-zinc-950` to match the dark theme. This alone will transform the app.

### 2. Sidebar Header is Underutilized

There's a small icon in the top-left of the sidebar but no app name. This is prime real estate for branding.

**Fix:** Add "RetroWeb" (or your app name) as a styled wordmark next to the icon. Consider a retro pixel-art font or a clean sans-serif with a subtle gradient.

### 3. No Visual Hierarchy on the Library Page

The drop zone is centered in a gray void. Even when empty, the Library page should feel like a place where your game collection lives.

**Fix:**
- Add a header: "Your Library" with game count
- Show section headers even when empty: "Recently Played", "Favorites", "All Games"
- The drop zone should be the empty state for "All Games", not the entire page

### 4. System Browser Should Never Be Empty

Even before any games are uploaded or BIOS installed, the System Browser should show the full catalog of supported systems. This is reference information, not dynamic content.

**Fix:** Populate from `systems.json` on first render. The data is static — there's no reason for this page to ever be blank.

### 5. Settings Page Should Have Structure Immediately

The Settings page should show organized sections even if some settings aren't wired up yet:

- **Display:** Shader presets, aspect ratio, FPS counter toggle
- **Audio:** Volume, audio latency
- **Input:** Controller mapping, keyboard shortcuts
- **Storage:** Quota meter, clear data buttons
- **Performance:** Threading toggle, cross-origin isolation status
- **About:** Version, legal, licenses

Even if the controls are disabled/placeholder, the structure communicates that this is a real app with a plan.

### 6. No Loading/Progress Feedback Anywhere

There's no visible loading state for anything. When a core is downloading, when a ROM is being processed, when saves are being read — the user sees nothing.

**Fix:** Add skeleton loaders (shimmer placeholders) for all async content, and a progress bar/spinner for file operations.

### 7. Version Badge Could Be More Useful

"v0.1.0 · WASM Powered" is nice but could also show environment status:

**Enhanced:** `v0.1.0 · WASM Powered · Threads: ✅` (or ❌ if SharedArrayBuffer unavailable)

This gives developers and power users instant diagnostics.

---

## Bonus Fool-Proof Additions

### Core Hosting Strategy

```
Primary:    /public/cores/{core}/{version}/{core}_libretro.wasm
Fallback:   jsDelivr CDN (pinned hash)
Lock:       Version pinned in coreMap.json — never "latest"
```

### Risk Register (add to README)

| Risk | Mitigation |
|---|---|
| Browser storage quota exceeded | Quota meter + warning at 80% + granular clearing |
| iOS Safari AudioContext blocked | Tap-to-start overlay |
| iOS Safari 700MB memory limit | Memory monitoring + warn before launching heavy games |
| Large ROM memory spike | Show loading % + enforce CHD for disc images |
| Core .wasm unavailable | Same-origin primary + CDN fallback + graceful error |
| Save corruption on crash | Auto-save every 30s + save versioning + export prompts |
| RetroArch menu appears | `menu_driver = "null"` + regression test |

### Future-Proofing

- Saves are tagged with core version hash → enables auto-migration path later
- `coreMap.json` + `systems.json` designed for community PRs when you open-source
- Storage layer abstracted behind a clean API → can swap Dexie for another backend later
- Emulator wrapper abstracted → can swap Nostalgist for another library without rewriting UI

---

## Priority Summary (What to Do This Week)

| Priority | Task | Time |
|---|---|---|
| **Now** | Fix content area background color (30 min) | 30 min |
| **Now** | Auto-launch fix — get ROMs booting without RA menu | 1–2 days |
| **This week** | Phase -1: Design foundation, empty states, toasts, legal modal | 1–2 days |
| **This week** | Phase 0: Stable emulator boot for 5 systems | 3–5 days |
| **Next week** | Phase 1: Real library with game cards | 4–6 days |
| **After that** | Phases 2–10 in order | Ongoing |

The single most impactful thing you can do in the next hour is change the content area background to match the dark sidebar. The second most impactful thing is fixing auto-launch. Everything else builds on those two foundations.
