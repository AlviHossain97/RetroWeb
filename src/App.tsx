import { Outlet, Link, useLocation, Navigate, useNavigate } from "react-router";
import type { ReactNode } from "react";
import { Gamepad2, LibraryBig, Settings2, Cpu, Save, LogOut, MessageCircle, Home, Download, X } from "lucide-react";
import { useState, useCallback, useEffect, useRef, useMemo, lazy, Suspense } from "react";
import { Toaster, toast } from "sonner";
import { validateBiosFilename, saveBIOS } from "./lib/storage/db";

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

/* From Uiverse.io by vinodjangid07 — logout button */
const LOGOUT_CSS = `
.rw-logout-btn {
  display: flex;
  align-items: center;
  justify-content: flex-start;
  width: 45px;
  height: 45px;
  border: none;
  border-radius: 50%;
  cursor: pointer;
  position: relative;
  z-index: 30;
  overflow: hidden;
  transition-duration: .3s;
  box-shadow: 2px 2px 10px rgba(0, 0, 0, 0.199);
  background-color: var(--accent-primary);
}

.rw-logout-btn .rw-logout-sign {
  width: 100%;
  transition-duration: .3s;
  display: flex;
  align-items: center;
  justify-content: center;
}

.rw-logout-btn .rw-logout-sign svg {
  width: 17px;
  height: 17px;
}

.rw-logout-btn .rw-logout-sign svg path {
  fill: white;
}

.rw-logout-btn .rw-logout-text {
  position: absolute;
  right: 0%;
  width: 0%;
  opacity: 0;
  color: white;
  font-size: 1.2em;
  font-weight: 600;
  transition-duration: .3s;
}

.rw-logout-btn:hover {
  width: 125px;
  border-radius: 40px;
  transition-duration: .3s;
}

.rw-logout-btn:hover .rw-logout-sign {
  width: 30%;
  transition-duration: .3s;
  padding-left: 20px;
}

.rw-logout-btn:hover .rw-logout-text {
  opacity: 1;
  width: 70%;
  transition-duration: .3s;
  padding-right: 10px;
}

.rw-logout-btn:active {
  transform: translate(2px, 2px);
}
`;

