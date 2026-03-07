import { useState, useEffect } from "react";
import { Cookie, ChevronDown, ChevronUp, Shield } from "lucide-react";

const STORAGE_KEY = "retroweb_cookie_consent";

interface ConsentState {
  essential: true;
  analytics: boolean;
  personalisation: boolean;
  decided: boolean;
}

export default function CookieConsent() {
  const [visible, setVisible] = useState(false);
  const [expanded, setExpanded] = useState(false);
  const [consent, setConsent] = useState<ConsentState>({
    essential: true,
    analytics: false,
    personalisation: false,
    decided: false,
  });

  useEffect(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (!stored) {
      const timer = setTimeout(() => setVisible(true), 1500);
      return () => clearTimeout(timer);
    }
  }, []);

  const save = (state: ConsentState) => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    setVisible(false);
  };

  const acceptAll = () => save({ essential: true, analytics: true, personalisation: true, decided: true });
  const rejectOptional = () => save({ essential: true, analytics: false, personalisation: false, decided: true });
  const savePreferences = () => save({ ...consent, decided: true });

  if (!visible) return null;

  return (
    <div
      className="fixed bottom-4 right-4 z-[60] w-full max-w-sm rounded-xl p-5 shadow-2xl"
      style={{
        background: 'var(--surface-1)',
        border: '1px solid var(--border-strong)',
        animation: 'fadeSlideIn 0.4s ease forwards',
      }}
    >
      <div className="flex items-start gap-3 mb-3">
        <div className="p-2 rounded-lg shrink-0" style={{ background: 'var(--surface-3)' }}>
          <Cookie size={18} style={{ color: 'var(--accent-primary)' }} />
        </div>
        <div>
          <h3 className="font-bold text-sm mb-1" style={{ color: 'var(--text-primary)' }}>Cookie Preferences</h3>
          <p className="text-xs leading-relaxed" style={{ color: 'var(--text-secondary)' }}>
            We use cookies to improve your experience. Essential cookies keep things working.
          </p>
        </div>
      </div>

      {expanded && (
        <div className="mb-4 space-y-3 pt-3" style={{ borderTop: '1px solid var(--border-soft)' }}>
          {[
            { key: 'essential', label: 'Essential', desc: 'Required for core functionality. Cannot be disabled.', locked: true },
            { key: 'analytics', label: 'Analytics', desc: 'Help us understand how the app is used.' },
            { key: 'personalisation', label: 'Personalisation', desc: 'Remember your preferences and settings.' },
          ].map((item) => (
            <div key={item.key} className="flex items-start justify-between gap-3">
              <div className="flex-1">
                <div className="flex items-center gap-1.5 mb-0.5">
                  <Shield size={12} style={{ color: item.locked ? 'var(--success)' : 'var(--text-muted)' }} />
                  <span className="text-xs font-semibold" style={{ color: 'var(--text-primary)' }}>{item.label}</span>
                  {item.locked && (
                    <span className="text-[10px] px-1.5 py-0.5 rounded" style={{ background: 'var(--surface-3)', color: 'var(--success)' }}>
                      Always On
                    </span>
                  )}
                </div>
                <p className="text-[11px]" style={{ color: 'var(--text-muted)' }}>{item.desc}</p>
              </div>
              <button
                disabled={item.locked}
                onClick={() => {
                  if (item.key === 'analytics') setConsent(p => ({ ...p, analytics: !p.analytics }));
                  if (item.key === 'personalisation') setConsent(p => ({ ...p, personalisation: !p.personalisation }));
                }}
                className="shrink-0 w-10 h-5 rounded-full transition-colors duration-200 relative disabled:opacity-60"
                style={{
                  background: (item.locked || consent[item.key as keyof ConsentState]) ? 'var(--accent-primary)' : 'var(--surface-3)',
                }}
              >
                <span
                  className="absolute top-0.5 w-4 h-4 rounded-full bg-white transition-transform duration-200"
                  style={{ transform: (item.locked || consent[item.key as keyof ConsentState]) ? 'translateX(20px)' : 'translateX(2px)' }}
                />
              </button>
            </div>
          ))}
          <button
            onClick={savePreferences}
            className="w-full text-xs font-bold py-2 rounded-lg transition-colors"
            style={{ background: 'var(--surface-3)', color: 'var(--text-primary)' }}
          >
            Save Preferences
          </button>
        </div>
      )}

      <div className="flex gap-2 mt-3">
        <button
          onClick={rejectOptional}
          className="flex-1 text-xs font-bold py-2 rounded-lg transition-colors"
          style={{ background: 'var(--surface-3)', color: 'var(--text-secondary)' }}
        >
          Reject
        </button>
        <button
          onClick={() => setExpanded(p => !p)}
          className="flex items-center gap-1 text-xs py-2 px-3 rounded-lg transition-colors"
          style={{ background: 'var(--surface-3)', color: 'var(--text-muted)' }}
        >
          Options {expanded ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
        </button>
        <button
          onClick={acceptAll}
          className="flex-1 text-xs font-bold py-2 rounded-lg transition-colors"
          style={{ background: 'var(--accent-primary)', color: '#fff' }}
        >
          Accept All
        </button>
      </div>
    </div>
  );
}
