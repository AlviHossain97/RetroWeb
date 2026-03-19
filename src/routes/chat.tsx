import { useState, useRef, useEffect, useCallback } from "react";
import { saveChatMessages, loadChatMessages, clearChatMessages, type ChatMessage } from "../lib/storage/db";
import { checkAndUnlock } from "../lib/achievements";

interface Message {
  role: "user" | "assistant";
  content: string;
  images?: string[]; // base64 encoded images
  grounded?: boolean;
  sources?: { id: number; title: string; url: string; snippet: string }[];
}

const OLLAMA_BASE = "/api/ollama";
const KOKORO_BASE = "/api/kokoro";
const STT_BASE = "/api/whisper";
const PISTATION_API = "/api/pistation";

/* ── Exact Cobp CSS (From Uiverse.io by Cobp) ── */
const COBP_CSS = `
.container-ia-chat {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: end;
  width: 300px;
}

.container-upload-files {
  position: absolute;
  left: 0;
  display: flex;
  color: #aaaaaa;
  transition: all 0.5s;

  & .upload-file {
    margin: 5px;
    padding: 2px;
    cursor: pointer;
    transition: all 0.5s;

    &:hover {
      color: #4c4c4c;
      scale: 1.1;
    }
  }
}

.input-text {
  max-width: 190px;
  width: 100%;
  margin-left: 72px;
  padding: 0.75rem 1rem;
  padding-right: 46px;
  border-radius: 50px;
  border: none;
  outline: none;
  background-color: #e9e9e9;
  color: #4c4c4c;
  font-size: 14px;
  line-height: 18px;
  font-family: "Segoe UI", Tahoma, Geneva, Verdana, sans-serif;
  font-weight: 500;
  transition: all 0.5s cubic-bezier(0.175, 0.885, 0.32, 1.05);
  z-index: 999;

  &::placeholder {
    color: #959595;
  }

  &:focus-within,
  &:valid {
    max-width: 250px;
    margin-left: 42px;

    & ~ .container-upload-files {
      opacity: 0;
      visibility: hidden;
      pointer-events: none;
      filter: blur(5px);
    }

    & ~ .label-files {
      transform: translateX(0) translateY(-50%) scale(1);
      opacity: 1;
      visibility: visible;
      pointer-events: all;
    }
  }

  &::selection {
    background-color: #4c4c4c;
    color: #e9e9e9;
  }

  &:valid ~ .label-text {
    transform: translateX(0) translateY(-50%) scale(1);
    opacity: 1;
    visibility: visible;
    pointer-events: all;
  }

  &:valid ~ .label-voice {
    transform: translateX(0) translateY(-50%) scale(0.25);
    opacity: 0;
    visibility: hidden;
    pointer-events: none;
  }
}

.input-voice {
  display: none;

  &:checked ~ .container-upload-files {
    opacity: 0;
    visibility: hidden;
    pointer-events: none;
    filter: blur(5px);
  }

  &:checked ~ .input-text {
    opacity: 0;
    visibility: hidden;
    pointer-events: none;
    filter: blur(5px);
  }
}

.label-files {
  position: absolute;
  top: 50%;
  left: 0;
  transform: translateX(-20px) translateY(-50%) scale(1);
  display: flex;
  padding: 0.5rem;
  color: #959595;
  background-color: #e9e9e9;
  border-radius: 50px;
  cursor: pointer;
  opacity: 0;
  visibility: hidden;
  pointer-events: none;
  transition: all 0.5s cubic-bezier(0.175, 0.885, 0.32, 1.05);

  &:focus-visible,
  &:hover {
    color: #4c4c4c;
  }
}

.label-voice,
.label-text {
  position: absolute;
  top: 50%;
  right: 0.25rem;
  transform: translateX(0) translateY(-50%) scale(1);
  width: 36px;
  height: 36px;
  display: flex;
  padding: 6px;
  border: none;
  outline: none;
  cursor: pointer;
  transition: all 0.5s cubic-bezier(0.175, 0.885, 0.32, 1.05);
  z-index: 999;
}

.input-voice:checked ~ .label-voice {
  background-color: #e9e9e9;
  right: 0;
  top: auto;
  bottom: 0;
  transform: none;
  width: 300px;
  height: 300px;
  border-radius: 3rem;
  box-shadow:
    0 10px 40px rgba(0, 0, 60, 0.25),
    inset 0 0 10px rgba(255, 255, 255, 0.5);

  & .icon-voice {
    opacity: 0;
  }

  & .text-voice p {
    opacity: 1;
  }
}

.label-voice {
  color: #959595;
  overflow: hidden;

  &:hover,
  &:focus-visible {
    color: #4c4c4c;
  }

  &:active svg {
    scale: 1.1;
  }

  & .icon-voice {
    position: absolute;
    transition: all 0.3s;
  }

  & .ai {
    --s: 200px;
    --p: calc(var(--s) / 4);
    position: absolute;
    inset: 0;
    margin: auto;
    width: var(--s);
    height: var(--s);
  }

  & .text-voice {
    position: absolute;
    inset: 1.25rem;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: space-between;

    & p {
      opacity: 0;
      transition: all 0.3s;
      text-wrap: nowrap;

      &:first-child {
        font-size: 20px;
        font-weight: 500;
        color: transparent;
        background-image: linear-gradient(
          -40deg,
          #959595 0% 35%,
          #e770cd 40%,
          #ffcef4 50%,
          #e770cd 60%,
          #959595 65% 100%
        );
        background-clip: text;
        background-size: 900px;
        animation: text-light 6s ease infinite;
      }

      &:last-child {
        font-size: 12px;
        color: #2b2b2b;
        mix-blend-mode: difference;
      }
    }
  }
}

@keyframes text-light {
  0% {
    background-position: 0px;
  }

  100% {
    background-position: 900px;
  }
}

.label-text {
  opacity: 0;
  visibility: hidden;
  pointer-events: none;
  transform: translateY(-50%) scale(0.25);
  color: #e9e9e9;
  background: linear-gradient(to top right, #9147ff, #ff4141);
  box-shadow: inset 0 0 4px rgba(255, 255, 255, 0.5);
  border-radius: 50px;

  &:hover,
  &:focus-visible {
    transform-origin: top center;
    box-shadow: inset 0 0 6px rgba(255, 255, 255, 1);
  }

  &:active {
    scale: 0.9;
  }
}

.ai {
  --z: 0;
  --s: 300px;
  --p: calc(var(--s) / 4);
  width: var(--s);
  aspect-ratio: 1;
  padding: var(--p);
  display: grid;
  place-items: center;
  position: relative;
  animation: circle1 5s ease-in-out infinite;

  &::before,
  &::after {
    content: "";
    position: absolute;
    top: 50%;
    left: 50%;
    width: 50%;
    height: 50%;
    border-radius: 50%;
    border: 2px solid white;
    box-shadow: 0 0 30px rgba(234, 170, 255, 1);
    filter: blur(5px);
    transform: translate(-50%, -50%);
    animation: wave 1.5s linear infinite;
  }

  &::after {
    animation-delay: 0.4s;
  }
}

@keyframes wave {
  0% {
    transform: translate(-50%, -50%) scale(1);
    opacity: 0;
    box-shadow: 0 0 50px rgba(234, 170, 255, 0.9);
  }
  35% {
    transform: translate(-50%, -50%) scale(1.3);
    opacity: 1;
  }
  70%,
  100% {
    transform: translate(-50%, -50%) scale(1.6);
    opacity: 0;
    box-shadow: 0 0 50px rgba(234, 170, 255, 0.3);
  }
}

@keyframes ai1 {
  0% {
    transform: rotate(0deg) translate(50%) scale(0.9);
    opacity: 0;
  }

  25% {
    transform: rotate(90deg) translate(50%) scale(1.8);
    opacity: 1;
  }

  50% {
    transform: rotate(180deg) translate(50%) scale(0.7);
    opacity: 0.4;
  }

  75% {
    transform: rotate(270deg) translate(50%) scale(1.2);
    opacity: 1;
  }

  100% {
    transform: rotate(360deg) translate(50%) scale(0.9);
    opacity: 0;
  }
}

@keyframes ai2 {
  0% {
    transform: rotate(90deg) translate(50%) scale(0.5);
  }

  25% {
    transform: rotate(180deg) translate(50%) scale(1.7);
    opacity: 0;
  }

  50% {
    transform: rotate(270deg) translate(50%) scale(1);
    opacity: 0;
  }

  75% {
    transform: rotate(360deg) translate(50%) scale(0.8);
    opacity: 0;
  }

  100% {
    transform: rotate(450deg) translate(50%) scale(0.5);
    opacity: 1;
  }
}

@keyframes ai3 {
  0% {
    transform: rotate(180deg) translate(50%) scale(0.8);
    opacity: 0.8;
  }

  25% {
    transform: rotate(270deg) translate(50%) scale(1.5);
  }

  50% {
    transform: rotate(360deg) translate(50%) scale(0.6);
    opacity: 0.4;
  }

  75% {
    transform: rotate(450deg) translate(50%) scale(1.3);
    opacity: 0.7;
  }

  100% {
    transform: rotate(540deg) translate(50%) scale(0.8);
    opacity: 0.8;
  }
}

@keyframes ai4 {
  0% {
    transform: rotate(270deg) translate(50%) scale(1);
    opacity: 1;
  }

  25% {
    transform: rotate(360deg) translate(50%) scale(0.7);
  }

  50% {
    transform: rotate(450deg) translate(50%) scale(1.6);
    opacity: 0.5;
  }

  75% {
    transform: rotate(540deg) translate(50%) scale(0.9);
    opacity: 0.8;
  }

  100% {
    transform: rotate(630deg) translate(50%) scale(1);
    opacity: 1;
  }
}

.c {
  position: absolute;
  width: 300px;
  aspect-ratio: 1;
  border-radius: 50%;
}

.c1 {
  background: radial-gradient(50% 50% at center, #c979ee, #74bcd6);
  width: 200px;
  animation: ai1 5.5s linear infinite;
}

.c2 {
  background: radial-gradient(50% 50% at center, #ef788c, #e7e7fb);
  width: 100px;
  animation: ai2 6s linear infinite;
}

.c3 {
  background: radial-gradient(50% 50% at center, #eb7fc6, transparent);
  width: 150px;
  opacity: 0.6;
  animation: ai3 4.8s linear infinite;
}

.c4 {
  background: #6d67c8;
  animation: ai4 5.2s linear infinite;
}

.container {
  overflow: hidden;
  background: #b6a9f8;
  width: 100%;
  border-radius: 50%;
  aspect-ratio: 1;
  position: relative;
  display: grid;
  place-items: center;
}

.glass {
  overflow: hidden;
  position: absolute;
  inset: calc(var(--p) - 4px);
  border-radius: 50%;
  backdrop-filter: blur(10px);
  box-shadow:
    0 0 50px rgba(255, 255, 255, 0.3),
    0 50px 50px rgba(0, 0, 0, 0.3),
    0 0 25px rgba(255, 255, 255, 1);
  background: radial-gradient(
    75px at 70% 30%,
    rgba(255, 255, 255, 0.7),
    transparent
  );
}

.rings {
  aspect-ratio: 1;
  border-radius: 50%;
  position: absolute;
  inset: 0;
  perspective: 11rem;
  opacity: 0.9;

  &:before,
  &:after {
    content: "";
    position: absolute;
    inset: 0;
    background: rgba(255, 0, 0, 1);
    border-radius: 50%;
    border: 6px solid transparent;
    mask:
      linear-gradient(#fff 0 0) padding-box,
      linear-gradient(#fff 0 0);
    background: linear-gradient(white, blue, magenta, violet, lightyellow)
      border-box;
    mask-composite: exclude;
  }
}

.rings::before {
  animation: ring180 10s ease-in-out infinite;
}

.rings::after {
  animation: ring90 10s ease-in-out infinite;
}

@keyframes ring180 {
  0% {
    transform: rotateY(180deg) rotateX(180deg) rotateZ(180deg);
  }

  25% {
    transform: rotateY(180deg) rotateX(180deg) rotateZ(180deg);
  }

  50% {
    transform: rotateY(360deg) rotateX(360deg) rotateZ(360deg);
  }

  80% {
    transform: rotateY(360deg) rotateX(360deg) rotateZ(360deg);
  }

  100% {
    transform: rotateY(540deg) rotateX(540deg) rotateZ(540deg);
  }
}

@keyframes ring90 {
  0% {
    transform: rotateY(90deg) rotateX(90deg) rotateZ(90deg);
  }

  25% {
    transform: rotateY(90deg) rotateX(90deg) rotateZ(90deg) scale(1.1);
  }

  50% {
    transform: rotateY(270deg) rotateX(270deg) rotateZ(270deg);
  }

  75% {
    transform: rotateY(270deg) rotateX(270deg) rotateZ(270deg);
  }

  100% {
    transform: rotateY(450deg) rotateX(450deg) rotateZ(450deg);
  }
}

@keyframes circle1 {
  0% {
    transform: scale(0.97);
  }

  15% {
    transform: scale(1);
  }

  30% {
    transform: scale(0.98);
  }

  45% {
    transform: scale(1);
  }

  60% {
    transform: scale(0.97);
  }

  85% {
    transform: scale(1);
  }

  100% {
    transform: scale(0.97);
  }
}

.bin-button {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background-color: rgb(255, 95, 95);
  cursor: pointer;
  border: 1.5px solid rgb(255, 201, 201);
  transition-duration: 0.3s;
  position: relative;
  overflow: hidden;
}
.bin-bottom {
  width: 10px;
  z-index: 2;
}
.bin-top {
  width: 12px;
  transform-origin: right;
  transition-duration: 0.3s;
  z-index: 2;
}
.bin-button:hover .bin-top {
  transform: rotate(45deg);
}
.bin-button:hover {
  background-color: rgb(255, 0, 0);
}
.bin-button:active {
  transform: scale(0.9);
}
.garbage {
  position: absolute;
  width: 10px;
  height: auto;
  z-index: 1;
  opacity: 0;
  transition: all 0.3s;
}
.bin-button:hover .garbage {
  animation: throw 0.4s linear;
}
@keyframes throw {
  from {
    transform: translate(-400%, -700%);
    opacity: 0;
  }
  to {
    transform: translate(0%, 0%);
    opacity: 1;
  }
}
`;

