# Development log

Month-by-month record of what was built, what was learned, and what was
deferred. The project ran from October 2025 through April 2026 as a
BSc final-year artefact at the University of Roehampton.

This is a development *log*, not a project plan. Decisions captured
here are the ones that were actually made, not the ones initially
proposed. Where reality diverged from the plan in the report, this
log carries the authoritative version.

---

## October 2025 — Pi side, first principles

**Goal.** Get RetroPie running on a Raspberry Pi 3, paired with a
controller, capable of launching at least one emulator from
EmulationStation. Establish the Pi's role in the architecture.

**What was done.**

- Flashed RetroPie 4.8 onto a 32 GB microSD; first boot, controller
  config wizard completed with an 8BitDo SN30 Pro (USB).
- Verified EmulationStation appears on TV via HDMI and that the
  carousel rendering is smooth on the Pi 3 GPU.
- Installed `lr-mgba`, `lr-snes9x`, `lr-fceumm`, `lr-genesis-plus-gx`
  cores via the RetroPie setup script.
- Confirmed local-storage gameplay: dropped a public-domain test ROM
  on the SD card, launched it from EmulationStation, validated input
  latency was acceptable.

**Learned.**

- The Pi 3 is fine for emulation up to PSX-class systems. Anything
  more demanding (N64, Dreamcast) is beyond its envelope without
  significant tuning, which informed the decision to focus the
  artefact's emulation surface on retro-handheld and 8/16-bit consoles.
- `runcommand` is the right integration point. Its onstart/onend
  hooks are well-documented, fire reliably, and have access to the
  ROM path, system, and core via positional arguments.

**Deferred.** Network integration; that came in January once the
laptop side was capable of hosting a Samba share.

---

## November 2025 — End-to-end Pi pipeline validation

**Goal.** Validate that the full Pi-side launch pipeline works
end-to-end with a non-trivial GBA title, before committing time to
custom homebrew that might mask integration bugs.

**What was done.**

- Pulled an open-source GBA homebrew title (a community-released test
  ROM, distributed under a permissive licence). Loaded it through
  EmulationStation, confirmed `lr-mgba` plays it cleanly.
- Wrote a stub `runcommand-onstart.sh` that simply logged ROM path
  and timestamp to `/tmp/test.log` — confirmed RetroPie fires the
  hook with the expected arguments.
- Wrote a matching `runcommand-onend.sh` stub that logged the exit.

**Learned.**

- The hook contract is `runcommand-onstart.sh <system> <emulator>
  <rompath> <commandline>`. That's enough metadata to identify a
  session uniquely on the laptop side without needing a separate
  per-game registration step.
- Hook output is captured by RetroPie's own log; nothing is silently
  swallowed. Good for debugging from the Pi shell.

**Deferred.** Actual session POST to the laptop — there was no
laptop-side endpoint to POST to yet.

---

## December 2025 — Mid-point report; documentation & literature

**Goal.** Submit the mid-point report for the FYP module on time.
Limited new code.

**What was done.**

- Wrote literature review: prior Pi-as-arcade work (Rzepka, Gamess),
  thin-client architectures for Pi-class hardware (Suder), retro
  emulator design.
- Refined the architecture diagram to reflect the now-locked decision
  to split work across two hosts, with Sunshine + Moonlight as the
  bridge.
- Drafted the database schema (sessions, games, devices,
  daily_game_stats, daily_system_stats, achievements,
  user_achievements, controller_profiles, ai_conversations,
  ai_messages).
- Risk register and timeline.

**Learned.**

- The literature is unambiguous that running modern web frontends on
  Pi-class hardware is a workload mismatch. This validated the
  Sunshine + Moonlight choice over a "render the dashboard on the Pi
  in a browser" alternative that had been considered.

**Deferred.** All implementation.

---

## January 2026 — The turning point: Samba + CIFS

**Goal.** Get the laptop and the Pi to share a filesystem, so ROMs
and media live in one place but are accessible from both hosts.
Without this, the project is a single-host emulator, not a
network-aware system.

**What was done.**

