import { Outlet, Link, useLocation } from "react-router";
import type { ReactNode } from "react";
import {
  Gamepad2,
  LibraryBig,
  Settings2,
  Menu,
  X,
  Cpu,
  Save,
  Zap,
  ChevronRight,
} from "lucide-react";
import { useState, useCallback, useEffect } from "react";
import { Toaster, toast } from "sonner";
import LegalModal from "./components/LegalModal";
import CookieConsent from "./components/CookieConsent";
import { validateBiosFilename, saveBIOS } from "./lib/storage/db";

function isActivePath(currentPath: string, targetPath: string) {
  if (targetPath === "/") return currentPath === "/";
  return currentPath.startsWith(targetPath);
}

interface NavItem {
  to: string;
  label: string;
  icon: ReactNode;
  description?: string;
}

const navItems: NavItem[] = [
  { to: "/", label: "Library", icon: <LibraryBig size={20} />, description: "Browse & play games" },
  { to: "/systems", label: "Systems", icon: <Gamepad2 size={20} />, description: "Supported platforms" },
  { to: "/bios", label: "BIOS Vault", icon: <Cpu size={20} />, description: "Firmware files" },
  { to: "/saves", label: "Saves", icon: <Save size={20} />, description: "Save management" },
  { to: "/settings", label: "Settings", icon: <Settings2 size={20} />, description: "Preferences" },
];