export default function App() {
  const [isGlobalDragging, setIsGlobalDragging] = useState(false);
  const [showInstallBanner, setShowInstallBanner] = useState(false);
  const deferredPromptRef = useRef<BeforeInstallPromptEvent | null>(null);
  const location = useLocation();
  const navigate = useNavigate();

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

  const isPlaying = location.pathname === "/play";
  const isLoggedIn = sessionStorage.getItem("retroweb.loggedIn") === "true";

  // Offline mode indicator
  const [isOffline, setIsOffline] = useState(!navigator.onLine);
  useEffect(() => {
    const goOffline = () => setIsOffline(true);
    const goOnline = () => setIsOffline(false);
    window.addEventListener("offline", goOffline);
    window.addEventListener("online", goOnline);
    return () => { window.removeEventListener("offline", goOffline); window.removeEventListener("online", goOnline); };
  }, []);

  const handleLogout = useCallback(() => {
    sessionStorage.removeItem("retroweb.loggedIn");
    navigate("/login");
  }, [navigate]);

  const handleDrop = useCallback(
    async (e: React.DragEvent) => {
      e.preventDefault();
      setIsGlobalDragging(false);

      if (!e.dataTransfer.files?.length) return;

      const files = Array.from(e.dataTransfer.files);
      let biosInstalled = 0;

      for (const file of files) {
        const validation = validateBiosFilename(file.name);
        if (!validation.isValid || !validation.systemId || !validation.expectedName) {
          continue;
        }

        try {
          const buffer = await file.arrayBuffer();
          await saveBIOS(validation.expectedName, validation.systemId, new Uint8Array(buffer), {
            sourceFilename: file.name,
          });
          biosInstalled++;
          toast.success(`✅ Installed BIOS: ${validation.expectedName}`);
        } catch (error) {
          console.error("Failed to install dropped BIOS", error);
          toast.error(`Failed to install ${file.name}`);
        }
      }

      if (biosInstalled === 0 && location.pathname !== "/" && location.pathname !== "/library") {
        toast.warning("Not a recognized BIOS file. Drop ROMs on the Library page.");
      }
    },
    [location.pathname]
  );

  const handleDragOver = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      if (!isPlaying) {
        setIsGlobalDragging(true);
      }
    },
    [isPlaying]
  );

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    if (e.clientX === 0 || e.clientY === 0) {
      setIsGlobalDragging(false);
    }
  }, []);

  useEffect(() => {
    const handleWindowDrop = (e: DragEvent) => {
      e.preventDefault();
      setIsGlobalDragging(false);
    };

    window.addEventListener("drop", handleWindowDrop);
    return () => window.removeEventListener("drop", handleWindowDrop);
  }, []);

  const navItems = useMemo(() => [
    { to: "/", label: "Home", icon: <Home size={18} /> },
    { to: "/library", label: "Library", icon: <LibraryBig size={18} /> },
    { to: "/systems", label: "Supported Systems", icon: <Gamepad2 size={18} /> },
    { to: "/bios", label: "BIOS Vault", icon: <Cpu size={18} /> },
    { to: "/saves", label: "Saves Vault", icon: <Save size={18} /> },
    { to: "/controller", label: "Controller Test", icon: <Gamepad2 size={18} /> },
    { to: "/chat", label: "AI Chat", icon: <MessageCircle size={18} /> },
    { to: "/settings", label: "Settings", icon: <Settings2 size={18} /> },
  ] satisfies NavItem[], []);

  if (!isLoggedIn) {
    return <Navigate to="/login" replace />;
  }

  return (
    <div
      className="min-h-screen bg-background text-foreground flex flex-col relative"
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      <style dangerouslySetInnerHTML={{ __html: NAV_CSS + LOGOUT_CSS }} />

      {isGlobalDragging && !isPlaying && location.pathname !== "/" && (
        <div className="absolute inset-0 z-50 bg-black/80 backdrop-blur-sm flex flex-col items-center justify-center border-4 border-dashed border-primary m-4 rounded-xl pointer-events-none">
          <Cpu className="text-primary w-24 h-24 mb-6 animate-pulse" />
          <h2 className="text-3xl font-bold text-white mb-2">Drop BIOS Here</h2>
          <p className="text-neutral-300 text-lg">We&apos;ll validate and install it automatically.</p>
        </div>
      )}

      {/* PWA Install Banner */}
      {showInstallBanner && !isPlaying && (
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
        className={
          isPlaying
            ? "w-full h-screen bg-black"
            : "flex-1 flex flex-col relative overflow-hidden bg-background pt-20 pb-16 md:pb-0 page-transition"
        }
      >
        {!isPlaying && <Suspense fallback={null}><PongBackground /></Suspense>}
        <Outlet />
      </main>

      {/* Fixed top-left nav — Uiverse by Admin12121 (hidden on mobile) */}
      {!isPlaying && (
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
      )}

      {/* Mobile bottom tab bar */}
      {!isPlaying && (
        <nav className="md:hidden fixed bottom-0 left-0 right-0 z-30 flex justify-around items-center py-2 px-1" style={{ background: 'var(--surface-1)', borderTop: '1px solid var(--border-soft)' }}>
          {[
            { to: "/", label: "Home", icon: <Home size={20} /> },
            { to: "/library", label: "Library", icon: <LibraryBig size={20} /> },
            { to: "/chat", label: "Chat", icon: <MessageCircle size={20} /> },
            { to: "/saves", label: "Saves", icon: <Save size={20} /> },
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
      )}

      {/* Fixed top-right controls */}
      {!isPlaying && (
        <div className="fixed top-4 right-4 z-40 flex items-center gap-2">
          <Suspense fallback={null}><NotificationCenter /></Suspense>
          <button className="rw-logout-btn" onClick={handleLogout}>
            <span className="rw-logout-sign">
              <LogOut size={17} color="white" />
            </span>
            <span className="rw-logout-text">Logout</span>
          </button>
        </div>
      )}
    </div>
  );
}
