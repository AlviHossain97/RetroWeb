import { Trash2 } from "lucide-react";

interface ChatClearDialogProps {
  onConfirm: () => void;
  onCancel: () => void;
}

export function ChatClearDialog({ onConfirm, onCancel }: ChatClearDialogProps) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <div
        className="w-[320px] rounded-2xl p-6 animate-[scaleIn_0.15s_ease-out]"
        style={{ background: "var(--surface-1)", border: "1px solid var(--border-soft)", boxShadow: "var(--shadow-lg)" }}
      >
        <div className="flex flex-col items-center text-center">
          <div
            className="w-12 h-12 rounded-full flex items-center justify-center mb-4"
            style={{ background: "rgba(239,68,68,0.15)" }}
          >
            <Trash2 size={24} style={{ color: "var(--danger)" }} />
          </div>
          <h2 className="text-lg font-bold mb-2" style={{ color: "var(--text-primary)" }}>Clear chat?</h2>
          <p className="text-sm mb-6" style={{ color: "var(--text-muted)" }}>
            All messages will be permanently deleted. This cannot be undone.
          </p>
          <div className="flex gap-3 w-full">
            <button
              onClick={onCancel}
              className="flex-1 px-4 py-2.5 rounded-xl text-sm font-medium transition-colors hover:opacity-80"
              style={{ background: "var(--surface-2)", color: "var(--text-secondary)", border: "1px solid var(--border-soft)" }}
            >
              Cancel
            </button>
            <button
              onClick={onConfirm}
              className="flex-1 px-4 py-2.5 rounded-xl text-sm font-medium text-white transition-colors hover:opacity-90"
              style={{ background: "var(--danger)" }}
            >
              Clear
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
