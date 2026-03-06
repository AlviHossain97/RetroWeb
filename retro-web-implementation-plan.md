# RetroWeb — Implementation Plan v2 (Production-Ready)

> **Last revised:** February 2026
> **Status:** Pre-development — ready for Phase 0 kickoff

---

## 0) Goal & Non-Goals (v1)

### Goal

A beautiful, fast, fully client-side React web app that lets users upload their own ROMs + BIOS and play **all "Doable" + "Experimental"** systems from RetroPie's official supported-systems list while staying 100% legal and private.

### Non-Goals (v1)

- Hosting or streaming any ROMs/BIOS
- Guaranteed high-performance PS2 / GameCube / Wii / Dreamcast on low-end devices
- User accounts or cloud sync (add in v2)
- Scraping box art automatically (user can upload or we add optional free cover API later)

---

## 1) System Support Strategy — Doable + Experimental

### Source of Truth

[https://retropie.org.uk/docs/Supported-Systems/](https://retropie.org.uk/docs/Supported-Systems/) (74 systems as of Feb 2026). We maintain our own `systems.json` + `coreMap.json` derived from it.

### Three Tiers in UI (honest & clear)

| Tier | Label in UI | Example Systems | Expected Performance (mid-range laptop/desktop) | Warning Banner? |
|---|---|---|---|---|
| **Doable** | ✅ Supported | NES, SNES, GB/GBC/GBA, Genesis, PS1, Atari, Master System, PCE/TG16 | Excellent (60 fps, low latency) | No |
| **Experimental** | ⚠️ Experimental | N64, Dreamcast, Saturn, PSP, Neo Geo CD | Playable on powerful devices; may drop frames | Yes + perf toggle |
| **Hidden** | Not listed | PS2, GameCube, Wii, most MAME heavy sets, 3DO | Not viable in browser today | N/A |

### Core Mapping (`coreMap.json`)

Single source of truth. Core URLs **must** be pinned to a specific version hash — never "latest" — to prevent save-state breakage across updates.

```json
{
  "nes": {
    "tier": "doable",
    "preferredCore": "fceumm",
    "fallbackCores": ["nestopia", "mesen"],
    "extensions": [".nes", ".zip"],
    "biosRequired": [],
    "coreVersion": "1.22.0",
    "corePath": "/cores/fceumm/1.22.0/fceumm_libretro"
  },
  "ps1": {
    "tier": "doable",
    "preferredCore": "duckstation",
    "extensions": [".chd"],
    "biosRequired": ["scph5501.bin"],
    "coreVersion": "0.1.7823",
    "corePath": "/cores/duckstation/0.1.7823/duckstation_libretro"
  }
}
```

### ✦ NEW: Core Availability Audit (Phase 0 Deliverable)

Before building any system catalog UI, we must produce a verified matrix:

| System | Core | .js exists? | .wasm exists? | Boots in Chrome? | Boots in Firefox? | Boots in Safari? | Save works? |
|---|---|---|---|---|---|---|---|
| NES | fceumm | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| ... | ... | ... | ... | ... | ... | ... | ... |

**Rule:** No system enters the UI catalog until its preferred core passes all columns. This prevents shipping a beautiful `/systems` page for systems we can't actually run.

---

## 2) High-Level Architecture (2026 Edition)

### ✦ CORRECTED: Framework Decision

~~Next.js does not use Vite under the hood.~~ Next.js 15 uses its own build pipeline (with optional Turbopack in dev). This plan removes the incorrect "Vite under the hood" claim.

**Framework choice — make it deliberately:**

| Option | Best For | Trade-offs |
|---|---|---|
| **Next.js 15 (App Router, `output: 'export'`)** | If you want file-based routing, static export to GitHub Pages/Cloudflare Pages, and optional SSR later | Static export has edge cases with navigation/state; test early. No server-side runtime on static hosts. |
| **Vite + React Router** | If you want the simplest SPA deployment, predictable client-side routing, zero SSR surprises | No built-in SSR; you'd add it yourself later if needed. |

**Recommendation:** If the primary goal is a client-side emulator app (not a content/SEO site), **Vite + React Router is simpler and more predictable.** If you want Next's ecosystem and plan to add SSR landing pages for SEO, keep Next — but test navigation and state retention in static-export mode in Phase 0.

### Tech Stack

| Layer | Choice | Why |
|---|---|---|
| Framework | **Vite 6 + React Router 7 + TypeScript** (or Next.js 15 if SSR needed) | Predictable SPA, fast HMR |
| UI | Tailwind CSS 4 + shadcn/ui + Radix | Beautiful, accessible, mobile-first |
| State | Zustand + Zustand middleware (persist) | Simple, performant library management |
| Storage | Dexie.js (IndexedDB) + Origin Private File System (OPFS) | Handles large files safely |
| Emulator runtime | **Nostalgist.js** | Clean API, RetroArch WASM cores, VFS support |
| Fallback emulator | EmulatorJS via isolated `<iframe>` | Only for cores not available in Nostalgist |

### ✦ NEW: Architecture Diagram

```
┌─────────────────────────────────────────────────────┐
│                    Browser Tab                       │
│                                                      │
│  ┌──────────┐  ┌──────────┐  ┌───────────────────┐  │
│  │ React UI │──│ Zustand   │──│ Storage Layer     │  │
│  │ (Router) │  │ (State)   │  │ Dexie + OPFS      │  │
│  └────┬─────┘  └──────────┘  └───────────────────┘  │
│       │                                              │
│  ┌────▼──────────────────────────────────────────┐   │
│  │           Nostalgist.js Wrapper                │   │
│  │  ┌─────────────┐  ┌────────────────────────┐  │   │
│  │  │ Core Loader  │  │ Virtual File System    │  │   │
│  │  │ (same-origin │  │ (ROM/BIOS/Saves)       │  │   │
│  │  │  .wasm/.js)  │  │                        │  │   │
│  │  └─────────────┘  └────────────────────────┘  │   │
│  └───────────────────────────────────────────────┘   │
│                                                      │
│  ┌──────────────┐  ┌──────────────────────────────┐  │
│  │ Service      │  │ Gamepad API / Keyboard /     │  │
│  │ Worker (PWA) │  │ Touch Controls               │  │
│  └──────────────┘  └──────────────────────────────┘  │
└─────────────────────────────────────────────────────┘

    ┌──────────────────────────────────┐
    │  Static Host (Pages / Vercel)    │
    │  /cores/  (same-origin WASM)     │
    │  /assets/ (app shell)            │
    └──────────────────────────────────┘
```

---

## 3) Cross-Origin Isolation & Core Hosting (Critical Path)

### ✦ CORRECTED: The COEP Problem with CDN-Hosted Cores

If you enable these headers (required for `SharedArrayBuffer` / multithreading):

```
Cross-Origin-Opener-Policy: same-origin
Cross-Origin-Embedder-Policy: require-corp
```

…then **every subresource** must be COEP-compatible. If your `.wasm`/`.js` cores are loaded cross-origin from jsDelivr and the CDN response doesn't include `Cross-Origin-Resource-Policy: cross-origin` or proper CORS headers, **the emulator will fail to load**.

### ✦ CORRECTED: Core Hosting Strategy (Same-Origin First)

**Primary:** Host cores under your own domain, version-pinned via path:

```
/cores/fceumm/1.22.0/fceumm_libretro.wasm
/cores/fceumm/1.22.0/fceumm_libretro.js
/cores/duckstation/0.1.7823/duckstation_libretro.wasm
```

**Fallback:** jsDelivr CDN mirror (only used if same-origin fails, and only in non-COEP mode).

### ✦ NEW: Threading Capability — Runtime Switch

Not all environments support cross-origin isolation. Use a **runtime capability check** instead of hard-requiring it:

```typescript
// capability-check.ts
export function getThreadingCapability() {
  const hasSharedArrayBuffer = typeof SharedArrayBuffer !== 'undefined';
  const isCrossOriginIsolated = self.crossOriginIsolated === true;

  return {
    canUseThreads: hasSharedArrayBuffer && isCrossOriginIsolated,
    reason: !hasSharedArrayBuffer
      ? 'SharedArrayBuffer not available'
      : !isCrossOriginIsolated
      ? 'Cross-origin isolation not enabled'
      : 'ready',
  };
}
```

| Mode | Headers | Threading | When |
|---|---|---|---|
| **Standard** (default) | None required | Single-threaded cores | Works everywhere |
| **Performance** | COOP + COEP | Multi-threaded cores | User opts in via Settings; host must support custom headers |

**In Settings → Performance:** Show a "Threading Capability" diagnostic panel that displays current isolation status and explains what the user gains/loses.

---

## 4) Storage & File Handling (the make-or-break part)

### Golden Rule

**Never** upload ROMs/BIOS to your server. Everything stays client-side.

### Hybrid Strategy

| File Type | Format Strategy | Storage Destination | Loading Mechanism |
|---|---|---|---|
| **Cartridge ROMs** | `.zip` or uncompressed | In-memory (or OPFS if "Keep in library" checked) | Full load to RAM |
| **CD Images** | **`.chd` only** (enforced) | OPFS (mandatory due to size) | Streamed via WASM virtual file system |
| **BIOS Files** | Uncompressed | Dexie + OPFS | Loaded to VFS on core boot |
| **Saves/States** | `.srm`, `.state` | Dexie + OPFS | Read/Write on interval + on exit |
| **Metadata** | Custom name, playtime, cover | Dexie | Read on library load |

### ✦ NEW: CHD Enforcement as a Product Feature (Not Just a Warning)

Turn the `.chd` requirement from a technical constraint into a polished UX:

1. **Preflight rejection:** If user drops a `.bin`, `.cue`, `.iso`, or zipped disc image, reject it immediately with a friendly modal (not an error).
2. **"Why CHD?" modal:** Explain that CHD files are smaller, faster to load, and the only format that works reliably in a browser without crashing.
3. **"How to Convert" help page:** Step-by-step guide to using `chdman` (the official tool). Link only to the tool's legitimate source — no links to copyrighted content.
4. **Format badge on system cards:** Each system card in `/systems` shows accepted formats clearly (e.g., "Accepts: .chd only").

### ✦ NEW: Storage Quota Meter

Users will fill their browser storage without realizing it. Add an explicit quota/space meter:

```typescript
// storage-quota.ts
export async function getStorageEstimate() {
  if (navigator.storage && navigator.storage.estimate) {
    const { usage, quota } = await navigator.storage.estimate();
    return {
      usedMB: Math.round((usage ?? 0) / 1024 / 1024),
      totalMB: Math.round((quota ?? 0) / 1024 / 1024),
      percentUsed: Math.round(((usage ?? 0) / (quota ?? 1)) * 100),
    };
  }
  return null;
}
```

Display this in **Settings → Storage** as a progress bar with breakdown: ROMs, saves, BIOS, cache.

### ✦ NEW: Granular Data Clearing

Users panic-delete everything when they just want to free space. Offer:

- **Clear ROM cache** (keeps saves, BIOS, settings)
- **Clear saves only** (with confirmation + export prompt)
- **Clear BIOS files** (will need re-upload)
- **Wipe everything** (nuclear option, double-confirm)

### Export/Import

- Full profile zip (settings + mappings + saves)
- Per-game save zip
- "Library backup" (metadata + save states; ROMs excluded for size)

### ROM Detection Flow

1. Extension match against `coreMap.json`
2. Header magic bytes (NES iNES `$4E $45 $53 $1A`, GBA `$2E $00 $00 $EA`, etc.)
3. Optional MD5 lookup against a small local database for ambiguous files
4. Reject known non-ROM files with helpful message (e.g., "This looks like a save file, not a ROM")

### ZIP Handling Caveat

ZIP support is mandatory for cartridge systems (`jszip` or `zip.js`). However, **strictly reject zipping of CD images** — unzipping 600MB+ directly into browser RAM will crash mobile browsers. The CHD enforcement above handles this naturally.

---

## 5) UX Plan (Polished Flows)

### Pages / Routes

| Route | Purpose |
|---|---|
| `/` | Landing + Library (drag & drop zone, virtualized grid) |
| `/systems` | Browse by tier; shows extensions, BIOS status, controller preview |
| `/game/:id` | Details, play button, save manager, notes |
| `/play` | Fullscreen player (Nostalgist component) |
| `/settings` | Video / Audio / Input / Storage / Performance diagnostics |
| `/help/chd` | "How to convert to CHD" guide |

### Core Flow

```
Upload → auto-detect system → BIOS prompt (if missing)
  → "Launch" → player with overlay quick menu
     (save state, load state, reset, screenshot, shader presets, controller remap)
```

### ✦ NEW: First-Run Experience

1. **Legal disclaimer** (must acknowledge to proceed)
2. **Quick setup wizard:** "Which systems do you want to play?" → shows only relevant BIOS prompts
3. **Demo mode:** Include a single public-domain homebrew ROM (e.g., a well-known NES homebrew) so users can verify the app works before uploading their own files

### ✦ NEW: Offline Indicator & Resilience

Since this is a PWA that works offline:

- Show a subtle connectivity indicator in the status bar
- If user tries to add a new system that needs core download while offline, explain clearly
- All previously loaded cores + ROMs work fully offline

### Mobile / PWA

- Installable PWA (manifest + service worker)
- Touch controls (virtual overlay, configurable per system)
- Landscape lock on mobile during gameplay
- iOS Safari: Show "Tap to start audio" overlay (known AudioContext restriction)

---

## 6) Emulator Feature Plan

### v1 Must-Have

- Nostalgist.js integration with same-origin core loading
- Core auto + manual selection (with pinned stable versions)
- BIOS upload & validation (exact filename + optional size/hash check)
- SRAM + save-state persistence to Dexie/OPFS
- Gamepad API + keyboard + on-screen touch controls
- Fullscreen + pointer lock
- Auto-save on tab blur / visibility change (critical for mobile)

### v1.1 Should-Have

- Save states UI (thumbnails + timestamps)
- Per-game control remapping
- Shader presets (CRT, scanlines, sharp bilinear)
- Screenshot gallery
- Fast-forward toggle

### Nice-to-Have (v2)

- RetroAchievements integration (via their public API, user provides token)
- Cloud sync (user-provided WebDAV or S3 endpoint)
- Netplay (very advanced — WebRTC-based)
- Box art from public cover databases

---

## 7) Performance & Compatibility Plan

### Device Tiers

| Environment | Doable Systems | Experimental Systems |
|---|---|---|
| Desktop Chrome/Edge | Buttery 60fps | Playable on mid+ hardware |
| Desktop Firefox | Excellent | Good (slightly behind Chrome WASM perf) |
| Desktop Safari | Good (test AudioContext) | Variable |
| iOS Safari | Good (< 700MB memory!) | Limited — warn user |
| Android Chrome | Excellent | Playable on flagship devices |

### Quality Gates (Before Each Release)

- **Test matrix:** Chrome, Firefox, Safari (desktop + mobile) × (Doable tier sample + Experimental tier sample)
- **60 fps target** on Doable systems on a 2023 MacBook Air / mid-range Windows laptop
- **Memory budget:** < 700 MB peak on mobile (iOS Safari crash threshold), < 1.5 GB peak on desktop
- **Core load time:** < 3s on broadband, < 8s on slow 3G (for same-origin hosted cores)

### Performance Tactics

- Prefer lighter cores when multiple exist (e.g., `fceumm` over `mesen` for NES)
- Run-ahead + threaded video where supported (Performance mode only)
- Lazy-load cores only when launching a game
- Warn + offer "Performance mode" toggle on Experimental systems
- Dispose core + free WASM memory when returning to library

### ✦ NEW: Memory Pressure Handling

```typescript
// memory-monitor.ts
if ('memory' in performance) {
  const mem = (performance as any).memory;
  const usedMB = mem.usedJSHeapSize / 1024 / 1024;
  if (usedMB > 600) {
    // Show warning: "Memory usage is high. Consider closing other tabs."
  }
}

// Also listen for the (non-standard but useful) memory pressure events
if ('onmemorypressure' in window) {
  window.addEventListener('memorypressure', () => {
    // Trigger auto-save, then warn user
  });
}
```

---

## 8) Service Worker Strategy

### ✦ CORRECTED: What to Cache vs. Pass Through

The service worker must **not** accidentally break large streaming fetches or interfere with COEP. Refined rules:

| Resource | SW Behavior | Why |
|---|---|---|
| App shell (HTML, CSS, JS bundles) | **Cache (stale-while-revalidate)** | Fast offline loads |
| UI assets (icons, fonts, images) | **Cache (cache-first)** | Offline PWA support |
| Core `.wasm` / `.js` files (same-origin) | **Cache (cache-first, versioned key)** | Avoid re-downloading 5MB+ cores; version key ensures updates |
| Core `.wasm` / `.js` files (cross-origin CDN) | **Network-only (pass-through)** | Avoid COEP header issues |
| ROM / CHD reads from OPFS | **Skip entirely** | These are local filesystem ops, SW shouldn't intercept |
| API calls (if any future v2) | **Network-first** | Freshness matters |

### Key Implementation Detail

```typescript
// sw.ts — fetch handler
self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);

  // Never intercept opfs:// or blob: URLs
  if (url.protocol !== 'https:' && url.protocol !== 'http:') return;

  // Pass through cross-origin core fetches
  if (!url.origin === self.location.origin) return;

  // Cache same-origin cores by version path
  if (url.pathname.startsWith('/cores/')) {
    event.respondWith(cacheFirst(event.request));
    return;
  }

  // App shell: stale-while-revalidate
  event.respondWith(staleWhileRevalidate(event.request));
});
```

---

## 9) Security, Legal & Safety UX

### Legal Screen (First Launch + Persistent Footer)

> "RetroWeb does not provide games or BIOS files. You must own the original hardware and software. By using this app, you confirm that you have the legal right to use any files you upload."

- Shown as a blocking modal on first launch (must acknowledge)
- Persistent small footer link on every page
- No weasel words — clear and direct

### Security

- Strict Content Security Policy (CSP)
- COOP/COEP headers when Performance mode is enabled (see Section 3)
- All code runs in browser sandbox
- Filename sanitization (strip path traversal, null bytes, special chars)
- No `eval()`, no remote script execution from ROM data
- Subresource Integrity (SRI) hashes on all third-party scripts

### Privacy-First

- **Zero analytics by default** (optional Plausible self-hosted, clearly disclosed)
- Clear "Delete all my data" button in Settings
- No telemetry, no tracking pixels, no third-party cookies
- ROM file contents never leave the browser

---

## 10) Error Handling & Resilience

### ✦ NEW: Graceful Degradation Strategy

| Failure | User Sees | Recovery |
|---|---|---|
| Core fails to load | "This system's emulator couldn't load. Try refreshing, or switch to a fallback core." + core picker | Auto-retry once, then offer manual core selection |
| ROM file corrupt | "This file doesn't appear to be a valid [system] ROM. Check the file and try again." | Clear error, no crash |
| BIOS wrong hash | "This BIOS file doesn't match what [system] expects. Expected: scph5501.bin (hash: abc123...)" | Show expected filename + hash |
| OPFS quota exceeded | "Storage is full. Free up space in Settings → Storage." | Link directly to storage manager |
| WASM OOM | "The emulator ran out of memory. Close other tabs and try again." | Auto-save attempted before crash |
| Core crash mid-game | "The emulator encountered an error. Your last auto-save is safe." | Offer reload with last auto-save |
| Safari AudioContext blocked | Large "Tap to Start Audio" overlay | Single tap resumes |

### ✦ NEW: Crash Recovery

- **Auto-save every 60 seconds** during gameplay (configurable)
- **Auto-save on `visibilitychange`** (tab switch, app minimize)
- On next launch after crash, detect orphaned state and offer "Resume where you left off?"

---

## 11) Accessibility

### ✦ NEW: Accessibility Plan

- Full keyboard navigation throughout the UI (not just during gameplay)
- ARIA labels on all interactive elements
- Reduced-motion mode (disables UI animations, shader transitions)
- High-contrast mode for the app UI (not the emulated game)
- Screen reader announcements for state changes ("Game loaded", "Save complete", "Error: BIOS missing")
- Focus management: return focus to correct element after modals close
- Touch target minimum: 44×44px on mobile

---

## 12) Testing Strategy

### ✦ NEW: Comprehensive Testing Plan

| Layer | Tool | What |
|---|---|---|
| Unit tests | Vitest | Storage layer, ROM detection, BIOS validation, core mapping logic |
| Component tests | Testing Library | UI components, modals, drag-drop zone |
| Integration tests | Playwright | Full upload → detect → launch → save → export flow |
| Visual regression | Playwright screenshots | Key pages across viewports |
| Performance tests | Lighthouse CI + custom | Memory budget, core load time, FPS (via `requestAnimationFrame` timing) |
| Cross-browser | BrowserStack / Playwright | Chrome, Firefox, Safari × desktop, mobile |
| Manual QA | Test matrix spreadsheet | Each Doable system plays for 5 min with save/load cycle |

### ✦ NEW: CI Pipeline

```
PR opened → lint + type check → unit tests → build → deploy preview
  → Playwright E2E (Chrome) → Lighthouse CI → merge
Release → full cross-browser matrix → deploy to staging → manual QA → production
```

---

## 13) Implementation Phases (with Success Criteria)

### Phase 0 — Setup, Security & Validation (1 week)

**Tasks:**
- Scaffold Vite + React Router + TS + Tailwind + shadcn + Zustand + Dexie
- Configure COOP/COEP headers (as optional middleware / hosting config)
- Host first core same-origin, version-pinned
- Nostalgist.js proof-of-concept with NES (fceumm)
- **Core availability audit** for all planned Doable systems
- Threading capability check utility

**Success criteria:** NES ROM boots and renders frames in Chrome, Firefox, and Safari. Core loads from same-origin. Audit spreadsheet complete for 12 Doable systems.

### Phase 1 — Core Loop (2–3 weeks)

**Tasks:**
- Library page with drag & drop + auto-detect
- Nostalgist player route
- BIOS prompt & validation (filename + optional hash check)
- Save persistence (SRAM + save states to Dexie/OPFS)
- Basic error handling for all failure modes
- Auto-save on visibility change

**Success criteria:** Play NES ROM end-to-end with save persistence. Upload BIOS for PS1, launch PS1 game. Saves survive browser restart.

### Phase 2 — System Catalog & Tiers (3 weeks)

**Tasks:**
- Full `systems.json` + `coreMap.json` + `biosRules.json`
- Doable tier live (12 systems)
- System browser page with tier labels, format badges, BIOS status
- CHD enforcement flow (rejection + "Why CHD?" modal + conversion guide)
- Storage quota meter

**Success criteria:** All 12 Doable systems playable. CHD-only enforcement working for disc systems. User can see storage usage.

### Phase 3 — Polish & Storage (2–3 weeks)

**Tasks:**
- OPFS + Dexie full integration with granular clearing
- Save manager (list, export, import, delete per-game)
- Export/import full profile
- PWA manifest + service worker (with correct caching strategy)
- Mobile touch controls
- First-run wizard + legal disclaimer

**Success criteria:** PWA installs on Android + iOS. Touch controls work for NES/SNES/GBA. Full save export/import cycle works.

### Phase 4 — Experimental Systems + UX Polish (ongoing)

**Tasks:**
- Add N64/PSP/Dreamcast as Experimental tier (with CHD enforcement for disc systems)
- Shader UI (CRT, scanlines, sharp bilinear)
- Per-game control remapping
- Screenshot gallery
- Performance mode toggle (threading)
- Threading capability diagnostic panel

**Success criteria:** N64 game runs at >30fps on a 2023 MacBook Air. Shader toggle works without performance regression on Doable systems.

### Phase 5 — Launch Readiness

**Tasks:**
- Full cross-browser test matrix pass
- Accessibility audit (keyboard nav, screen reader, focus management)
- Legal copy review
- Performance budget verification
- `docs/compatibility.md` with real results
- Lighthouse score > 90 on all categories
- Soft launch with beta testers

**Success criteria:** All quality gates pass. No P0 bugs. Compatibility doc published.

---

## 14) Deliverables Checklist

### Product

- [ ] RetroPie-inspired catalog with honest tier labels
- [ ] Drag & drop ROM + BIOS upload with validation
- [ ] Seamless player with RetroArch-quality experience
- [ ] Full local save persistence + export/import
- [ ] CHD enforcement with conversion guide
- [ ] PWA installable (Android + iOS)
- [ ] Storage quota meter + granular clearing
- [ ] First-run wizard with legal disclaimer
- [ ] Offline gameplay support
- [ ] Clear legal & privacy messaging

### Engineering

- [ ] `systems.json` + `coreMap.json` + `biosRules.json`
- [ ] Same-origin core hosting with version pinning
- [ ] COOP/COEP middleware (optional performance mode)
- [ ] `storage/` layer (Dexie + OPFS wrapper + quota monitoring)
- [ ] `player/` Nostalgist wrapper component
- [ ] Service worker with correct caching strategy
- [ ] Threading capability check + runtime switch
- [ ] Error boundary + crash recovery system
- [ ] Comprehensive test suite (unit + integration + E2E)
- [ ] CI pipeline (lint → test → build → deploy)
- [ ] `docs/compatibility.md` with real test results
- [ ] Core availability audit spreadsheet (maintained)

---

## 15) Risk Register

### ✦ NEW: Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Browser storage quota hit on mobile | High | Medium | Quota meter + granular clearing + clear warnings before space runs out |
| iOS Safari audio context blocked | Certain | Low | "Tap to Start" overlay; well-known pattern |
| iOS Safari 700MB memory limit | High | High | Memory monitoring; warn before launching Experimental games on iOS; prefer light cores |
| Core not available as web build for a listed system | Medium | High | Core audit in Phase 0; don't list systems without verified cores |
| COEP breaks cross-origin resources | Medium | High | Same-origin core hosting; threading as opt-in |
| jsDelivr CDN goes down | Low | Medium | Same-origin primary + CDN fallback (not the reverse) |
| Save state format changes between core versions | Medium | High | Pin core versions; version saves; warn before core upgrade |
| User uploads massive uncompressed ISO (4GB+) | Medium | Medium | CHD enforcement; file size pre-check; reject with helpful message |
| Legal takedown / misunderstanding | Low | High | No ROMs/BIOS hosted; clear legal messaging; no scraping; open-source |
| Nostalgist.js abandoned | Low | Medium | It wraps standard RetroArch WASM; we can fork or replace the thin wrapper |

---

## 16) Future Roadmap (v2+)

- **RetroAchievements** integration (user provides API token)
- **Cloud sync** (user-provided WebDAV, S3, or Google Drive endpoint)
- **Community core map PRs** (open-source `coreMap.json` for contributions)
- **Box art** from public cover databases (optional, user-initiated)
- **Netplay** via WebRTC (very ambitious)
- **Optional analytics** (Plausible self-hosted, user opt-in)
- **Theme system** (dark/light/retro CRT theme for the app UI itself)

---

## Appendix A: Key Technical Decisions Log

| Decision | Chosen | Rejected | Rationale |
|---|---|---|---|
| Framework | Vite + React Router | Next.js static export | Simpler SPA, no SSR edge cases, predictable routing |
| Core hosting | Same-origin, version-pinned paths | jsDelivr CDN primary | COEP compatibility, reliability, cache control |
| Threading | Opt-in "Performance mode" | Always-on COEP | Broader compatibility by default; power users opt in |
| CD format | CHD only (enforced) | bin/cue/iso accepted | Browser memory safety; better compression; single-file |
| Storage | Dexie + OPFS hybrid | IndexedDB only | OPFS handles large files better; Dexie for metadata |
| Emulator wrapper | Nostalgist.js | EmulatorJS | Cleaner API, no iframe required; EmulatorJS as fallback only |

---

## Appendix B: Recommended File Structure

```
retro-web/
├── public/
│   ├── cores/                  # Same-origin WASM cores (version-pinned)
│   │   ├── fceumm/1.22.0/
│   │   ├── snes9x/1.62.3/
│   │   └── ...
│   ├── manifest.json
│   └── sw.js
├── src/
│   ├── components/
│   │   ├── ui/                 # shadcn/ui components
│   │   ├── Library/
│   │   ├── Player/             # Nostalgist wrapper
│   │   ├── SystemBrowser/
│   │   ├── SaveManager/
│   │   ├── Controls/           # Touch overlay, gamepad, keyboard
│   │   └── Diagnostics/        # Threading check, storage meter
│   ├── data/
│   │   ├── systems.json
│   │   ├── coreMap.json
│   │   └── biosRules.json
│   ├── hooks/
│   │   ├── useEmulator.ts
│   │   ├── useStorage.ts
│   │   ├── useGamepad.ts
│   │   └── useMemoryMonitor.ts
│   ├── lib/
│   │   ├── storage/            # Dexie + OPFS wrapper
│   │   ├── detection/          # ROM detection, magic bytes
│   │   ├── capability/         # Threading check, quota
│   │   └── chd/                # CHD validation
│   ├── routes/
│   │   ├── index.tsx           # / — Library
│   │   ├── systems.tsx         # /systems
│   │   ├── game.$id.tsx        # /game/:id
│   │   ├── play.tsx            # /play
│   │   ├── settings.tsx        # /settings
│   │   └── help.chd.tsx        # /help/chd
│   ├── store/                  # Zustand stores
│   └── App.tsx
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
├── docs/
│   ├── compatibility.md
│   ├── core-audit.md
│   └── architecture.md
└── scripts/
    └── audit-cores.ts          # Automated core availability checker
```
