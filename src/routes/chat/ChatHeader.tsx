import { MoreVertical } from "lucide-react";
import { MODEL_ICONS } from "./constants";
import type { OverlayState } from "./constants";

interface ChatHeaderProps {
  selectedModel: string;
  nvidiaOnline: boolean;
  kokoroOnline: boolean;
  overlay: OverlayState;
  setOverlay: (v: OverlayState) => void;
}

export function ChatHeader({ selectedModel, nvidiaOnline, kokoroOnline, overlay, setOverlay }: ChatHeaderProps) {
  const info = MODEL_ICONS[selectedModel];
  const statusDot = nvidiaOnline ? "var(--success)" : "var(--danger)";

  return (
    <div
      className="retro-chat-header flex items-center justify-between px-4 py-4 shrink-0"
    >
      <button
        onClick={() => setOverlay(overlay === "modelPicker" ? "none" : "modelPicker")}
        className="retro-button retro-button--ghost px-4 py-2 min-h-0 text-[0.56rem]"
        aria-label="Select AI model"
      >
        {info && <img src={info.icon} alt="" className="w-5 h-5 rounded object-contain" />}
        <span className="truncate max-w-[160px]">{info?.label || selectedModel}</span>
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" style={{ color: "var(--accent-secondary)" }}>
          <polyline points="6 9 12 15 18 9" />
        </svg>
      </button>

      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2 flex-wrap justify-end">
          <div className="w-1.5 h-1.5 rounded-full" style={{ background: statusDot }} />
          <span className="text-sm font-semibold uppercase tracking-[0.14em]" style={{ color: "var(--text-primary)" }}>PiStation AI</span>
          {kokoroOnline && (
            <span className="retro-chip">Voice</span>
          )}
        </div>

        <button
          onClick={() => setOverlay(overlay === "overflowMenu" ? "none" : "overflowMenu")}
          className="retro-button retro-button--ghost retro-icon-button min-h-0 text-[0.56rem]"
          aria-label="Menu"
        >
          <MoreVertical size={18} />
        </button>
      </div>
    </div>
  );
}
