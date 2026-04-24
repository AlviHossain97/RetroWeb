<div align="center">

# PiStation · RetroWeb

**A self-hosted retro gaming dashboard with browser-based emulation, live stats, and a local voice assistant.**

[![React 19](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=white)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-strict-3178C6?logo=typescript&logoColor=white)](https://www.typescriptlang.org)
[![Vite 7](https://img.shields.io/badge/Vite-7-646CFF?logo=vite&logoColor=white)](https://vitejs.dev)
[![Tailwind v4](https://img.shields.io/badge/Tailwind-v4-06B6D4?logo=tailwindcss&logoColor=white)](https://tailwindcss.com)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Parakeet TDT 1.1B](https://img.shields.io/badge/STT-Parakeet%20TDT%201.1B-76B900?logo=nvidia&logoColor=white)](https://huggingface.co/nvidia/parakeet-tdt-1.1b)
[![Kokoro TTS](https://img.shields.io/badge/TTS-Kokoro%20ONNX-FF6F00)](https://github.com/thewh1teagle/kokoro-onnx)
[![PWA](https://img.shields.io/badge/PWA-installable-5A0FC8?logo=pwa&logoColor=white)]()
[![License](https://img.shields.io/badge/license-private-lightgrey)]()

</div>

---

## Table of Contents

- [What is PiStation?](#what-is-pistation)
- [Feature Matrix](#feature-matrix)
- [Architecture](#architecture)
- [Voice Pipeline](#voice-pipeline)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Service Map](#service-map)
- [Project Layout](#project-layout)
- [Scripts Reference](#scripts-reference)
- [Voice Activation Modes](#voice-activation-modes)
- [Model Picker](#model-picker)
- [Troubleshooting](#troubleshooting)
- [Hardware Requirements](#hardware-requirements)
- [Roadmap](#roadmap)
- [Tech Stack](#tech-stack)

---

## What is PiStation?

PiStation is a **browser-first retro gaming platform** that runs entirely in the user's browser via WebAssembly, backed by a FastAPI service for analytics and a local AI voice assistant. The stack was designed to run on a laptop/desktop GPU and stream to a Raspberry Pi client via Sunshine + Moonlight.

**Key properties:**

- Emulation runs in the browser (no server-side game state).
- Voice, LLM, and TTS are **self-hosted by default** — the assistant works without sending audio to third-party services.
- Gaming stats (sessions, playtime, achievements) persist in MySQL via the FastAPI backend.
- PWA-installable, controller-first UI.

---

## Feature Matrix

| Area | Status | Notes |
|---|---|---|
| Dashboard analytics | ✅ | Total playtime, top games, system share, recent sessions |
| Sessions tracking | ✅ | Live "now playing" + historical search/filter |
| Achievements | ✅ | Unlock progress + category grouping |
| Controller diagnostics | ✅ | Live gamepad visualization + keyboard rebinding |
| AI chat (text) | ✅ | Multi-model via NVIDIA integrate API |
| AI chat (voice) | ✅ | Parakeet STT → NVIDIA LLM → Kokoro TTS |
| Voice activation modes | ✅ | Auto near-field · Headset · Push-to-talk (`T` key) |
| Web-grounded answers | ✅ | Optional Tavily / SearXNG backend |
| Kiosk mode | ✅ | TV/cabinet-ready fullscreen, `?lite=1` minimal variant |
| Sunshine game streaming | ✅ | NVENC → Moonlight client on Pi |
| Pi dashboard streaming | ⚙️ Opt-in | Set `PI_IP=x.x.x.x` to enable Xvfb+FFmpeg UDP stream |
| Library page | 🚧 | Route exists, "coming soon" |
| Image generation | ✅ | ImageRouter API (optional) |

---

## Architecture

```mermaid
flowchart LR
    subgraph Browser["🌐 Browser (React 19 PWA)"]
        UI[Dashboard UI]
        VC[Voice Capture<br/>AudioWorklet]
        EM[Nostalgist + WASM<br/>RetroArch cores]
    end

    subgraph Backend["⚙️ FastAPI :8000"]
        VGW[Voice Gateway<br/>WebSocket]
        AIC[AI Context Service<br/>+ grounding]
        DB[(MySQL<br/>stats/sessions)]
    end

    subgraph LocalAI["🧠 Local AI services"]
        PAR[Parakeet STT<br/>:8786 · GPU fp16]
        KOK[Kokoro TTS<br/>:8787 · ONNX]
    end

    subgraph Cloud["☁️ External APIs"]
        NV[NVIDIA integrate<br/>/chat/completions]
        IR[ImageRouter<br/>optional]
        TV[Tavily / SearXNG<br/>optional]
    end

    UI -->|HTTPS| Backend
    VC -.PCM16 WS.-> VGW
    VGW -->|POST /v1/audio/transcriptions| PAR
    VGW -->|POST /v1/chat/completions| NV
    VGW -->|POST /v1/audio/speech| KOK
    AIC --> NV
    AIC -.grounding.-> TV
    Backend --> DB
    EM -.streams fb.-> Sunshine[Sunshine NVENC :47990]
```

---

## Voice Pipeline

End-to-end flow for a single spoken turn:

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant Mic as Browser Mic<br/>(AudioWorklet)
    participant WS as Voice Gateway<br/>(FastAPI WS)
    participant Parakeet as Parakeet STT<br/>(:8786 GPU)
    participant LLM as NVIDIA LLM<br/>(integrate API)
    participant Kokoro as Kokoro TTS<br/>(:8787 GPU)
    participant Speaker as Browser Playback<br/>(AudioContext)

    User->>Mic: speaks
    Mic->>WS: input_audio.chunk<br/>(PCM16 @ 16kHz, base64, 80ms frames)
    Mic->>WS: input_audio.stop (silence cutoff)
    WS->>Parakeet: POST audio.wav (16kHz mono)
    Parakeet-->>WS: { text: "..." }
    WS-->>User: user.transcript.final
    WS->>LLM: chat/completions (stream)
    LLM-->>WS: delta tokens
    WS-->>User: assistant.text.delta (streamed)
    WS->>Kokoro: POST speech text
    Kokoro-->>WS: WAV @ 22.05kHz
    WS-->>Speaker: assistant.audio.chunk<br/>(PCM16 chunks, base64)
    Speaker->>User: plays voice reply
```

**Key invariants:**

- Audio leaving the browser is always **PCM16 @ 16 kHz mono** (downsampled client-side in `voice-capture-processor.js`).
- Audio returning to the browser is always **PCM16 @ 22.05 kHz mono**, rechunked at 80 ms boundaries for smooth playback.
- VAD auto-suppresses while TTS is playing, so the assistant can't transcribe its own voice in `auto_near_field` mode.

<details>
<summary><b>Click for deeper voice internals</b></summary>

- **Providers:** `voice_provider_order` in `.env` accepts `hosted,voicechat,legacy`. `legacy` is the current local Parakeet+Kokoro cascade; `voicechat` is the NVIDIA Nemotron realtime preview (disabled by default).
- **Graceful fallback:** if the primary provider's `health()` fails at session-start time, the gateway falls back to the next in order and emits a `provider.changed` event.
- **Session timeout:** `VOICE_SESSION_MAX_SECONDS` (default 840s / 14 min). A `session.expiring` event fires 5–30 s before to let the client reconnect cleanly.
- **Turn cancellation:** the frontend can send `response.cancel`; the gateway sets a `cancel_event` that interrupts both LLM streaming and TTS chunk delivery.
- **Text-chat TTS:** typed messages also get voiced when voice is enabled. `createTTSSession()` in `useChatVoice.ts` returns a dedicated `AudioContext`-backed session that flushes at sentence/clause boundaries so playback starts while the LLM is still generating.

</details>

---

## Quick Start

### Prerequisites

| Requirement | Version | Why |
|---|---|---|
| Node.js | 20.19+ or 22.12+ | Vite 7 |
| Python | 3.12+ | FastAPI + NeMo |
| CUDA GPU | RTX 20-series or newer, 8 GB+ VRAM | Parakeet 1.1B fp16 + Kokoro ONNX |
| MySQL | 8.x (XAMPP OK) | Stats/sessions persistence |
| NVIDIA API key | [build.nvidia.com](https://build.nvidia.com) | LLM inference |

### Install

```bash
git clone https://github.com/AlviHossain97/RetroWeb.git PiStation
cd PiStation
npm install
python3 -m pip install -r backend/requirements.txt
cp backend/.env.example backend/.env
# Edit backend/.env — set NVIDIA_API_KEY and DB_PASSWORD at minimum.
```

### Run the whole stack

```bash
npm start
```

Equivalent to: `node start.mjs`, which boots **XAMPP → FastAPI → Kokoro → Parakeet → Vite → Sunshine** in that order. The dashboard lands on `http://localhost:5173`.

### Run the frontend alone

If you don't need the AI stack (offline dev on UI-only changes):

```bash
npm run dev
```

### Run tests

```bash
npm test
python3 -m unittest discover -s backend/tests
```

---

## Configuration

All backend config lives in [`backend/.env`](backend/.env.example) (gitignored) and is loaded via pydantic-settings. **Shell env vars take precedence over `.env`** — set `NVIDIA_API_KEY` globally if you want it inherited by any process without editing the file.

<details>
<summary><b>Full environment variable reference</b></summary>

### Required

| Variable | Example | Purpose |
|---|---|---|
| `NVIDIA_API_KEY` | `nvapi-...` | LLM chat completions |
| `DB_PASSWORD` | `changeme` | MySQL user password |

### Voice cascade

| Variable | Default | Purpose |
|---|---|---|
| `VOICE_PROVIDER_ORDER` | `legacy` | Ordered list: `legacy`, `voicechat`, `hosted` |
| `VOICE_LOCAL_STT_URL` | `http://localhost:8786` | Parakeet server endpoint |
| `VOICE_LOCAL_TTS_URL` | `http://localhost:8787` | Kokoro server endpoint |
| `VOICE_SESSION_MAX_SECONDS` | `840` | Session lifetime before forced reconnect |
| `NVIDIA_MODEL` | `stepfun-ai/step-3.5-flash` | LLM used by voice cascade |

### Optional — NVIDIA Nemotron realtime voicechat

| Variable | Default | Purpose |
|---|---|---|
| `NVIDIA_VOICECHAT_ENABLED` | `false` | Enable the single-provider realtime fallback |
| `NVIDIA_VOICECHAT_MODEL` | `nemotron-voicechat` | Model name |
| `NVIDIA_VOICECHAT_UPSTREAM_URL` | — | WebSocket URL |

### Optional — web grounding

| Variable | Default | Purpose |
|---|---|---|
| `WEB_SEARCH_MODE` | `auto` | `auto` / `always` / `never` |
| `SEARXNG_URL` | — | Self-hosted search endpoint |
| `TAVILY_API_KEY` | — | Managed search fallback |
| `SEARCH_TOP_K` | `5` | Results per query |

### Optional — image generation

| Variable | Default | Purpose |
|---|---|---|
| `IMAGEROUTER_API_KEY` | — | Enables `/ai/generate-image` |
| `IMAGEROUTER_IMAGE_MODEL` | `google/nano-banana-2:free` | Default image model |

### Parakeet runtime tunables (server env, not in `.env`)

| Variable | Default | Purpose |
|---|---|---|
| `PARAKEET_MODEL` | `nvidia/parakeet-tdt-1.1b` | Swap to `parakeet-tdt-0.6b-v2` for pure-English or lower VRAM |
| `PARAKEET_DEVICE` | `cuda` | Set `cpu` for CPU-only (very slow) |
| `PARAKEET_HALF` | `1` | Set `0` to force fp32 |

</details>

---

## Service Map

| Service | Port | Started by | Kills gracefully via |
|---|---|---|---|
| Vite dev server | 5173 | `start.mjs` | Ctrl+C |
| FastAPI backend | 8000 | `start.mjs` → `uvicorn` | SIGTERM |
| Parakeet STT | 8786 | `start.mjs` → `scripts/parakeet-server.py` | SIGTERM |
| Kokoro TTS | 8787 | `start.mjs` → `scripts/kokoro-tts-server.py` | SIGTERM |
| MySQL (XAMPP) | 3306 | `/opt/lampp/lampp start` | `/opt/lampp/lampp stop` |
| Sunshine | 47990 | `start.mjs` | systray → Quit |
| phpMyAdmin | 80 | XAMPP Apache | XAMPP |

---

## Project Layout

```
PiStation/
├── backend/                       FastAPI + pydantic-settings
│   ├── app/
│   │   ├── routes/                12 route modules (voice, ai, stats, sessions, …)
│   │   ├── services/              voice_gateway, ai_context, grounding, tools, …
│   │   ├── repositories/          MySQL query layer
│   │   ├── models/                Pydantic DTOs
│   │   └── config.py              Settings (pydantic-settings)
│   ├── migrations/                SQL + seed
│   ├── tests/                     unittest (voice gateway, Speechmatics client)
│   └── requirements.txt
├── scripts/
│   ├── parakeet-server.py         NeMo ASR REST wrapper (:8786)
│   ├── kokoro-tts-server.py       Kokoro-ONNX REST wrapper (:8787)
│   ├── kokoro-models/             354 MB ONNX weights + voices
│   ├── audit-cores.ts / download-cores.ts
│   └── dashboard-stream.sh        Xvfb + FFmpeg UDP stream for Pi kiosk
├── src/                           React app
│   ├── routes/                    Lazy-loaded page components
│   ├── components/                UI + shadcn primitives
│   ├── lib/                       Business logic (emulation, storage, i18n, …)
│   ├── gamepad/                   Input mapping
│   ├── data/                      Static config (coreMap, system metadata)
│   └── stores/                    Zustand stores
├── public/
│   ├── cores/                     RetroArch WASM cores
│   ├── audio-worklets/            voice-capture-processor.js
│   ├── model-icons/               Model picker thumbnails
│   └── fonts/
├── tests/                         Node test runner (.test.mjs)
├── start.mjs                      Service orchestrator
├── vite.config.ts                 Proxies: /api/nvidia, /api/pistation (ws:true), /api/kokoro, /api/whisper
└── package.json
```

---

## Scripts Reference

| Script | What it does |
|---|---|
| `npm start` | Bring up the whole stack (XAMPP, FastAPI, Kokoro, Parakeet, Vite, Sunshine) |
| `npm run dev` | Vite only — useful for UI-only iterations |
| `npm run build` | `tsc -b && vite build` — typechecks and produces `dist/` |
| `npm run preview` | Serve the production build locally |
| `npm run lint` | ESLint over the repo |
| `npm test` | Run frontend tests (`tests/*.test.mjs`) |
| `PI_IP=192.168.1.100 npm start` | Additionally stream the desktop to a Pi via UDP |

---

## Voice Activation Modes

Configurable in the chat → voice settings overlay. The mode persists per session.

| Mode | Trigger | Best for |
|---|---|---|
| `auto_near_field` | Continuous listening with VAD (energy + silence cutoff ≈ 1300 ms) | Desktop mic at 0.5–2 m |
| `headset` | Same VAD but tighter thresholds (noise: 0.010, silence: 900 ms) | Wearing a headset |
| `push_to_talk` | Hold `T` key or long-press mic button | Noisy rooms, shared spaces |

**Internal safety:** in all continuous modes, the frontend suppresses VAD activation while TTS audio is actively playing, so the assistant can't transcribe its own voice.

---

## Model Picker

Currently exposed LLMs (editable in [`src/routes/chat/constants.ts`](src/routes/chat/constants.ts)):

- Gemma 3 27B
- Kimi K2 Thinking
- Mistral Large 3 675B
- Step 3.5 Flash
- **DeepSeek V4 Pro** *(default for reasoning-heavy replies)*
- **MiniMax M2.7**
- GLM 4.7

All go through NVIDIA's `integrate.api.nvidia.com/v1/chat/completions` with streaming enabled. To add another, append to `NVIDIA_MODELS` and drop an icon at `public/model-icons/{modelname}.png`.

---

## Troubleshooting

<details>
<summary><b>🎙️ Mic shows 0 input devices in browser</b></summary>

Usually one of:

1. **PipeWire user service is down.** Verify: `systemctl --user is-active pipewire pipewire-pulse wireplumber`. Fix: `systemctl --user start pipewire.socket pipewire pipewire-pulse wireplumber`.
2. **No default source configured.** Check `wpctl status` — the `Sources:` block should have an entry with `*` marker. If not: `wpctl set-default <node-id>`.
3. **Browser process cached an empty device list.** After fixing 1 or 2, fully quit the browser (not just close the tab) and reopen.
4. **Brave fingerprinting Shield blocking.** Click the lion icon in URL bar → "Block fingerprinting" → "Allow all fingerprinting", then reload.

</details>

<details>
<summary><b>🧠 Parakeet OOMs on load (8 GB GPU)</b></summary>

The loader is already fp16 + CPU-first, but if you still OOM:

1. Close Brave before launching the stack — its GPU process reserves ~300–500 MB of VRAM.
2. Temporarily stop Sunshine if you're not streaming: `pkill -x sunshine`.
3. Fall back to the 0.6b model: `PARAKEET_MODEL=nvidia/parakeet-tdt-0.6b-v2 npm start`.

</details>

<details>
<summary><b>🔊 Dashboard is laggy</b></summary>

Common causes in order of likelihood:

1. **Browser running with GL disabled after a driver change.** Check `ps -ef | grep gpu-process` — if you see `--use-gl=disabled` or `--disable-gpu-compositing`, fully quit and restart the browser.
2. **`packagekitd` doing an update check.** It'll settle in ~60 s. `systemctl stop packagekit` if urgent.
3. **Parakeet + Kokoro + Sunshine + browser all competing for the GPU.** Check `nvidia-smi`; if VRAM > 95 % used, stop Sunshine.

</details>

<details>
<summary><b>⚙️ FastAPI won't start with VOICE_PROVIDER_ORDER error</b></summary>

pydantic-settings tries to JSON-decode list-typed env vars by default. The fix is already applied (`NoDecode` annotation in `config.py`). If you still hit this, make sure your `VOICE_PROVIDER_ORDER` is a plain comma-separated string like `legacy` or `legacy,voicechat`, **not** a JSON array.

</details>

<details>
<summary><b>🌐 Text chat works but voice chat returns "Could not transcribe"</b></summary>

Open `/tmp/pistation.log` and look for `[VOICE] input_audio.stop chunks_sent=N bytes=NNNNN (~X.XXs)`.

- `chunks_sent=0` → frontend isn't streaming audio. Check mic permission + that `/api/pistation` Vite proxy has `ws: true`.
- `bytes` tiny but chunks > 0 → audio is silent. Check OS mic level in GNOME Settings.
- Transcription path runs but returns empty text → audio was silent or Parakeet rejected it. Try a longer, louder phrase.

</details>

---

## Hardware Requirements

**Minimum** (dashboard-only):

- 4 GB RAM
- Any x86_64 CPU, last 5 years
- Any Chromium / Firefox / Brave browser with WebAssembly + SharedArrayBuffer support

**Recommended** (full voice + AI stack):

- NVIDIA GPU ≥ 8 GB VRAM, CUDA 12.x
- 16 GB system RAM
- SSD (Kokoro ONNX + Parakeet 1.1B = ~4 GB cached)
- Wired Ethernet or 5 GHz Wi-Fi (for Sunshine streaming)

**Tested on**: HP OMEN Laptop 15 · RTX 3070 Laptop 8 GB · Zorin OS 18.1 · driver 580.126.09.

---

## Roadmap

- [x] Voice cascade (Parakeet → NVIDIA → Kokoro)
- [x] Text-chat TTS (Kokoro for typed replies)
- [x] Multi-model LLM picker
- [x] Web-grounded answers (Tavily/SearXNG)
- [x] Kiosk mode + Pi dashboard stream
- [ ] Library page (ROM browser with filters)
- [ ] Cloud save sync
- [ ] Per-user profiles
- [ ] Netplay matchmaking
- [ ] Mobile controller companion app

---

## Tech Stack

<details open>
<summary><b>Frontend</b></summary>

React 19 · TypeScript (strict) · Vite 7 · Tailwind CSS v4 · shadcn/ui · Zustand · Dexie · react-router v7 · Nostalgist (RetroArch WASM) · lucide-react · sonner · vite-plugin-pwa

</details>

<details>
<summary><b>Backend</b></summary>

FastAPI · pydantic-settings · PyMySQL · DBUtils · httpx · websockets · Jinja2 · BeautifulSoup4

</details>

<details>
<summary><b>AI & Voice</b></summary>

NVIDIA NeMo (Parakeet TDT 1.1B, fp16 on CUDA) · kokoro-onnx (v1.0 model + voices-v1.0.bin) · NVIDIA integrate API (chat completions) · Tavily / SearXNG (optional web grounding) · ImageRouter (optional image gen)

</details>

<details>
<summary><b>Infrastructure</b></summary>

Node 22 · Python 3.12 · MySQL 8 (XAMPP) · Sunshine NVENC · PipeWire / WirePlumber · PWA / Service Worker

</details>

---

## Can the README be interactive?

Short answer: **partially.** GitHub's Markdown renderer strips JavaScript, iframes, and forms — so no "click here to run a command." But it does support:

- ✅ **Mermaid diagrams** — the architecture + sequence diagrams above render live on GitHub and auto-theme with light/dark mode. Diagrams with `click` directives can even be navigable.
- ✅ **Collapsible `<details>`** — used throughout this README to hide verbose sections by default.
- ✅ **Clickable ToC** — anchor-linked headings.
- ✅ **Live status badges** — the shields.io badges at the top refresh on every page load.
- ✅ **Task lists** — checkboxes in the Roadmap section can be toggled directly on GitHub if you have write access.
- ✅ **Animated SVG** — inline SVG with SMIL animations renders (works for loading spinners, pulse effects).
- ✅ **Embedded GIFs / videos** — drop a `.gif` or `.mp4` in `docs/` and the README auto-plays them on GitHub.

**What would require more work:**

- A live demo — not viable here, since PiStation needs a GPU + MySQL + local AI services.
- "Try it in your browser" — possible if we extract the pure-emulation UI into a Stackblitz / Codesandbox project (no voice, no stats).
- Runtime status indicators (is Parakeet up right now?) — would need a publicly reachable `/health` endpoint + a shields.io endpoint badge.

If you want, I can add any of:
- a demo `.gif` placeholder so you can drop in a recording later
- a `mermaid` state diagram of the voice turn-taking FSM
- a shields.io endpoint badge wired to your backend's `/ai/voice/health`

Say which and I'll extend this.

---

<div align="center">

**PiStation** · retro gaming, modern stack, self-hosted.

</div>
