# RetroWeb AI Assistant — Technical Documentation

## Overview

The RetroWeb AI Assistant is a fully local, privacy-first conversational AI feature integrated into the PiStation emulator PWA. It runs entirely on the user's machine — no cloud APIs, no telemetry, no data leaving the browser. The assistant is purpose-built for retro gaming: it can answer questions about classic games, analyze in-game screenshots, provide walkthroughs, recommend titles, quiz users on trivia, and even speak responses aloud using local text-to-speech.

The entire implementation lives in a single route component at `src/routes/chat.tsx`, with persistence handled by Dexie (IndexedDB) and integration points in the emulator's play page.

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                        Browser (Client-Side)                     │
│                                                                  │
│  ┌──────────┐    ┌──────────────┐    ┌──────────────────────┐   │
│  │ chat.tsx  │───▶│  Ollama API  │───▶│ Local LLM (e.g.     │   │
│  │ (React)   │    │ :11434       │    │ LLaVA, Falcon, LFM) │   │
│  └────┬─────┘    └──────────────┘    └──────────────────────┘   │
│       │                                                          │
│       ├──────────▶ Kokoro TTS API (:8787) ──▶ Local TTS Engine  │
│       │                                                          │
│       ├──────────▶ Whisper STT API (:8786) ──▶ Local Whisper    │
│       │                                                          │
│       └──────────▶ Dexie (IndexedDB) ──▶ Chat History Storage   │
│                                                                  │
│  ┌──────────┐                                                    │
│  │ play.tsx  │──── sessionStorage ────▶ Screenshot / Game Name   │
│  └──────────┘                          passed to chat.tsx        │
└──────────────────────────────────────────────────────────────────┘
```

### Service Dependencies (All Local)

| Service | Default URL | Purpose |
|---------|------------|---------|
| **Ollama** | `http://localhost:11434` | LLM inference (chat completions, vision) |
| **Kokoro TTS** | `http://localhost:8787` | Text-to-speech synthesis |
| **Whisper STT** | `http://localhost:8786` | Speech-to-text transcription |

All three services run locally on the user's machine. The assistant degrades gracefully — if Kokoro or Whisper are offline, text chat still works. If Ollama is offline, the assistant shows an "Offline" status indicator and messages cannot be sent.

---

## LLM Integration (Ollama)

### Health Check & Model Discovery

On mount and every **15 seconds**, the assistant polls `GET /api/tags` on the Ollama server. This serves two purposes:

1. **Connectivity check** — determines if the Ollama service is reachable (sets the `ollamaOnline` flag).
2. **Model enumeration** — parses the response to extract all locally available model names, populating the model picker dropdown.

```typescript
const tagsRes = await fetch(`${OLLAMA_BASE}/api/tags`, { signal: AbortSignal.timeout(3000) });
const data = await tagsRes.json();
const names: string[] = (data.models || []).map((m: { name: string }) => m.name);
```

If the request fails or times out (3-second timeout), the assistant is marked offline.

### Supported Models

The assistant supports any model available in the user's local Ollama installation. Three models have dedicated branding (icons and display labels):

| Model ID | Display Label | Icon |
|----------|--------------|------|
| `llava:7b` | LLaVA 7B | `/model-icons/llava.png` |
| `falcon3:10b` | Falcon 3 10B | `/model-icons/falcon-edge.png` |
| `lfm2:24b` | LFM2 24B | `/model-icons/liquid_logo_black.png` |

The default model is `llava:7b` (a multimodal model that supports both text and image inputs). Any additional models pulled into Ollama appear in the model picker with a generic icon.

### Streaming Chat Completions

Messages are sent to `POST /api/chat` using Ollama's streaming API:

```typescript
const res = await fetch(`${OLLAMA_BASE}/api/chat`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    model: selectedModel,
    messages: apiMessages,
    stream: true,
    think: false,
  }),
});
```

The response body is a **newline-delimited JSON stream** (NDJSON). Each line is a JSON object containing `message.content` with the next token(s). The assistant reads the stream using a `ReadableStream` reader and `TextDecoder`, parsing each line incrementally:

```typescript
const reader = res.body.getReader();
const decoder = new TextDecoder();
let full = "";

while (true) {
  const { done, value } = await reader.read();
  if (done) break;
  const chunk = decoder.decode(value, { stream: true });
  for (const line of chunk.split("\n").filter(Boolean)) {
    const json = JSON.parse(line);
    if (json.message?.content) {
      full += json.message.content;
      // Update the assistant message in real-time
    }
  }
}
```

This gives the user a live typing effect as tokens arrive.

### System Prompt & Conversation Context

Every request includes a **system prompt** that is dynamically assembled from:

