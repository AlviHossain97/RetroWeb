import { useCallback, useEffect, useRef, useState } from "react";
import { API_BASE } from "@/lib/api/client";
import { PISTATION_API, type Message, type VoiceState } from "./constants";
import type { TTSSession } from "./useChatSend";
import {
  VOICE_INPUT_CHUNK_MS,
  VOICE_INPUT_FORMAT,
  VOICE_INPUT_SAMPLE_RATE,
  buildVoiceConversationHistory,
  buildVoiceWsUrl,
  decodePcm16Base64,
  downsampleFloat32Buffer,
  appendFloat32Buffer,
  encodePcm16Base64,
  float32ToPcm16Bytes,
  pcm16ToFloat32,
  type VoiceGatewayCommand,
  type VoiceGatewayEvent,
  type VoiceSessionConfig,
} from "./voiceProtocol";
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

type TranscriptApi = {
  messages: Message[];
  appendUser: (msg: Message) => void;
  appendAssistant: (msg: Message) => void;
  patchLastAssistant: (patch: Partial<Message>) => void;
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

  const constraints: ExtendedAudioConstraints = {
    echoCancellation: true,
    noiseSuppression: true,
    autoGainControl: true,
    channelCount: 1,
    sampleRate: VOICE_INPUT_SAMPLE_RATE,
  };

  if (supported.voiceIsolation) constraints.voiceIsolation = true;
  if (supported.suppressLocalAudioPlayback) constraints.suppressLocalAudioPlayback = true;

  return constraints;
}

function energyForChunk(bytes: Uint8Array): number {
  const samples = new Int16Array(bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength));
  if (samples.length === 0) return 0;
  let total = 0;
  for (let i = 0; i < samples.length; i++) {
    total += Math.abs(samples[i]) / 32768;
  }
  return total / samples.length;
}

