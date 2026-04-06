import { useRef, useEffect } from "react";
import { X } from "lucide-react";
import type { ActivationMode } from "./useChatVoice";

interface ChatVoiceSettingsModalProps {
  activationMode: ActivationMode;
  setActivationMode: (v: ActivationMode) => void;
  noiseSuppressionEnabled: boolean;
  setNoiseSuppressionEnabled: (v: boolean) => void;
  echoCancellationEnabled: boolean;
  setEchoCancellationEnabled: (v: boolean) => void;
  agcEnabled: boolean;
  setAgcEnabled: (v: boolean) => void;
  onClose: () => void;
}

export function ChatVoiceSettingsModal({
  activationMode, setActivationMode,
  noiseSuppressionEnabled, setNoiseSuppressionEnabled,
  echoCancellationEnabled, setEchoCancellationEnabled,
  agcEnabled, setAgcEnabled,
  onClose,
}: ChatVoiceSettingsModalProps) {
  const firstFocusRef = useRef<HTMLSelectElement>(null);
  const modalRef = useRef<HTMLDivElement>(null);

  // Focus first interactive element on mount
  useEffect(() => {
    firstFocusRef.current?.focus();
  }, []);

  // Focus trap
  useEffect(() => {
    const modal = modalRef.current;
    if (!modal) return;

    const handleTab = (e: KeyboardEvent) => {
      if (e.key === "Escape") { onClose(); return; }
      if (e.key !== "Tab") return;

      const focusable = modal.querySelectorAll<HTMLElement>(
        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
      );
      if (focusable.length === 0) return;

      const first = focusable[0];
      const last = focusable[focusable.length - 1];

      if (e.shiftKey) {
        if (document.activeElement === first) {
          e.preventDefault();
          last.focus();
        }
      } else {
        if (document.activeElement === last) {
          e.preventDefault();
          first.focus();
        }
      }
    };

    modal.addEventListener("keydown", handleTab);
    return () => modal.removeEventListener("keydown", handleTab);
  }, [onClose]);

  return (
    <div className="retro-modal-backdrop fixed inset-0 z-50 flex items-center justify-center" onClick={onClose}>
      <div
        ref={modalRef}
        className="retro-modal-panel w-full max-w-md mx-4 rounded-[1.6rem] p-6 animate-[scaleIn_0.15s_ease-out]"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-lg font-bold uppercase tracking-[0.14em]" style={{ color: "var(--text-primary)" }}>Voice Settings</h2>
          <button
            onClick={onClose}
            className="retro-button retro-button--ghost retro-icon-button min-h-0 text-[0.56rem]"
            aria-label="Close voice settings"
          >
            <X size={18} />
          </button>
        </div>

        <div className="space-y-5">
          {/* Mic Gating Mode */}
          <div>
            <label className="block text-xs font-medium mb-1.5" style={{ color: "var(--text-secondary)" }}>
              Mic Gating Mode
            </label>
            <select
              ref={firstFocusRef}
              value={activationMode}
              onChange={e => setActivationMode(e.target.value as ActivationMode)}
              className="retro-select w-full rounded-xl px-3 py-3 text-sm outline-none cursor-pointer"
              style={{ background: "rgba(15, 18, 33, 0.65)", color: "var(--text-primary)", border: "2px solid var(--border-soft)" }}
            >
              <option value="auto_near_field">Near-Field (Quiet Room)</option>
              <option value="headset">Headset (More Permissive)</option>
              <option value="push_to_talk">Push To Talk</option>
            </select>
            <p className="text-[10px] mt-1.5 leading-tight" style={{ color: "var(--text-muted)" }}>
              {activationMode === "auto_near_field" && "Strict adaptive noise floor. Rejects distant TV/chatter."}
              {activationMode === "headset" && "Lower threshold for nearby whispers. Use with headset."}
              {activationMode === "push_to_talk" && "Hold the mic button or press T to record. Release to send."}
            </p>
          </div>

          <div style={{ borderTop: "1px solid var(--border-soft)" }} />

          {/* DSP checkboxes */}
          <div className="space-y-3">
            <p className="text-[10px] uppercase tracking-wider font-bold" style={{ color: "var(--text-muted)" }}>
              Browser Audio Processing
            </p>
            {[
              { label: "Noise Suppression", checked: noiseSuppressionEnabled, onChange: setNoiseSuppressionEnabled },
              { label: "Echo Cancellation", checked: echoCancellationEnabled, onChange: setEchoCancellationEnabled },
              { label: "Auto Gain Control (AGC)", checked: agcEnabled, onChange: setAgcEnabled },
            ].map((opt) => (
              <label key={opt.label} className="retro-list-item flex items-center gap-3 cursor-pointer px-3 py-3">
                <input
                  type="checkbox"
                  checked={opt.checked}
                  onChange={e => opt.onChange(e.target.checked)}
                  className="w-4 h-4 rounded accent-red-600"
                />
                <span className="text-sm" style={{ color: "var(--text-primary)" }}>{opt.label}</span>
              </label>
            ))}
            <p className="text-[10px] italic" style={{ color: "var(--text-muted)" }}>
              Disable AGC if background noise keeps getting boosted.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