- Configured Samba on the laptop to share `/path/to/games` and
  `/path/to/media` over the LAN with credentialled access.
- On the Pi, installed `cifs-utils` and added an `/etc/fstab` entry
  mounting the laptop's share at `/mnt/laptop`. Confirmed the mount
  survives reboots.
- Pointed EmulationStation's GBA system path at `/mnt/laptop/games`
  so ROMs added on the laptop appear in the Pi's carousel
  automatically.
- Validated transfer speeds at ~10 MB/s sustained over wired
  Ethernet, fine for ROM seeking and Kodi media playback.

**Learned.**

- This is the change that turned the project from a hobby emulator
  setup into the artefact described in the report. Once the two hosts
  share a filesystem, everything else (session POSTs, dashboard
  analytics, media library) follows naturally.
- CIFS protocol version matters on older Pi kernels (`vers=2.0`
  needed in some cases instead of `3.0`).
- mDNS / `avahi-daemon` is worth installing on both ends so the
  hostname `laptop.local` resolves without DNS configuration.

---

## February 2026 — Media loop (Kodi + Jellyfin)

**Goal.** Add Loop 2 — media playback — so the artefact is more than
"a Pi that plays games against the laptop's filesystem".

**What was done.**

- Installed Jellyfin server on the laptop (separate process, not part
  of `start.mjs`); pointed it at the media share.
- Installed Kodi on the Pi (`apt install kodi`).
- Registered **Jellyfin** as an EmulationStation system entry so it
  appears in the carousel alongside GBA, SNES, etc., consistent with
  the one-place-to-launch-everything UX goal. The launcher script
  (`Jellyfin.sh` under `~/RetroPie/roms/jellyfin/`) opens an X session
  on a separate VT and runs Kodi-standalone (with the Jellyfin-for-Kodi
  add-on configured) — or, if Kodi isn't available, falls back to a
  Chromium kiosk pointing at Jellyfin's web UI. The launcher's
  exit-handling was fragile in this iteration and was reworked in
  April; see that entry.
- Inside Kodi, installed the **Jellyfin for Kodi** add-on and signed
  in to the laptop's Jellyfin instance. Confirmed library sync,
  thumbnails, and 1080p HEVC playback.

**Learned.**

- The right interaction philosophy beats the right protocol. Kodi as
  a Jellyfin client felt better than running a browser-based Jellyfin
  client on the Pi: Kodi was designed for TV + controller, browsers
  weren't. This same principle would later drive the Sunshine /
  Moonlight choice over rendering the dashboard in a Pi browser.
- The Jellyfin-for-Kodi add-on writes Kodi-native metadata, so the
  Pi's library browser is fast even though the actual files live on
  the laptop.

---

## March 2026 — The big month: dashboard, voice, Red Racer

**Goal.** Build Loop 3 (the dashboard, the AI assistant, the
streamed delivery to the Pi) and the first original homebrew title
to populate it with real session data.

**What was done.**

### Laptop component

- React 19 + Vite 7 + Tailwind v4 PWA scaffolded in `src/`.
- FastAPI backend in `backend/` with 12 route modules covering
  sessions, games, devices, achievements, AI chat, voice, web
  grounding, image generation.
- MySQL schema implemented from the December design; XAMPP for local
  hosting, phpMyAdmin for inspection.
- Voice cascade: **Parakeet TDT 1.1B** (NeMo, fp16 on CUDA, exposed
  on `:8786`) for STT, **Kokoro ONNX** (`:8787`) for TTS, NVIDIA's
  `integrate.api.nvidia.com` for LLM completions. WebSocket gateway
  in `backend/app/services/voice_gateway.py` orchestrates the
  Mic → STT → LLM → TTS → Speaker chain with VAD, three activation
  modes, graceful provider fallback, and turn cancellation.
- Session ingest API (`backend/app/routes/session_routes.py`): two
  endpoints, `POST /session/start` and `POST /session/end`. The Pi-side
  `session_logger.py` POSTs to these via the laptop's hostname.
