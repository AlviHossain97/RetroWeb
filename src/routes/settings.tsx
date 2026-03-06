import { useEffect, useState } from "react";
import { Copy, RefreshCcw, Search } from "lucide-react";
import { toast } from "sonner";
import { getStorageEstimate } from "../lib/capability/storage-quota";
import { getThreadingCapability } from "../lib/capability/capability-check";
import { getAllBIOSFiles, getAllGames, getAllSaves } from "../lib/storage/db";

type SettingsState = {
  displayShader: "none" | "crt" | "scanlines" | "sharp";
  aspectRatio: "original" | "stretch" | "integer";
  showFps: boolean;
  volume: number;
  audioLatency: "auto" | "low" | "normal";
  autosaveIntervalSec: 30 | 60 | 120 | 0;
  autosaveOnExit: boolean;
  defaultSaveSlot: number;
  touchOpacity: number;
  touchSize: number;
};

const SETTINGS_KEY = "retroweb.settings.v1";

const DEFAULT_SETTINGS: SettingsState = {
  displayShader: "none",
  aspectRatio: "original",
  showFps: false,
  volume: 100,
  audioLatency: "auto",
  autosaveIntervalSec: 60,
  autosaveOnExit: true,
  defaultSaveSlot: 0,
  touchOpacity: 80,
  touchSize: 100,
};

