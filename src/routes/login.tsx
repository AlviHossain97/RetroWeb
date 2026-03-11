import { useState } from "react";
import { useNavigate } from "react-router";
import { Gamepad2, Eye, EyeOff, User, Lock, ArrowRight } from "lucide-react";
import LoaderOverlay from "../components/LoaderOverlay";

export default function Login() {
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const enterApp = () => {
    setLoading(true);
    sessionStorage.setItem("retroweb.loggedIn", "true");
    setTimeout(() => navigate("/"), 2500);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!username.trim() || !password.trim()) {
      setError("Please fill in all fields.");
      return;
    }
    setError("");
    enterApp();
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
            <h1 className="text-2xl font-bold tracking-tight" style={{ color: 'var(--text-primary)' }}>Welcome Back</h1>
            <p className="text-sm mt-1" style={{ color: 'var(--text-muted)' }}>Sign in to your vault</p>
          </div>

          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            {/* Username */}
            <div className="relative">
              <User size={16} className="absolute left-3 top-1/2 -translate-y-1/2" style={{ color: 'var(--text-muted)' }} />
              <input
                type="text"
                placeholder="Username or email"
                value={username}
                onChange={e => setUsername(e.target.value)}
                className="w-full rounded-xl pl-10 pr-4 py-3 text-sm outline-none transition-all"
                style={{
                  background: 'var(--surface-2)',
                  border: '2px solid var(--border-soft)',
                  color: 'var(--text-primary)',
                  boxShadow: '2px 2px 0px var(--border-soft)',
                }}
                onFocus={e => { (e.target as HTMLInputElement).style.boxShadow = '2px 2px 0px rgba(204,0,0,0.5)'; (e.target as HTMLInputElement).style.borderColor = 'rgba(204,0,0,0.5)'; }}
                onBlur={e => { (e.target as HTMLInputElement).style.boxShadow = '2px 2px 0px var(--border-soft)'; (e.target as HTMLInputElement).style.borderColor = 'var(--border-soft)'; }}
              />
            </div>

            {/* Password */}
            <div className="relative">
              <Lock size={16} className="absolute left-3 top-1/2 -translate-y-1/2" style={{ color: 'var(--text-muted)' }} />
              <input
                type={showPassword ? "text" : "password"}
                placeholder="Password"
                value={password}
                onChange={e => setPassword(e.target.value)}
                className="w-full rounded-xl pl-10 pr-10 py-3 text-sm outline-none transition-all"
                style={{
                  background: 'var(--surface-2)',
                  border: '2px solid var(--border-soft)',
                  color: 'var(--text-primary)',
                  boxShadow: '2px 2px 0px var(--border-soft)',
                }}
                onFocus={e => { (e.target as HTMLInputElement).style.boxShadow = '2px 2px 0px rgba(204,0,0,0.5)'; (e.target as HTMLInputElement).style.borderColor = 'rgba(204,0,0,0.5)'; }}
                onBlur={e => { (e.target as HTMLInputElement).style.boxShadow = '2px 2px 0px var(--border-soft)'; (e.target as HTMLInputElement).style.borderColor = 'var(--border-soft)'; }}
              />
              <button
                type="button"
                onClick={() => setShowPassword(p => !p)}
                className="absolute right-3 top-1/2 -translate-y-1/2"
                style={{ color: 'var(--text-muted)' }}
              >
                {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>

            {/* Remember me + Forgot */}
            <div className="flex items-center justify-between text-sm">
              <label className="flex items-center gap-2 cursor-pointer" style={{ color: 'var(--text-muted)' }}>
                <input
                  type="checkbox"
                  checked={rememberMe}
                  onChange={e => setRememberMe(e.target.checked)}
                  className="w-4 h-4 rounded accent-[var(--accent-primary)]"
                />
                Remember me
              </label>
              <button type="button" className="text-xs transition-colors" style={{ color: 'var(--accent-primary)' }}>
                Forgot password?
              </button>
            </div>

            {/* Error */}
            {error && (
              <p className="text-xs text-center py-2 rounded-lg" style={{ background: 'rgba(239,68,68,0.1)', color: '#ef4444', border: '1px solid rgba(239,68,68,0.2)' }}>
                {error}
              </p>
            )}

            {/* Sign In button */}
            <button
              type="submit"
              className="w-full py-3 rounded-xl font-bold text-sm transition-all flex items-center justify-center gap-2 mt-1"
              style={{
                background: 'linear-gradient(135deg, #cc0000, #ff4400)',
                color: '#fff',
                boxShadow: '0 4px 16px rgba(204,0,0,0.4)',
              }}
              onMouseEnter={e => { (e.currentTarget as HTMLElement).style.boxShadow = '0 6px 20px rgba(204,0,0,0.6)'; }}
              onMouseLeave={e => { (e.currentTarget as HTMLElement).style.boxShadow = '0 4px 16px rgba(204,0,0,0.4)'; }}
            >
              Sign In <ArrowRight size={16} />
            </button>

            {/* Separator */}
            <div className="flex items-center gap-3 my-1">
              <div className="flex-1 h-px" style={{ background: 'var(--border-soft)' }} />
              <span className="text-xs" style={{ color: 'var(--text-muted)' }}>or</span>
              <div className="flex-1 h-px" style={{ background: 'var(--border-soft)' }} />
            </div>

            {/* Continue without signing in */}
            <button
              type="button"
              onClick={() => enterApp()}
              className="w-full py-3 rounded-xl font-bold text-sm transition-all"
              style={{
                background: 'var(--surface-2)',
                color: 'var(--text-secondary)',
                border: '1px solid var(--border-soft)',
              }}
              onMouseEnter={e => { (e.currentTarget as HTMLElement).style.color = 'var(--text-primary)'; (e.currentTarget as HTMLElement).style.borderColor = 'var(--border-strong, var(--border-soft))'; }}
              onMouseLeave={e => { (e.currentTarget as HTMLElement).style.color = 'var(--text-secondary)'; (e.currentTarget as HTMLElement).style.borderColor = 'var(--border-soft)'; }}
            >
              Continue without signing in
            </button>
          </form>

          {/* Sign up link */}
          <p className="text-center text-xs mt-6" style={{ color: 'var(--text-muted)' }}>
            New here?{" "}
            <button type="button" className="font-bold transition-colors" style={{ color: 'var(--accent-primary)' }}>
              Create account →
            </button>
          </p>


        </div>
      </div>
    </div>
  );
}
