import { useState, useRef, useEffect, useCallback } from "react";

interface Message {
  role: "user" | "assistant";
  content: string;
  images?: string[]; // base64 encoded images
}

const OLLAMA_BASE = "http://localhost:11434";
const KOKORO_BASE = "http://localhost:8787";

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

export default function Chat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [ollamaOnline, setOllamaOnline] = useState(false);
  const [kokoroOnline, setKokoroOnline] = useState(false);
  const selectedModel = "llava:7b";
  const [voiceEnabled, setVoiceEnabled] = useState(true);
  const [listening, setListening] = useState(false);
  const [pendingImages, setPendingImages] = useState<string[]>([]); // base64 images
  const [pendingFiles, setPendingFiles] = useState<{ name: string; content: string }[]>([]); // text files
  const chatDisplayRef = useRef<HTMLDivElement>(null);
  const imageInputRef = useRef<HTMLInputElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const voiceCheckboxId = useRef(`voice-${Math.random().toString(36).slice(2)}`).current;
  const voiceModeRef = useRef(false);
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
        const tagsRes = await fetch(`${OLLAMA_BASE}/api/tags`, { signal: AbortSignal.timeout(3000) });
        if (!cancelled) setOllamaOnline(tagsRes.ok);
      } catch { if (!cancelled) setOllamaOnline(false); }
      try {
        const kRes = await fetch(`${KOKORO_BASE}/health`, { signal: AbortSignal.timeout(3000) });
        if (!cancelled) setKokoroOnline(kRes.ok);
      } catch { if (!cancelled) setKokoroOnline(false); }
    };
    check();
    const interval = setInterval(check, 15000);
    return () => { cancelled = true; clearInterval(interval); };
  }, []);

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
  const speakChunk = useCallback(async (text: string): Promise<void> => {
    if (!kokoroOnline || !voiceEnabled || !text.trim()) return;
    try {
      const res = await fetch(`${KOKORO_BASE}/tts`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text, voice: "af_heart", speed: 1.2 }),
      });
      if (res.ok) {
        const blob = await res.blob();
        const audio = new Audio(URL.createObjectURL(blob));
        await new Promise<void>((resolve) => {
          audio.onended = () => resolve();
          audio.onerror = () => resolve();
          audio.play().catch(() => resolve());
        });
      }
    } catch { /* silent fail */ }
  }, [kokoroOnline, voiceEnabled]);

  // Speak full text (legacy, for non-streaming use)
  const speak = speakChunk;

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
    if (streaming || !ollamaOnline || !selectedModel) return;
    if (!directText) {
      setInput("");
      setPendingImages([]);
      setPendingFiles([]);
    }
    const userMsg: Message = { role: "user", content: text, images: images && images.length > 0 ? images : undefined };
    const assistantMsg: Message = { role: "assistant", content: "" };
    setMessages(prev => [...prev, userMsg, assistantMsg]);
    setStreaming(true);

    // TTS queue for sentence-level streaming in voice mode
    const isVoice = voiceModeRef.current && voiceEnabled;
    const ttsQueue: Promise<void>[] = [];
    let sentenceBuffer = "";
    const SENTENCE_END = /[.!?]\s*$/;

    const flushSentence = (force?: boolean) => {
      const trimmed = sentenceBuffer.trim();
      if (!trimmed || !isVoice) return;
      if (force || SENTENCE_END.test(trimmed)) {
        const toSpeak = trimmed;
        sentenceBuffer = "";
        const prev = ttsQueue[ttsQueue.length - 1] || Promise.resolve();
        ttsQueue.push(prev.then(() => speakChunk(toSpeak)));
      }
    };

    try {
      const res = await fetch(`${OLLAMA_BASE}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          model: selectedModel,
          messages: [...messages, userMsg].map(m => {
            const msg: Record<string, unknown> = { role: m.role, content: m.content };
            if (m.images && m.images.length > 0) msg.images = m.images;
            return msg;
          }),
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
                updated[updated.length - 1] = { role: "assistant", content: full };
                return updated;
              });
              flushSentence();
            }
          } catch { /* skip malformed */ }
        }
      }

      // Flush any remaining text
      flushSentence(true);

      // Wait for all TTS to finish before resuming listening
      if (ttsQueue.length > 0) {
        await ttsQueue[ttsQueue.length - 1];
      }

      if (voiceModeRef.current) {
        startRecRef.current();
      }
    } catch {
      setMessages(prev => {
        const updated = [...prev];
        updated[updated.length - 1] = { role: "assistant", content: "Sorry, I couldn't connect to the AI. Make sure Ollama is running." };
        return updated;
      });
      if (voiceModeRef.current) {
        startRecRef.current();
      }
    } finally {
      setStreaming(false);
    }
  }, [input, streaming, ollamaOnline, selectedModel, messages, speakChunk, voiceEnabled, pendingImages, pendingFiles]);

  const sendMessage = useCallback(() => { sendMessageDirect(); }, [sendMessageDirect]);

  // Whisper STT: record audio chunk, send to /stt, get transcript
  const transcribeChunk = useCallback(async (blob: Blob): Promise<string> => {
    const form = new FormData();
    form.append("audio", blob, "audio.wav");
    const res = await fetch(`${KOKORO_BASE}/stt`, { method: "POST", body: form });
    if (!res.ok) return "";
    const data = await res.json();
    return (data.text || "").trim();
  }, []);

  // Start recording a single utterance, transcribe, send, speak, loop
  const startListeningLoop = useCallback(async () => {
    if (!voiceModeRef.current) return;

    try {
      // Get mic stream (reuse if already open)
      if (!mediaStreamRef.current) {
        mediaStreamRef.current = await navigator.mediaDevices.getUserMedia({ audio: true });
      }
      const stream = mediaStreamRef.current;

      // Use AudioContext for silence detection
      const audioCtx = new AudioContext();
      const source = audioCtx.createMediaStreamSource(stream);
      const analyser = audioCtx.createAnalyser();
      analyser.fftSize = 512;
      source.connect(analyser);
      const dataArray = new Uint8Array(analyser.frequencyBinCount);

      const recorder = new MediaRecorder(stream, { mimeType: "audio/webm;codecs=opus" });
      mediaRecorderRef.current = recorder;
      const chunks: Blob[] = [];
      recorder.ondataavailable = (e) => { if (e.data.size > 0) chunks.push(e.data); };

      const audioBlob = await new Promise<Blob>((resolve) => {
        recorder.onstop = () => {
          audioCtx.close();
          resolve(new Blob(chunks, { type: "audio/webm" }));
        };
        recorder.start(100);

        let speechDetected = false;
        let silenceStart = 0;
        const SILENCE_THRESHOLD = 5; // frequency avg below this = silence
        const SILENCE_DURATION = 1500; // ms of silence after speech before auto-stop
        const MIN_SPEECH_DURATION = 500; // minimum recording time before silence can stop
        const MAX_DURATION = 15000; // hard cap
        const startTime = Date.now();
        let logCounter = 0;

        const checkSilence = () => {
          if (recorder.state !== "recording") return;
          if (!voiceModeRef.current) { recorder.stop(); return; }
          if (Date.now() - startTime > MAX_DURATION) {
            console.log("[Voice] Max duration reached, stopping");
            recorder.stop();
            return;
          }

          analyser.getByteFrequencyData(dataArray);
          const avg = dataArray.reduce((a, b) => a + b, 0) / dataArray.length;

          // Log every ~30 frames (~0.5s) for debugging
          if (logCounter++ % 30 === 0) {
            console.log(`[Voice] avg=${avg.toFixed(1)} speechDetected=${speechDetected} elapsed=${Date.now() - startTime}ms`);
          }

          if (avg > SILENCE_THRESHOLD) {
            speechDetected = true;
            silenceStart = 0;
          } else if (speechDetected && (Date.now() - startTime > MIN_SPEECH_DURATION)) {
            if (!silenceStart) silenceStart = Date.now();
            else if (Date.now() - silenceStart > SILENCE_DURATION) {
              console.log("[Voice] Silence detected after speech, stopping");
              recorder.stop();
              return;
            }
          }
          requestAnimationFrame(checkSilence);
        };
        requestAnimationFrame(checkSilence);
      });

      if (!voiceModeRef.current) return;

      // Transcribe with Whisper
      console.log(`[Voice] Sending ${audioBlob.size} bytes to STT`);
      const transcript = await transcribeChunk(audioBlob);
      console.log(`[Voice] Transcript: "${transcript}"`);

      if (!transcript || !voiceModeRef.current) {
        console.log("[Voice] Empty transcript or voice mode off, restarting loop");
        if (voiceModeRef.current) startRecRef.current();
        return;
      }

      // Send to AI
      console.log(`[Voice] Sending to AI: "${transcript}"`);
      sendDirectRef.current(transcript);
    } catch (err) {
      console.error("[Whisper] Error:", err);
      if (voiceModeRef.current) {
        setTimeout(() => startRecRef.current(), 1000);
      }
    }
  }, [transcribeChunk]);

  // Keep refs in sync
  sendDirectRef.current = (text: string) => sendMessageDirect(text);
  startRecRef.current = startListeningLoop;

  // Toggle voice mode
  const toggleListening = useCallback(() => {
    if (voiceModeRef.current) {
      // Stop voice mode
      voiceModeRef.current = false;
      setListening(false);
      mediaRecorderRef.current?.stop();
      mediaRecorderRef.current = null;
      // Release mic
      mediaStreamRef.current?.getTracks().forEach(t => t.stop());
      mediaStreamRef.current = null;
    } else {
      // Start voice mode
      voiceModeRef.current = true;
      setListening(true);
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

      {/* Header */}
      <div className="px-4 py-3 border-b dark:border-zinc-700">
        <div className="flex justify-between items-center">
          <h2 className="text-lg font-semibold text-zinc-800 dark:text-white">
            RetroWeb AI
          </h2>
          <div className="flex items-center gap-2">
            {messages.length > 0 && (
              <button
                onClick={() => setMessages([])}
                className="text-xs px-2 py-1 rounded-full bg-zinc-600 text-zinc-300 hover:bg-red-600 hover:text-white transition-colors"
                title="Clear chat"
              >
                🗑️
              </button>
            )}
            <button
              onClick={() => setVoiceEnabled(v => !v)}
              className={`text-xs px-2 py-1 rounded-full ${voiceEnabled ? "bg-purple-500 text-white" : "bg-zinc-600 text-zinc-300"}`}
            >
              {voiceEnabled ? "🔊" : "🔇"}
            </button>
            <div className={`${statusColor} text-white text-xs px-2 py-1 rounded-full`}>
              {statusText}
            </div>
          </div>
        </div>
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
          <div
            key={i}
            className={`chat-message max-w-md rounded-lg px-3 py-1.5 text-sm ${
              msg.role === "user"
                ? "self-start bg-zinc-500 text-white"
                : "self-end bg-blue-500 text-white"
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