type SectionId = "storage" | "performance" | "display" | "audio" | "input" | "saves" | "data" | "about";

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

  const capability = getThreadingCapability();

  useEffect(() => {
    void getStorageEstimate().then(setStorage);
  }, []);

  useEffect(() => {
    localStorage.setItem(SETTINGS_KEY, JSON.stringify(settings));
  }, [settings]);

  useEffect(() => {
    const buildDebugInfo = async () => {
      const [bios, games, saves, estimate] = await Promise.all([getAllBIOSFiles(), getAllGames(), getAllSaves(), getStorageEstimate()]);

      const payload = [
        `RetroWeb Debug Info`,
        `Time: ${new Date().toISOString()}`,
        `User Agent: ${navigator.userAgent}`,
        `Threads: ${capability.canUseThreads ? "enabled" : `disabled (${capability.reason})`}`,
        `Cross Origin Isolated: ${self.crossOriginIsolated ? "yes" : "no"}`,
        `Storage: ${estimate ? `${estimate.usedMB}MB / ${estimate.totalMB}MB (${estimate.percentUsed}%)` : "unavailable"}`,
        `Games: ${games.length}`,
        `Saves: ${saves.length}`,
        `Installed BIOS: ${bios.length}`,
      ].join("\n");

      setDebugInfo(payload);
    };

    void buildDebugInfo();
  }, [capability.canUseThreads, capability.reason]);

  const updateSettings = (next: Partial<SettingsState>) => {
    setSettings((prev) => ({ ...prev, ...next }));
  };

  const resetSection = (section: SectionId) => {
    if (section === "display") {
      updateSettings({
        displayShader: DEFAULT_SETTINGS.displayShader,
        aspectRatio: DEFAULT_SETTINGS.aspectRatio,
        showFps: DEFAULT_SETTINGS.showFps,
      });
    }

    if (section === "audio") {
      updateSettings({
        volume: DEFAULT_SETTINGS.volume,
        audioLatency: DEFAULT_SETTINGS.audioLatency,
      });
    }

    if (section === "input") {
      updateSettings({
        touchOpacity: DEFAULT_SETTINGS.touchOpacity,
        touchSize: DEFAULT_SETTINGS.touchSize,
      });
    }

    if (section === "saves") {
      updateSettings({
        autosaveIntervalSec: DEFAULT_SETTINGS.autosaveIntervalSec,
        autosaveOnExit: DEFAULT_SETTINGS.autosaveOnExit,
        defaultSaveSlot: DEFAULT_SETTINGS.defaultSaveSlot,
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
    display: sectionMatches("Display", ["shader", "aspect", "fps", "video"]),
    audio: sectionMatches("Audio", ["volume", "latency"]),
    input: sectionMatches("Input", ["controller", "touch", "mapping"]),
    saves: sectionMatches("Saves", ["autosave", "slot", "sram"]),
    data: sectionMatches("Data Management", ["clear", "backup", "import", "export"]),
    about: sectionMatches("About & Debug", ["debug", "copy", "environment"]),
  };

  return (
    <div className="flex-1 w-full max-w-5xl mx-auto p-4 md:p-8">
      <h1 className="text-[32px] font-bold tracking-tight text-foreground mb-6">Settings</h1>

      <div className="relative mb-8 max-w-md">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" size={16} />
        <input
          type="text"
          value={searchQuery}
          onChange={(event) => setSearchQuery(event.target.value)}
          placeholder="Search settings..."
          className="w-full bg-card border border-border pl-9 pr-3 py-2.5 text-sm rounded-md focus:outline-none focus:border-primary transition-colors text-foreground"
        />
      </div>

      {visibleSections.storage && (
        <section className="mb-10">
          <h2 className="text-xl font-bold mb-4 border-b border-border pb-2 text-foreground">Storage Usage</h2>
          {storage ? (
            <div className="bg-card border border-border rounded-md shadow-sm p-6">
              <div className="flex justify-between mb-3 text-sm font-sans font-medium">
                <span className="text-foreground">{storage.usedMB} MB Used</span>
                <span className="text-muted-foreground">{storage.totalMB} MB Total</span>
              </div>
              <div className="w-full bg-[#111111] h-2 mb-4 overflow-hidden rounded-full">
                <div
                  className={`h-full ${storage.percentUsed > 80 ? "bg-destructive" : "bg-primary"}`}
                  style={{ width: `${Math.max(1, storage.percentUsed)}%` }}
                />
              </div>
              <p className="font-sans text-xs text-muted-foreground uppercase tracking-widest">Storage includes ROM metadata, BIOS files, SRAM and save states.</p>
            </div>
          ) : (
            <p className="text-neutral-500">Calculating storage...</p>
          )}
        </section>
      )}

      {visibleSections.performance && (
        <section className="mb-10">
          <h2 className="text-xl font-bold mb-4 border-b border-border pb-2 text-foreground">Performance & Compatibility</h2>
          <div className="bg-card border border-border rounded-md shadow-sm p-6">
            <div className="flex items-center gap-4 mb-3">
              <span className="font-sans text-sm font-medium text-foreground">Multi-threading (WASM Threads)</span>
              {capability.canUseThreads ? (
                <span className="px-2 py-1 bg-muted border border-green-500/30 text-green-500 rounded-sm text-[10px] uppercase tracking-widest font-bold">Enabled</span>
              ) : (
                <span className="px-2 py-1 bg-muted border border-yellow-500/30 text-yellow-500 rounded-sm text-[10px] uppercase tracking-widest font-bold">Disabled</span>
              )}
            </div>
            <p className="font-sans text-sm text-muted-foreground">
              {capability.canUseThreads
                ? "Cross-Origin Isolation is active. High-performance threaded cores are available."
                : `Threading is unavailable: ${capability.reason}`}
            </p>
          </div>
        </section>
      )}

      {visibleSections.display && (
        <section className="mb-10">
          <div className="flex items-center justify-between mb-4 border-b border-border pb-2">
            <h2 className="text-xl font-bold text-foreground">Display</h2>
            <button onClick={() => resetSection("display")} className="font-sans text-[10px] uppercase font-bold tracking-widest text-muted-foreground hover:text-foreground inline-flex items-center gap-1.5 transition-colors">
              <RefreshCcw size={12} /> RESET
            </button>
          </div>
          <div className="bg-card border border-border p-6 grid sm:grid-cols-2 gap-6">
            <label className="text-sm font-sans">
              <span className="block text-xs font-medium text-muted-foreground mb-2 uppercase tracking-widest">Shader preset</span>
              <select
                className="w-full bg-[#111111] border border-border px-3 py-2 focus:outline-none focus:border-primary text-foreground"
                value={settings.displayShader}
                onChange={(event) => updateSettings({ displayShader: event.target.value as SettingsState["displayShader"] })}
              >
                <option value="none">None</option>
                <option value="crt">CRT</option>
                <option value="scanlines">Scanlines</option>
                <option value="sharp">Sharp</option>
              </select>
            </label>

            <label className="text-sm font-sans">
              <span className="block text-xs font-bold text-muted-foreground mb-2 uppercase tracking-widest">Aspect ratio</span>
              <select
                className="w-full bg-[#111111] border border-border rounded-sm px-3 py-2 focus:outline-none focus:border-primary text-foreground"
                value={settings.aspectRatio}
                onChange={(event) => updateSettings({ aspectRatio: event.target.value as SettingsState["aspectRatio"] })}
              >
                <option value="original">Original</option>
                <option value="stretch">Stretch</option>
                <option value="integer">Integer</option>
              </select>
            </label>

            <label className="text-sm font-sans flex items-center gap-3 mt-1 text-foreground">
              <input
                type="checkbox"
                className="accent-primary w-4 h-4 cursor-pointer"
                checked={settings.showFps}
                onChange={(event) => updateSettings({ showFps: event.target.checked })}
              />
              Show FPS counter
            </label>
          </div>
        </section>
      )}

      {visibleSections.audio && (
        <section className="mb-10">
          <div className="flex items-center justify-between mb-4 border-b border-border pb-2">
            <h2 className="text-xl font-bold text-foreground">Audio</h2>
            <button onClick={() => resetSection("audio")} className="font-sans text-[10px] uppercase font-bold tracking-widest text-muted-foreground hover:text-foreground inline-flex items-center gap-1.5 transition-colors">
              <RefreshCcw size={12} /> RESET
            </button>
          </div>
          <div className="bg-card border border-border rounded-md shadow-sm p-6 grid sm:grid-cols-2 gap-6">
            <label className="text-sm font-sans">
              <span className="block text-xs font-bold text-muted-foreground mb-3 uppercase tracking-widest">Master volume ({settings.volume}%)</span>
              <input
                type="range"
                min={0}
                max={150}
                value={settings.volume}
                onChange={(event) => updateSettings({ volume: Number(event.target.value) })}
                className="w-full accent-primary"
              />
            </label>

            <label className="text-sm font-sans">
              <span className="block text-xs font-bold text-muted-foreground mb-2 uppercase tracking-widest">Audio latency</span>
              <select
                className="w-full bg-[#111111] border border-border rounded-sm px-3 py-2 focus:outline-none focus:border-primary text-foreground"
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

      {visibleSections.input && (
        <section className="mb-10">
          <div className="flex items-center justify-between mb-4 border-b border-border pb-2">
            <h2 className="text-xl font-bold text-foreground">Input</h2>
            <button onClick={() => resetSection("input")} className="font-sans text-[10px] uppercase font-bold tracking-widest text-muted-foreground hover:text-foreground inline-flex items-center gap-1.5 transition-colors">
              <RefreshCcw size={12} /> RESET
            </button>
          </div>
          <div className="bg-card border border-border rounded-md shadow-sm p-6 grid sm:grid-cols-2 gap-6">
            <label className="text-sm font-sans">
              <span className="block text-xs font-bold text-muted-foreground mb-3 uppercase tracking-widest">Touch opacity ({settings.touchOpacity}%)</span>
              <input
                type="range"
                min={20}
                max={100}
                value={settings.touchOpacity}
                onChange={(event) => updateSettings({ touchOpacity: Number(event.target.value) })}
                className="w-full accent-primary"
              />
            </label>

            <label className="text-sm font-sans">
              <span className="block text-xs font-bold text-muted-foreground mb-3 uppercase tracking-widest">Touch size ({settings.touchSize}%)</span>
              <input
                type="range"
                min={60}
                max={140}
                value={settings.touchSize}
                onChange={(event) => updateSettings({ touchSize: Number(event.target.value) })}
                className="w-full accent-primary"
              />
            </label>
          </div>
        </section>
      )}

      {visibleSections.saves && (
        <section className="mb-10">
          <div className="flex items-center justify-between mb-4 border-b border-border pb-2">
            <h2 className="text-xl font-bold text-foreground">Saves</h2>
            <button onClick={() => resetSection("saves")} className="font-sans text-[10px] uppercase font-bold tracking-widest text-muted-foreground hover:text-foreground inline-flex items-center gap-1.5 transition-colors">
              <RefreshCcw size={12} /> RESET
            </button>
          </div>
          <div className="bg-card border border-border rounded-md shadow-sm p-6 grid sm:grid-cols-2 gap-6">
            <label className="text-sm font-sans">
              <span className="block text-xs font-bold text-muted-foreground mb-2 uppercase tracking-widest">Auto-save interval</span>
              <select
                className="w-full bg-[#111111] border border-border rounded-sm px-3 py-2 focus:outline-none focus:border-primary text-foreground"
                value={settings.autosaveIntervalSec}
                onChange={(event) => updateSettings({ autosaveIntervalSec: Number(event.target.value) as SettingsState["autosaveIntervalSec"] })}
              >
                <option value={30}>30s</option>
                <option value={60}>60s</option>
                <option value={120}>2min</option>
                <option value={0}>Off</option>
              </select>
            </label>

            <label className="text-sm font-sans">
              <span className="block text-xs font-bold text-muted-foreground mb-2 uppercase tracking-widest">Default save slot</span>
              <input
                type="number"
                min={0}
                max={9}
                value={settings.defaultSaveSlot}
                onChange={(event) => updateSettings({ defaultSaveSlot: Math.min(9, Math.max(0, Number(event.target.value))) })}
                className="w-full bg-[#111111] border border-border rounded-sm px-3 py-2 focus:outline-none focus:border-primary text-foreground"
              />
            </label>

            <label className="text-sm font-sans flex items-center gap-3 mt-1 text-foreground">
              <input
                type="checkbox"
                className="accent-primary w-4 h-4 cursor-pointer"
                checked={settings.autosaveOnExit}
                onChange={(event) => updateSettings({ autosaveOnExit: event.target.checked })}
              />
              Auto-save on tab close / app exit
            </label>
          </div>
        </section>
      )}

      {visibleSections.data && (
        <section className="mb-10">
          <h2 className="text-xl font-bold mb-4 border-b border-border pb-2 text-foreground">Data Management</h2>
          <div className="bg-card border border-border rounded-md shadow-sm p-6 grid sm:grid-cols-2 gap-4">
            <button className="text-xs font-sans tracking-widest uppercase font-bold rounded-sm px-4 py-3 bg-muted border border-border text-foreground hover:bg-secondary transition-colors text-left flex items-center justify-between">Clear ROM cache <span className="text-[10px] text-muted-foreground font-normal normal-case tracking-normal">Keeps saves</span></button>
            <button className="text-xs font-sans tracking-widest uppercase font-bold rounded-sm px-4 py-3 bg-muted border border-border text-foreground hover:bg-secondary transition-colors text-left flex items-center justify-between">Export Backup <span className="text-[10px] text-muted-foreground font-normal normal-case tracking-normal">.zip</span></button>
            <button className="text-xs font-sans tracking-widest uppercase font-bold rounded-sm px-4 py-3 bg-muted border border-border text-foreground hover:bg-secondary transition-colors text-left flex items-center justify-between">Import Backup <span className="text-[10px] text-muted-foreground font-normal normal-case tracking-normal">.zip</span></button>
            <button className="text-xs font-sans tracking-widest uppercase font-bold rounded-sm px-4 py-3 bg-[#1A0A0A] border border-destructive/30 text-destructive hover:bg-destructive hover:text-white transition-colors text-left">Clear Everything</button>
          </div>
        </section>
      )}

      {visibleSections.about && (
        <section className="mb-10">
          <h2 className="text-xl font-bold mb-4 border-b border-border pb-2 text-foreground">About & Debug</h2>
          <div className="bg-card border border-border rounded-md shadow-sm p-6">
            <div className="grid sm:grid-cols-2 gap-3 font-sans text-sm text-muted-foreground mb-6">
              <p>Version: <span className="text-foreground">v0.2.0-dev</span></p>
              <p>Threads: <span className="text-foreground">{capability.canUseThreads ? "Enabled" : "Disabled"}</span></p>
              <p>OPFS: <span className="text-foreground">{"storage" in navigator ? "Available" : "Unavailable"}</span></p>
              <p>IndexedDB: <span className="text-foreground">{"indexedDB" in window ? "Available" : "Unavailable"}</span></p>
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
              className="px-4 py-2 font-sans text-xs font-bold tracking-widest uppercase rounded-sm bg-muted border border-border text-foreground hover:bg-secondary transition-colors flex items-center gap-2"
            >
              <Copy size={14} /> Copy Debug Info
            </button>

            <pre className="mt-6 text-xs text-muted-foreground rounded-sm bg-[#0A0A0A] border border-[#222222] p-4 overflow-auto max-h-48 font-mono">
              {debugInfo || "Collecting debug info..."}
            </pre>
          </div>
        </section>
      )}
    </div>
  );
}
