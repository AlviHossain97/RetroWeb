import { Check } from "lucide-react";
import { NVIDIA_MODELS, MODEL_ICONS } from "./constants";

interface ChatModelPickerProps {
  selectedModel: string;
  onSelect: (model: string) => void;
  onClose: () => void;
}

export function ChatModelPicker({ selectedModel, onSelect, onClose }: ChatModelPickerProps) {
  return (
    <>
      {/* Click-outside overlay */}
      <div className="fixed inset-0 z-30" onClick={onClose} />
      {/* Popover */}
      <div
        className="absolute left-4 top-14 z-40 w-72 rounded-xl p-1.5 animate-[scaleIn_0.15s_ease-out]"
        style={{ background: "var(--surface-1)", border: "1px solid var(--border-soft)", boxShadow: "var(--shadow-lg)" }}
      >
        <p className="px-3 pt-2 pb-1.5 text-[10px] uppercase tracking-wider font-bold" style={{ color: "var(--text-muted)" }}>
          Choose Model
        </p>
        {NVIDIA_MODELS.map((m) => {
          const info = MODEL_ICONS[m];
          const isSelected = selectedModel === m;
          return (
            <button
              key={m}
              onClick={() => onSelect(m)}
              className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-left transition-colors"
              style={{
                background: isSelected ? "rgba(204,0,0,0.1)" : "transparent",
                color: "var(--text-primary)",
              }}
            >
              <div className="w-5 h-5 shrink-0">
                {info ? (
                  <img src={info.icon} alt="" className="w-5 h-5 rounded object-contain" />
                ) : (
                  <div className="w-5 h-5 rounded-full" style={{ background: "var(--surface-3)" }} />
                )}
              </div>
              <span className="text-sm flex-1">{info?.label || m}</span>
              {isSelected && <Check size={16} style={{ color: "var(--accent-primary)" }} />}
            </button>
          );
        })}
      </div>
    </>
  );
}
