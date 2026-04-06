import { useRef, useEffect } from "react";
import { Trash2 } from "lucide-react";

interface ChatClearDialogProps {
  onConfirm: () => void;
  onCancel: () => void;
}

export function ChatClearDialog({ onConfirm, onCancel }: ChatClearDialogProps) {
  const cancelRef = useRef<HTMLButtonElement>(null);
  const modalRef = useRef<HTMLDivElement>(null);

  // Focus cancel button on mount
  useEffect(() => {
    cancelRef.current?.focus();
  }, []);

  // Focus trap
  useEffect(() => {
    const modal = modalRef.current;
    if (!modal) return;

    const handleTab = (e: KeyboardEvent) => {
      if (e.key === "Escape") { onCancel(); return; }
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
  }, [onCancel]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm" onClick={onCancel}>
      <div
        ref={modalRef}
        className="w-[320px] rounded-2xl p-6 animate-[scaleIn_0.15s_ease-out]"
        style={{ background: "var(--surface-1)", border: "1px solid var(--border-soft)", boxShadow: "var(--shadow-lg)" }}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex flex-col items-center text-center">
          <div
            className="w-12 h-12 rounded-full flex items-center justify-center mb-4"
            style={{ background: "color-mix(in srgb, var(--danger) 15%, transparent)" }}
          >
            <Trash2 size={24} style={{ color: "var(--danger)" }} />
          </div>
          <h2 className="text-lg font-bold mb-2" style={{ color: "var(--text-primary)" }}>Clear chat?</h2>
          <p className="text-sm mb-6" style={{ color: "var(--text-muted)" }}>
            All messages will be permanently deleted. This cannot be undone.
          </p>
          <div className="flex gap-3 w-full">
            <button
              ref={cancelRef}
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
