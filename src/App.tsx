import { Outlet, Link, useLocation } from "react-router";
import type { ReactNode } from "react";
import { Gamepad2, Settings2, MessageCircle, Home, Download, X, LayoutDashboard, Activity, Monitor, Trophy, BarChart3 } from "lucide-react";
import { useState, useEffect, useRef, useMemo, lazy, Suspense } from "react";
import { Toaster, toast } from "sonner";
import { useInputMode } from "@/hooks/useInputMode";
import { useGamepadNavigation } from "@/hooks/useGamepadNavigation";
import { RetroPiece } from "@/components/RetroPiece";

// Lazy-load heavy shell components (not on critical render path)
const LegalModal = lazy(() => import("./components/LegalModal"));
const CookieConsent = lazy(() => import("./components/CookieConsent"));
const PacmanGhostEasterEgg = lazy(() => import("./components/PacmanGhostEasterEgg"));
const SynthwaveBackground = lazy(() => import("./components/SynthwaveBackground"));
const OnboardingTutorial = lazy(() => import("./components/OnboardingTutorial"));
const NotificationCenter = lazy(() => import("./components/NotificationCenter"));

interface BeforeInstallPromptEvent extends Event {
  prompt(): Promise<void>;
}

interface NavItem {
  to: string;
  label: string;
  icon: ReactNode;
}

