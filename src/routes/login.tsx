import { useState } from "react";
import { useNavigate } from "react-router";
import { Gamepad2, ArrowRight } from "lucide-react";
import LoaderOverlay from "../components/LoaderOverlay";

export default function Login() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);

  const enterApp = () => {
    setLoading(true);
    sessionStorage.setItem("retroweb.loggedIn", "true");
    setTimeout(() => navigate("/"), 2500);
  };

  return (
    <div
      className="min-h-screen flex items-center justify-center p-4"
      style={{
        background: 'var(--bg-primary)',
        position: 'relative',
        overflow: 'hidden',
      }}
    >
      <LoaderOverlay visible={loading} mode="init" />
      {/* Background glow orbs */}
      <div style={{ position: 'absolute', top: '15%', left: '20%', width: 400, height: 400, borderRadius: '50%', background: 'radial-gradient(circle, rgba(204,0,0,0.08) 0%, transparent 70%)', pointerEvents: 'none' }} />
      <div style={{ position: 'absolute', bottom: '20%', right: '15%', width: 300, height: 300, borderRadius: '50%', background: 'radial-gradient(circle, rgba(139,92,246,0.06) 0%, transparent 70%)', pointerEvents: 'none' }} />

      <div
        className="w-full max-w-md relative"
        style={{
          animation: 'scaleIn 0.4s ease',
        }}
      >
        <style>{`
          @keyframes scaleIn {
            from { opacity: 0; transform: scale(0.95) translateY(8px); }
            to { opacity: 1; transform: scale(1) translateY(0); }
          }
        `}</style>

        <div
          className="rounded-2xl p-8"
          style={{
            background: 'var(--surface-1)',
            border: '1px solid var(--border-strong, var(--border-soft))',
            boxShadow: '4px 4px 0px rgba(204,0,0,0.4), 8px 8px 0px rgba(204,0,0,0.15)',
          }}
        >
          {/* Logo */}
          <div className="flex flex-col items-center mb-8">
            <div
              className="w-14 h-14 rounded-2xl flex items-center justify-center mb-4"
              style={{ background: 'rgba(204,0,0,0.15)', border: '1px solid rgba(204,0,0,0.3)', boxShadow: '0 0 24px rgba(204,0,0,0.2)' }}
            >
              <Gamepad2 size={28} style={{ color: 'var(--accent-primary)' }} />
            </div>
            <h1 className="text-2xl font-bold tracking-tight" style={{ color: 'var(--text-primary)' }}>RetroWeb</h1>
            <p className="text-sm mt-1 text-center" style={{ color: 'var(--text-muted)' }}>
              Browser-based retro gaming platform.
              <br />No account needed — everything stays local.
            </p>
          </div>

          {/* Enter button */}
          <button
            type="button"
            onClick={enterApp}
            className="w-full py-3 rounded-xl font-bold text-sm transition-all flex items-center justify-center gap-2"
            style={{
              background: 'linear-gradient(135deg, #cc0000, #ff4400)',
              color: '#fff',
              boxShadow: '0 4px 16px rgba(204,0,0,0.4)',
            }}
            onMouseEnter={e => { (e.currentTarget as HTMLElement).style.boxShadow = '0 6px 20px rgba(204,0,0,0.6)'; }}
            onMouseLeave={e => { (e.currentTarget as HTMLElement).style.boxShadow = '0 4px 16px rgba(204,0,0,0.4)'; }}
          >
            Enter <ArrowRight size={16} />
          </button>

          <p className="text-center text-[10px] mt-6" style={{ color: 'var(--text-muted)' }}>
            Your ROMs, saves, and BIOS files are stored locally in your browser.
          </p>
        </div>
      </div>
    </div>
  );
}
