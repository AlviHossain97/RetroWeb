import { useState, useCallback, useRef } from "react";
import { KOKORO_BASE, STT_BASE } from "./constants";
import type { VoiceState } from "./constants";
import type { TTSSession } from "./useChatSend";
import { checkAndUnlock } from "../../lib/achievements";

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

  const constraints: ExtendedAudioConstraints = {
    echoCancellation: true,
    noiseSuppression: true,
    autoGainControl: true,
    channelCount: 1,
    sampleRate: 16000,
  };

  if (supported.voiceIsolation) constraints.voiceIsolation = true;
  if (supported.suppressLocalAudioPlayback) constraints.suppressLocalAudioPlayback = true;

  return constraints;
}

function sanitizeForTTS(text: string): string {
  return text
    .replace(/\*{1,3}([^*]+)\*{1,3}/g, "$1")
    .replace(/_{1,3}([^_]+)_{1,3}/g, "$1")
    .replace(/~~([^~]+)~~/g, "$1")
    .replace(/`([^`]+)`/g, "$1")
    .replace(/^#{1,6}\s+/gm, "")
    .replace(/^[\-*+]\s+/gm, "")
    .replace(/^\d+\.\s+/gm, "")
    .replace(/\[([^\]]+)\]\([^)]+\)/g, "$1")
    .replace(/```[\s\S]*?```/g, "")
    .replace(/\p{Emoji_Presentation}/gu, "")
    .replace(/\p{Extended_Pictographic}/gu, "")
    .replace(/\s{2,}/g, " ")
    .trim();
}

export function useChatVoice(opts: {
  kokoroOnline: boolean;
  onTranscript: (text: string) => void;
}) {
  const { kokoroOnline, onTranscript } = opts;
  const [voiceState, setVoiceState] = useState<VoiceState>("idle");
  const [voiceError, setVoiceError] = useState<string | null>(null);

  // Settings
  const [voiceEnabled, setVoiceEnabled] = useState(true);
  const [activationMode, setActivationMode] = useState<"auto_near_field" | "headset" | "push_to_talk">("auto_near_field");
  const [noiseSuppressionEnabled, setNoiseSuppressionEnabled] = useState(true);
  const [echoCancellationEnabled, setEchoCancellationEnabled] = useState(true);
  const [agcEnabled, setAgcEnabled] = useState(true);

  // Refs
  const voiceModeRef = useRef(false);
  const ttsPlayingRef = useRef(false);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const startRecRef = useRef<() => void>(() => {});

  // STT
  const transcribeChunk = useCallback(async (blob: Blob): Promise<string> => {
    const form = new FormData();
    form.append("file", blob, "audio.webm");
    form.append("model", "nvidia/parakeet-tdt-0.6b-v2");
    const res = await fetch(`${STT_BASE}/v1/audio/transcriptions`, { method: "POST", body: form });
    if (!res.ok) return "";
    const data = await res.json();
    return (data.text || "").trim();
  }, []);

  // Start recording a single utterance, transcribe, send, loop
  const startListeningLoop = useCallback(async () => {
    if (!voiceModeRef.current) return;

    try {
      // Get mic stream (reuse if already open)
      if (!mediaStreamRef.current) {
        const baseConstraints = buildVoiceCaptureConstraints();
        baseConstraints.noiseSuppression = noiseSuppressionEnabled;
        baseConstraints.autoGainControl = agcEnabled;
        baseConstraints.echoCancellation = echoCancellationEnabled;
        mediaStreamRef.current = await navigator.mediaDevices.getUserMedia({ audio: baseConstraints, video: false });
      }

      // Verify the stream is still active
      if (!mediaStreamRef.current.active || mediaStreamRef.current.getAudioTracks().every(t => t.readyState === "ended")) {
        const baseConstraints = buildVoiceCaptureConstraints();
        baseConstraints.noiseSuppression = noiseSuppressionEnabled;
        baseConstraints.autoGainControl = agcEnabled;
        baseConstraints.echoCancellation = echoCancellationEnabled;
        mediaStreamRef.current = await navigator.mediaDevices.getUserMedia({ audio: baseConstraints, video: false });
      }

      // AudioContext for silence detection
      const audioCtx = new AudioContext();
      const source = audioCtx.createMediaStreamSource(mediaStreamRef.current);
      const analyser = audioCtx.createAnalyser();
      analyser.fftSize = 512;
      source.connect(analyser);
      const dataArray = new Uint8Array(analyser.frequencyBinCount);

      const mimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus")
        ? "audio/webm;codecs=opus"
        : MediaRecorder.isTypeSupported("audio/webm")
          ? "audio/webm"
          : "";
      const recorder = new MediaRecorder(mediaStreamRef.current, mimeType ? { mimeType } : undefined);
      mediaRecorderRef.current = recorder;
      const chunks: Blob[] = [];
      recorder.ondataavailable = (e) => { if (e.data.size > 0) chunks.push(e.data); };

      const { blob: audioBlob } = await new Promise<{ blob: Blob; peakEnergy: number }>((resolve) => {
        let _peakEnergy = 0;
        recorder.onstop = () => {
          audioCtx.close();
          const blob = new Blob(chunks, { type: mimeType || "audio/webm" });
          resolve({ blob, peakEnergy: _peakEnergy });
        };
        recorder.onerror = () => {
          audioCtx.close();
          resolve({ blob: new Blob([], { type: "audio/webm" }), peakEnergy: 0 });
        };
        recorder.start(250);

        let speechDetected = false;
        let silenceStart = 0;
        let consecutiveSpeechMs = 0;
        let consecutiveSilenceMs = 0;
        let noiseFloor = 10;

        const SILENCE_DURATION = 1500;
        const MIN_SPEECH_DURATION = activationMode === "headset" ? 300 : 500;
        const TARGET_SNR_MARGIN = activationMode === "headset" ? 1.4 : 2.5;
        const MIN_ABSOLUTE_ENERGY = 15;
        const MAX_DURATION = 30000;

        const startTime = Date.now();
        let lastFrameTime = performance.now();

        const checkSilence = () => {
          if (recorder.state !== "recording") return;
          if (!voiceModeRef.current) { recorder.stop(); return; }
          const now = Date.now();
          const pNow = performance.now();
          const dt = pNow - lastFrameTime;
          lastFrameTime = pNow;

          if (now - startTime > MAX_DURATION) {
            recorder.stop();
            return;
          }

          analyser.getByteFrequencyData(dataArray);

          const binStart = 10;
          const binEnd = 109;
          let speechBandEnergy = 0;
          for (let i = binStart; i <= binEnd; i++) {
            speechBandEnergy += dataArray[i];
          }
          speechBandEnergy /= (binEnd - binStart + 1);

          const smoothingFactor = 0.03;
          if (!speechDetected) {
            noiseFloor = (noiseFloor * (1 - smoothingFactor)) + (speechBandEnergy * smoothingFactor);
          }

          const snrRatio = noiseFloor > 0 ? speechBandEnergy / noiseFloor : 1;
          const isCurrentFrameSpeech = speechBandEnergy >= MIN_ABSOLUTE_ENERGY && snrRatio >= TARGET_SNR_MARGIN;

          if (isCurrentFrameSpeech) {
            consecutiveSpeechMs += dt;
            consecutiveSilenceMs = 0;
            if (speechBandEnergy > _peakEnergy) _peakEnergy = speechBandEnergy;
          } else {
            consecutiveSilenceMs += dt;
            consecutiveSpeechMs = 0;
          }

          if (!speechDetected && consecutiveSpeechMs > MIN_SPEECH_DURATION) {
            speechDetected = true;
            silenceStart = 0;
          }

          if (speechDetected && !isCurrentFrameSpeech) {
            if (!silenceStart) silenceStart = now;
            else if (now - silenceStart > SILENCE_DURATION) {
              recorder.stop();
              return;
            }
          } else if (speechDetected && isCurrentFrameSpeech) {
            silenceStart = 0;
          }

          requestAnimationFrame(checkSilence);
        };
        requestAnimationFrame(checkSilence);
      });

      if (!voiceModeRef.current) return;

      // Pre-STT size rejection
      const MIN_BYTES = activationMode === "headset" ? 2000 : 4000;
      if (audioBlob.size < MIN_BYTES) {
        if (voiceModeRef.current && !ttsPlayingRef.current) startRecRef.current();
        return;
      }

      setVoiceState("processing");
      const transcript = await transcribeChunk(audioBlob);

      if (!transcript || !voiceModeRef.current) {
        setVoiceState("listening");
        if (voiceModeRef.current && !ttsPlayingRef.current) startRecRef.current();
        return;
      }

      // Post-STT quality validation
      const words = transcript.trim().split(/\s+/);
      const isTooShort = words.length < 2 && transcript.length < 5;
      const validShortWords = ["yes", "no", "stop", "pause", "play", "skip"];
      const isAllowedShort = validShortWords.includes(transcript.toLowerCase().replace(/[^a-z]/g, ""));

      if (isTooShort && !isAllowedShort && activationMode !== "headset") {
        setVoiceState("listening");
        if (voiceModeRef.current && !ttsPlayingRef.current) startRecRef.current();
        return;
      }

      onTranscript(transcript);
    } catch (err) {
      console.error("[VOICE] Pipeline error:", err);
      setVoiceState("error");
      setVoiceError("Voice pipeline error. Check microphone permissions.");
      if (voiceModeRef.current) {
        setTimeout(() => startRecRef.current(), 1000);
      }
    }
  }, [transcribeChunk, activationMode, noiseSuppressionEnabled, agcEnabled, echoCancellationEnabled, onTranscript]);

  // Keep ref in sync
  startRecRef.current = startListeningLoop;

  const toggleListening = useCallback(() => {
    if (voiceModeRef.current) {
      // Stop voice mode
      voiceModeRef.current = false;
      setVoiceState("idle");
      setVoiceError(null);
      mediaRecorderRef.current?.stop();
      mediaRecorderRef.current = null;
      mediaStreamRef.current?.getTracks().forEach(t => t.stop());
      mediaStreamRef.current = null;
    } else {
      // Start voice mode
      voiceModeRef.current = true;
      setVoiceState("listening");
      void checkAndUnlock("voice_mode");
      startRecRef.current();
    }
  }, []);

  const dismissError = useCallback(() => {
    setVoiceState("idle");
    setVoiceError(null);
  }, []);

  // TTS Session Factory
  const createTTSSession = useCallback((): TTSSession | null => {
    if (!kokoroOnline || !voiceEnabled) return null;

    const audioQueue: Promise<HTMLAudioElement | null>[] = [];
    let playChain = Promise.resolve();

    const muteMic = (mute: boolean) => {
      mediaStreamRef.current?.getAudioTracks().forEach(t => { t.enabled = !mute; });
    };

    const fetchAudio = (text: string): Promise<HTMLAudioElement | null> => {
      const cleaned = sanitizeForTTS(text);
      if (!cleaned) return Promise.resolve(null);
      return fetch(`${KOKORO_BASE}/v1/audio/speech`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ model: "kokoro", input: cleaned, voice: "af_heart", speed: 1.2, response_format: "mp3" }),
      }).then(res => {
        if (!res.ok) return null;
        return res.blob().then(blob => new Audio(URL.createObjectURL(blob)));
      }).catch(() => null);
    };

    const playAudio = (audio: HTMLAudioElement): Promise<void> => {
      return new Promise<void>(resolve => {
        audio.onended = () => resolve();
        audio.onerror = () => resolve();
        audio.play().catch(() => resolve());
      });
    };

    return {
      flush(text: string) {
        if (!ttsPlayingRef.current) {
          ttsPlayingRef.current = true;
          setVoiceState("speaking");
          muteMic(true);
        }
        const audioPromise = fetchAudio(text);
        audioQueue.push(audioPromise);
        playChain = playChain.then(() =>
          audioPromise.then(audio => audio ? playAudio(audio) : undefined)
        );
      },
      async finish() {
        await playChain.catch(() => {});
        ttsPlayingRef.current = false;
        muteMic(false);
        setVoiceState("listening");
        if (voiceModeRef.current) {
          startRecRef.current();
        }
      },
      cancel() {
        ttsPlayingRef.current = false;
        muteMic(false);
        if (voiceModeRef.current) {
          setVoiceState("listening");
          startRecRef.current();
        }
      },
      isPlaying() {
        return ttsPlayingRef.current;
      },
    };
  }, [kokoroOnline, voiceEnabled]);

  return {
    voiceState,
    voiceError,
    toggleListening,
    dismissError,
    voiceEnabled, setVoiceEnabled,
    activationMode, setActivationMode,
    noiseSuppressionEnabled, setNoiseSuppressionEnabled,
    echoCancellationEnabled, setEchoCancellationEnabled,
    agcEnabled, setAgcEnabled,
    createTTSSession,
    // Expose ref for external coordination
    voiceModeRef,
  };
}