export default function App() {
  const [showInstallBanner, setShowInstallBanner] = useState(false);
  const deferredPromptRef = useRef<BeforeInstallPromptEvent | null>(null);
  const location = useLocation();

  // Controller-first UX: detect input mode and enable gamepad navigation
  const inputMode = useInputMode();
  useGamepadNavigation({ enabled: inputMode === "gamepad" });

  useEffect(() => {
    document.documentElement.setAttribute("data-input-mode", inputMode);
  }, [inputMode]);

  // Apply saved theme + accessibility on mount
  useEffect(() => {
    try {
      const raw = localStorage.getItem("retroweb.settings.v1");
      if (raw) {
        const parsed = JSON.parse(raw);
        if (parsed.theme) document.documentElement.setAttribute("data-theme", parsed.theme);
        if (parsed.highContrast) document.documentElement.classList.add("a11y-high-contrast");
        if (parsed.largeText) document.documentElement.classList.add("a11y-large-text");
        if (parsed.reducedMotion) document.documentElement.classList.add("a11y-reduced-motion");
      }
    } catch { /* noop */ }
  }, []);

  // PWA install prompt
  useEffect(() => {
    const handler = (e: Event) => {
      e.preventDefault();
      deferredPromptRef.current = e as BeforeInstallPromptEvent;
      setShowInstallBanner(true);
    };
    window.addEventListener("beforeinstallprompt", handler);
    return () => window.removeEventListener("beforeinstallprompt", handler);
  }, []);

  const handleInstallPWA = async () => {
    const prompt = deferredPromptRef.current;
    if (!prompt) return;
    await prompt.prompt();
    deferredPromptRef.current = null;
    setShowInstallBanner(false);
  };

  // PWA auto-update notification
  useEffect(() => {
    if (!("serviceWorker" in navigator)) return;
    const handleControllerChange = () => {
      toast.info("🔄 New version available! Refreshing…", { duration: 3000 });
      setTimeout(() => window.location.reload(), 2000);
    };
    navigator.serviceWorker.addEventListener("controllerchange", handleControllerChange);
    // Also check for waiting service worker
    navigator.serviceWorker.ready.then(reg => {
      reg.addEventListener("updatefound", () => {
        const newSW = reg.installing;
        if (!newSW) return;
        newSW.addEventListener("statechange", () => {
          if (newSW.state === "installed" && navigator.serviceWorker.controller) {
            toast("🆕 Update available!", {
              action: { label: "Refresh", onClick: () => window.location.reload() },
              duration: 10000,
            });
          }
        });
      });
    }).catch(() => {});
    return () => navigator.serviceWorker.removeEventListener("controllerchange", handleControllerChange);
  }, []);


  // Offline mode indicator
  const [isOffline, setIsOffline] = useState(!navigator.onLine);
  useEffect(() => {
    const goOffline = () => setIsOffline(true);
    const goOnline = () => setIsOffline(false);
    window.addEventListener("offline", goOffline);
    window.addEventListener("online", goOnline);
    return () => { window.removeEventListener("offline", goOffline); window.removeEventListener("online", goOnline); };
  }, []);

  const navItems = useMemo(() => [
    { to: "/", label: "Home", icon: <Home size={18} /> },
    { to: "/dashboard", label: "Dashboard", icon: <LayoutDashboard size={18} /> },
    { to: "/sessions", label: "Sessions", icon: <Activity size={18} /> },
    { to: "/games", label: "Games", icon: <Gamepad2 size={18} /> },
    { to: "/systems", label: "Systems", icon: <Gamepad2 size={18} /> },
    { to: "/devices", label: "Devices", icon: <Monitor size={18} /> },
    { to: "/chat", label: "Chat", icon: <MessageCircle size={18} /> },
    { to: "/controller", label: "Controller", icon: <Gamepad2 size={18} /> },
    { to: "/achievements", label: "Achievements", icon: <Trophy size={18} /> },
    { to: "/stats", label: "Stats", icon: <BarChart3 size={18} /> },
    { to: "/settings", label: "Settings", icon: <Settings2 size={18} /> },
  ] satisfies NavItem[], []);

  const isRouteActive = (to: string) => {
    if (to === "/") return location.pathname === "/";
    return location.pathname === to || location.pathname.startsWith(`${to}/`);
  };

  const shellTop = isOffline ? 48 : 16;
  const mainPaddingTop = isOffline ? 124 : 92;

  return (
    <div
      className="retro-shell min-h-screen bg-background text-foreground flex flex-col relative"
    >
      {/* PWA Install Banner */}
      {showInstallBanner && (
        <div className="retro-banner fixed bottom-4 left-4 right-4 md:left-auto md:right-4 md:w-[22rem] z-40 rounded-[1.4rem] p-4 flex items-center gap-3">
          <Download size={24} style={{ color: 'var(--accent-primary)', flexShrink: 0 }} />
          <div className="flex-1 min-w-0">
            <p className="text-sm font-semibold uppercase tracking-[0.16em]" style={{ color: 'var(--text-primary)' }}>Install PiStation</p>
            <p className="text-xs" style={{ color: 'var(--text-muted)' }}>Add to home screen for the best experience</p>
          </div>
          <button onClick={() => void handleInstallPWA()} className="retro-button px-4 py-2 min-h-0 text-[0.56rem]">
            Install
          </button>
          <button onClick={() => setShowInstallBanner(false)} className="retro-button retro-button--ghost retro-icon-button min-h-0 text-[0.56rem]" style={{ minWidth: '3rem' }}>
            <X size={14} />
          </button>
        </div>
      )}

      {/* Offline mode indicator */}
      {isOffline && (
        <div className="fixed top-0 left-0 right-0 z-50 text-center py-2 text-[0.62rem] font-bold tracking-[0.2em] uppercase" style={{ background: 'linear-gradient(90deg, rgba(204,0,0,0.96), rgba(229,20,0,0.96))', color: '#f0f0f5', boxShadow: '0 8px 24px rgba(0,0,0,0.28)' }}>
          Offline Mode: AI features and cloud sync are unavailable. Local games still work.
        </div>
      )}

      <Toaster theme="dark" position="bottom-right" />
      <Suspense fallback={null}>
        <LegalModal />
        <CookieConsent />
        <OnboardingTutorial />
        <PacmanGhostEasterEgg frightenThreshold={5} frightenDuration={4000} />
      </Suspense>

      <header className="retro-topbar" style={{ top: `${shellTop}px` }}>
        <div className="retro-topbar__inner">
          <Link to="/" className="retro-topbar__brand hidden sm:flex" aria-label="Go to PiStation home">
            <RetroPiece size="sm" />
            <span className="retro-topbar__brand-text">PiStation</span>
          </Link>

          <nav className="retro-topbar__scroll" aria-label="Primary navigation">
            <div className="retro-topbar__links">
              {navItems.map((item) => (
                <Link
                  key={item.to}
                  to={item.to}
                  className={`retro-top-link ${isRouteActive(item.to) ? "retro-top-link--active" : ""}`}
                >
                  <span>{item.icon}</span>
                  <span>{item.label}</span>
                </Link>
              ))}
            </div>
          </nav>

          <div className="retro-topbar__actions">
            <Suspense fallback={null}><NotificationCenter /></Suspense>
          </div>
        </div>
      </header>

      <main
        className="retro-main flex-1 flex flex-col relative overflow-hidden bg-background"
        style={{ paddingTop: `${mainPaddingTop}px`, paddingBottom: "1.5rem" }}
      >
        <Suspense fallback={null}><SynthwaveBackground /></Suspense>
        <div key={location.pathname} className="relative z-10 flex flex-1 flex-col min-h-0 page-transition">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
