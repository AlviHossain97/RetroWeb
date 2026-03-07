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
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/85 backdrop-blur-md p-4">
      <div
        className="max-w-lg w-full rounded-2xl p-8 relative shadow-2xl"
        style={{
          background: 'var(--surface-1)',
          border: '1px solid var(--border-strong)',
          animation: 'scaleIn 0.3s cubic-bezier(0.34,1.56,0.64,1)',
        }}
      >
        {/* Icon */}
        <div className="flex items-center gap-4 mb-7">
          <div className="p-3 rounded-xl" style={{background: 'rgba(204,0,0,0.12)', border: '1px solid rgba(204,0,0,0.25)'}}>
            <AlertTriangle size={28} style={{color: 'var(--accent-primary)'}} />
          </div>
          <div>
            <h2 className="text-2xl font-bold" style={{color: 'var(--text-primary)'}}>Legal Notice</h2>
            <p className="text-sm mt-0.5" style={{color: 'var(--text-muted)'}}>Please read before continuing</p>
          </div>
        </div>

        <div className="space-y-3 mb-8">
          <p className="text-sm leading-relaxed" style={{color: 'var(--text-secondary)'}}>
            Welcome to <strong style={{color: 'var(--text-primary)'}}>RetroWeb</strong>. Before using this emulator, please acknowledge:
          </p>
          <ul className="space-y-2.5">
            {[
              'RetroWeb does NOT host, provide, or distribute any game ROMs or BIOS files.',
              'You must legally own the original hardware and software for any files you upload.',
              'Piracy is strictly prohibited. Only use this with software you legally own.',
              'All files stay on your local device. No data is transmitted to external servers.',
            ].map((item, i) => (
              <li key={i} className="flex items-start gap-2.5 text-sm" style={{color: 'var(--text-secondary)'}}>
                <div className="w-1.5 h-1.5 rounded-full mt-1.5 shrink-0" style={{background: 'var(--accent-primary)'}} />
                {item}
              </li>
            ))}
          </ul>
        </div>

        <button
          onClick={handleAccept}
          className="w-full flex items-center justify-center gap-2.5 py-3.5 rounded-xl font-bold text-sm transition-all hover:brightness-110 active:scale-[0.98]"
          style={{
            background: 'linear-gradient(135deg, var(--accent-primary), #e94057)',
            color: '#fff',
            boxShadow: '0 4px 20px var(--accent-glow)',
          }}
        >
          <ShieldCheck size={18} />
          I Understand &amp; Agree
        </button>
      </div>
    </div>
  );
}