function AIOrb() {
  return (
    <div className="ai">
      <div className="container">
        <div className="c c4" />
        <div className="c c3" />
        <div className="c c2" />
        <div className="c c1" />
      </div>
      <div className="glass">
        <div className="rings" />
      </div>
    </div>
  );
}

const MODEL_ICONS: Record<string, { icon: string; label: string }> = {
  "llava:7b": { icon: "/model-icons/llava.png", label: "LLaVA 7B" },
  "falcon3:10b": { icon: "/model-icons/falcon-edge.png", label: "Falcon 3 10B" },
  "lfm2:24b": { icon: "/model-icons/liquid_logo_black.png", label: "LFM2 24B" },
};

type ExtendedAudioConstraints = MediaTrackConstraints & {
  voiceIsolation?: boolean;
  suppressLocalAudioPlayback?: boolean;
};

function buildVoiceCaptureConstraints(): ExtendedAudioConstraints {
  const supported = (typeof navigator !== "undefined" && navigator.mediaDevices?.getSupportedConstraints)
    ? navigator.mediaDevices.getSupportedConstraints() as MediaTrackSupportedConstraints & {
      voiceIsolation?: boolean;
      suppressLocalAudioPlayback?: boolean;
    }
    : {};

  const constraints: ExtendedAudioConstraints = {};

  if (supported.echoCancellation) constraints.echoCancellation = true;
  if (supported.noiseSuppression) constraints.noiseSuppression = true;
  if (supported.autoGainControl) constraints.autoGainControl = true;
  if (supported.channelCount) constraints.channelCount = 1;
  if (supported.sampleRate) constraints.sampleRate = 16000;
  if (supported.sampleSize) constraints.sampleSize = 16;
  if (supported.voiceIsolation) constraints.voiceIsolation = true;
  if (supported.suppressLocalAudioPlayback) constraints.suppressLocalAudioPlayback = true;

  return constraints;
}