- Multi-model picker (DeepSeek V4 Pro, Kimi K2 Thinking, Step 3.5
  Flash, Mistral Large 3, Gemma 3 27B, GLM 4.7, MiniMax M2.7).
- Web grounding via Tavily / SearXNG.
- Sunshine NVENC configured to capture the laptop's display and
  stream to the Pi's Moonlight client. End-to-end Pi-perceived
  latency below one frame at 60 Hz on wired Ethernet.

### Pi component

- Wired the runcommand hooks against the now-live FastAPI session
  endpoints. The hooks shell out to `~/pistation/session_logger.py`,
  which POSTs to `/session/start` (records `pi_hostname`, `rom_path`,
  `system_name`, `emulator`, `core`, `started_at`) and on game exit
  POSTs to `/session/end` (records `ended_at`, `duration_seconds`),
  with state persisted between hooks in `/tmp/pistation_session.json`.
  Verified end-to-end that a game launched on the Pi appears as a row
  in the laptop's MySQL `sessions` table and as a tile on the dashboard.
- Paired `moonlight-qt` against the laptop's Sunshine; created a
  `RetroWeb.sh` launcher in `~/RetroPie/retropiemenu/` that opens
  `xinit` + `matchbox-window-manager` + `moonlight-qt` at 720p30 /
  8 Mbps / H.264 / software-decoded. Reachable from the RetroPie
  system menu inside ES.

### Games

- Built **Red Racer** (the first original homebrew title): Python
  prototype on the laptop iterating gameplay (lane logic, fuel /
  nitro / repair pickups, AI traffic, missions, achievements), then
  ported to GBA-native C with fixed-point math, 240×160 framebuffer,
  no dynamic allocation in hot paths. Shipped `RedRacer_Phys.gba`,
  loaded by EmulationStation through `/mnt/laptop/games/Red Racer/...`.

**Learned.**

- The voice cascade's hardest invariant is **VAD suppression while
  TTS is playing**. Without it, the assistant transcribes its own
  voice and gets stuck in a feedback loop. The fix is surface-area:
  the frontend's mic capture path explicitly gates on the TTS
  playback state.
- Sunshine + Moonlight just works on a wired LAN — the latency is
  invisible in normal use. On Wi-Fi, NVENC bitrate has to be tuned
  down or stutter creeps in.
- Red Racer's Python-prototype-first approach saved significant time:
  the entire gameplay design was settled before a single line of GBA
  C was written, so the GBA port's debugging budget was spent on
  hardware constraints rather than design questions.

**Deferred.**

- "Library" page (browse-by-cover view of all games on the Samba
  share) — route exists in `src/routes/`, content is "coming soon".
  Out of scope for the artefact submission; the dashboard's analytics
  view is the primary surface.

---

## April 2026 — Final-month polish; Mythical and Bastion

**Goal.** Round out the original homebrew corpus to three titles,
write the final report, and prepare the artefact for submission.

**What was done.**

### Games

- Built **Mythical** (top-down adventure / exploration). Same pipeline
  as Red Racer plus a C++ desktop-simulator intermediate stage:
  `cpp_core/` (engine-agnostic simulation), `cpp_port/` (desktop
  renderer), `gba_project/` (GBA target with C entry point and a
  Python asset-baking step). Shipped `Mythical_GBA.gba`. All assets
  project-author original.
- Built **Bastion Tower Defence** on Butano (C++23 GBA engine).
  Initial Python+SDL2 prototype rewritten as C++ with SDL2 for the
  desktop simulator, then ported to Butano for the GBA target via a
  hardware-abstraction layer in `src_cpp/hal/`. Shipped
  `BastionTD.gba` and `BastionTD_fixed.gba`.

### Documentation

- Rewrote the top-level README from a dashboard-only narrative to a
  full system-overview README that gives equal weight to the Pi side,
  the laptop side, and the games corpus. Relocated the existing
  dashboard README under `laptop/README.md`.
- Wrote `pi/README.md` covering the Pi-side architecture, services,
  runcommand hook contract, and setup.
