import { useState, useEffect } from "react";
import { Cookie, Settings2, Check, X } from "lucide-react";

const CONSENT_KEY = "pistation.cookie_consent";

export default function CookieConsent() {
  const [isVisible, setIsVisible] = useState(false);
  const [showPreferences, setShowPreferences] = useState(false);
  const [preferences, setPreferences] = useState({
    essential: true,
    analytics: false,
    personalization: true,
  });

  useEffect(() => {
    const consent = localStorage.getItem(CONSENT_KEY);
    if (!consent) {
      const timer = setTimeout(() => setIsVisible(true), 2000);
      return () => clearTimeout(timer);
    }
  }, []);

  const handleAccept = () => {
    localStorage.setItem(CONSENT_KEY, JSON.stringify({ ...preferences, analytics: true, accepted: true, ts: Date.now() }));
    setIsVisible(false);
  };

  const handleSavePreferences = () => {
    localStorage.setItem(CONSENT_KEY, JSON.stringify({ ...preferences, accepted: true, ts: Date.now() }));
    setIsVisible(false);
  };

  const handleReject = () => {
    localStorage.setItem(CONSENT_KEY, JSON.stringify({ essential: true, analytics: false, personalization: false, accepted: true, ts: Date.now() }));
    setIsVisible(false);
  };

  if (!isVisible) return null;

  return (
    <div className="fixed bottom-6 right-6 z-50 animate-in slide-in-from-bottom-5 duration-500 w-[380px] max-w-[calc(100vw-2rem)]">
      <div className="rounded-2xl overflow-hidden" style={{ boxShadow: "var(--shadow-xl)" }}>
        {/* Main card */}
        <div className="bg-card border border-border rounded-2xl">
          <div className="flex flex-col items-center justify-between pt-8 px-6 pb-6 relative">
            {/* Cookie icon */}
            <span className="relative mx-auto -mt-12 mb-6">
              <div className="w-16 h-16 rounded-2xl bg-primary/10 border border-primary/20 flex items-center justify-center glow-primary">
                <Cookie className="text-primary" size={28} />
              </div>
            </span>

            <h5 className="text-sm font-semibold mb-2 text-left mr-auto text-foreground">
              Your privacy matters
            </h5>

            <p className="w-full mb-4 text-sm text-muted-foreground leading-relaxed">
              We use local storage to save your preferences, game data, and session info.
              Everything stays on your device.
            </p>

            {showPreferences && (
              <div className="w-full mb-4 space-y-3 p-4 bg-secondary rounded-xl border border-border">
                <label className="flex items-center justify-between cursor-not-allowed">
                  <span className="text-sm text-foreground">Essential</span>
                  <div className="w-10 h-6 rounded-full bg-primary/20 border border-primary/30 flex items-center justify-end px-1">
                    <div className="w-4 h-4 rounded-full bg-primary" />
                  </div>
                </label>
                <label className="flex items-center justify-between cursor-pointer" onClick={() => setPreferences(p => ({ ...p, analytics: !p.analytics }))}>
                  <span className="text-sm text-foreground">Analytics</span>
                  <div className={`w-10 h-6 rounded-full border flex items-center px-1 transition-colors ${preferences.analytics ? "bg-primary/20 border-primary/30 justify-end" : "bg-secondary border-border justify-start"}`}>
                    <div className={`w-4 h-4 rounded-full transition-colors ${preferences.analytics ? "bg-primary" : "bg-muted-foreground"}`} />
                  </div>
                </label>
                <label className="flex items-center justify-between cursor-pointer" onClick={() => setPreferences(p => ({ ...p, personalization: !p.personalization }))}>
                  <span className="text-sm text-foreground">Personalization</span>
                  <div className={`w-10 h-6 rounded-full border flex items-center px-1 transition-colors ${preferences.personalization ? "bg-primary/20 border-primary/30 justify-end" : "bg-secondary border-border justify-start"}`}>
                    <div className={`w-4 h-4 rounded-full transition-colors ${preferences.personalization ? "bg-primary" : "bg-muted-foreground"}`} />
                  </div>
                </label>
              </div>
            )}

            <div className="flex w-full gap-2">
              {showPreferences ? (
                <>
                  <button
                    onClick={handleReject}
                    className="flex-1 px-4 py-2.5 text-sm font-medium text-muted-foreground hover:text-foreground border border-border rounded-xl transition-colors hover:bg-secondary"
                  >
                    <X size={14} className="inline mr-1" />
                    Reject
                  </button>
                  <button
                    onClick={handleSavePreferences}
                    className="flex-1 px-4 py-2.5 text-sm font-semibold text-primary-foreground bg-primary hover:bg-primary/90 rounded-xl transition-colors"
                  >
                    <Check size={14} className="inline mr-1" />
                    Save
                  </button>
                </>
              ) : (
                <>
                  <button
                    onClick={() => setShowPreferences(true)}
                    className="flex items-center justify-center gap-1.5 px-4 py-2.5 text-sm font-medium text-muted-foreground hover:text-foreground border border-border rounded-xl transition-colors hover:bg-secondary"
                  >
                    <Settings2 size={14} />
                    Options
                  </button>
                  <button
                    onClick={handleAccept}
                    className="flex-1 px-6 py-2.5 text-sm font-semibold text-primary-foreground bg-primary hover:bg-primary/90 rounded-xl transition-colors glow-primary"
                  >
                    Accept All
                  </button>
                </>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
