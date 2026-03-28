import { X } from "lucide-react";

interface ChatVoiceSettingsModalProps {
  activationMode: string;
  setActivationMode: (v: any) => void;
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
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <div
        className="w-full max-w-md mx-4 rounded-2xl p-6 animate-[scaleIn_0.15s_ease-out]"
        style={{ background: "var(--surface-1)", border: "1px solid var(--border-soft)", boxShadow: "var(--shadow-lg)" }}
        onKeyDown={(e) => e.key === "Escape" && onClose()}
      >
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-lg font-bold" style={{ color: "var(--text-primary)" }}>Voice Settings</h2>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg transition-colors hover:opacity-80"
            style={{ color: "var(--text-muted)" }}
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
              value={activationMode}
              onChange={e => setActivationMode(e.target.value)}
              className="w-full rounded-xl px-3 py-2.5 text-sm outline-none cursor-pointer"
              style={{ background: "var(--surface-2)", color: "var(--text-primary)", border: "1px solid var(--border-soft)" }}
            >
              <option value="auto_near_field">Near-Field (Quiet Room)</option>
              <option value="headset">Headset (More Permissive)</option>
              <option value="push_to_talk">Push To Talk (Coming Soon)</option>
            </select>
            <p className="text-[10px] mt-1.5 leading-tight" style={{ color: "var(--text-muted)" }}>
              {activationMode === "auto_near_field" && "Strict adaptive noise floor. Rejects distant TV/chatter."}
              {activationMode === "headset" && "Lower threshold for nearby whispers. Use with headset."}
              {activationMode === "push_to_talk" && "Only listens while you hold the spacebar."}
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
              <label key={opt.label} className="flex items-center gap-3 cursor-pointer">
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