export default function Chat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [ollamaOnline, setOllamaOnline] = useState(false);
  const [kokoroOnline, setKokoroOnline] = useState(false);
  const [selectedModel, setSelectedModel] = useState("qwen3.5:9b");
  const [availableModels, setAvailableModels] = useState<string[]>([]);
  const [showModelPicker, setShowModelPicker] = useState(false);
  const [showClearConfirm, setShowClearConfirm] = useState(false);
  const [voiceEnabled, setVoiceEnabled] = useState(true);
  const [listening, setListening] = useState(false);
  const [webMode, setWebMode] = useState<"auto" | "always" | "never">("auto");
  const [pendingImages, setPendingImages] = useState<string[]>([]);
  const [pendingFiles, setPendingFiles] = useState<{ name: string; content: string }[]>([]);
  const chatDisplayRef = useRef<HTMLDivElement>(null);
  const imageInputRef = useRef<HTMLInputElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const voiceCheckboxId = useRef(`voice-${Math.random().toString(36).slice(2)}`).current;
  const voiceModeRef = useRef(false);
  const ttsPlayingRef = useRef(false);
  const processingRef = useRef(false);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const sendDirectRef = useRef<(text: string) => void>(() => {});
  const startRecRef = useRef<() => void>(() => {});

  // Auto-scroll chat
  useEffect(() => {
    chatDisplayRef.current?.scrollTo({ top: chatDisplayRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  // Health check Ollama + Kokoro
  useEffect(() => {
    let cancelled = false;
    const check = async () => {
      try {
        const tagsRes = await fetch(`${OLLAMA_BASE}/api/tags`, { signal: AbortSignal.timeout(8000) });
        if (!cancelled) {
          setOllamaOnline(tagsRes.ok);
          if (tagsRes.ok) {
            const data = await tagsRes.json();
            const names: string[] = (data.models || []).map((m: { name: string }) => m.name);
            setAvailableModels(names);
            // Auto-select first available model if current selection isn't installed
            setSelectedModel(prev => names.includes(prev) ? prev : (names[0] || prev));
          }
        }
      } catch { if (!cancelled) setOllamaOnline(false); }
      try {
        const kRes = await fetch(`${KOKORO_BASE}/health`, { signal: AbortSignal.timeout(8000) });
        if (!cancelled) setKokoroOnline(kRes.ok);
      } catch { if (!cancelled) setKokoroOnline(false); }
    };
    check();
    const interval = setInterval(check, 15000);
    return () => { cancelled = true; clearInterval(interval); };
  }, []);

  // Load chat history from IndexedDB on mount
  useEffect(() => {
    loadChatMessages().then((saved) => {
      if (saved.length > 0) {
        setMessages(saved.map((m) => ({ role: m.role, content: m.content, images: m.images })));
      }
    });
  }, []);

  // Persist chat messages when they change
  useEffect(() => {
    if (messages.length === 0) return;
    const toSave: ChatMessage[] = messages.map((m, i) => ({
      role: m.role,
      content: m.content,
      images: m.images,
      timestamp: i,
    }));
    saveChatMessages(toSave);
  }, [messages]);

  // File upload handlers
  const handleImageUpload = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files) return;
    Array.from(files).forEach(file => {
      const reader = new FileReader();
      reader.onload = () => {
        const base64 = (reader.result as string).split(",")[1]; // strip data:...;base64,
        setPendingImages(prev => [...prev, base64]);
      };
      reader.readAsDataURL(file);
    });
    e.target.value = ""; // reset so same file can be re-selected
  }, []);

  const handleFileUpload = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files) return;
    Array.from(files).forEach(file => {
      if (file.type.startsWith("image/")) {
        const reader = new FileReader();
        reader.onload = () => {
          const base64 = (reader.result as string).split(",")[1];
          setPendingImages(prev => [...prev, base64]);
        };
        reader.readAsDataURL(file);
      } else {
        const reader = new FileReader();
        reader.onload = () => {
          setPendingFiles(prev => [...prev, { name: file.name, content: reader.result as string }]);
        };
        reader.readAsText(file);
      }
    });
    e.target.value = "";
  }, []);

  const removePendingImage = useCallback((idx: number) => {
    setPendingImages(prev => prev.filter((_, i) => i !== idx));
  }, []);

  const removePendingFile = useCallback((idx: number) => {
    setPendingFiles(prev => prev.filter((_, i) => i !== idx));
  }, []);

  const acquireMicrophoneStream = useCallback(async (): Promise<MediaStream> => {
    const audio = buildVoiceCaptureConstraints();
    console.log("[HEART] 🎚️ Requesting enhanced microphone constraints:", audio);
    return navigator.mediaDevices.getUserMedia({ audio });
  }, []);

  // Send message — accepts optional directText for voice mode
  const sendMessageDirect = useCallback(async (directText?: string) => {
    let text = (directText ?? input).trim();
    // Append file contents as context
    if (pendingFiles.length > 0 && !directText) {
      const fileContext = pendingFiles.map(f => `[File: ${f.name}]\n${f.content}`).join("\n\n");
      text = text ? `${text}\n\n${fileContext}` : fileContext;
    }
    const images = !directText ? [...pendingImages] : undefined;
    if (!text && (!images || images.length === 0)) return;
    if (!text) text = "What's in this image?";
    if (streaming || processingRef.current || !ollamaOnline || !selectedModel) return;
    processingRef.current = true;
    if (!directText) {
      setInput("");
      setPendingImages([]);
      setPendingFiles([]);
    }
    const userMsg: Message = { role: "user", content: text, images: images && images.length > 0 ? images : undefined };
    const assistantMsg: Message = { role: "assistant", content: "" };
    setMessages(prev => [...prev, userMsg, assistantMsg]);
    setStreaming(true);

    // Achievement triggers
    void checkAndUnlock("ai_chat");
    if (images && images.length > 0) void checkAndUnlock("screenshot_ai");

    // TTS queue for streaming voice — fires on first word boundary for minimal latency
    const isVoice = voiceModeRef.current && voiceEnabled;
    let sentenceBuffer = "";
    let chunkIndex = 0;
    const SENTENCE_END = /[.!?]\s*$/;
    const CLAUSE_END = /[,;:\u2014\u2013]\s*$/;
    const audioQueue: Promise<HTMLAudioElement | null>[] = [];
    let playChain = Promise.resolve();

    const sanitizeForTTS = (text: string): string =>
      text
        // Strip markdown formatting
        .replace(/\*{1,3}([^*]+)\*{1,3}/g, "$1")   // **bold**, *italic*
        .replace(/_{1,3}([^_]+)_{1,3}/g, "$1")       // __bold__, _italic_
        .replace(/~~([^~]+)~~/g, "$1")                // ~~strikethrough~~
        .replace(/`([^`]+)`/g, "$1")                  // `inline code`
        .replace(/^#{1,6}\s+/gm, "")                  // # headers
        .replace(/^[\-*+]\s+/gm, "")                  // - bullet points
        .replace(/^\d+\.\s+/gm, "")                   // 1. numbered lists
        .replace(/\[([^\]]+)\]\([^)]+\)/g, "$1")      // [link](url)
        .replace(/```[\s\S]*?```/g, "")               // code blocks
        // Strip emoji
        .replace(/\p{Emoji_Presentation}/gu, "")
        .replace(/\p{Extended_Pictographic}/gu, "")
        .replace(/\s{2,}/g, " ")
        .trim();

    const fetchAudio = (text: string): Promise<HTMLAudioElement | null> => {
      const cleaned = sanitizeForTTS(text);
      if (!cleaned) return Promise.resolve(null);
      return fetch(`${KOKORO_BASE}/v1/audio/speech`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ model: "kokoro", input: cleaned, voice: "af_heart", speed: 1.2, response_format: "mp3" }),
      }).then(res => {
        if (!res.ok) return null;
        return res.blob().then(blob => {
          const audio = new Audio(URL.createObjectURL(blob));
          return audio;
        });
      }).catch(() => null);
    };

    const muteMic = (mute: boolean) => {
      mediaStreamRef.current?.getAudioTracks().forEach(t => { t.enabled = !mute; });
    };

    const playAudio = (audio: HTMLAudioElement): Promise<void> => {
      return new Promise<void>(resolve => {
        audio.onended = () => resolve();
        audio.onerror = () => resolve();
        audio.play().catch(() => resolve());
      });
    };

    const enqueueSpeak = (text: string) => {
      sentenceBuffer = "";
      chunkIndex++;
      if (!ttsPlayingRef.current) {
        ttsPlayingRef.current = true;
        muteMic(true);
      }
      const audioPromise = fetchAudio(text);
      audioQueue.push(audioPromise);
      playChain = playChain.then(() =>
        audioPromise.then(audio => audio ? playAudio(audio) : undefined)
      );
    };

    const flushSentence = (force?: boolean) => {
      const trimmed = sentenceBuffer.trim();
      if (!trimmed || !isVoice || !kokoroOnline || !voiceEnabled) return;
      // First chunk: fire on the very first word boundary to minimize time-to-speech
      if (chunkIndex === 0 && trimmed.includes(" ")) {
        enqueueSpeak(trimmed);
        return;
      }
      const isSentenceEnd = SENTENCE_END.test(trimmed);
      const isClauseEnd = CLAUSE_END.test(trimmed) && trimmed.length >= 40;
      const isOverflow = trimmed.length >= 120;
      if (force || isSentenceEnd || isClauseEnd || isOverflow) {
        enqueueSpeak(trimmed);
      }
    };

    try {
      // Fetch gaming data context from PiStation backend
      let gamingContext = "";
      try {
        const ctxRes = await fetch(`${PISTATION_API}/ai/context`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ question: text }),
          signal: AbortSignal.timeout(3000),
        });
        if (ctxRes.ok) {
          const ctxData = await ctxRes.json();
          gamingContext = ctxData.context || "";
        }
      } catch { /* backend unavailable, continue without context */ }

      // Build game-aware system context
      const personaBase = "You are a helpful PiStation assistant, an AI for a retro gaming dashboard platform.";
      const dataBlock = gamingContext ? `\n\nHere is the user's real gaming data from their PiStation:\n${gamingContext}\n\nUse this data to answer questions about their gaming habits, stats, and history accurately.` : "";
      const voiceInstructions = isVoice ? " IMPORTANT: Your response will be read aloud by a text-to-speech engine. Do NOT use any markdown formatting whatsoever — no asterisks, no bold, no italic, no headers, no bullet points, no numbered lists, no code blocks. Write in plain conversational text only. Keep responses short and punchy (2-4 sentences max)." : "";
      
      // Web Grounding
      let webSources: any[] = [];
      let systemAppend = "";
      let grounded = false;
      let groundingFailed = false;
      
      if (webMode !== "never") {
        console.log(`[HEART] 🌐 Web grounding: mode=${webMode}`);
        setMessages(prev => {
          const updated = [...prev];
          updated[updated.length - 1] = { role: "assistant", content: "🔍 Searching the web..." };
          return updated;
        });
        try {
          const hist = messages.slice(-6).map(m => ({ role: m.role, content: m.content }));
          const groundRes = await fetch(`${PISTATION_API}/ai/ground`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ question: text, history: hist, mode: webMode }),
            signal: AbortSignal.timeout(30000),
          });
          if (groundRes.ok) {
            const groundData = await groundRes.json();
            console.log("[HEART] 🌐 Ground response:", groundData);
            if (groundData.error) {
              // Backend explicitly signaled a grounding failure
              console.warn("[HEART] 🌐 Grounding error:", groundData.error);
              groundingFailed = true;
            } else if (groundData.grounded) {
              grounded = true;
              webSources = groundData.sources || [];
              systemAppend = groundData.system_append || "";
              console.log(`[HEART] 🌐 Grounded with ${webSources.length} sources`);
            } else {
              console.log("[HEART] 🌐 Router decided: no search needed");
            }
          } else {
            console.error(`[HEART] 🌐 Ground endpoint returned ${groundRes.status}`);
            groundingFailed = true;
          }
        } catch (e) {
          console.error("[HEART] 🌐 Ground fetch failed:", e);
          groundingFailed = true;
        }
        
        // In ALWAYS mode, if grounding failed, show an explicit error and stop
        if (webMode === "always" && groundingFailed) {
          setMessages(prev => {
            const updated = [...prev];
            updated[updated.length - 1] = {
              role: "assistant",
              content: "⚠️ Web verification is currently unavailable, so I can't provide a verified answer right now. Please try again in a moment, or switch to Auto/Never web mode.",
            };
            return updated;
          });
          setStreaming(false);
          processingRef.current = false;
          return;
        }
        
        // Reset the typing placeholder
        setMessages(prev => {
          const updated = [...prev];
          updated[updated.length - 1] = { role: "assistant", content: "" };
          return updated;
        });
      }

      const systemPrompt = `${personaBase} You can help with tips, cheats, walkthroughs, gaming analytics, and general retro gaming knowledge. Be concise and helpful.${voiceInstructions}${dataBlock}\n${systemAppend}`;

      const apiMessages = [
        { role: "system", content: systemPrompt },
        ...[...messages, userMsg].map(m => {
          const msg: Record<string, unknown> = { role: m.role, content: m.content };
          if (m.images && m.images.length > 0) msg.images = m.images;
          return msg;
        }),
      ];

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

      if (!res.ok || !res.body) throw new Error("Stream failed");
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let full = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        const chunk = decoder.decode(value, { stream: true });
        for (const line of chunk.split("\n").filter(Boolean)) {
          try {
            const json = JSON.parse(line);
            if (json.message?.content) {
              full += json.message.content;
              sentenceBuffer += json.message.content;
              setMessages(prev => {
                const updated = [...prev];
                updated[updated.length - 1] = { 
                  role: "assistant", 
                  content: full,
                  grounded: grounded,
                  sources: webSources
                };
                return updated;
              });
              flushSentence();
            }
          } catch { /* skip malformed */ }
        }
      }

      // Flush any remaining text
      flushSentence(true);

      // Wait for TTS to finish before resuming listener
      // This prevents TTS audio from being captured by the mic
      playChain
        .catch(() => {})
        .finally(() => {
          ttsPlayingRef.current = false;
          muteMic(false);
          if (voiceModeRef.current) {
            console.log("[HEART] 🔄 TTS complete, resuming listener...");
            startRecRef.current();
          }
        });
    } catch {
      setMessages(prev => {
        const updated = [...prev];
        updated[updated.length - 1] = { role: "assistant", content: "Sorry, I couldn't connect to the AI. Make sure Ollama is running." };
        return updated;
      });
      ttsPlayingRef.current = false;
      if (mediaStreamRef.current) {
        mediaStreamRef.current.getAudioTracks().forEach(t => { t.enabled = true; });
      }
      if (voiceModeRef.current) {
        console.log("[HEART] 🔄 Error recovery, resuming listener...");
        startRecRef.current();
      }
    } finally {
      setStreaming(false);
      processingRef.current = false;
    }
  }, [input, streaming, ollamaOnline, selectedModel, messages, kokoroOnline, voiceEnabled, pendingImages, pendingFiles]);

  const sendMessage = useCallback(() => { sendMessageDirect(); }, [sendMessageDirect]);

  // STT: record audio, send to local Parakeet STT server
  const transcribeChunk = useCallback(async (blob: Blob): Promise<string> => {
    console.log(`[HEART] 📝 Transcribing ${blob.size} bytes of audio...`);
    const form = new FormData();
    form.append("file", blob, "audio.webm");
    form.append("model", "nvidia/parakeet-tdt-0.6b-v2");
    const t0 = performance.now();
    const res = await fetch(`${STT_BASE}/v1/audio/transcriptions`, { method: "POST", body: form });
    if (!res.ok) {
      console.warn(`[HEART] ❌ STT returned HTTP ${res.status}`);
      return "";
    }
    const data = await res.json();
    const text = (data.text || "").trim();
    const ms = Math.round(performance.now() - t0);
    console.log(`[HEART] 📝 Parakeet returned: '${text}' (${ms}ms)`);
    return text;
  }, []);

  // Start recording a single utterance, transcribe, send, speak, loop
  const startListeningLoop = useCallback(async () => {
    if (!voiceModeRef.current) return;

    try {
      console.log("[HEART] 🎤 Listening...");
      // Get mic stream (reuse if already open)
      if (!mediaStreamRef.current) {
        console.log("[HEART] 🎤 Requesting microphone access...");
        mediaStreamRef.current = await acquireMicrophoneStream();
        console.log("[HEART] ✅ Microphone access granted");
      }
      const stream = mediaStreamRef.current;

      // Verify the stream is still active
      if (!stream.active || stream.getAudioTracks().every(t => t.readyState === "ended")) {
        console.log("[HEART] ⚠️ Mic stream ended, re-acquiring...");
        mediaStreamRef.current = await acquireMicrophoneStream();
      }

      // Use AudioContext for silence detection
      const audioCtx = new AudioContext();
      const source = audioCtx.createMediaStreamSource(mediaStreamRef.current);
      const analyser = audioCtx.createAnalyser();
      analyser.fftSize = 512;
      source.connect(analyser);
      const dataArray = new Uint8Array(analyser.frequencyBinCount);

      // Choose a supported mimeType
      const mimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
        ? "audio/webm;codecs=opus"
        : MediaRecorder.isTypeSupported("audio/webm")
          ? "audio/webm"
          : "";
      const recorder = new MediaRecorder(mediaStreamRef.current, mimeType ? { mimeType } : undefined);
      mediaRecorderRef.current = recorder;
      const chunks: Blob[] = [];
      recorder.ondataavailable = (e) => { if (e.data.size > 0) chunks.push(e.data); };

      const { blob: audioBlob, peakEnergy } = await new Promise<{ blob: Blob; peakEnergy: number }>((resolve) => {
        let _peakEnergy = 0;
        recorder.onstop = () => {
          audioCtx.close();
          const blob = new Blob(chunks, { type: mimeType || "audio/webm" });
          console.log(`[HEART] 🛑 Recording stopped — ${blob.size} bytes, peak energy: ${_peakEnergy.toFixed(1)}`);
          resolve({ blob, peakEnergy: _peakEnergy });
        };
        recorder.onerror = (e) => {
          console.error("[HEART] ❌ MediaRecorder error:", e);
          audioCtx.close();
          resolve({ blob: new Blob([], { type: "audio/webm" }), peakEnergy: 0 });
        };
        recorder.start(250); // capture data every 250ms for more reliable chunks

        let speechDetected = false;
        let silenceStart = 0;
        const SILENCE_THRESHOLD = 15; // frequency avg below this = silence
        const SILENCE_DURATION = 1500; // ms of silence after speech before auto-stop
        const MIN_SPEECH_DURATION = 500;
        const MAX_DURATION = 30000; // 30s max
        const startTime = Date.now();

        const checkSilence = () => {
          if (recorder.state !== "recording") return;
          if (!voiceModeRef.current) { recorder.stop(); return; }
          if (Date.now() - startTime > MAX_DURATION) {
            console.log("[HEART] ⏱️ Max recording duration reached, stopping...");
            recorder.stop();
            return;
          }

          analyser.getByteFrequencyData(dataArray);
          const avg = dataArray.reduce((a, b) => a + b, 0) / dataArray.length;

          if (avg > SILENCE_THRESHOLD) {
            if (!speechDetected) {
              console.log("[HEART] 🗣️ Speech detected");
            }
            speechDetected = true;
            silenceStart = 0;
            if (avg > _peakEnergy) _peakEnergy = avg;
          } else if (speechDetected && (Date.now() - startTime > MIN_SPEECH_DURATION)) {
            if (!silenceStart) silenceStart = Date.now();
            else if (Date.now() - silenceStart > SILENCE_DURATION) {
              console.log("[HEART] 🔇 Silence detected after speech, stopping...");
              recorder.stop();
              return;
            }
          }
          requestAnimationFrame(checkSilence);
        };
        requestAnimationFrame(checkSilence);
      });

      if (!voiceModeRef.current) return;

      // Skip empty or too-quiet recordings (prevents phantom transcriptions)
      const MIN_PEAK_ENERGY = 20;
      if (audioBlob.size < 1000 || peakEnergy < MIN_PEAK_ENERGY) {
        console.log(`[HEART] ⚠️ Audio too small or quiet (size=${audioBlob.size}, peak=${peakEnergy.toFixed(1)}), skipping`);
        // Don't restart if TTS is playing — playChain.finally() will handle it
        if (voiceModeRef.current && !ttsPlayingRef.current) startRecRef.current();
        return;
      }

      const transcript = await transcribeChunk(audioBlob);

      if (!transcript || !voiceModeRef.current) {
        console.log("[HEART] 🔄 No transcript or voice mode off, restarting listener...");
        // Don't restart if TTS is playing — playChain.finally() will handle it
        if (voiceModeRef.current && !ttsPlayingRef.current) startRecRef.current();
        return;
      }

      console.log(`[HEART] 💬 Sending: "${transcript}"`);
      sendDirectRef.current(transcript);
    } catch (err) {
      console.error("[HEART] ❌ Voice pipeline error:", err);
      if (voiceModeRef.current) {
        setTimeout(() => startRecRef.current(), 1000);
      }
    }
  }, [acquireMicrophoneStream, transcribeChunk]);

  // Keep refs in sync
  sendDirectRef.current = (text: string) => sendMessageDirect(text);
  startRecRef.current = startListeningLoop;

  // Toggle voice mode
  const toggleListening = useCallback(() => {
    if (voiceModeRef.current) {
      // Stop voice mode
      console.log("[HEART] 🛑 Stopping voice pipeline...");
      voiceModeRef.current = false;
      setListening(false);
      mediaRecorderRef.current?.stop();
      mediaRecorderRef.current = null;
      // Release mic
      mediaStreamRef.current?.getTracks().forEach(t => t.stop());
      mediaStreamRef.current = null;
    } else {
      // Start voice mode
      console.log("[HEART] ✅ Starting voice pipeline...");
      voiceModeRef.current = true;
      setListening(true);
      void checkAndUnlock("voice_mode");
      startRecRef.current();
    }
  }, []);

  const statusText = ollamaOnline
    ? kokoroOnline ? "Online · Voice" : "Online"
    : "Offline";
  const statusColor = ollamaOnline ? "bg-green-500" : "bg-red-500";

  return (
    <div className="flex-1 flex flex-col h-full">
      <style dangerouslySetInnerHTML={{ __html: COBP_CSS }} />

      {/* Clear Chat Confirmation */}
      {showClearConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
          <div className="select-none w-[280px] flex flex-col p-4 items-center justify-center bg-gray-800 border border-gray-800 shadow-lg rounded-2xl group">
            <div className="text-center p-3 flex-auto justify-center">
              <svg
                fill="currentColor"
                viewBox="0 0 20 20"
                className="group-hover:animate-bounce w-12 h-12 flex items-center text-gray-600 fill-red-500 mx-auto"
                xmlns="http://www.w3.org/2000/svg"
              >
                <path
                  clipRule="evenodd"
                  d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z"
                  fillRule="evenodd"
                />
              </svg>
              <h2 className="text-xl font-bold py-4 text-gray-200">Are you sure?</h2>
              <p className="font-bold text-sm text-gray-500 px-2">
                Do you really want to clear all messages? This cannot be undone.
              </p>
            </div>
            <div className="p-2 mt-2 flex items-center justify-center gap-2 w-full">
              <button
                onClick={() => setShowClearConfirm(false)}
                className="bg-gray-700 px-4 py-2 text-xs shadow-sm font-medium tracking-wider border-2 border-gray-600 hover:border-gray-700 text-gray-300 rounded-full hover:shadow-lg hover:bg-gray-800 transition ease-in duration-300"
              >
                Cancel
              </button>
              <button
                onClick={() => { setMessages([]); clearChatMessages(); setShowClearConfirm(false); }}
                className="bg-red-500 hover:bg-transparent px-4 py-2 text-xs shadow-sm hover:shadow-lg font-medium tracking-wider border-2 border-red-500 hover:border-red-500 text-white hover:text-red-500 rounded-full transition ease-in duration-300"
              >
                Confirm
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Header */}
      <div className="px-4 py-3 border-b dark:border-zinc-700">
        <div className="flex justify-between items-center">
          <h2 className="text-lg font-semibold text-zinc-800 dark:text-white">
            PiStation AI
          </h2>
          <div className="flex items-center gap-2">
            {availableModels.length > 1 && (
              <button
                onClick={() => setShowModelPicker(v => !v)}
                className="text-xs px-2 py-1 rounded-full bg-zinc-700 text-white border border-zinc-600 hover:bg-zinc-600 transition-colors flex items-center gap-1.5"
              >
                {MODEL_ICONS[selectedModel] && (
                  <img src={MODEL_ICONS[selectedModel].icon} alt="" className="w-3.5 h-3.5 object-contain" />
                )}
                {MODEL_ICONS[selectedModel]?.label || selectedModel}
              </button>
            )}
            {messages.length > 0 && (
              <button
                onClick={() => {
                  const md = messages.map(m => `**${m.role === "user" ? "You" : "AI"}:**\n${m.content}`).join("\n\n---\n\n");
                  const blob = new Blob([`# PiStation AI Chat\n\n${md}`], { type: "text/markdown" });
                  const url = URL.createObjectURL(blob);
                  const a = document.createElement("a");
                  a.href = url;
                  a.download = `retroweb-chat-${new Date().toISOString().slice(0, 10)}.md`;
                  a.click();
                  URL.revokeObjectURL(url);
                }}
                className="text-xs px-2 py-1 rounded-full bg-zinc-700 text-white border border-zinc-600 hover:bg-zinc-600 transition-colors"
                title="Export chat as Markdown"
              >
                📥
              </button>
            )}
            {messages.length > 0 && (
              <button
                onClick={() => setShowClearConfirm(true)}
                className="bin-button"
                title="Clear chat"
              >
                <svg
                  className="bin-top"
                  viewBox="0 0 39 7"
                  fill="none"
                  xmlns="http://www.w3.org/2000/svg"
                >
                  <line y1="5" x2="39" y2="5" stroke="white" strokeWidth="4" />
                  <line x1="12" y1="1.5" x2="26.0357" y2="1.5" stroke="white" strokeWidth="3" />
                </svg>
                <svg
                  className="bin-bottom"
                  viewBox="0 0 33 39"
                  fill="none"
                  xmlns="http://www.w3.org/2000/svg"
                >
                  <mask id="path-1-inside-1_8_19" fill="white">
                    <path d="M0 0H33V35C33 37.2091 31.2091 39 29 39H4C1.79086 39 0 37.2091 0 35V0Z" />
                  </mask>
                  <path
                    d="M0 0H33H0ZM37 35C37 39.4183 33.4183 43 29 43H4C-0.418278 43 -4 39.4183 -4 35H4H29H37ZM4 43C-0.418278 43 -4 39.4183 -4 35V0H4V35V43ZM37 0V35C37 39.4183 33.4183 43 29 43V35V0H37Z"
                    fill="white"
                    mask="url(#path-1-inside-1_8_19)"
                  />
                  <line x1="12" y1="6" x2="12" y2="29" stroke="white" strokeWidth="4" />
                  <line x1="21" y1="6" x2="21" y2="29" stroke="white" strokeWidth="4" />
                </svg>
                <svg
                  className="garbage"
                  viewBox="0 0 24 24"
                  fill="none"
                  xmlns="http://www.w3.org/2000/svg"
                >
                  <path d="M2 6L6 2M6 2L10 6M6 2V18" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                  <path d="M14 6L18 2M18 2L22 6M18 2V18" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </button>
            )}
            <button
              onClick={() => setVoiceEnabled(v => !v)}
              className={`text-xs px-2 py-1 rounded-full ${voiceEnabled ? "bg-purple-500 text-white" : "bg-zinc-600 text-zinc-300"}`}
              title="Toggle Voice Mode"
            >
              {voiceEnabled ? "🔊" : "🔇"}
            </button>
            <select
              value={webMode}
              onChange={e => setWebMode(e.target.value as "auto" | "always" | "never")}
              className="text-xs bg-zinc-700 text-white border border-zinc-600 rounded-full px-2 py-1"
              title="Web Search Mode"
            >
              <option value="auto">🌐 Web: Auto</option>
              <option value="always">🌐 Web: Always</option>
              <option value="never">🌐 Web: Never</option>
            </select>
            <div className={`${statusColor} text-white text-xs px-2 py-1 rounded-full`}>
              {statusText}
            </div>
          </div>
        </div>
      </div>

      {/* Model Picker */}
      {showModelPicker && (
        <div className="px-4 py-3 border-b dark:border-zinc-700">
          <div className="flex flex-col gap-2">
            <legend className="text-sm font-semibold text-zinc-300 select-none">Choose Model</legend>
            {availableModels.map((m) => {
              const info = MODEL_ICONS[m];
              return (
                <label
                  key={m}
                  htmlFor={`model-${m}`}
                  className={`font-medium h-12 relative hover:bg-zinc-700 flex items-center px-3 gap-3 rounded-lg cursor-pointer select-none transition-all ${
                    selectedModel === m
                      ? "text-blue-400 bg-blue-500/10 ring-1 ring-blue-400/50"
                      : "text-zinc-300"
                  }`}
                >
                  <div className="w-5 h-5 flex-shrink-0">
                    {info ? (
                      <img src={info.icon} alt="" className="w-5 h-5 object-contain" />
                    ) : (
                      <div className="w-5 h-5 rounded-full bg-zinc-600" />
                    )}
                  </div>
                  <span className="text-sm">{info?.label || m}</span>
                  <input
                    type="radio"
                    name="model"
                    id={`model-${m}`}
                    checked={selectedModel === m}
                    onChange={() => { setSelectedModel(m); setShowModelPicker(false); }}
                    className="w-4 h-4 absolute accent-blue-500 right-3"
                  />
                </label>
              );
            })}
          </div>
        </div>
      )}

      {/* Quick Actions */}
      <div className="px-4 py-2 border-b dark:border-zinc-700 flex items-center gap-2 flex-wrap">
        <button
          onClick={() => { void sendMessageDirect("What are my gaming stats? Give me a summary of my total playtime, most played games, and favorite systems."); }}
          className="text-xs px-2 py-1 rounded-full bg-blue-600 text-white hover:bg-blue-500 transition-colors"
          title="View your gaming stats"
        >
          📊 My Stats
        </button>
        <button
          onClick={() => { void sendMessageDirect("Based on my gaming history and play patterns, what retro game should I play next? Give me 3 recommendations with brief reasons."); }}
          className="text-xs px-2 py-1 rounded-full bg-emerald-600 text-white hover:bg-emerald-500 transition-colors"
          title="Get AI game recommendations"
        >
          🎲 Recommend
        </button>
        <button
          onClick={() => { void sendMessageDirect("Give me a fun retro gaming trivia question! Make it multiple choice (A/B/C/D) and don't reveal the answer until I guess. Pick from any classic game or console."); }}
          className="text-xs px-2 py-1 rounded-full bg-purple-600 text-white hover:bg-purple-500 transition-colors"
          title="Retro gaming trivia quiz"
        >
          🎯 Quiz
        </button>
        <button
          onClick={() => { void sendMessageDirect("What's my longest gaming session ever? And which game have I spent the most time on?"); }}
          className="text-xs px-2 py-1 rounded-full bg-amber-600 text-white hover:bg-amber-500 transition-colors"
          title="Ask about your gaming records"
        >
          🏆 Records
        </button>
      </div>

      {/* Messages */}
      <div
        ref={chatDisplayRef}
        className="flex-1 p-4 overflow-y-auto flex flex-col space-y-2"
      >
        {messages.length === 0 && (
          <div className="flex-1 flex flex-col items-center justify-center gap-4">
            <p className="text-sm text-zinc-400">Ask me anything</p>
          </div>
        )}
        {messages.map((msg, i) => (
          <div key={i} className={`flex flex-col max-w-[85%] ${msg.role === "user" ? "self-end items-end" : "self-start"}`}>
            {/* The main message bubble */}
            <div
              className={`chat-message rounded-lg px-3 py-2 text-sm break-words ${
                msg.role === "user"
                  ? "bg-zinc-600 text-white rounded-br-none"
                  : "bg-blue-600 text-white rounded-bl-none shadow-sm"
              }`}
            >
              {msg.images && msg.images.length > 0 && (
                <div className="flex flex-wrap gap-1 mb-1">
                  {msg.images.map((img, j) => (
                    <img key={j} src={`data:image/png;base64,${img}`} alt="uploaded" className="max-w-[200px] max-h-[150px] rounded object-cover" />
                  ))}
                </div>
              )}
              {msg.content || (streaming && i === messages.length - 1 ? "..." : "")}
            </div>

            {/* Sources / Grounded badge below assistant message */}
            {msg.role === "assistant" && msg.grounded && (
              <div className="mt-1 flex flex-col items-start gap-1">
                <span className="text-[10px] font-medium text-emerald-400 flex items-center gap-1 bg-emerald-500/10 px-1.5 py-0.5 rounded border border-emerald-500/20">
                  <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>
                  Verified with web sources
                </span>
                
                {msg.sources && msg.sources.length > 0 && (
                  <details className="text-[10px] text-zinc-400 group cursor-pointer w-full max-w-sm mt-0.5">
                    <summary className="select-none hover:text-zinc-300 transition-colors list-none flex items-center gap-1">
                      <span className="group-open:rotate-90 transition-transform">▸</span> Show {msg.sources.length} sources
                    </summary>
                    <div className="flex flex-col gap-1.5 mt-1.5 pl-2 border-l border-zinc-700 pb-1">
                      {msg.sources.map(src => (
                        <a 
                          key={src.id} 
                          href={src.url} 
                          target="_blank" 
                          rel="noreferrer"
                          className="hover:bg-zinc-800/50 p-1.5 rounded transition-colors block border border-transparent hover:border-zinc-700"
                        >
                          <div className="font-medium text-blue-400 flex items-center gap-1 truncate">
                            <span className="text-zinc-500">[{src.id}]</span> {src.title}
                          </div>
                          {src.snippet && (
                            <div className="text-zinc-500 mt-0.5 truncate text-[9px]">{src.snippet}</div>
                          )}
                        </a>
                      ))}
                    </div>
                  </details>
                )}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Input — Exact Cobp structure (From Uiverse.io by Cobp) */}
      <div className="px-3 py-3 border-t dark:border-zinc-700 flex flex-col items-center gap-2">
        {/* Pending attachments preview */}
        {(pendingImages.length > 0 || pendingFiles.length > 0) && (
          <div className="flex flex-wrap gap-2 w-[300px] px-1">
            {pendingImages.map((img, i) => (
              <div key={`img-${i}`} className="relative group">
                <img src={`data:image/png;base64,${img}`} alt="pending" className="w-12 h-12 rounded object-cover border border-zinc-600" />
                <button onClick={() => removePendingImage(i)} className="absolute -top-1 -right-1 w-4 h-4 rounded-full bg-red-500 text-white text-[10px] flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">×</button>
              </div>
            ))}
            {pendingFiles.map((f, i) => (
              <div key={`file-${i}`} className="relative group flex items-center gap-1 bg-zinc-700 rounded px-2 py-1 text-xs text-zinc-300">
                📄 {f.name.length > 15 ? f.name.slice(0, 12) + "..." : f.name}
                <button onClick={() => removePendingFile(i)} className="ml-1 text-red-400 hover:text-red-300">×</button>
              </div>
            ))}
          </div>
        )}
        {/* Hidden file inputs */}
        <input ref={imageInputRef} type="file" accept="image/*" multiple className="hidden" onChange={handleImageUpload} />
        <input ref={fileInputRef} type="file" multiple className="hidden" onChange={handleFileUpload} />
        <div className="container-ia-chat">
          <input
            type="checkbox"
            id={voiceCheckboxId}
            className="input-voice"
            checked={listening}
            onChange={() => {}}
          />
          <input
            className="input-text"
            type="text"
            required
            placeholder="Message..."
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === "Enter" && sendMessage()}
            disabled={streaming}
          />
          <div className="container-upload-files">
            <svg className="upload-file" style={{ cursor: "default", opacity: 0.4 }} xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><path d="M8 14s1.5 2 4 2 4-2 4-2"/><line x1="9" y1="9" x2="9.01" y2="9"/><line x1="15" y1="9" x2="15.01" y2="9"/></svg>
            <svg className="upload-file" onClick={() => imageInputRef.current?.click()} style={{ cursor: "pointer" }} xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/></svg>
            <svg className="upload-file" onClick={() => fileInputRef.current?.click()} style={{ cursor: "pointer" }} xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21.44 11.05l-9.19 9.19a6 6 0 01-8.49-8.49l9.19-9.19a4 4 0 015.66 5.66l-9.2 9.19a2 2 0 01-2.83-2.83l8.49-8.48"/></svg>
          </div>
          <label className="label-files">
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
          </label>
          <label onClick={toggleListening} className="label-voice">
            <svg className="icon-voice" xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24"><path fill="none" stroke="currentColor" strokeLinecap="round" strokeWidth="2" d="M12 4v16m4-13v10M8 7v10m12-6v2M4 11v2" /></svg>
            <AIOrb />
            <div className="text-voice">
              <p>{streaming ? "Thinking..." : "Listening..."}</p>
              <p>tap to stop</p>
            </div>
          </label>
          <button className="label-text" onClick={sendMessage} type="button">
            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24"><path fill="none" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="m5 12l7-7l7 7m-7 7V5" /></svg>
          </button>
        </div>
      </div>
    </div>
  );
}
