import type { VoiceState } from "./constants";
import type { ActivationMode } from "./useChatVoice";

interface ChatVoiceBarProps {
  voiceState: VoiceState;
  activationMode: ActivationMode;
  liveTranscript?: string;
  provider?: string | null;
  onStop: () => void;
}

const CONTINUOUS_TEXT: Record<VoiceState, string> = {
  idle: "",
  listening: "Listening...",
  processing: "AI is thinking...",
  speaking: "Speaking...",
  error: "Voice error",
};

const PTT_TEXT: Record<VoiceState, string> = {
  idle: "",
  listening: "Recording...",
  processing: "Processing...",
  speaking: "Speaking...",
  error: "Voice error",
};

export function ChatVoiceBar({ voiceState, activationMode, liveTranscript, provider, onStop }: ChatVoiceBarProps) {
  if (voiceState === "idle") return null;

  const statusMap = activationMode === "push_to_talk" ? PTT_TEXT : CONTINUOUS_TEXT;
  const barColor = voiceState === "processing" ? "var(--accent-cyan)" : "var(--accent-primary)";

  return (
    <div
      className="retro-chat-header shrink-0 flex items-center justify-between px-4 py-3"
      style={{ borderTop: "3px solid rgba(204, 0, 0, 0.18)" }}
    >
      <div className="flex items-center gap-3 min-w-0">
        <div className="flex items-end gap-0.5 h-4 shrink-0">
          {[0, 1, 2, 3, 4].map((i) => (
            <div
              key={i}
              className="w-0.5 rounded-full"
              style={{
                background: barColor,
                height: "100%",
                animation: `voiceBar 0.8s ease-in-out ${i * 0.1}s infinite`,
              }}
            />
          ))}
        </div>
        <div className="min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-sm" style={{ color: "var(--text-secondary)" }} aria-live="polite">
              {statusMap[voiceState]}
            </span>
            {provider && (
              <span className="retro-chip text-[10px]">{provider}</span>
            )}
          </div>
          {liveTranscript && (
            <p className="text-xs truncate mt-1" style={{ color: "var(--text-muted)" }}>
              {liveTranscript}
            </p>
          )}
        </div>
      </div>
      <button
        onClick={onStop}
        className="retro-button retro-button--ghost px-4 py-2 min-h-0 text-[0.56rem]"
        aria-label="Stop voice"
      >
        Stop
      </button>
    </div>
  );
}
