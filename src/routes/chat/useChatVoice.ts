import { useState, useCallback, useRef, useEffect } from "react";
import { KOKORO_BASE, PISTATION_API, STT_BASE } from "./constants";
import type { VoiceState } from "./constants";
import type { TTSSession } from "./useChatSend";
import { checkAndUnlock } from "../../lib/achievements";

function logVoiceStage(stage: string, detail?: string) {
  if (detail) {
    console.log(`[VOICE] ${stage} —`, detail);
  } else {
    console.log(`[VOICE] ${stage}`);
  }
  fetch(`${PISTATION_API}/ai/voice-stage`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ stage, detail: detail ?? null }),
    keepalive: true,
  }).catch(() => {});
}

export type ActivationMode = "auto_near_field" | "headset" | "push_to_talk";

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
  const [voiceModeActive, setVoiceModeActive] = useState(false);

  // Settings
  const [voiceEnabled, setVoiceEnabled] = useState(true);
  const [activationMode, setActivationMode] = useState<ActivationMode>("auto_near_field");
  const [noiseSuppressionEnabled, setNoiseSuppressionEnabled] = useState(true);
  const [echoCancellationEnabled, setEchoCancellationEnabled] = useState(true);
  const [agcEnabled, setAgcEnabled] = useState(true);

  // Refs
  const voiceModeRef = useRef(false);
  const ttsPlayingRef = useRef(false);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const startRecRef = useRef<() => void>(() => {});
  const retryTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const retryCountRef = useRef(0);
  const pttSourceRef = useRef<"keyboard" | "pointer" | null>(null);
  const activationModeRef = useRef<ActivationMode>(activationMode);
  const audioCtxRef = useRef<AudioContext | null>(null);

  // Keep refs in sync with state
  activationModeRef.current = activationMode;

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

  // Core recording loop — handles both continuous (near-field/headset) and PTT modes
  const startListeningLoop = useCallback(async () => {
    if (!voiceModeRef.current) return;
    logVoiceStage("recording_start", `mode=${activationModeRef.current}`);
    retryCountRef.current = 0;

    try {
      // Get mic stream (reuse if already open)
      if (!mediaStreamRef.current) {
        const baseConstraints = buildVoiceCaptureConstraints();
        baseConstraints.noiseSuppression = noiseSuppressionEnabled;
        baseConstraints.autoGainControl = agcEnabled;
        baseConstraints.echoCancellation = echoCancellationEnabled;
        mediaStreamRef.current = await navigator.mediaDevices.getUserMedia({ audio: baseConstraints, video: false });
      }

      // Bail if cancelled during getUserMedia (e.g., PTT release during permission dialog)
      if (!voiceModeRef.current) {
        mediaStreamRef.current?.getTracks().forEach(t => t.stop());
        mediaStreamRef.current = null;
        setVoiceModeActive(false);
        setVoiceState("idle");
        return;
      }

      // Verify the stream is still active
      if (!mediaStreamRef.current.active || mediaStreamRef.current.getAudioTracks().every(t => t.readyState === "ended")) {
        const baseConstraints = buildVoiceCaptureConstraints();
        baseConstraints.noiseSuppression = noiseSuppressionEnabled;
        baseConstraints.autoGainControl = agcEnabled;
        baseConstraints.echoCancellation = echoCancellationEnabled;
        mediaStreamRef.current = await navigator.mediaDevices.getUserMedia({ audio: baseConstraints, video: false });
      }

      // AudioContext for silence detection — reuse across recordings
      if (!audioCtxRef.current || audioCtxRef.current.state === "closed") {
        audioCtxRef.current = new AudioContext();
      }
      const audioCtx = audioCtxRef.current;
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
          source.disconnect();
          analyser.disconnect();
          const blob = new Blob(chunks, { type: mimeType || "audio/webm" });
          resolve({ blob, peakEnergy: _peakEnergy });
        };
        recorder.onerror = () => {
          source.disconnect();
          analyser.disconnect();
          resolve({ blob: new Blob([], { type: "audio/webm" }), peakEnergy: 0 });
        };
        recorder.start(250);

        let speechDetected = false;
        let silenceStart = 0;
        let consecutiveSpeechMs = 0;
        let consecutiveSilenceMs = 0;
        let noiseFloor = 10;

        const isPTT = activationModeRef.current === "push_to_talk";
        const SILENCE_DURATION = 1500;
        const MIN_SPEECH_DURATION = isPTT ? 1500 : (activationModeRef.current === "headset" ? 300 : 500);
        const TARGET_SNR_MARGIN = activationModeRef.current === "headset" ? 1.4 : 2.5;
        const MIN_ABSOLUTE_ENERGY = 15;
        const MAX_DURATION = 30000;

        const startTime = Date.now();
        let lastFrameTime = performance.now();
        let lastDebugLog = 0;

        const checkSilence = () => {
          if (recorder.state !== "recording") return;
          if (!voiceModeRef.current) {
            if (recorder.state === "recording") recorder.stop();
            return;
          }
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
          // Only adapt the noise floor during quiet frames — otherwise it chases the voice
          if (!speechDetected && speechBandEnergy < 25) {
            noiseFloor = (noiseFloor * (1 - smoothingFactor)) + (speechBandEnergy * smoothingFactor);
          }

          const snrRatio = noiseFloor > 0 ? speechBandEnergy / noiseFloor : 1;
          const LOUD_ENERGY_BYPASS = 60;
          const isCurrentFrameSpeech =
            (speechBandEnergy >= MIN_ABSOLUTE_ENERGY && snrRatio >= TARGET_SNR_MARGIN) ||
            speechBandEnergy >= LOUD_ENERGY_BYPASS;

          if (pNow - lastDebugLog > 500) {
            lastDebugLog = pNow;
            console.log(`[VOICE-DBG] energy=${speechBandEnergy.toFixed(1)} floor=${noiseFloor.toFixed(1)} snr=${snrRatio.toFixed(2)} speech=${isCurrentFrameSpeech} detected=${speechDetected}`);
          }

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

      // After recording stops, check if we should still process
      if (!voiceModeRef.current && activationModeRef.current !== "push_to_talk") {
        return;
      }

      // Pre-STT size rejection
      const isPTTNow = activationModeRef.current === "push_to_talk";
      const MIN_BYTES = isPTTNow ? 2000 : (activationModeRef.current === "headset" ? 2000 : 4000);
      if (audioBlob.size < MIN_BYTES) {
        logVoiceStage("audio_rejected", `${audioBlob.size}B < ${MIN_BYTES}B min — looping`);
        if (isPTTNow) {
          voiceModeRef.current = false;
          pttSourceRef.current = null;
          setVoiceModeActive(false);
          setVoiceState("idle");
        } else if (voiceModeRef.current && !ttsPlayingRef.current) {
          startRecRef.current();
        }
        return;
      }
      logVoiceStage("recording_done", `${audioBlob.size} bytes`);

      setVoiceState("processing");
      logVoiceStage("transcribing", `${audioBlob.size} bytes`);
      const transcript = await transcribeChunk(audioBlob);
      if (transcript) logVoiceStage("transcribed", transcript);

      if (!transcript) {
        if (isPTTNow || !voiceModeRef.current) {
          voiceModeRef.current = false;
          pttSourceRef.current = null;
          setVoiceModeActive(false);
          setVoiceState("idle");
        } else {
          setVoiceState("listening");
          if (voiceModeRef.current && !ttsPlayingRef.current) startRecRef.current();
        }
        return;
      }

      // Post-STT quality validation (skip for PTT — user explicitly spoke)
      if (!isPTTNow) {
        const words = transcript.trim().split(/\s+/);
        const isTooShort = words.length < 2 && transcript.length < 5;
        const validShortWords = ["yes", "no", "stop", "pause", "play", "skip"];
        const isAllowedShort = validShortWords.includes(transcript.toLowerCase().replace(/[^a-z]/g, ""));

        if (isTooShort && !isAllowedShort && activationModeRef.current !== "headset") {
          setVoiceState("listening");
          if (voiceModeRef.current && !ttsPlayingRef.current) startRecRef.current();
          return;
        }
      }

      logVoiceStage("ai_receiving", transcript);
      onTranscript(transcript);

      // For PTT, clean up after sending
      if (isPTTNow) {
        voiceModeRef.current = false;
        pttSourceRef.current = null;
        setVoiceModeActive(false);
        if (mediaStreamRef.current) {
          mediaStreamRef.current.getTracks().forEach(t => t.stop());
          mediaStreamRef.current = null;
        }
        setVoiceState("idle");
      }
    } catch (err) {
      console.error("[VOICE] Pipeline error:", err);

      const name = err instanceof DOMException ? err.name : "";
      const isFatal =
        name === "NotFoundError" ||
        name === "NotAllowedError" ||
        name === "NotReadableError";

      if (retryTimeoutRef.current) {
        clearTimeout(retryTimeoutRef.current);
        retryTimeoutRef.current = null;
      }

      mediaRecorderRef.current = null;
      if (mediaStreamRef.current) {
        mediaStreamRef.current.getTracks().forEach(track => track.stop());
        mediaStreamRef.current = null;
      }

      setVoiceState("error");

      if (isFatal) {
        voiceModeRef.current = false;
        retryCountRef.current = 0;
        pttSourceRef.current = null;
        setVoiceModeActive(false);
        setVoiceError(
          name === "NotFoundError"
            ? "No microphone found. Connect a mic and try again."
            : name === "NotAllowedError"
            ? "Microphone access denied. Allow mic access in browser settings."
            : "Microphone is busy or unavailable. Close other apps using it and try again."
        );
        return;
      }

      if (voiceModeRef.current && retryCountRef.current < 1) {
        retryCountRef.current += 1;
        setVoiceError("Voice pipeline error. Retrying...");
        retryTimeoutRef.current = setTimeout(() => {
          startRecRef.current();
        }, 1000);
      } else {
        voiceModeRef.current = false;
        retryCountRef.current = 0;
        pttSourceRef.current = null;
        setVoiceModeActive(false);
        setVoiceError("Voice pipeline error. Please try again.");
      }
    }
  }, [transcribeChunk, noiseSuppressionEnabled, agcEnabled, echoCancellationEnabled, onTranscript]);

  // Keep ref in sync
  startRecRef.current = startListeningLoop;

  // --- Voice mode controls ---

  const startVoiceMode = useCallback(() => {
    if (voiceModeRef.current) return;
    voiceModeRef.current = true;
    pttSourceRef.current = null;
    setVoiceModeActive(true);
    setVoiceState("listening");
    setVoiceError(null);
    logVoiceStage("listening");
    void checkAndUnlock("voice_mode");
    startRecRef.current();
  }, []);

  const stopVoiceMode = useCallback(() => {
    voiceModeRef.current = false;
    pttSourceRef.current = null;
    setVoiceModeActive(false);
    setVoiceState("idle");
    setVoiceError(null);
    if (retryTimeoutRef.current) {
      clearTimeout(retryTimeoutRef.current);
      retryTimeoutRef.current = null;
    }
    retryCountRef.current = 0;
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === "recording") {
      mediaRecorderRef.current.stop();
    }
    mediaRecorderRef.current = null;
    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach(t => t.stop());
      mediaStreamRef.current = null;
    }
    if (audioCtxRef.current && audioCtxRef.current.state !== "closed") {
      audioCtxRef.current.close();
      audioCtxRef.current = null;
    }
  }, []);

  const startRecording = useCallback((source: "keyboard" | "pointer") => {
    if (voiceModeRef.current) return;
    if (voiceState !== "idle" && voiceState !== "error") return;
    pttSourceRef.current = source;
    voiceModeRef.current = true;
    setVoiceModeActive(true);
    setVoiceState("listening");
    setVoiceError(null);
    void checkAndUnlock("voice_mode");
    startRecRef.current();
  }, [voiceState]);

  const stopRecording = useCallback((source: "keyboard" | "pointer") => {
    if (pttSourceRef.current !== source) return;
    voiceModeRef.current = false;
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === "recording") {
      mediaRecorderRef.current.stop();
    }
  }, []);

  const dismissError = useCallback(() => {
    setVoiceModeActive(false);
    setVoiceState("idle");
    setVoiceError(null);
  }, []);

  const recoverAfterAssistantTurn = useCallback(() => {
    if (ttsPlayingRef.current) return;
    if (voiceModeRef.current) {
      setVoiceModeActive(true);
      setVoiceState("listening");
      startRecRef.current();
      return;
    }
    setVoiceModeActive(false);
    setVoiceState("idle");
  }, []);

  // Unmount cleanup
  useEffect(() => {
    return () => {
      voiceModeRef.current = false;
      if (retryTimeoutRef.current) {
        clearTimeout(retryTimeoutRef.current);
        retryTimeoutRef.current = null;
      }
      retryCountRef.current = 0;
      pttSourceRef.current = null;
      if (mediaRecorderRef.current) {
        if (mediaRecorderRef.current.state === "recording") {
          mediaRecorderRef.current.stop();
        }
        mediaRecorderRef.current = null;
      }
      if (mediaStreamRef.current) {
        mediaStreamRef.current.getTracks().forEach(t => t.stop());
        mediaStreamRef.current = null;
      }
      if (audioCtxRef.current && audioCtxRef.current.state !== "closed") {
        audioCtxRef.current.close();
        audioCtxRef.current = null;
      }
    };
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
        audio.onended = () => { URL.revokeObjectURL(audio.src); resolve(); };
        audio.onerror = () => { URL.revokeObjectURL(audio.src); resolve(); };
        audio.play().catch(() => { URL.revokeObjectURL(audio.src); resolve(); });
      });
    };

    return {
      flush(text: string) {
        if (!ttsPlayingRef.current) {
          ttsPlayingRef.current = true;
          setVoiceState("speaking");
          muteMic(true);
        }
        logVoiceStage("kokoro_speaking", text);
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
        if (voiceModeRef.current) {
          setVoiceModeActive(true);
          setVoiceState("listening");
          startRecRef.current();
        } else {
          setVoiceModeActive(false);
          setVoiceState("idle");
        }
      },
      cancel() {
        ttsPlayingRef.current = false;
        muteMic(false);
        if (voiceModeRef.current) {
          setVoiceModeActive(true);
          setVoiceState("listening");
          startRecRef.current();
        } else {
          setVoiceModeActive(false);
          setVoiceState("idle");
        }
      },
      isPlaying() {
        return ttsPlayingRef.current;
      },
    };
  }, [kokoroOnline, voiceEnabled]);

  return {
    voiceState,
    voiceModeActive,
    voiceError,
    startVoiceMode,
    stopVoiceMode,
    startRecording,
    stopRecording,
    dismissError,
    recoverAfterAssistantTurn,
    voiceEnabled, setVoiceEnabled,
    activationMode, setActivationMode,
    noiseSuppressionEnabled, setNoiseSuppressionEnabled,
    echoCancellationEnabled, setEchoCancellationEnabled,
    agcEnabled, setAgcEnabled,
    createTTSSession,
    voiceModeRef,
  };
}
