import { Outlet, Link, useLocation } from "react-router";
import type { ReactNode } from "react";
import { Gamepad2, Settings2, MessageCircle, Home, Download, X, LayoutDashboard, Activity, Monitor, Trophy, BarChart3 } from "lucide-react";
import { useState, useEffect, useRef, useMemo, lazy, Suspense } from "react";
import { Toaster, toast } from "sonner";
import { useInputMode } from "@/hooks/useInputMode";
import { useGamepadNavigation } from "@/hooks/useGamepadNavigation";

// Lazy-load heavy shell components (not on critical render path)
const LegalModal = lazy(() => import("./components/LegalModal"));
const CookieConsent = lazy(() => import("./components/CookieConsent"));
const PacmanGhostEasterEgg = lazy(() => import("./components/PacmanGhostEasterEgg"));
const PongBackground = lazy(() => import("./components/PongBackground"));
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

/* From Uiverse.io by Admin12121 */
const NAV_CSS = `
.rw-menu {
  padding: 0.5rem;
  background-color: var(--surface-1);
  position: fixed;
  top: 1rem;
  left: 1rem;
  z-index: 30;
  display: flex;
  justify-content: center;
  border-radius: 15px;
  box-shadow: 0 10px 25px 0 rgba(0, 0, 0, 0.4);
  border: 1px solid var(--border-soft);
  color: var(--text-muted);
}

.rw-link {
  display: inline-flex;
  justify-content: center;
  align-items: center;
  width: 70px;
  height: 50px;
  border-radius: 8px;
  position: relative;
  z-index: 1;
  overflow: hidden;
  transform-origin: center left;
  transition: width 0.2s ease-in;
  text-decoration: none;
  color: inherit;
}

.rw-link:before {
  position: absolute;
  z-index: -1;
  content: "";
  display: block;
  border-radius: 8px;
  width: 100%;
  height: 100%;
  top: 0;
  transform: translateX(100%);
  transition: transform 0.2s ease-in;
  transform-origin: center right;
  background-color: rgba(204, 0, 0, 0.15);
}

.rw-link:hover,
.rw-link:focus {
  outline: 0;
  width: 130px;
  color: var(--accent-secondary);
}

.rw-link:hover:before,
.rw-link:focus:before {
  transform: translateX(0);
}

.rw-link:hover .rw-link-title,
.rw-link:focus .rw-link-title {
  transform: translateX(0);
  opacity: 1;
}

.rw-link-icon {
  width: 28px;
  height: 28px;
  display: block;
  flex-shrink: 0;
  left: 18px;
  position: absolute;
}

.rw-link-icon svg {
  width: 28px;
  height: 28px;
}

.rw-link-title {
  transform: translateX(100%);
  transition: transform 0.2s ease-in;
  transform-origin: center right;
  display: block;
  text-align: center;
  text-indent: 28px;
  width: 100%;
}
`;

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

  return (
    <div
      className="min-h-screen bg-background text-foreground flex flex-col relative"
    >
      <style dangerouslySetInnerHTML={{ __html: NAV_CSS }} />

      {/* PWA Install Banner */}
      {showInstallBanner && (
        <div className="fixed bottom-20 md:bottom-4 left-4 right-4 md:left-auto md:right-4 md:w-80 z-40 rounded-xl p-4 flex items-center gap-3 shadow-lg" style={{ background: 'var(--surface-1)', border: '1px solid var(--border-soft)' }}>
          <Download size={24} style={{ color: 'var(--accent-primary)', flexShrink: 0 }} />
          <div className="flex-1 min-w-0">
            <p className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>Install RetroWeb</p>
            <p className="text-xs" style={{ color: 'var(--text-muted)' }}>Add to home screen for the best experience</p>
          </div>
          <button onClick={() => void handleInstallPWA()} className="px-3 py-1.5 rounded-lg text-xs font-bold" style={{ background: 'var(--accent-primary)', color: '#fff' }}>Install</button>
          <button onClick={() => setShowInstallBanner(false)} style={{ color: 'var(--text-muted)' }}><X size={16} /></button>
        </div>
      )}

      {/* Offline mode indicator */}
      {isOffline && (
        <div className="fixed top-0 left-0 right-0 z-50 text-center py-1.5 text-xs font-bold tracking-wider" style={{ background: '#b91c1c', color: '#fff' }}>
          ⚠️ You are offline — AI features and cloud sync are unavailable. Local games still work!
        </div>
      )}

      <Toaster theme="dark" position="bottom-right" />
      <Suspense fallback={null}>
        <LegalModal />
        <CookieConsent />
        <OnboardingTutorial />
        <PacmanGhostEasterEgg frightenThreshold={5} frightenDuration={4000} />
      </Suspense>

      <main
        key={location.pathname}
        className="flex-1 flex flex-col relative overflow-hidden bg-background pt-20 pb-16 md:pb-0 page-transition"
      >
        <Suspense fallback={null}><PongBackground /></Suspense>
        <Outlet />
      </main>

      {/* Fixed top-left nav — Uiverse by Admin12121 (hidden on mobile) */}
      <nav className="rw-menu hidden md:flex">
        {navItems.map(item => (
          <Link
            key={item.to}
            to={item.to}
            className="rw-link"
          >
            <span className="rw-link-icon">{item.icon}</span>
            <span className="rw-link-title">{item.label}</span>
          </Link>
        ))}
      </nav>

      {/* Mobile bottom tab bar */}
      <nav className="md:hidden fixed bottom-0 left-0 right-0 z-30 flex justify-around items-center py-2 px-1" style={{ background: 'var(--surface-1)', borderTop: '1px solid var(--border-soft)' }}>
          {[
            { to: "/", label: "Home", icon: <Home size={20} /> },
            { to: "/dashboard", label: "Dashboard", icon: <LayoutDashboard size={20} /> },
            { to: "/games", label: "Games", icon: <Gamepad2 size={20} /> },
            { to: "/chat", label: "Chat", icon: <MessageCircle size={20} /> },
            { to: "/settings", label: "Settings", icon: <Settings2 size={20} /> },
          ].map(item => (
            <Link
              key={item.to}
              to={item.to}
              className="flex flex-col items-center gap-0.5 text-[10px] transition-colors"
              style={{ color: location.pathname === item.to ? 'var(--accent-primary)' : 'var(--text-muted)' }}
            >
              {item.icon}
              {item.label}
            </Link>
          ))}
        </nav>

      {/* Fixed top-right controls */}
      <div className="fixed top-4 right-4 z-40 flex items-center gap-2">
        <Suspense fallback={null}><NotificationCenter /></Suspense>
      </div>
    </div>
  );
}
