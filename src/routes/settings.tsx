import { useCallback, useEffect, useState } from "react";
import { Copy, RefreshCcw, Search, HardDrive, Cpu, Volume2, Info } from "lucide-react";
import { toast } from "sonner";
import { getStorageEstimate } from "@/lib/capability/storage-quota";
import { getThreadingCapability } from "@/lib/capability/capability-check";
import { useI18n, LANGUAGE_LABELS, type Lang } from "@/lib/i18n";

type SettingsState = {
  volume: number;
  audioLatency: "auto" | "low" | "normal";
  theme: "default" | "nes" | "gameboy" | "snes" | "terminal";
  highContrast: boolean;
  largeText: boolean;
  reducedMotion: boolean;
};

const SETTINGS_KEY = "retroweb.settings.v1";

const DEFAULT_SETTINGS: SettingsState = {
  volume: 100,
  audioLatency: "auto",
  theme: "default",
  highContrast: false,
  largeText: false,
  reducedMotion: false,
};

type SectionId = "storage" | "performance" | "theme" | "audio" | "accessibility" | "about";

export default function Settings() {
  const [storage, setStorage] = useState<{ usedMB: number; totalMB: number; percentUsed: number } | null>(null);
  const [settings, setSettings] = useState<SettingsState>(() => {
    try {
      const raw = localStorage.getItem(SETTINGS_KEY);
      if (!raw) return DEFAULT_SETTINGS;
      const parsed = JSON.parse(raw) as Partial<SettingsState>;
      return { ...DEFAULT_SETTINGS, ...parsed };
    } catch {
      return DEFAULT_SETTINGS;
    }
  });
  const [searchQuery, setSearchQuery] = useState("");
  const [debugInfo, setDebugInfo] = useState("");
  const { lang, setLang } = useI18n();

  const capability = getThreadingCapability();
  const refreshStorageEstimate = useCallback(async () => {
    setStorage(await getStorageEstimate());
  }, []);

  const refreshDebugInfo = useCallback(async () => {
    const estimate = await getStorageEstimate();
    const payload = [
      `PiStation Debug Info`,
      `Time: ${new Date().toISOString()}`,
      `User Agent: ${navigator.userAgent}`,
      `Threads: ${capability.canUseThreads ? "enabled" : `disabled (${capability.reason})`}`,
      `Cross Origin Isolated: ${self.crossOriginIsolated ? "yes" : "no"}`,
      `Storage: ${estimate ? `${estimate.usedMB}MB / ${estimate.totalMB}MB (${estimate.percentUsed}%)` : "unavailable"}`,
    ].join("\n");
    setDebugInfo(payload);
  }, [capability.canUseThreads, capability.reason]);

  useEffect(() => {
    void refreshStorageEstimate();
  }, [refreshStorageEstimate]);

  useEffect(() => {
    localStorage.setItem(SETTINGS_KEY, JSON.stringify(settings));
    document.documentElement.classList.toggle("a11y-high-contrast", settings.highContrast);
    document.documentElement.classList.toggle("a11y-large-text", settings.largeText);
    document.documentElement.classList.toggle("a11y-reduced-motion", settings.reducedMotion);
  }, [settings]);

  useEffect(() => {
    void refreshDebugInfo();
  }, [refreshDebugInfo]);

  const updateSettings = (next: Partial<SettingsState>) => {
    setSettings((prev) => ({ ...prev, ...next }));
  };

  const resetSection = (section: SectionId) => {
    if (section === "audio") {
      updateSettings({
        volume: DEFAULT_SETTINGS.volume,
        audioLatency: DEFAULT_SETTINGS.audioLatency,
      });
    }

    if (section === "theme") {
      updateSettings({ theme: DEFAULT_SETTINGS.theme });
      document.documentElement.setAttribute("data-theme", DEFAULT_SETTINGS.theme);
    }

    if (section === "accessibility") {
      updateSettings({
        highContrast: DEFAULT_SETTINGS.highContrast,
        largeText: DEFAULT_SETTINGS.largeText,
        reducedMotion: DEFAULT_SETTINGS.reducedMotion,
      });
    }

    toast.success("Section reset to defaults");
  };

  const sectionMatches = (title: string, keywords: string[]) => {
    const q = searchQuery.trim().toLowerCase();
    if (!q) return true;
    return [title, ...keywords].some((token) => token.toLowerCase().includes(q));
  };

  const visibleSections = {
    storage: sectionMatches("Storage Usage", ["storage", "quota", "usage"]),
    performance: sectionMatches("Performance & Compatibility", ["threads", "wasm", "compatibility"]),
    theme: sectionMatches("Theme", ["theme", "appearance"]),
    audio: sectionMatches("Audio", ["volume", "latency"]),
    accessibility: sectionMatches("Accessibility", ["contrast", "large text", "reduced motion", "a11y"]),
    about: sectionMatches("About & Debug", ["debug", "copy", "environment"]),
  };

  return (
    <div className="flex-1 w-full max-w-4xl mx-auto p-4 md:p-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold tracking-tight" style={{color: 'var(--text-primary)'}}>Settings</h1>
        <p className="text-sm mt-1" style={{color: 'var(--text-muted)'}}>Configure your PiStation experience</p>
      </div>

      <div className="relative mb-8 max-w-md">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2" size={16} style={{color: 'var(--text-muted)'}} />
        <input
          type="text"
          value={searchQuery}
          onChange={(event) => setSearchQuery(event.target.value)}
          placeholder="Search settings..."
          className="w-full pl-9 pr-3 py-2.5 text-sm rounded-xl focus:outline-none focus:ring-2"
          style={{background: 'var(--surface-2)', color: 'var(--text-primary)', border: '1px solid var(--border-soft)'}}
        />
      </div>

      {visibleSections.storage && (
        <section className="mb-10">
          <h2 className="text-base font-bold mb-4 pb-2 flex items-center gap-2" style={{color: 'var(--text-primary)', borderBottom: '1px solid var(--border-soft)'}}><HardDrive size={16} style={{color: 'var(--accent-primary)'}} /> Storage Usage</h2>
          {storage ? (
            <div style={{background: 'var(--surface-1)', border: '1px solid var(--border-soft)'}} className="rounded-xl p-6">
              <div className="flex justify-between mb-3 text-sm font-medium">
                <span style={{color: 'var(--text-primary)'}}>{storage.usedMB} MB Used</span>
                <span style={{color: 'var(--text-muted)'}}>{storage.totalMB} MB Total</span>
              </div>
              <div className="w-full h-2 mb-4 overflow-hidden rounded-full" style={{background: 'var(--surface-2)'}}>
                <div
                  className="h-full rounded-full"
                  style={{ width: `${Math.max(1, storage.percentUsed)}%`, background: storage.percentUsed > 80 ? '#ef4444' : 'var(--accent-primary)' }}
                />
              </div>
              <p className="text-xs" style={{color: 'var(--text-muted)'}}>Browser storage usage for PiStation data.</p>
            </div>
          ) : (
            <p style={{color: 'var(--text-muted)'}}>Calculating storage...</p>
          )}
        </section>
      )}

      {visibleSections.performance && (
        <section className="mb-10">
          <h2 className="text-base font-bold mb-4 pb-2 flex items-center gap-2" style={{color: 'var(--text-primary)', borderBottom: '1px solid var(--border-soft)'}}><Cpu size={16} style={{color: 'var(--accent-primary)'}} /> Performance &amp; Compatibility</h2>
          <div style={{background: 'var(--surface-1)', border: '1px solid var(--border-soft)'}} className="rounded-xl p-6">
            <div className="flex items-center gap-4 mb-3">
              <span className="text-sm font-medium" style={{color: 'var(--text-primary)'}}>Multi-threading (WASM Threads)</span>
              {capability.canUseThreads ? (
                <span className="px-2 py-1 rounded-md text-[10px] uppercase tracking-widest font-bold" style={{background: 'rgba(34,197,94,0.15)', color: '#22c55e'}}>Enabled</span>
              ) : (
                <span className="px-2 py-1 rounded-md text-[10px] uppercase tracking-widest font-bold" style={{background: 'rgba(234,179,8,0.15)', color: '#eab308'}}>Disabled</span>
              )}
            </div>
            <p className="text-sm" style={{color: 'var(--text-muted)'}}>
              {capability.canUseThreads
                ? "Cross-Origin Isolation is active. High-performance threaded cores are available."
                : `Threading is unavailable: ${capability.reason}`}
            </p>
          </div>
        </section>
      )}

      {visibleSections.theme && (
        <section className="mb-10">
          <div className="flex items-center justify-between mb-4 pb-2" style={{borderBottom: '1px solid var(--border-soft)'}}>
            <h2 className="text-base font-bold flex items-center gap-2" style={{color: 'var(--text-primary)'}}>🎨 Theme</h2>
            <button onClick={() => resetSection("theme")} className="text-[10px] uppercase font-bold tracking-widest inline-flex items-center gap-1.5 transition-colors hover:opacity-80" style={{color: 'var(--text-muted)'}}>
              <RefreshCcw size={12} /> RESET
            </button>
          </div>
          <div className="rounded-xl p-6" style={{background: 'var(--surface-1)', border: '1px solid var(--border-soft)'}}>
            <label className="text-sm">
              <span className="block text-xs font-bold mb-2 uppercase tracking-widest" style={{color: 'var(--text-muted)'}}>Theme</span>
              <select
                className="w-full rounded-lg px-3 py-2 focus:outline-none text-sm"
                style={{background: 'var(--surface-2)', color: 'var(--text-primary)', border: '1px solid var(--border-soft)'}}
                value={settings.theme}
                onChange={(event) => {
                  const theme = event.target.value as SettingsState["theme"];
                  updateSettings({ theme });
                  document.documentElement.setAttribute("data-theme", theme);
                }}
              >
                <option value="default">Default (Dark)</option>
                <option value="nes">NES Classic</option>
                <option value="gameboy">Game Boy</option>
                <option value="snes">SNES Purple</option>
                <option value="terminal">Terminal Green</option>
              </select>
            </label>
          </div>
        </section>
      )}

      {visibleSections.audio && (
        <section className="mb-10">
          <div className="flex items-center justify-between mb-4 pb-2" style={{borderBottom: '1px solid var(--border-soft)'}}>
            <h2 className="text-base font-bold flex items-center gap-2" style={{color: 'var(--text-primary)'}}><Volume2 size={16} style={{color: 'var(--accent-primary)'}} /> Audio</h2>
            <button onClick={() => resetSection("audio")} className="text-[10px] uppercase font-bold tracking-widest inline-flex items-center gap-1.5 transition-colors hover:opacity-80" style={{color: 'var(--text-muted)'}}>
              <RefreshCcw size={12} /> RESET
            </button>
          </div>
          <div className="rounded-xl p-6 grid sm:grid-cols-2 gap-6" style={{background: 'var(--surface-1)', border: '1px solid var(--border-soft)'}}>
            <label className="text-sm">
              <span className="block text-xs font-bold mb-3 uppercase tracking-widest" style={{color: 'var(--text-muted)'}}>Master volume ({settings.volume}%)</span>
              <input
                type="range"
                min={0}
                max={150}
                value={settings.volume}
                onChange={(event) => updateSettings({ volume: Number(event.target.value) })}
                className="w-full accent-primary"
              />
            </label>

            <label className="text-sm">
              <span className="block text-xs font-bold mb-2 uppercase tracking-widest" style={{color: 'var(--text-muted)'}}>Audio latency</span>
              <select
                className="w-full rounded-lg px-3 py-2 focus:outline-none text-sm"
                style={{background: 'var(--surface-2)', color: 'var(--text-primary)', border: '1px solid var(--border-soft)'}}
                value={settings.audioLatency}
                onChange={(event) => updateSettings({ audioLatency: event.target.value as SettingsState["audioLatency"] })}
              >
                <option value="auto">Auto</option>
                <option value="low">Low</option>
                <option value="normal">Normal</option>
              </select>
            </label>
          </div>
        </section>
      )}

      {visibleSections.accessibility && (
        <section className="mb-10" aria-label="Accessibility settings">
          <div className="flex items-center justify-between mb-4 pb-2" style={{borderBottom: '1px solid var(--border-soft)'}}>
            <h2 className="text-base font-bold flex items-center gap-2" style={{color: 'var(--text-primary)'}}>♿ Accessibility</h2>
            <button onClick={() => resetSection("accessibility")} className="text-[10px] uppercase font-bold tracking-widest inline-flex items-center gap-1.5 transition-colors hover:opacity-80" style={{color: 'var(--text-muted)'}}>
              <RefreshCcw size={12} /> RESET
            </button>
          </div>
          <div className="rounded-xl p-6 grid gap-4" style={{background: 'var(--surface-1)', border: '1px solid var(--border-soft)'}}>
            <label className="flex items-center justify-between cursor-pointer">
              <div>
                <span className="text-sm font-medium" style={{color: 'var(--text-primary)'}}>High Contrast</span>
                <p className="text-xs" style={{color: 'var(--text-muted)'}}>Increase contrast for better visibility</p>
              </div>
              <input type="checkbox" checked={settings.highContrast} onChange={(e) => updateSettings({ highContrast: e.target.checked })} className="w-5 h-5 accent-blue-500" />
            </label>
            <label className="flex items-center justify-between cursor-pointer">
              <div>
                <span className="text-sm font-medium" style={{color: 'var(--text-primary)'}}>Large Text</span>
                <p className="text-xs" style={{color: 'var(--text-muted)'}}>Increase base font size for readability</p>
              </div>
              <input type="checkbox" checked={settings.largeText} onChange={(e) => updateSettings({ largeText: e.target.checked })} className="w-5 h-5 accent-blue-500" />
            </label>
            <label className="flex items-center justify-between cursor-pointer">
              <div>
                <span className="text-sm font-medium" style={{color: 'var(--text-primary)'}}>Reduced Motion</span>
                <p className="text-xs" style={{color: 'var(--text-muted)'}}>Disable animations and transitions</p>
              </div>
              <input type="checkbox" checked={settings.reducedMotion} onChange={(e) => updateSettings({ reducedMotion: e.target.checked })} className="w-5 h-5 accent-blue-500" />
            </label>
            <label className="flex items-center justify-between">
              <div>
                <span className="text-sm font-medium" style={{color: 'var(--text-primary)'}}>Language</span>
                <p className="text-xs" style={{color: 'var(--text-muted)'}}>Interface language</p>
              </div>
              <select
                className="rounded-lg px-3 py-1.5 text-sm"
                style={{background: 'var(--surface-2)', color: 'var(--text-primary)', border: '1px solid var(--border-soft)'}}
                value={lang}
                onChange={(e) => setLang(e.target.value as Lang)}
              >
                {(Object.entries(LANGUAGE_LABELS) as [Lang, string][]).map(([code, label]) => (
                  <option key={code} value={code}>{label}</option>
                ))}
              </select>
            </label>
          </div>
        </section>
      )}

      {visibleSections.about && (
        <section className="mb-10">
          <h2 className="text-base font-bold mb-4 pb-2 flex items-center gap-2" style={{color: 'var(--text-primary)', borderBottom: '1px solid var(--border-soft)'}}><Info size={16} style={{color: 'var(--accent-primary)'}} /> About &amp; Debug</h2>
          <div className="rounded-xl p-6" style={{background: 'var(--surface-1)', border: '1px solid var(--border-soft)'}}>
            <div className="grid sm:grid-cols-2 gap-3 text-sm mb-6" style={{color: 'var(--text-muted)'}}>
              <p>Version: <span style={{color: 'var(--text-primary)'}}>v0.2.0-dev</span></p>
              <p>Threads: <span style={{color: 'var(--text-primary)'}}>{capability.canUseThreads ? "Enabled" : "Disabled"}</span></p>
              <p>IndexedDB: <span style={{color: 'var(--text-primary)'}}>{"indexedDB" in window ? "Available" : "Unavailable"}</span></p>
            </div>

            <button
              onClick={async () => {
                try {
                  await navigator.clipboard.writeText(debugInfo);
                  toast.success("Debug info copied to clipboard");
                } catch {
                  toast.error("Failed to copy debug info");
                }
              }}
              className="px-4 py-2 text-xs font-bold tracking-widest uppercase rounded-lg flex items-center gap-2 hover:opacity-80 transition-opacity"
              style={{background: 'var(--surface-2)', color: 'var(--text-primary)', border: '1px solid var(--border-soft)'}}
            >
              <Copy size={14} /> Copy Debug Info
            </button>

            <pre className="mt-6 text-xs rounded-lg p-4 overflow-auto max-h-48 font-mono" style={{background: 'var(--surface-2)', color: 'var(--text-muted)', border: '1px solid var(--border-soft)'}}>
              {debugInfo || "Collecting debug info..."}
            </pre>
          </div>
        </section>
      )}
    </div>
  );
}
