import { Globe, Volume2, Settings, Download, Trash2 } from "lucide-react";

interface ChatOverflowMenuProps {
  webMode: string;
  setWebMode: (v: "auto" | "always" | "never") => void;
  voiceEnabled: boolean;
  setVoiceEnabled: (v: boolean) => void;
  hasMessages: boolean;
  onExport: () => void;
  onClear: () => void;
  onVoiceSettings: () => void;
  onClose: () => void;
}

export function ChatOverflowMenu({
  webMode, setWebMode,
  voiceEnabled, setVoiceEnabled,
  hasMessages,
  onExport, onClear, onVoiceSettings, onClose,
}: ChatOverflowMenuProps) {
  return (
    <>
      <div className="fixed inset-0 z-30" onClick={onClose} />
      <div
        className="retro-modal-panel absolute right-4 top-16 z-40 w-64 rounded-[1.4rem] p-2 animate-[scaleIn_0.15s_ease-out]"
      >
        <p className="px-3 pt-2 pb-1 text-[10px] uppercase tracking-wider font-bold" style={{ color: "var(--text-muted)" }}>
          Conversation
        </p>
        <div className="flex items-center justify-between px-3 py-2 rounded-xl" style={{ color: "var(--text-primary)" }}>
          <div className="flex items-center gap-2 text-sm">
            <Globe size={14} style={{ color: "var(--text-muted)" }} />
            Web Search
          </div>
          <select
            value={webMode}
            onChange={e => { setWebMode(e.target.value as any); onClose(); }}
            className="retro-select text-xs rounded-lg px-2 py-1 outline-none cursor-pointer"
            style={{ background: "rgba(15, 18, 33, 0.65)", border: "2px solid var(--border-soft)", color: "var(--text-secondary)" }}
          >
            <option value="auto">Auto</option>
            <option value="always">Always</option>
            <option value="never">Never</option>
          </select>
        </div>

        <div className="mx-2 my-1" style={{ borderTop: "1px solid var(--border-soft)" }} />

        {/* Voice */}
        <p className="px-3 pt-1 pb-1 text-[10px] uppercase tracking-wider font-bold" style={{ color: "var(--text-muted)" }}>
          Voice
        </p>
        <button
          onClick={() => { setVoiceEnabled(!voiceEnabled); onClose(); }}
          className="w-full flex items-center justify-between px-3 py-2 rounded-xl text-sm transition-colors hover:opacity-80"
          style={{ color: "var(--text-primary)" }}
        >
          <div className="flex items-center gap-2">
            <Volume2 size={14} style={{ color: "var(--text-muted)" }} />
            Realtime Voice
          </div>
          <span
            className={`retro-chip ${voiceEnabled ? "retro-chip--success" : ""}`}
            style={{
              background: voiceEnabled ? undefined : "rgba(15, 18, 33, 0.7)",
              color: voiceEnabled ? undefined : "var(--text-muted)",
            }}
          >
            {voiceEnabled ? "ENABLED" : "OFF"}
          </span>
        </button>
        <button
          onClick={() => { onVoiceSettings(); }}
          className="w-full flex items-center gap-2 px-3 py-2 rounded-xl text-sm transition-colors hover:opacity-80"
          style={{ color: "var(--text-primary)" }}
        >
          <Settings size={14} style={{ color: "var(--text-muted)" }} />
          Voice Settings...
        </button>

        <div className="mx-2 my-1" style={{ borderTop: "1px solid var(--border-soft)" }} />

        {/* Chat */}
        <p className="px-3 pt-1 pb-1 text-[10px] uppercase tracking-wider font-bold" style={{ color: "var(--text-muted)" }}>
          Chat
        </p>
        {hasMessages && (
          <button
            onClick={() => { onExport(); onClose(); }}
            className="w-full flex items-center gap-2 px-3 py-2 rounded-xl text-sm transition-colors hover:opacity-80"
            style={{ color: "var(--text-primary)" }}
          >
            <Download size={14} style={{ color: "var(--text-muted)" }} />
            Export Chat
          </button>
        )}
        {hasMessages && (
          <button
            onClick={() => { onClear(); }}
            className="w-full flex items-center gap-2 px-3 py-2 rounded-xl text-sm transition-colors hover:opacity-80"
            style={{ color: "var(--danger)" }}
          >
            <Trash2 size={14} />
            Clear Chat
          </button>
        )}
      </div>
    </>
  );
}