export default function App() {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [isGlobalDragging, setIsGlobalDragging] = useState(false);
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const location = useLocation();

  const isPlaying = location.pathname === "/play";

  const closeMenu = () => setIsMobileMenuOpen(false);

  useEffect(() => {
    setIsMobileMenuOpen(false);
  }, [location.pathname]);

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
          toast.success(`Installed BIOS: ${validation.expectedName}`);
        } catch (error) {
          console.error("Failed to install dropped BIOS", error);
          toast.error(`Failed to install ${file.name}`);
        }
      }

      if (biosInstalled === 0 && location.pathname !== "/") {
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

  return (
    <div
      className="min-h-screen bg-background text-foreground flex md:flex-row flex-col relative"
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      {isGlobalDragging && !isPlaying && location.pathname !== "/" && (
        <div className="absolute inset-0 z-50 bg-black/85 backdrop-blur-md flex flex-col items-center justify-center border-2 border-dashed border-primary m-4 rounded-2xl pointer-events-none">
          <div className="relative">
            <div className="absolute inset-0 bg-primary/20 rounded-full blur-3xl scale-150" />
            <Cpu className="text-primary w-20 h-20 mb-6 animate-pulse relative z-10" />
          </div>
          <h2 className="text-3xl font-bold text-white mb-2">Drop BIOS Here</h2>
          <p className="text-muted-foreground text-lg">We'll validate and install it automatically.</p>
        </div>
      )}

      <Toaster
        theme="dark"
        position="bottom-right"
        toastOptions={{
          style: {
            background: "var(--card)",
            border: "1px solid var(--border)",
            color: "var(--foreground)",
          },
        }}
      />
      <LegalModal />
      <CookieConsent />

      {/* Mobile header */}
      {!isPlaying && (
        <header className="md:hidden flex items-center justify-between px-4 py-3 border-b border-border bg-sidebar/95 backdrop-blur-lg z-30 sticky top-0">
          <Link to="/" className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-primary/10 border border-primary/20 flex items-center justify-center">
              <Zap className="text-primary" size={18} />
            </div>
            <h1 className="text-lg font-bold tracking-tight text-foreground">PiStation</h1>
          </Link>
          <button
            onClick={() => setIsMobileMenuOpen((prev) => !prev)}
            className="p-2 text-muted-foreground hover:text-foreground rounded-lg hover:bg-secondary transition-colors"
            aria-label="Toggle menu"
          >
            {isMobileMenuOpen ? <X size={22} /> : <Menu size={22} />}
          </button>
        </header>
      )}

      {/* Mobile menu overlay */}
      {isMobileMenuOpen && !isPlaying && (
        <div className="md:hidden fixed inset-0 top-[57px] z-30">
          <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={closeMenu} />
          <nav className="relative bg-sidebar border-r border-border w-72 h-full p-4 flex flex-col gap-1 overflow-y-auto animate-in slide-in-from-left duration-200">
            {navItems.map((item) => {
              const active = isActivePath(location.pathname, item.to);
              return (
                <Link
                  key={item.to}
                  to={item.to}
                  onClick={closeMenu}
                  className={`flex items-center gap-3 px-4 py-3 rounded-lg text-sm transition-all ${
                    active
                      ? "bg-primary/10 text-primary font-semibold border border-primary/20"
                      : "text-muted-foreground hover:bg-secondary hover:text-foreground border border-transparent"
                  }`}
                >
                  {item.icon}
                  <div className="flex flex-col">
                    <span>{item.label}</span>
                    {item.description && (
                      <span className="text-[11px] text-muted-foreground font-normal">{item.description}</span>
                    )}
                  </div>
                </Link>
              );
            })}
          </nav>
        </div>
      )}

      {/* Desktop sidebar */}
      {!isPlaying && (
        <aside
          className={`hidden md:flex flex-col bg-sidebar border-r border-border h-screen sticky top-0 transition-all duration-300 ${
            isSidebarCollapsed ? "w-[72px]" : "w-[260px]"
          }`}
        >
          <div className={`flex items-center gap-3 px-5 pt-6 pb-4 ${isSidebarCollapsed ? "justify-center" : ""}`}>
            <div className="w-10 h-10 rounded-xl bg-primary/10 border border-primary/20 flex items-center justify-center shrink-0 glow-primary">
              <Zap className="text-primary" size={22} />
            </div>
            {!isSidebarCollapsed && (
              <div className="flex flex-col">
                <h1 className="text-xl font-bold tracking-tight text-foreground">PiStation</h1>
                <span className="text-[10px] text-muted-foreground uppercase tracking-widest font-medium">
                  Gaming Hub
                </span>
              </div>
            )}
          </div>

          <div className="mx-4 mb-2 h-px bg-border" />

          <nav className="flex-1 flex flex-col gap-0.5 px-3 py-2">
            {navItems.map((item) => {
              const active = isActivePath(location.pathname, item.to);
              return (
                <Link
                  key={item.to}
                  to={item.to}
                  title={isSidebarCollapsed ? item.label : undefined}
                  className={`group flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-all relative ${
                    active
                      ? "bg-primary/10 text-primary font-semibold"
                      : "text-muted-foreground hover:bg-secondary/60 hover:text-foreground"
                  } ${isSidebarCollapsed ? "justify-center" : ""}`}
                >
                  {active && (
                    <div className="absolute left-0 top-1/2 -translate-y-1/2 w-[3px] h-5 bg-primary rounded-r-full" />
                  )}
                  <span className={`shrink-0 transition-transform ${active ? "scale-110" : "group-hover:scale-105"}`}>
                    {item.icon}
                  </span>
                  {!isSidebarCollapsed && (
                    <>
                      <span className="flex-1">{item.label}</span>
                      {active && <ChevronRight size={14} className="text-primary/50" />}
                    </>
                  )}
                </Link>
              );
            })}
          </nav>

          <div className="px-3 pb-2">
            <button
              onClick={() => setIsSidebarCollapsed(!isSidebarCollapsed)}
              className="w-full flex items-center justify-center py-2 rounded-lg text-muted-foreground hover:text-foreground hover:bg-secondary/60 transition-colors"
              title={isSidebarCollapsed ? "Expand sidebar" : "Collapse sidebar"}
            >
              <ChevronRight
                size={16}
                className={`transition-transform duration-300 ${isSidebarCollapsed ? "" : "rotate-180"}`}
              />
            </button>
          </div>

          {!isSidebarCollapsed && (
            <div className="px-5 pb-4 pt-2 border-t border-border">
              <div className="flex items-center gap-2 text-[11px] text-muted-foreground font-mono">
                <div className="w-1.5 h-1.5 rounded-full bg-[var(--success)] animate-pulse" />
                <span>v0.3.0</span>
                <span className="text-border">|</span>
                <span>WASM Ready</span>
              </div>
            </div>
          )}
        </aside>
      )}

      <main
        className={
          isPlaying
            ? "w-full h-screen bg-black"
            : "flex-1 flex flex-col relative overflow-hidden bg-background min-h-screen"
        }
      >
        <Outlet />
      </main>
    </div>
  );
}
