import { Outlet, Link, useLocation } from "react-router";
import type { ReactNode } from "react";
import { Gamepad2, LibraryBig, Settings2, Menu, X, Cpu, Save } from "lucide-react";
import { useState, useCallback, useEffect } from "react";
import { Toaster, toast } from "sonner";
import LegalModal from "./components/LegalModal";
import { validateBiosFilename, saveBIOS } from "./lib/storage/db";

function isActivePath(currentPath: string, targetPath: string) {
  if (targetPath === "/") return currentPath === "/";
  return currentPath.startsWith(targetPath);
}

interface NavItem {
  to: string;
  label: string;
  icon: ReactNode;
}

interface NavLinksProps {
  items: NavItem[];
  currentPath: string;
  onNavigate: () => void;
}

function NavLinks({ items, currentPath, onNavigate }: NavLinksProps) {
  return (
    <>
      {items.map((item) => {
        const active = isActivePath(currentPath, item.to);
        return (
          <Link
            key={item.to}
            to={item.to}
            onClick={onNavigate}
            className={`flex items-center gap-3.5 px-6 py-3 font-sans text-sm transition-colors ${active ? "bg-primary text-primary-foreground font-bold" : "text-muted-foreground hover:bg-[#333333]/50 hover:text-foreground"
              } border-l-4 ${active ? "border-white" : "border-transparent"}`}
          >
            {item.icon}
            {item.label}
          </Link>
        );
      })}
    </>
  );
}

export default function App() {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [isGlobalDragging, setIsGlobalDragging] = useState(false);
  const location = useLocation();

  const isPlaying = location.pathname === "/play";

  const closeMenu = () => setIsMobileMenuOpen(false);

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

  const navItems = [
    { to: "/", label: "Library", icon: <LibraryBig size={18} /> },
    { to: "/systems", label: "Supported Systems", icon: <Gamepad2 size={18} /> },
    { to: "/bios", label: "BIOS Vault", icon: <Cpu size={18} /> },
    { to: "/saves", label: "Saves Vault", icon: <Save size={18} /> },
    { to: "/settings", label: "Settings", icon: <Settings2 size={18} /> },
  ] satisfies NavItem[];

  return (
    <div
      className="min-h-screen bg-background text-foreground flex md:flex-row flex-col relative"
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      {isGlobalDragging && !isPlaying && location.pathname !== "/" && (
        <div className="absolute inset-0 z-50 bg-black/80 backdrop-blur-sm flex flex-col items-center justify-center border-4 border-dashed border-primary m-4 rounded-xl pointer-events-none">
          <Cpu className="text-primary w-24 h-24 mb-6 animate-pulse" />
          <h2 className="text-3xl font-bold text-white mb-2">Drop BIOS Here</h2>
          <p className="text-neutral-300 text-lg">We&apos;ll validate and install it automatically.</p>
        </div>
      )}

      <Toaster theme="dark" position="bottom-right" />
      <LegalModal />

      {!isPlaying && (
        <header className="md:hidden flex items-center justify-between p-4 border-b border-neutral-800 bg-neutral-950 z-20 sticky top-0">
          <div className="flex items-center gap-2">
            <Gamepad2 className="text-primary" size={24} />
            <h1 className="text-xl font-bold tracking-tight">RetroWeb</h1>
          </div>
          <button onClick={() => setIsMobileMenuOpen((prev) => !prev)} className="p-2 text-neutral-400 hover:text-white">
            {isMobileMenuOpen ? <X size={24} /> : <Menu size={24} />}
          </button>
        </header>
      )}

      {isMobileMenuOpen && !isPlaying && (
        <div className="md:hidden fixed inset-0 top-[73px] bg-neutral-950 z-20 p-4 flex flex-col gap-2 border-t border-neutral-800">
          <NavLinks items={navItems} currentPath={location.pathname} onNavigate={closeMenu} />
        </div>
      )}

      {!isPlaying && (
        <aside className="hidden md:flex flex-col w-[260px] bg-sidebar border-r border-border h-screen sticky top-0 py-8">
          <div className="flex items-center mb-8 px-7 gap-3">
            <Gamepad2 className="text-primary" size={28} />
            <h1 className="text-[24px] font-bold tracking-tight text-foreground">RetroWeb</h1>
          </div>
          <nav className="flex-1 flex flex-col">
            <NavLinks items={navItems} currentPath={location.pathname} onNavigate={closeMenu} />
          </nav>
          <div className="mt-auto px-7 pb-4">
            <p className="text-xs text-muted-foreground font-mono">v0.2.0 • WASM Powered</p>
          </div>
        </aside>
      )}

      <main className={isPlaying ? "w-full h-screen bg-black" : "flex-1 flex flex-col relative overflow-hidden bg-background"}>
        <Outlet />
      </main>
    </div>
  );
}