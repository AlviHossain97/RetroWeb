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
      className="flex items-center justify-between px-4 py-3 shrink-0"
      style={{ background: "var(--surface-1)", borderBottom: "1px solid var(--border-soft)" }}
    >
      {/* Model chip (left) */}
      <button
        onClick={() => setOverlay(overlay === "modelPicker" ? "none" : "modelPicker")}
        className="flex items-center gap-2 px-3 py-1.5 rounded-xl text-sm transition-colors hover:opacity-80"
        style={{ background: "var(--surface-2)", border: "1px solid var(--border-soft)", color: "var(--text-primary)" }}
        aria-label="Select AI model"
      >
        {info && <img src={info.icon} alt="" className="w-5 h-5 rounded object-contain" />}
        <span className="truncate max-w-[160px]">{info?.label || selectedModel}</span>
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" style={{ color: "var(--text-muted)" }}>
          <polyline points="6 9 12 15 18 9" />
        </svg>
      </button>

      {/* Title + status (center/right) */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2">
          <div className="w-1.5 h-1.5 rounded-full" style={{ background: statusDot }} />
          <span className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>PiStation AI</span>
          {kokoroOnline && (
            <span className="text-[10px] px-1.5 py-0.5 rounded-md" style={{ background: "var(--surface-2)", color: "var(--text-muted)" }}>Voice</span>
          )}
        </div>

        {/* Overflow menu button (far right) */}
        <button
          onClick={() => setOverlay(overlay === "overflowMenu" ? "none" : "overflowMenu")}
          className="p-1.5 rounded-lg transition-colors hover:opacity-80"
          style={{ color: "var(--text-muted)" }}
          aria-label="Menu"
        >
          <MoreVertical size={18} />
        </button>
      </div>
    </div>
  );
}