1. **Persona prompt** — one of five personality templates (see [Personas](#personas) below).
2. **Game context** — if the user recently played a game, its name is injected: `"The user recently played: {gameName}."` (read from `sessionStorage.getItem("retroweb.lastPlayedGame")`).
3. **Instruction suffix** — `"You can help with tips, cheats, walkthroughs, and general retro gaming knowledge. Be concise and helpful."`

The full conversation history (all previous messages plus the new user message) is sent with each request, preserving multi-turn context. Images are included inline in the message payload when the model supports multimodal input (e.g., LLaVA).

---

## Personas

The assistant supports **5 distinct personalities** that change its tone, expertise focus, and conversational style. The user selects a persona from a dropdown in the chat header.

| Persona ID | Label | System Prompt Summary |
|-----------|-------|----------------------|
| `default` | 🤖 Assistant | Helpful retro gaming assistant for RetroWeb |
| `clerk` | 🏪 Store Clerk | Friendly 90s game store clerk, nostalgic and casual |
| `speedrunner` | ⚡ Speedrunner | Expert speedrunner, technical, mentions frame data and strats |
| `historian` | 📚 Historian | Gaming historian and collector, focuses on cultural context and trivia |
| `comedian` | 😄 Comedian | Witty comedian, makes jokes and puns about classic games |

Persona selection only changes the system prompt prefix. It does not affect the model, temperature, or any other inference parameter.

---

## Multimodal Input (Vision)

### Image Upload

Users can attach images to their messages via two methods:

1. **Image file picker** — clicking the image icon in the input bar opens a file picker (`accept="image/*"`). Selected images are read as base64 via `FileReader.readAsDataURL()`, stripped of the `data:...;base64,` prefix, and stored in the `pendingImages` state array.
2. **Emulator screenshot** — when playing a game, the user can click "Ask AI" in the emulator overlay. This captures the current canvas frame, converts it to a base64 PNG, stores it in `sessionStorage` under `retroweb.screenshotForAI`, and navigates to `/chat`. On mount, the chat page checks for this key and auto-attaches the screenshot.

When images are attached, they appear as a preview row above the input field. Each can be individually removed. If the user sends a message with only images (no text), the prompt defaults to `"What's in this image?"`.

Images are passed to the Ollama API as a `images` array (base64-encoded strings) within the message object, which multimodal models like LLaVA can process.

### File Upload

Non-image files can also be attached. They are read as plain text via `FileReader.readAsText()` and stored in `pendingFiles`. When the message is sent, file contents are appended to the user's text as:

```
[File: filename.txt]
<file contents>
```

This allows users to paste code, configuration files, or text documents for the AI to analyze.

---

## Voice Mode (Speech-to-Text → LLM → Text-to-Speech)

Voice mode creates a **hands-free conversational loop**: the user speaks, the speech is transcribed, the transcription is sent to the LLM, the response is spoken aloud, and then recording resumes. This entire pipeline runs locally.

### Speech-to-Text (Whisper)

When voice mode is activated (by clicking the voice/microphone icon):

1. **Microphone access** is requested via `navigator.mediaDevices.getUserMedia({ audio: true })`.
2. A `MediaRecorder` captures audio in `audio/webm;codecs=opus` format.
3. An `AudioContext` with an `AnalyserNode` performs **real-time silence detection**:
   - **Silence threshold**: Frequency average below `5` is considered silence.
   - **Silence duration**: `1500ms` of silence after speech triggers auto-stop.
   - **Minimum speech duration**: `500ms` before silence detection activates.
   - **Maximum recording duration**: `15000ms` hard cap.
4. The recorded audio blob is sent to the local Whisper server:

```typescript
const form = new FormData();
form.append("file", blob, "audio.webm");
form.append("model", "Systran/faster-whisper-small");
const res = await fetch(`${WHISPER_BASE}/v1/audio/transcriptions`, {
  method: "POST",
  body: form,
});
```

5. The returned transcript text is passed directly to `sendMessageDirect()`, bypassing the text input.

### Text-to-Speech (Kokoro TTS)

As the LLM streams its response, the assistant performs **clause-level TTS** to minimize perceived latency:

1. **Sentence buffer** accumulates streamed tokens.
2. The buffer is **flushed** (sent to TTS) when any of these conditions are met:
   - A sentence-ending punctuation is detected: `.`, `!`, `?`
   - A clause boundary is detected (`, ; : — –`) **and** the buffer exceeds 30 characters.
   - The buffer exceeds **120 characters** (overflow flush).
   - The stream ends (force flush).
3. Each flush sends a request to Kokoro TTS:

```typescript
fetch(`${KOKORO_BASE}/v1/audio/speech`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    model: "kokoro",
    input: text,
    voice: "af_heart",
    speed: 1.2,
    response_format: "mp3",
  }),
});
```

4. **Audio fetching happens in parallel** (multiple TTS requests can be in-flight simultaneously), but **playback is sequential** — audio clips are chained with promises so they play in order without overlapping.
5. After all TTS playback finishes, the recording loop automatically restarts for the next user utterance.

### Voice Mode Lifecycle

```
[User taps mic] → voiceModeRef = true → startListeningLoop()
        │
        ▼
[Recording with silence detection] → auto-stop after silence
        │
        ▼
[Whisper transcription] → transcript text
        │
        ▼
[sendMessageDirect(transcript)] → LLM streaming response
        │
        ▼
[Clause-level TTS] → audio playback (sequential)
        │
        ▼
[All audio done] → startListeningLoop() again (loop)
        │
        ▼
[User taps mic again] → voiceModeRef = false → stop recording, release mic
```

---

## Quick Actions

The assistant offers three one-click quick actions in the toolbar:

### 🎲 Recommend

Sends a pre-built prompt asking the AI to recommend 3 retro games based on the user's recently played games and preferences.

### 🎯 Quiz

Sends a prompt requesting a multiple-choice (A/B/C/D) retro gaming trivia question. The AI is instructed not to reveal the answer until the user guesses.

### 🗺️ Walkthrough Mode

A toggle that, when active, **automatically captures and analyzes screenshots every 30 seconds** while the user plays a game. It reads the emulator screenshot from `sessionStorage.getItem("retroweb.screenshotForAI")` and sends it with a prompt asking for a quick gameplay tip. This creates a real-time AI co-pilot experience during gameplay.

When deactivated, the 30-second interval timer is cleared.

---

## Chat Persistence (Dexie / IndexedDB)

### Schema

Chat messages are stored in the `chatMessages` table (added in database version 4):

```typescript
interface ChatMessage {
  id?: number;        // Auto-incremented primary key
  role: "user" | "assistant";
  content: string;
  images?: string[];  // Base64-encoded image data
  timestamp: number;  // Used for ordering
}
```

Index: `++id, timestamp`

### Persistence Behavior

- **On mount**: `loadChatMessages()` is called to restore the previous conversation from IndexedDB.
- **On every message change**: The entire message array is serialized and written to IndexedDB. This is a **full replace** strategy — `saveChatMessages()` calls `db.chatMessages.clear()` followed by `db.chatMessages.bulkAdd(messages)`.
- **On clear**: The user can clear all chat history, which calls `clearChatMessages()` (truncates the table) and resets the in-memory `messages` state.

### Chat Export

Users can export the entire conversation as a Markdown file. The export button generates a `.md` file with each message formatted as:

```markdown
# RetroWeb AI Chat

**You:**
<user message>

---

**AI:**
<assistant response>
```

The file is downloaded as `retroweb-chat-YYYY-MM-DD.md`.

---

## Integration with the Emulator (play.tsx)

The AI chat is tightly integrated with the emulator's play page through `sessionStorage`:

### Screenshot Capture ("Ask AI" Button)

When the user clicks "Ask AI" during gameplay:

1. `play.tsx` calls `captureThumbnail()` to grab the current emulator canvas as a base64 PNG.
2. The base64 data (stripped of the data URI prefix) is stored in `sessionStorage.setItem("retroweb.screenshotForAI", base64)`.
3. The router navigates to `/chat`.
4. `chat.tsx` checks for this sessionStorage key on mount, auto-attaches it as a pending image, and removes the key.

### Game Context

When a game boots in the emulator, `play.tsx` stores the game filename in `sessionStorage.setItem("retroweb.lastPlayedGame", gameName)`. The chat assistant reads this value to inject game-aware context into the system prompt, enabling responses like "Since you're playing Super Mario World, here's a tip...".

---

## Achievements

The AI assistant triggers three achievements tracked in `src/lib/achievements.ts`:

| Achievement ID | Title | Description | Trigger |
|---------------|-------|-------------|---------|
| `ai_chat` | AI Assistant | Send a message to the AI chat | Any message sent |
| `voice_mode` | Voice Commander | Use voice mode in AI chat | Voice mode activated |
| `screenshot_ai` | Show & Tell | Send a screenshot to the AI | Message sent with attached image(s) |

Achievements are unlocked via `checkAndUnlock()` which checks if already unlocked in Dexie before writing.

---

## UI Components

### Status Indicator

A pill-shaped badge in the header shows connectivity status:
- **🟢 "Online · Voice"** — Ollama and Kokoro are both reachable.
- **🟢 "Online"** — Ollama is reachable, Kokoro is not.
- **🔴 "Offline"** — Ollama is unreachable.

### Model Picker

When multiple models are available in Ollama, a dropdown shows all models with:
- Custom icon and label for known models (LLaVA, Falcon, LFM2).
- A generic colored circle for unknown models.
- Radio-button selection with visual highlight on the active model.

### AI Orb

A decorative animated orb component (`AIOrb`) rendered inside the voice mode overlay. It consists of:
- Four layered radial-gradient circles (`c1`–`c4`) with independent rotation and scale animations.
- A glass-effect overlay with backdrop blur.
- Animated ring borders that rotate in 3D space.
- Pulsing wave effects radiating outward.

The orb serves as a visual indicator that the AI is listening or thinking.

### Input Bar

The input area uses a custom CSS-animated design (credited to "Cobp" from Uiverse.io) with:
- A text input that expands on focus.
- Three upload icons (emoji placeholder, image picker, file picker) that fade out when typing.
- A voice mode toggle (microphone icon) that expands into a full-screen orb overlay when active.
- A gradient send button that appears when text is entered.

### Clear Chat Confirmation

A modal dialog with an animated trash can icon. Requires explicit confirmation before clearing all messages from both state and IndexedDB.

---

## State Management

All state is managed with React `useState` hooks local to the `Chat` component. There is **no Zustand store** for chat state — persistence is handled directly through Dexie.

### Key State Variables

| Variable | Type | Purpose |
|----------|------|---------|
| `messages` | `Message[]` | Full conversation history |
| `input` | `string` | Current text input value |
| `streaming` | `boolean` | Whether a response is currently being streamed |
| `ollamaOnline` | `boolean` | Ollama service connectivity |
| `kokoroOnline` | `boolean` | Kokoro TTS service connectivity |
| `selectedModel` | `string` | Currently selected LLM model ID |
| `availableModels` | `string[]` | All models found in Ollama |
| `showModelPicker` | `boolean` | Model picker dropdown visibility |
| `showClearConfirm` | `boolean` | Clear confirmation modal visibility |
| `voiceEnabled` | `boolean` | Whether TTS playback is enabled |
| `listening` | `boolean` | Whether voice recording is active (UI state) |
| `pendingImages` | `string[]` | Base64 images queued for the next message |
| `pendingFiles` | `{name, content}[]` | Text files queued for the next message |
| `persona` | `string` | Currently selected AI persona |
| `walkthroughMode` | `boolean` | Whether auto-screenshot analysis is active |

### Key Refs

| Ref | Purpose |
|-----|---------|
| `voiceModeRef` | Tracks voice mode state outside React render cycle (used in async loops) |
| `mediaRecorderRef` | Current MediaRecorder instance for voice capture |
| `mediaStreamRef` | Current microphone MediaStream (reused across recordings) |
| `sendDirectRef` | Stable reference to `sendMessageDirect` for use in voice loop callbacks |
| `startRecRef` | Stable reference to `startListeningLoop` for recursive call from within itself |
| `chatDisplayRef` | Chat message container for auto-scroll |
| `walkthroughRef` | Interval timer ID for walkthrough mode cleanup |

---

## Route Registration

The chat page is lazy-loaded in `src/main.tsx`:

```typescript
const Chat = lazy(() => import('./routes/chat.tsx'));
// ...
<Route path="chat" element={<Chat />} />
```

Navigation entries exist in `src/App.tsx`:
- Desktop sidebar: `{ to: "/chat", label: "AI Chat", icon: <MessageCircle /> }`
- Mobile bottom nav: `{ to: "/chat", label: "Chat", icon: <MessageCircle /> }`

---

## Privacy & Security

- **No cloud APIs**: All AI inference, TTS, and STT run on the user's local machine.
- **No data exfiltration**: Chat messages are stored only in the browser's IndexedDB. No network requests are made to external servers.
- **Microphone access**: Requested only when the user explicitly activates voice mode. The media stream is released when voice mode is deactivated.
- **Session-scoped context**: Game names and screenshots are passed via `sessionStorage`, which is automatically cleared when the browser tab closes.
- **User-controlled persistence**: Chat history can be cleared at any time with the delete button. Export is an explicit user action.

---

## Error Handling

- **Ollama offline**: The send button is disabled. If a request fails mid-stream, the assistant message is replaced with: `"Sorry, I couldn't connect to the AI. Make sure Ollama is running."`
- **Kokoro offline**: Text chat works normally; TTS is silently skipped.
- **Whisper failure**: If transcription returns empty or fails, the voice loop restarts after a 1-second delay.
- **Malformed stream data**: Individual JSON parse failures within the NDJSON stream are silently skipped (`catch { /* skip malformed */ }`), allowing the stream to continue processing valid chunks.
- **Voice mode interruption**: If voice mode is toggled off during any stage (recording, transcription, or playback), the pipeline gracefully exits at the next checkpoint.
