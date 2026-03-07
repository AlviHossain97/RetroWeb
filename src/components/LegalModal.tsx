import { useState } from "react";
import { AlertTriangle, ShieldCheck } from "lucide-react";

export default function LegalModal() {
  const [isOpen, setIsOpen] = useState(() => {
    const hasSeenModal = localStorage.getItem("retroweb_legal_accepted");
    return !hasSeenModal;
  });

  const handleAccept = () => {
    localStorage.setItem("retroweb_legal_accepted", "true");
    setIsOpen(false);
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/85 backdrop-blur-md p-4">
      <div
        className="bg-card border border-border p-8 max-w-lg w-full rounded-2xl relative animate-in fade-in zoom-in duration-300"
        style={{ boxShadow: "var(--shadow-xl)" }}
      >
        <div className="flex items-center gap-4 mb-8">
          <div className="w-14 h-14 rounded-xl bg-destructive/10 border border-destructive/20 flex items-center justify-center shrink-0">
            <AlertTriangle size={28} className="text-destructive" />
          </div>
          <div>
            <h2 className="text-2xl font-bold text-foreground">Legal Notice</h2>
            <p className="text-sm text-muted-foreground">Please read before continuing</p>
          </div>
        </div>

        <div className="space-y-4 text-muted-foreground mb-8">
          <p className="text-sm leading-relaxed">
            Welcome to <strong className="text-foreground font-semibold">PiStation</strong>.
            Before you begin, please acknowledge the following:
          </p>
          <ul className="space-y-3 text-sm">
            {[
              "PiStation does NOT host, provide, or distribute any game ROMs or BIOS files.",
              "You must legally own the original hardware and software for any files you upload.",
              "Piracy is strictly prohibited. Do not use this tool for copyrighted material you do not own.",
              "All files remain entirely on your local device. No data is transmitted externally.",
            ].map((text, i) => (
              <li key={i} className="flex gap-3">
                <div className="w-1.5 h-1.5 rounded-full bg-primary mt-2 shrink-0" />
                <span>{text}</span>
              </li>
            ))}
          </ul>
        </div>

        <button
          onClick={handleAccept}
          className="btn-cta w-full py-4 text-sm"
        >
          <ShieldCheck size={18} />
          I Understand & Agree
        </button>
      </div>
    </div>
  );
}
