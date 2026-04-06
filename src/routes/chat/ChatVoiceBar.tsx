import type { VoiceState } from "./constants";
import type { ActivationMode } from "./useChatVoice";

interface ChatVoiceBarProps {
  voiceState: VoiceState;
  activationMode: ActivationMode;
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

export function ChatVoiceBar({ voiceState, activationMode, onStop }: ChatVoiceBarProps) {
  if (voiceState === "idle") return null;

  const statusMap = activationMode === "push_to_talk" ? PTT_TEXT : CONTINUOUS_TEXT;
  const barColor = voiceState === "processing" ? "var(--accent-cyan)" : "var(--accent-primary)";

  return (
    <div
      className="shrink-0 flex items-center justify-between px-4 py-2.5"
      style={{ background: "var(--surface-1)", borderTop: "1px solid var(--border-soft)" }}
    >
      <div className="flex items-center gap-3">
        {/* Animated bars */}
        <div className="flex items-end gap-0.5 h-4">
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
        <span className="text-sm" style={{ color: "var(--text-secondary)" }} aria-live="polite">
          {statusMap[voiceState]}
        </span>
      </div>
      <button
        onClick={onStop}
        className="px-3 py-1 rounded-lg text-xs font-medium transition-colors hover:opacity-80"
        style={{ background: "var(--surface-2)", color: "var(--text-secondary)" }}
        aria-label="Stop voice"
      >
        Stop
      </button>
    </div>
  );
}