export function useChatVoice(opts: {
  voiceAvailable: boolean;
  selectedModel: string;
  transcript: TranscriptApi;
}) {
  const { voiceAvailable, selectedModel, transcript } = opts;
  const [voiceState, setVoiceState] = useState<VoiceState>("idle");
  const [voiceError, setVoiceError] = useState<string | null>(null);
  const [voiceModeActive, setVoiceModeActive] = useState(false);
  const [voiceEnabled, setVoiceEnabled] = useState(true);
  const [activationMode, setActivationMode] = useState<ActivationMode>("auto_near_field");
  const [noiseSuppressionEnabled, setNoiseSuppressionEnabled] = useState(true);
  const [echoCancellationEnabled, setEchoCancellationEnabled] = useState(true);
  const [agcEnabled, setAgcEnabled] = useState(true);
  const [liveTranscript, setLiveTranscript] = useState("");
  const [activeProvider, setActiveProvider] = useState<string | null>(null);

  const voiceModeRef = useRef(false);
  const activationModeRef = useRef<ActivationMode>(activationMode);
  const selectedModelRef = useRef(selectedModel);
  const messagesRef = useRef(transcript.messages);
  const wsRef = useRef<WebSocket | null>(null);
  const gatewayReadyRef = useRef(false);
  const reconnectingRef = useRef(false);
  const pttPressedRef = useRef(false);
  const inputStreamingRef = useRef(false);
  const sessionConfigRef = useRef<VoiceSessionConfig | null>(null);

  const mediaStreamRef = useRef<MediaStream | null>(null);
  const audioCtxRef = useRef<AudioContext | null>(null);
  const sourceNodeRef = useRef<MediaStreamAudioSourceNode | null>(null);
  const silentGainRef = useRef<GainNode | null>(null);
  const captureWorkletNodeRef = useRef<AudioWorkletNode | null>(null);
  const captureProcessorRef = useRef<ScriptProcessorNode | null>(null);
  const captureBufferRef = useRef<Float32Array>(new Float32Array(0));
  const sourceRateRef = useRef(VOICE_INPUT_SAMPLE_RATE);

  const playbackSourcesRef = useRef<Set<AudioBufferSourceNode>>(new Set());
  const playbackCursorRef = useRef(0);

  const speechDetectedRef = useRef(false);
  const speechMsRef = useRef(0);
  const silenceMsRef = useRef(0);
  const noiseFloorRef = useRef(0.008);
  const lastChunkAtRef = useRef<number | null>(null);

  const pendingAssistantRef = useRef(false);
  const assistantTextRef = useRef("");

  const handleGatewayEventRef = useRef<(event: VoiceGatewayEvent) => void>(() => {});
  const startInputStreamingRef = useRef<(source: "continuous" | "push_to_talk") => void>(() => {});
  const stopInputStreamingRef = useRef<() => void>(() => {});

  activationModeRef.current = activationMode;
  selectedModelRef.current = selectedModel;
  messagesRef.current = transcript.messages;

  const voiceApiBase = API_BASE || PISTATION_API;

  const dismissError = useCallback(() => {
    setVoiceError(null);
  }, []);

  const sendGatewayCommand = useCallback((command: VoiceGatewayCommand) => {
    const socket = wsRef.current;
    if (!socket || socket.readyState !== WebSocket.OPEN) return;
    socket.send(JSON.stringify(command));
  }, []);

  const syncGatewaySessionConfig = useCallback(() => {
    sendGatewayCommand({
      type: "session.configure",
      selected_model: selectedModelRef.current,
      activation_mode: activationModeRef.current,
      conversation_history: buildVoiceConversationHistory(messagesRef.current),
      client: {
        user_agent: navigator.userAgent,
        platform: navigator.platform,
      },
    });
  }, [sendGatewayCommand]);

  const stopPlayback = useCallback((sendCancel: boolean) => {
    if (sendCancel) {
      sendGatewayCommand({ type: "response.cancel" });
    }
    playbackSourcesRef.current.forEach((source) => {
      try {
        source.stop();
      } catch {
        // ignore already-stopped sources
      }
    });
    playbackSourcesRef.current.clear();

    const ctx = audioCtxRef.current;
    playbackCursorRef.current = ctx ? ctx.currentTime + 0.03 : 0;

    if (voiceModeRef.current) {
      setVoiceState(inputStreamingRef.current || activationModeRef.current !== "push_to_talk" ? "listening" : "idle");
    } else {
      setVoiceState("idle");
    }
  }, [sendGatewayCommand]);

  const resetTurnState = useCallback(() => {
    pendingAssistantRef.current = false;
    assistantTextRef.current = "";
    setLiveTranscript("");
    speechDetectedRef.current = false;
    speechMsRef.current = 0;
    silenceMsRef.current = 0;
  }, []);

  const stopInputStreaming = useCallback(() => {
    if (!inputStreamingRef.current) return;
    inputStreamingRef.current = false;
    sendGatewayCommand({ type: "input_audio.stop" });
    setVoiceState("processing");
  }, [sendGatewayCommand]);

  const startInputStreaming = useCallback((source: "continuous" | "push_to_talk") => {
    if (!voiceModeRef.current || !gatewayReadyRef.current || inputStreamingRef.current) return;
    stopPlayback(true);
    sendGatewayCommand({ type: "input_audio.start", source });
    inputStreamingRef.current = true;
    speechDetectedRef.current = true;
    speechMsRef.current = 0;
    silenceMsRef.current = 0;
    setVoiceState("listening");
  }, [sendGatewayCommand, stopPlayback]);

  startInputStreamingRef.current = startInputStreaming;
  stopInputStreamingRef.current = stopInputStreaming;

  const handlePcmChunk = useCallback((bytes: Uint8Array) => {
    if (!voiceModeRef.current || !gatewayReadyRef.current) return;

    const energy = energyForChunk(bytes);
    const now = performance.now();
    const dt = lastChunkAtRef.current ? now - lastChunkAtRef.current : VOICE_INPUT_CHUNK_MS;
    lastChunkAtRef.current = now;

    if (activationModeRef.current === "push_to_talk") {
      if (!inputStreamingRef.current) return;
      sendGatewayCommand({
        type: "input_audio.chunk",
        audio: encodePcm16Base64(bytes),
        sample_rate_hz: VOICE_INPUT_SAMPLE_RATE,
        format: VOICE_INPUT_FORMAT,
      });
      return;
    }

    const noiseThreshold = activationModeRef.current === "headset" ? 0.01 : 0.015;
    const snrMultiplier = activationModeRef.current === "headset" ? 1.7 : 2.2;
    if (!inputStreamingRef.current && energy < noiseThreshold * 1.5) {
      noiseFloorRef.current = (noiseFloorRef.current * 0.95) + (energy * 0.05);
    }
    const threshold = Math.max(noiseThreshold, noiseFloorRef.current * snrMultiplier);
    const isSpeech = energy >= threshold;

    if (!inputStreamingRef.current) {
      // While TTS is playing out the speakers, near-field mics pick it up as
      // "speech" and re-trigger a turn mid-reply. Suppress VAD until playback
      // drains so the assistant isn't transcribing its own voice.
      if (playbackSourcesRef.current.size > 0) {
        speechMsRef.current = 0;
        return;
      }
      if (isSpeech) {
        speechMsRef.current += dt;
        const minSpeech = activationModeRef.current === "headset" ? 120 : 180;
        if (speechMsRef.current >= minSpeech) {
          startInputStreamingRef.current("continuous");
          sendGatewayCommand({
            type: "input_audio.chunk",
            audio: encodePcm16Base64(bytes),
            sample_rate_hz: VOICE_INPUT_SAMPLE_RATE,
            format: VOICE_INPUT_FORMAT,
          });
        }
      } else {
        speechMsRef.current = Math.max(0, speechMsRef.current - dt);
      }
      return;
    }

    sendGatewayCommand({
      type: "input_audio.chunk",
      audio: encodePcm16Base64(bytes),
      sample_rate_hz: VOICE_INPUT_SAMPLE_RATE,
      format: VOICE_INPUT_FORMAT,
    });

    if (isSpeech) {
      speechDetectedRef.current = true;
      silenceMsRef.current = 0;
    } else if (speechDetectedRef.current) {
      silenceMsRef.current += dt;
      const silenceCutoff = activationModeRef.current === "headset" ? 900 : 1300;
      if (silenceMsRef.current >= silenceCutoff) {
        stopInputStreamingRef.current();
      }
    }
  }, [sendGatewayCommand]);

  const handleCaptureFloatChunk = useCallback((chunk: Float32Array) => {
    if (!voiceModeRef.current) return;
    const combined = appendFloat32Buffer(captureBufferRef.current, chunk);
    const sourceRate = sourceRateRef.current || VOICE_INPUT_SAMPLE_RATE;
    const requiredSamples = Math.max(256, Math.round(sourceRate * (VOICE_INPUT_CHUNK_MS / 1000)));

    let offset = 0;
    while ((combined.length - offset) >= requiredSamples) {
      const windowChunk = combined.slice(offset, offset + requiredSamples);
      const downsampled = downsampleFloat32Buffer(windowChunk, sourceRate, VOICE_INPUT_SAMPLE_RATE);
      const pcmBytes = float32ToPcm16Bytes(downsampled);
      handlePcmChunk(pcmBytes);
      offset += requiredSamples;
    }

    captureBufferRef.current = combined.slice(offset);
  }, [handlePcmChunk]);

  const ensureAudioPipeline = useCallback(async () => {
    if (!mediaStreamRef.current || !mediaStreamRef.current.active || mediaStreamRef.current.getAudioTracks().every((track) => track.readyState === "ended")) {
      const constraints = buildVoiceCaptureConstraints();
      constraints.noiseSuppression = noiseSuppressionEnabled;
      constraints.autoGainControl = agcEnabled;
      constraints.echoCancellation = echoCancellationEnabled;
      mediaStreamRef.current = await navigator.mediaDevices.getUserMedia({ audio: constraints, video: false });
    }

    if (!audioCtxRef.current || audioCtxRef.current.state === "closed") {
      audioCtxRef.current = new AudioContext();
    }

    const audioCtx = audioCtxRef.current;
    if (audioCtx.state === "suspended") {
      await audioCtx.resume().catch(() => {});
    }
    sourceRateRef.current = audioCtx.sampleRate;

    if (!silentGainRef.current) {
      silentGainRef.current = audioCtx.createGain();
      silentGainRef.current.gain.value = 0;
      silentGainRef.current.connect(audioCtx.destination);
    }

    if (!sourceNodeRef.current) {
      sourceNodeRef.current = audioCtx.createMediaStreamSource(mediaStreamRef.current);
    }

    if (captureWorkletNodeRef.current || captureProcessorRef.current) return;

    const onCaptureMessage = (value: Float32Array | ArrayBuffer) => {
      const chunk = value instanceof Float32Array ? value : new Float32Array(value);
      handleCaptureFloatChunk(chunk);
    };

    try {
      if (audioCtx.audioWorklet) {
        await audioCtx.audioWorklet.addModule("/audio-worklets/voice-capture-processor.js");
        const workletNode = new AudioWorkletNode(audioCtx, "voice-capture-processor");
        workletNode.port.onmessage = (event) => onCaptureMessage(event.data as Float32Array | ArrayBuffer);
        sourceNodeRef.current.connect(workletNode);
        workletNode.connect(silentGainRef.current);
        captureWorkletNodeRef.current = workletNode;
        return;
      }
    } catch (err) {
      console.warn("[VOICE] AudioWorklet unavailable, falling back to ScriptProcessorNode", err);
    }

    const processor = audioCtx.createScriptProcessor(4096, 1, 1);
    processor.onaudioprocess = (event) => {
      const samples = new Float32Array(event.inputBuffer.getChannelData(0));
      onCaptureMessage(samples);
    };
    sourceNodeRef.current.connect(processor);
    processor.connect(silentGainRef.current);
    captureProcessorRef.current = processor;
  }, [agcEnabled, echoCancellationEnabled, handleCaptureFloatChunk, noiseSuppressionEnabled]);

  const enqueueAssistantAudio = useCallback((base64: string, sampleRate = 22050) => {
    const audioCtx = audioCtxRef.current;
    if (!audioCtx) return;

    const int16 = decodePcm16Base64(base64);
    const float32 = pcm16ToFloat32(int16);
    const buffer = audioCtx.createBuffer(1, float32.length, sampleRate);
    buffer.copyToChannel(new Float32Array(float32), 0);

    const source = audioCtx.createBufferSource();
    source.buffer = buffer;
    source.connect(audioCtx.destination);

    const startAt = Math.max(audioCtx.currentTime + 0.02, playbackCursorRef.current || (audioCtx.currentTime + 0.02));
    playbackCursorRef.current = startAt + buffer.duration;
    playbackSourcesRef.current.add(source);
    source.onended = () => {
      playbackSourcesRef.current.delete(source);
      if (playbackSourcesRef.current.size === 0 && voiceModeRef.current && !inputStreamingRef.current) {
        setVoiceState(activationModeRef.current === "push_to_talk" ? "idle" : "listening");
      }
    };
    source.start(startAt);
    setVoiceState("speaking");
  }, []);

  const connectGatewaySession = useCallback(async () => {
    const response = await fetch(`${voiceApiBase}/ai/voice/session`, { method: "POST" });
    if (!response.ok) {
      const body = await response.json().catch(() => ({}));
      throw new Error(body.detail || `Voice session failed (${response.status})`);
    }

    const config = await response.json() as VoiceSessionConfig;
    sessionConfigRef.current = config;
    setActiveProvider(config.provider || null);

    const wsUrl = buildVoiceWsUrl(voiceApiBase, config.ws_path);
    const socket = new WebSocket(wsUrl);
    wsRef.current = socket;
    gatewayReadyRef.current = false;

    socket.onopen = () => {
      logVoiceStage("gateway_open", config.provider);
    };

    socket.onmessage = (event) => {
      if (wsRef.current !== socket) return;
      try {
        const payload = JSON.parse(event.data) as VoiceGatewayEvent;
        handleGatewayEventRef.current(payload);
      } catch (err) {
        console.warn("[VOICE] Failed to parse gateway event", err);
      }
    };

    socket.onclose = () => {
      if (wsRef.current !== socket) return;
      wsRef.current = null;
      gatewayReadyRef.current = false;
      inputStreamingRef.current = false;
      if (voiceModeRef.current && !reconnectingRef.current) {
        setVoiceError("Voice connection closed");
        setVoiceState("error");
      }
    };

    socket.onerror = () => {
      if (wsRef.current !== socket) return;
      setVoiceError("Voice gateway connection failed");
    };
  }, [voiceApiBase]);

  const reconnectSession = useCallback(async () => {
    if (!voiceModeRef.current || reconnectingRef.current) return;
    reconnectingRef.current = true;
    logVoiceStage("gateway_reconnect");

    const oldSocket = wsRef.current;
    wsRef.current = null;
    gatewayReadyRef.current = false;
    inputStreamingRef.current = false;
    oldSocket?.close();

    try {
      await connectGatewaySession();
    } catch (err) {
      const message = err instanceof Error ? err.message : "Voice reconnection failed";
      setVoiceError(message);
      setVoiceState("error");
    } finally {
      reconnectingRef.current = false;
    }
  }, [connectGatewaySession]);

  const handleGatewayEvent = useCallback((event: VoiceGatewayEvent) => {
    switch (event.type) {
      case "session.ready":
        gatewayReadyRef.current = true;
        if (event.provider) setActiveProvider(event.provider);
        syncGatewaySessionConfig();
        if (activationModeRef.current !== "push_to_talk") {
          setVoiceState("listening");
        } else if (pttPressedRef.current) {
          startInputStreamingRef.current("push_to_talk");
        } else {
          setVoiceState("idle");
        }
        return;

      case "session.expiring":
        void reconnectSession();
        return;

      case "provider.changed":
        setActiveProvider(event.provider);
        return;

      case "user.transcript.delta":
        setLiveTranscript(event.text);
        return;

      case "user.transcript.final":
        setLiveTranscript("");
        transcript.appendUser({ role: "user", content: event.text });
        setVoiceState("processing");
        return;

      case "assistant.text.delta":
        if (!pendingAssistantRef.current) {
          pendingAssistantRef.current = true;
          assistantTextRef.current = "";
          transcript.appendAssistant({ role: "assistant", content: "" });
        }
        assistantTextRef.current += event.text;
        transcript.patchLastAssistant({ content: assistantTextRef.current });
        if (voiceState !== "speaking") {
          setVoiceState("processing");
        }
        return;

      case "assistant.text.final":
        if (!pendingAssistantRef.current) {
          pendingAssistantRef.current = true;
          transcript.appendAssistant({ role: "assistant", content: event.text });
        } else {
          transcript.patchLastAssistant({ content: event.text });
        }
        assistantTextRef.current = event.text;
        return;

      case "assistant.audio.chunk":
        enqueueAssistantAudio(event.audio, event.sample_rate_hz ?? 22050);
        return;

      case "assistant.interrupted":
        stopPlayback(false);
        return;

      case "turn.end":
        pendingAssistantRef.current = false;
        assistantTextRef.current = "";
        setLiveTranscript("");
        setVoiceState(voiceModeRef.current && activationModeRef.current !== "push_to_talk" ? "listening" : "idle");
        return;

      case "warning":
        console.warn("[VOICE]", event.message);
        return;

      case "error":
        setVoiceError(event.message);
        setVoiceState("error");
        return;
    }
  }, [enqueueAssistantAudio, reconnectSession, stopPlayback, syncGatewaySessionConfig, transcript, voiceState]);

  handleGatewayEventRef.current = handleGatewayEvent;

  const teardownAudio = useCallback(() => {
    stopPlayback(false);

    captureWorkletNodeRef.current?.disconnect();
    if (captureWorkletNodeRef.current) {
      captureWorkletNodeRef.current.port.onmessage = null;
    }
    captureWorkletNodeRef.current = null;

    captureProcessorRef.current?.disconnect();
    if (captureProcessorRef.current) {
      captureProcessorRef.current.onaudioprocess = null;
    }
    captureProcessorRef.current = null;

    sourceNodeRef.current?.disconnect();
    sourceNodeRef.current = null;

    silentGainRef.current?.disconnect();
    silentGainRef.current = null;

    mediaStreamRef.current?.getTracks().forEach((track) => track.stop());
    mediaStreamRef.current = null;

    captureBufferRef.current = new Float32Array(0);
    sourceRateRef.current = VOICE_INPUT_SAMPLE_RATE;
    playbackCursorRef.current = 0;
    lastChunkAtRef.current = null;
    noiseFloorRef.current = 0.008;

    if (audioCtxRef.current && audioCtxRef.current.state !== "closed") {
      void audioCtxRef.current.close().catch(() => {});
    }
    audioCtxRef.current = null;
  }, [stopPlayback]);

  const stopVoiceMode = useCallback(() => {
    voiceModeRef.current = false;
    setVoiceModeActive(false);
    setVoiceState("idle");
    setLiveTranscript("");
    setActiveProvider(null);

    pttPressedRef.current = false;
    inputStreamingRef.current = false;
    gatewayReadyRef.current = false;
    sessionConfigRef.current = null;
    resetTurnState();

    const socket = wsRef.current;
    wsRef.current = null;
    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify({ type: "session.close" }));
    }
    socket?.close();

    teardownAudio();
  }, [resetTurnState, teardownAudio]);

  const startVoiceMode = useCallback(async () => {
    if (voiceModeRef.current || !voiceAvailable || !voiceEnabled) return;
    voiceModeRef.current = true;
    setVoiceModeActive(true);
    setVoiceError(null);
    setVoiceState(activationModeRef.current === "push_to_talk" ? "idle" : "listening");
    logVoiceStage("voice_mode_start", activationModeRef.current);

    try {
      await ensureAudioPipeline();
      await connectGatewaySession();
      void checkAndUnlock("voice_mode");
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to start voice mode";
      stopVoiceMode();
      setVoiceError(message);
      setVoiceState("error");
    }
  }, [connectGatewaySession, ensureAudioPipeline, stopVoiceMode, voiceAvailable, voiceEnabled]);

  const startRecording = useCallback(async (_source: "keyboard" | "pointer") => {
    if (activationModeRef.current !== "push_to_talk" || !voiceAvailable || !voiceEnabled) return;
    pttPressedRef.current = true;

    if (!voiceModeRef.current) {
      voiceModeRef.current = true;
      setVoiceModeActive(true);
      setVoiceError(null);
      setVoiceState("idle");
      logVoiceStage("ptt_bootstrap");
      try {
        await ensureAudioPipeline();
        await connectGatewaySession();
        void checkAndUnlock("voice_mode");
      } catch (err) {
        const message = err instanceof Error ? err.message : "Failed to start push-to-talk";
        stopVoiceMode();
        setVoiceError(message);
        setVoiceState("error");
        return;
      }
    }

    if (gatewayReadyRef.current) {
      startInputStreaming("push_to_talk");
    }
  }, [connectGatewaySession, ensureAudioPipeline, startInputStreaming, stopVoiceMode, voiceAvailable, voiceEnabled]);

  const stopRecording = useCallback((_source: "keyboard" | "pointer") => {
    if (activationModeRef.current !== "push_to_talk") return;
    pttPressedRef.current = false;
    if (inputStreamingRef.current) {
      stopInputStreaming();
    }
  }, [stopInputStreaming]);

  const recoverAfterAssistantTurn = useCallback(() => {
    // Text chat no longer reuses the voice transport for spoken replies.
  }, []);

  // Dedicated audio resources for text-chat TTS replies. Kept separate from
  // the voice-mode WS playback pipeline (which deals with PCM16 chunks) —
  // here we fetch whole WAVs from Kokoro and decode them per chunk.
  const ttsCtxRef = useRef<AudioContext | null>(null);
  const ttsSourcesRef = useRef<Set<AudioBufferSourceNode>>(new Set());
  const ttsCursorRef = useRef(0);
  const ttsCancelledRef = useRef(false);
  const ttsQueueRef = useRef<Promise<void>>(Promise.resolve());

  const createTTSSession = useCallback((): TTSSession | null => {
    if (!voiceEnabled) return null;
    // Reset cancellation for a fresh turn; previous finish() should already
    // have drained the queue.
    ttsCancelledRef.current = false;

    const ensureCtx = (): AudioContext => {
      if (!ttsCtxRef.current || ttsCtxRef.current.state === "closed") {
        ttsCtxRef.current = new AudioContext();
        ttsCursorRef.current = 0;
      }
      if (ttsCtxRef.current.state === "suspended") {
        void ttsCtxRef.current.resume().catch(() => {});
      }
      return ttsCtxRef.current;
    };

    const synthesizeAndQueue = async (text: string) => {
      if (ttsCancelledRef.current) return;
      let wavBytes: ArrayBuffer;
      try {
        const res = await fetch("/api/kokoro/v1/audio/speech", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            model: "kokoro",
            input: text,
            voice: "af_heart",
            speed: 1.2,
            response_format: "wav",
          }),
        });
        if (!res.ok) {
          console.warn(`[TTS] Kokoro returned HTTP ${res.status}`);
          return;
        }
        wavBytes = await res.arrayBuffer();
      } catch (err) {
        console.warn("[TTS] Kokoro fetch failed:", err);
        return;
      }
      if (ttsCancelledRef.current) return;

      const ctx = ensureCtx();
      let buffer: AudioBuffer;
      try {
        buffer = await ctx.decodeAudioData(wavBytes.slice(0));
      } catch (err) {
        console.warn("[TTS] WAV decode failed:", err);
        return;
      }
      if (ttsCancelledRef.current) return;

      const src = ctx.createBufferSource();
      src.buffer = buffer;
      src.connect(ctx.destination);
      const startAt = Math.max(ctx.currentTime + 0.02, ttsCursorRef.current);
      ttsCursorRef.current = startAt + buffer.duration;
      ttsSourcesRef.current.add(src);

      await new Promise<void>((resolve) => {
        src.onended = () => {
          ttsSourcesRef.current.delete(src);
          resolve();
        };
        src.start(startAt);
      });
    };

    return {
      flush(text: string) {
        const trimmed = text.trim();
        if (!trimmed || ttsCancelledRef.current) return;
        // Chain each flush onto the promise queue so chunks play in order.
        ttsQueueRef.current = ttsQueueRef.current.then(() => synthesizeAndQueue(trimmed));
      },
      async finish() {
        try {
          await ttsQueueRef.current;
        } catch {
          // swallow — errors are already logged in synthesizeAndQueue.
        }
      },
      cancel() {
        ttsCancelledRef.current = true;
        ttsSourcesRef.current.forEach((s) => {
          try { s.stop(); } catch { /* already stopped */ }
        });
        ttsSourcesRef.current.clear();
        ttsCursorRef.current = ttsCtxRef.current
          ? ttsCtxRef.current.currentTime + 0.02
          : 0;
        // Reset the queue so subsequent flushes don't wait on stale promises.
        ttsQueueRef.current = Promise.resolve();
      },
      isPlaying: () => ttsSourcesRef.current.size > 0,
    };
  }, [voiceEnabled]);

  useEffect(() => {
    if (!voiceEnabled && voiceModeRef.current) {
      stopVoiceMode();
    }
  }, [stopVoiceMode, voiceEnabled]);

  useEffect(() => {
    return () => {
      stopVoiceMode();
    };
  }, [stopVoiceMode]);

  return {
    voiceState,
    voiceModeActive,
    voiceError,
    liveTranscript,
    activeProvider,
    startVoiceMode,
    stopVoiceMode,
    startRecording,
    stopRecording,
    dismissError,
    recoverAfterAssistantTurn,
    voiceEnabled,
    setVoiceEnabled,
    activationMode,
    setActivationMode,
    noiseSuppressionEnabled,
    setNoiseSuppressionEnabled,
    echoCancellationEnabled,
    setEchoCancellationEnabled,
    agcEnabled,
    setAgcEnabled,
    createTTSSession,
    voiceModeRef,
  };
}
