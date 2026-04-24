import type { Message } from "./constants";

export const VOICE_INPUT_SAMPLE_RATE = 16000;
export const VOICE_OUTPUT_SAMPLE_RATE = 22050;
export const VOICE_INPUT_CHUNK_MS = 80;
export const VOICE_INPUT_FORMAT = "pcm16";
export const VOICE_OUTPUT_FORMAT = "pcm16";

export interface VoiceProviderHealth {
  name: string;
  available: boolean;
  reason?: string | null;
}

export interface VoiceHealthResponse {
  available: boolean;
  active_provider?: string | null;
  providers: VoiceProviderHealth[];
  fallback_capable: boolean;
  reason?: string | null;
}

export interface VoiceSessionConfig {
  session_id: string;
  ws_path: string;
  provider: string;
  input_sample_rate_hz: number;
  output_sample_rate_hz: number;
  input_format: string;
  output_format: string;
  max_session_seconds: number;
}

export type VoiceGatewayCommand =
  | {
    type: "session.configure";
    selected_model: string;
    activation_mode: string;
    conversation_history: { role: "user" | "assistant" | "system"; content: string }[];
    client: { user_agent: string; platform: string };
  }
  | { type: "input_audio.start"; source: "continuous" | "push_to_talk" }
  | { type: "input_audio.chunk"; audio: string; sample_rate_hz: number; format: "pcm16" }
  | { type: "input_audio.stop" }
  | { type: "response.cancel" }
  | { type: "session.close" };

export type VoiceGatewayEvent =
  | {
    type: "session.ready";
    provider?: string;
    session_id?: string;
    input_sample_rate_hz?: number;
    output_sample_rate_hz?: number;
    input_format?: string;
    output_format?: string;
    max_session_seconds?: number;
  }
  | { type: "session.expiring"; seconds_remaining?: number; session_id?: string }
  | { type: "provider.changed"; provider: string; reason?: string }
  | { type: "user.transcript.delta"; text: string }
  | { type: "user.transcript.final"; text: string }
  | { type: "assistant.text.delta"; text: string }
  | { type: "assistant.text.final"; text: string }
  | { type: "assistant.audio.chunk"; audio: string; sample_rate_hz?: number; format?: string; sequence?: number }
  | { type: "assistant.interrupted" }
  | { type: "turn.end" }
  | { type: "warning"; message: string }
  | { type: "error"; message: string };

export function buildVoiceWsUrl(apiBase: string | undefined, wsPath: string): string {
  if (!apiBase || apiBase.startsWith("/")) {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    return `${protocol}//${window.location.host}${wsPath}`;
  }

  const base = new URL(apiBase);
  const origin = base.protocol === "https:" ? `wss://${base.host}` : `ws://${base.host}`;
  return `${origin}${wsPath}`;
}

export function encodePcm16Base64(data: Uint8Array): string {
  let binary = "";
  for (let i = 0; i < data.length; i++) {
    binary += String.fromCharCode(data[i]);
  }
  return btoa(binary);
}

export function decodePcm16Base64(base64: string): Int16Array {
  const binary = atob(base64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) {
    bytes[i] = binary.charCodeAt(i);
  }
  return new Int16Array(bytes.buffer);
}

export function pcm16ToFloat32(samples: Int16Array): Float32Array {
  const out = new Float32Array(samples.length);
  for (let i = 0; i < samples.length; i++) {
    out[i] = Math.max(-1, Math.min(1, samples[i] / 32768));
  }
  return out;
}

export function downsampleFloat32Buffer(input: Float32Array<ArrayBufferLike>, sourceRate: number, targetRate: number): Float32Array {
  if (sourceRate === targetRate) return input;
  const ratio = sourceRate / targetRate;
  const outputLength = Math.max(1, Math.round(input.length / ratio));
  const output = new Float32Array(outputLength);

  let offset = 0;
  for (let i = 0; i < outputLength; i++) {
    const nextOffset = Math.min(input.length, Math.round((i + 1) * ratio));
    let accum = 0;
    let count = 0;
    for (let j = offset; j < nextOffset; j++) {
      accum += input[j];
      count++;
    }
    output[i] = count > 0 ? accum / count : input[Math.min(offset, input.length - 1)] ?? 0;
    offset = nextOffset;
  }
  return output;
}

export function float32ToPcm16Bytes(input: Float32Array<ArrayBufferLike>): Uint8Array {
  const out = new Int16Array(input.length);
  for (let i = 0; i < input.length; i++) {
    const clamped = Math.max(-1, Math.min(1, input[i]));
    out[i] = clamped < 0 ? clamped * 32768 : clamped * 32767;
  }
  return new Uint8Array(out.buffer);
}

export function appendFloat32Buffer(existing: Float32Array<ArrayBufferLike>, incoming: Float32Array<ArrayBufferLike>): Float32Array {
  const merged = new Float32Array(existing.length + incoming.length);
  merged.set(existing);
  merged.set(incoming, existing.length);
  return merged;
}

export function buildVoiceConversationHistory(messages: Message[]): { role: "user" | "assistant" | "system"; content: string }[] {
  return messages
    .filter((message) => message.content.trim())
    .slice(-12)
    .map((message) => ({
      role: message.role,
      content: message.content,
    }));
}