- Wrote per-game READMEs with explicit asset attribution sections.
  Withdrew the IP-tainted Python-prototype reference assets for Red
  Racer (branded car PNGs, ripped soundtrack audio) and replaced
  them with a placeholder README explaining the situation.

### Repository hygiene

- Cleaned 1.5 GB of Bastion build-cache content (Windows MinGW
  toolchain, Butano clone with embedded `.git`, SDL2 binaries,
  installer caches, build artefacts) out of the games tree into a
  local build cache outside the repository, replacing it with a
  setup.md describing how to reconstitute the build environment.
- Tightened `.gitignore` to cover build outputs (`*.elf`, `*.o`,
  `*.a`, `*.d`, `*.sav`, `*.map`, `*.exe`, `*.dll`), editor/workflow
  scratch directories (`.bmad-*`), and nested `.vscode/`.
- Removed the Windows installer (`devkitProUpdater-3.0.3.exe`) and
  a `.vscode/settings.json` that had a permissive AI-tooling
  flag enabled — not appropriate for a public submission.

### Pi-side reconciliation pass

A pre-submission audit revealed multiple drift between the documented
architecture and the deployed Pi state. The reconciliation:

- **Loop 2 launcher.** The `Jellyfin.sh` cleanup logic was unreliable
  (Kodi exit occasionally left the Pi stuck and required a power
  cycle). Rewrote with a comprehensive `cleanup` trap on
  `EXIT/INT/TERM/HUP` that kills X / openbox / Kodi, deallocates the
  Kodi VT, switches back to ES on TTY1, and sends `SIGCONT` to ES in
  case it was paused. Old version backed up.
- **Game corpus deployment.** Mythical and Bastion's `.gba` ROMs were
  built but had not been copied to the Pi. All four (Red Racer,
  Mythical, BastionTD, BastionTD-fixed) are now in
  `/home/pi/RetroPie/roms/gba/` on the Pi.
- **CIFS mount.** Documented the setup as a pair of idempotent scripts
  ([`pi/scripts/setup-samba-laptop.sh`](pi/scripts/setup-samba-laptop.sh)
  and [`pi/scripts/setup-cifs-mount-pi.sh`](pi/scripts/setup-cifs-mount-pi.sh))
  rather than scattered prose. Once the laptop side is run, the Pi
  side mounts `/mnt/laptop` and updates the GBA `<path>` in the ES
  overlay.
- **Captured Pi-side scripts into the repo.** Deployed scripts
  (`runcommand-onstart.sh`, `runcommand-onend.sh`, `session_logger.py`,
  `Jellyfin.sh`, `RetroWeb.sh`) are now under `pi/scripts/` so the
  marker can read them alongside the rest of the artefact.

### Evaluation

- Final report writing — methodology, evaluation, reflection.
- Screenshots and a recorded demo for the report appendix.

**Learned.**

- Bastion was the most expensive of the three games to maintain in
  the build cache because of the toolchain footprint (1.4 GB of
  MinGW + Butano clone). Worth it for what Butano gives — modern
  C++23 ergonomics on a 32-bit ARM target — but the build setup
  warrants its own document, hence `BastionTD/setup.md`.
- The Python-prototype-first pipeline scaled across all three games
  without modification. That's the strongest evidence that the
  pipeline itself is the methodological contribution, not the games.

---

## What didn't ship

Every project has these. Captured here so the marker doesn't have to
infer:

- **Library page** (ROM browser with filters). Route exists, marked
  "coming soon" in the dashboard. Cut from scope to keep voice and
  analytics polish in.
- **Cloud save sync**. Save files stay in the SRAM of each `.gba`
  ROM and on the Pi's SD card. Not a deal-breaker for the single-Pi
  test setup.
- **Per-user profiles**. The dashboard has a single user. Multi-user
  was scoped out at the December mid-point.
- **Netplay matchmaking**. Listed as a long-term roadmap item; not
  attempted in this academic year.
- **Mobile controller companion app**. Long-term roadmap; not
  attempted.

These are explicit deferrals, not unfinished features. Each is
documented in the report's evaluation section with the reason it was
cut.
