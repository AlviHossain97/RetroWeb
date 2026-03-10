import { useCallback, useEffect, useRef, useState } from "react";
import { Copy, RefreshCcw, Search, HardDrive, Cpu, Monitor, Volume2, Gamepad, Save, Database, Info } from "lucide-react";
import { toast } from "sonner";
import { getStorageEstimate } from "../lib/capability/storage-quota";
import { getThreadingCapability } from "../lib/capability/capability-check";
import { db, getAllBIOSFiles, getAllGames, getAllSaves, removeRomFromOPFS, getAllCollections, getUnlockedAchievements, loadChatMessages, type Collection, type Achievement, type ChatMessage } from "../lib/storage/db";
import { checkAndUnlock } from "../lib/achievements";
import { useI18n, LANGUAGE_LABELS, type Lang } from "../lib/i18n";

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
  theme: "default" | "nes" | "gameboy" | "snes" | "terminal";
  highContrast: boolean;
  largeText: boolean;
  reducedMotion: boolean;
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
  theme: "default",
  highContrast: false,
  largeText: false,
  reducedMotion: false,
};

type SectionId = "storage" | "performance" | "display" | "audio" | "input" | "saves" | "data" | "accessibility" | "about";
type BackupPayload = {
  version: 1;
  createdAt: string;
  bios: Array<{
    filename: string;
    system: string;
    dataBase64: string;
    sourceFilename?: string;
    hashMd5?: string;
    verifiedHash?: boolean;
    expectedSize?: number;
    size: number;
    installedAt: number;
  }>;
  games: Awaited<ReturnType<typeof getAllGames>>;
  saves: Array<{
    id?: number;
    filename: string;
    system: string;
    type: "sram" | "state";
    dataBase64: string;
    timestamp: number;
    image?: string;
    slot?: number;
    coreId?: string;
    coreVersion?: string;
  }>;
  collections?: Collection[];
  achievements?: Achievement[];
  chatMessages?: ChatMessage[];
};

function bytesToBase64(data: Uint8Array): string {
  let binary = "";
  const chunkSize = 0x8000;
  for (let i = 0; i < data.length; i += chunkSize) {
    binary += String.fromCharCode(...data.subarray(i, i + chunkSize));
  }
  return btoa(binary);
}

function base64ToBytes(value: string): Uint8Array {
  const binary = atob(value);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) {
    bytes[i] = binary.charCodeAt(i);
  }
  return bytes;
}

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
  const importInputRef = useRef<HTMLInputElement>(null);
  const { lang, setLang } = useI18n();

  const capability = getThreadingCapability();
  const refreshStorageEstimate = useCallback(async () => {
    setStorage(await getStorageEstimate());
  }, []);

  const refreshDebugInfo = useCallback(async () => {
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
  }, [capability.canUseThreads, capability.reason]);

  const removeTrackedRomsFromOPFS = useCallback(async (gameIds: string[]) => {
    for (const gameId of gameIds) {
      await removeRomFromOPFS(gameId);
    }
  }, []);

  useEffect(() => {
    void refreshStorageEstimate();
  }, [refreshStorageEstimate]);

  useEffect(() => {
    localStorage.setItem(SETTINGS_KEY, JSON.stringify(settings));
    // Apply accessibility classes to root
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
    display: sectionMatches("Display", ["shader", "aspect", "fps", "video"]),
    audio: sectionMatches("Audio", ["volume", "latency"]),
    input: sectionMatches("Input", ["controller", "touch", "mapping"]),
    saves: sectionMatches("Saves", ["autosave", "slot", "sram"]),
    data: sectionMatches("Data Management", ["clear", "backup", "import", "export"]),
    accessibility: sectionMatches("Accessibility", ["contrast", "large text", "reduced motion", "a11y"]),
    about: sectionMatches("About & Debug", ["debug", "copy", "environment"]),
  };

  const handleClearRomCache = async () => {
    if (!window.confirm("Clear all cached ROM files and library entries? Saves will be kept.")) return;
    const games = await getAllGames();
    await removeTrackedRomsFromOPFS(games.map((game) => game.id));
    await db.games.clear();
    toast.success("ROM cache cleared. Save files were kept.");
    await Promise.all([refreshStorageEstimate(), refreshDebugInfo()]);
  };

  const handleExportBackup = async () => {
    const [bios, saves, games, collections, achievements, chatMessages] = await Promise.all([
      db.bios.toArray(), getAllSaves(), getAllGames(), getAllCollections(), getUnlockedAchievements(), loadChatMessages(),
    ]);
    const payload: BackupPayload = {
      version: 1,
      createdAt: new Date().toISOString(),
      bios: bios.map((entry) => ({
        filename: entry.filename,
        system: entry.system,
        dataBase64: bytesToBase64(entry.data),
        sourceFilename: entry.sourceFilename,
        hashMd5: entry.hashMd5,
        verifiedHash: entry.verifiedHash,
        expectedSize: entry.expectedSize,
        size: entry.size,
        installedAt: entry.installedAt,
      })),
      games,
      saves: saves.map((entry) => ({
        id: entry.id,
        filename: entry.filename,
        system: entry.system,
        type: entry.type,
        dataBase64: bytesToBase64(entry.data),
        timestamp: entry.timestamp.getTime(),
        image: entry.image,
        slot: entry.slot,
        coreId: entry.coreId,
        coreVersion: entry.coreVersion,
      })),
      collections,
      achievements,
      chatMessages,
    };

    const blob = new Blob([JSON.stringify(payload)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `retroweb-backup-${new Date().toISOString().slice(0, 10)}.json`;
    document.body.appendChild(anchor);
    anchor.click();
    document.body.removeChild(anchor);
    URL.revokeObjectURL(url);
    toast.success("Backup exported.");
  };

  const handleImportBackup = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    try {
      const raw = await file.text();
      const backup = JSON.parse(raw) as BackupPayload;
      if (!backup || backup.version !== 1 || !Array.isArray(backup.bios) || !Array.isArray(backup.games) || !Array.isArray(backup.saves)) {
        toast.error("Invalid backup file.");
        return;
      }
      if (!window.confirm("Importing a backup will overwrite current BIOS, library, and saves. Continue?")) return;

      const existingGames = await getAllGames();
      await removeTrackedRomsFromOPFS(existingGames.map((game) => game.id));
      await Promise.all([db.bios.clear(), db.games.clear(), db.saves.clear()]);

      await db.bios.bulkPut(
        backup.bios.map((entry) => ({
          filename: entry.filename,
          system: entry.system,
          data: base64ToBytes(entry.dataBase64),
          sourceFilename: entry.sourceFilename,
          hashMd5: entry.hashMd5,
          verifiedHash: entry.verifiedHash,
          expectedSize: entry.expectedSize,
          size: entry.size,
          installedAt: entry.installedAt,
        }))
      );
      await db.games.bulkPut(backup.games);
      await db.saves.bulkPut(
        backup.saves.map((entry) => ({
          id: entry.id,
          filename: entry.filename,
          system: entry.system,
          type: entry.type,
          data: base64ToBytes(entry.dataBase64),
          timestamp: new Date(entry.timestamp),
          image: entry.image,
          slot: entry.slot,
          coreId: entry.coreId,
          coreVersion: entry.coreVersion,
        }))
      );

      // Restore new tables if present
      if (backup.collections?.length) {
        await db.collections.clear();
        await db.collections.bulkPut(backup.collections);
      }
      if (backup.achievements?.length) {
        await db.achievements.clear();
        await db.achievements.bulkPut(backup.achievements);
      }
      if (backup.chatMessages?.length) {
        await db.chatMessages.clear();
        await db.chatMessages.bulkPut(backup.chatMessages);
      }

      toast.success("Backup imported.");
      await Promise.all([refreshStorageEstimate(), refreshDebugInfo()]);
    } catch {
      toast.error("Backup import failed.");
    } finally {
      event.target.value = "";
    }
  };

  const handleClearEverything = async () => {
    if (!window.confirm("This will delete all ROMs, BIOS files, saves, and library metadata. Continue?")) return;
    const games = await getAllGames();
    await removeTrackedRomsFromOPFS(games.map((game) => game.id));
    await Promise.all([db.bios.clear(), db.games.clear(), db.saves.clear()]);
    toast.success("All local data was cleared.");
    await Promise.all([refreshStorageEstimate(), refreshDebugInfo()]);
  };

  return (
    <div className="flex-1 w-full max-w-4xl mx-auto p-4 md:p-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold tracking-tight" style={{color: 'var(--text-primary)'}}>Settings</h1>
        <p className="text-sm mt-1" style={{color: 'var(--text-muted)'}}>Configure your RetroWeb experience</p>
      </div>

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
          <h2 className="text-base font-bold mb-4 pb-2 flex items-center gap-2" style={{color: 'var(--text-primary)', borderBottom: '1px solid var(--border-soft)'}}><HardDrive size={16} style={{color: 'var(--accent-primary)'}} /> Storage Usage</h2>
          {storage ? (
            <div style={{background: 'var(--surface-1)', border: '1px solid var(--border-soft)'}} className="rounded-md shadow-sm p-6">
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
          <h2 className="text-base font-bold mb-4 pb-2 flex items-center gap-2" style={{color: 'var(--text-primary)', borderBottom: '1px solid var(--border-soft)'}}><Cpu size={16} style={{color: 'var(--accent-primary)'}} /> Performance &amp; Compatibility</h2>
          <div style={{background: 'var(--surface-1)', border: '1px solid var(--border-soft)'}} className="rounded-md shadow-sm p-6">
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
          <div className="flex items-center justify-between mb-4 pb-2" style={{borderBottom: '1px solid var(--border-soft)'}}>
            <h2 className="text-base font-bold flex items-center gap-2" style={{color: 'var(--text-primary)'}}><Monitor size={16} style={{color: 'var(--accent-primary)'}} /> Display</h2>
            <button onClick={() => resetSection("display")} className="font-sans text-[10px] uppercase font-bold tracking-widest text-muted-foreground hover:text-foreground inline-flex items-center gap-1.5 transition-colors">
              <RefreshCcw size={12} /> RESET
            </button>
          </div>
          <div className="bg-card border border-border p-6 grid sm:grid-cols-2 gap-6" style={{background: 'var(--surface-1)', border: '1px solid var(--border-soft)'}}>
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
              {/* Shader preview */}
              <div className="mt-2 h-16 rounded-md overflow-hidden relative" style={{ background: 'linear-gradient(45deg, #e53e3e, #805ad5, #2b6cb0)', imageRendering: settings.displayShader === 'sharp' ? 'pixelated' : 'auto' }}>
                {settings.displayShader === 'scanlines' && (
                  <div className="absolute inset-0" style={{ background: 'repeating-linear-gradient(0deg, rgba(0,0,0,0.3) 0px, rgba(0,0,0,0.3) 1px, transparent 1px, transparent 3px)' }} />
                )}
                {settings.displayShader === 'crt' && (
                  <div className="absolute inset-0" style={{ background: 'repeating-linear-gradient(0deg, rgba(0,0,0,0.25) 0px, rgba(0,0,0,0.25) 1px, transparent 1px, transparent 3px)', borderRadius: '40%/8%', boxShadow: 'inset 0 0 30px rgba(0,0,0,0.5)' }} />
                )}
                <div className="absolute inset-0 flex items-center justify-center text-white/70 text-[10px] font-bold uppercase tracking-widest">
                  {settings.displayShader === 'none' ? 'No Effect' : settings.displayShader.toUpperCase()}
                </div>
              </div>
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

            <label className="text-sm font-sans">
              <span className="block text-xs font-bold text-muted-foreground mb-2 uppercase tracking-widest">Theme</span>
              <select
                className="w-full bg-[#111111] border border-border rounded-sm px-3 py-2 focus:outline-none focus:border-primary text-foreground"
                value={settings.theme}
                onChange={(event) => {
                  const theme = event.target.value as SettingsState["theme"];
                  updateSettings({ theme });
                  document.documentElement.setAttribute("data-theme", theme);
                  if (theme !== "default") void checkAndUnlock("theme_changed");
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
            <button onClick={() => resetSection("audio")} className="font-sans text-[10px] uppercase font-bold tracking-widest text-muted-foreground hover:text-foreground inline-flex items-center gap-1.5 transition-colors">
              <RefreshCcw size={12} /> RESET
            </button>
          </div>
          <div className="rounded-md shadow-sm p-6 grid sm:grid-cols-2 gap-6" style={{background: 'var(--surface-1)', border: '1px solid var(--border-soft)'}}>
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
          <div className="flex items-center justify-between mb-4 pb-2" style={{borderBottom: '1px solid var(--border-soft)'}}>
            <h2 className="text-base font-bold flex items-center gap-2" style={{color: 'var(--text-primary)'}}><Gamepad size={16} style={{color: 'var(--accent-primary)'}} /> Input</h2>
            <button onClick={() => resetSection("input")} className="font-sans text-[10px] uppercase font-bold tracking-widest text-muted-foreground hover:text-foreground inline-flex items-center gap-1.5 transition-colors">
              <RefreshCcw size={12} /> RESET
            </button>
          </div>
          <div className="rounded-md shadow-sm p-6 grid sm:grid-cols-2 gap-6" style={{background: 'var(--surface-1)', border: '1px solid var(--border-soft)'}}>
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
          <div className="flex items-center justify-between mb-4 pb-2" style={{borderBottom: '1px solid var(--border-soft)'}}>
            <h2 className="text-base font-bold flex items-center gap-2" style={{color: 'var(--text-primary)'}}><Save size={16} style={{color: 'var(--accent-primary)'}} /> Saves</h2>
            <button onClick={() => resetSection("saves")} className="font-sans text-[10px] uppercase font-bold tracking-widest text-muted-foreground hover:text-foreground inline-flex items-center gap-1.5 transition-colors">
              <RefreshCcw size={12} /> RESET
            </button>
          </div>
          <div className="rounded-md shadow-sm p-6 grid sm:grid-cols-2 gap-6" style={{background: 'var(--surface-1)', border: '1px solid var(--border-soft)'}}>
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
          <h2 className="text-base font-bold mb-4 pb-2 flex items-center gap-2" style={{color: 'var(--text-primary)', borderBottom: '1px solid var(--border-soft)'}}><Database size={16} style={{color: 'var(--accent-primary)'}} /> Data Management</h2>
          <div className="rounded-md shadow-sm p-6 grid sm:grid-cols-2 gap-4" style={{background: 'var(--surface-1)', border: '1px solid var(--border-soft)'}}>
            <button onClick={() => void handleClearRomCache()} className="text-xs font-sans tracking-widest uppercase font-bold rounded-sm px-4 py-3 bg-muted border border-border text-foreground hover:bg-secondary transition-colors text-left flex items-center justify-between">Clear ROM cache <span className="text-[10px] text-muted-foreground font-normal normal-case tracking-normal">Keeps saves</span></button>
            <button onClick={() => void handleExportBackup()} className="text-xs font-sans tracking-widest uppercase font-bold rounded-sm px-4 py-3 bg-muted border border-border text-foreground hover:bg-secondary transition-colors text-left flex items-center justify-between">Export Backup <span className="text-[10px] text-muted-foreground font-normal normal-case tracking-normal">.json</span></button>
            <button onClick={() => importInputRef.current?.click()} className="text-xs font-sans tracking-widest uppercase font-bold rounded-sm px-4 py-3 bg-muted border border-border text-foreground hover:bg-secondary transition-colors text-left flex items-center justify-between">Import Backup <span className="text-[10px] text-muted-foreground font-normal normal-case tracking-normal">.json</span></button>
            <button onClick={() => void handleClearEverything()} className="text-xs font-sans tracking-widest uppercase font-bold rounded-sm px-4 py-3 bg-[#1A0A0A] border border-destructive/30 text-destructive hover:bg-destructive hover:text-white transition-colors text-left">Clear Everything</button>
            <button
              onClick={() => {
                const input = document.createElement("input");
                input.type = "file";
                input.accept = ".srm,.state,.sav";
                input.multiple = true;
                input.webkitdirectory = true;
                input.onchange = async (e) => {
                  const files = (e.target as HTMLInputElement).files;
                  if (!files) return;
                  let count = 0;
                  for (const file of Array.from(files)) {
                    const name = file.name.toLowerCase();
                    if (name.endsWith(".srm") || name.endsWith(".sav") || name.endsWith(".state")) {
                      try {
                        const buffer = await file.arrayBuffer();
                        const type = name.endsWith(".state") ? "state" as const : "sram" as const;
                        const baseName = file.name.replace(/\.(srm|sav|state)$/i, "");
                        await db.saves.add({ filename: baseName, system: "imported", type, data: new Uint8Array(buffer), timestamp: new Date(), slot: type === "state" ? 0 : undefined });
                        count++;
                      } catch { /* skip duplicates */ }
                    }
                  }
                  if (count > 0) toast.success(`Imported ${count} RetroArch save(s)`);
                  else toast.info("No compatible saves found");
                };
                input.click();
              }}
              className="text-xs font-sans tracking-widest uppercase font-bold rounded-sm px-4 py-3 bg-muted border border-border text-foreground hover:bg-secondary transition-colors text-left flex items-center justify-between sm:col-span-2"
            >Import RetroArch Saves <span className="text-[10px] text-muted-foreground font-normal normal-case tracking-normal">.srm .state .sav</span></button>
          </div>
          <input ref={importInputRef} type="file" accept="application/json,.json" className="hidden" onChange={handleImportBackup} />

          {/* Cloud Save Sync via GitHub Gists */}
          <div className="mt-4 rounded-md shadow-sm p-6" style={{background: 'var(--surface-1)', border: '1px solid var(--border-soft)'}}>
            <h3 className="text-sm font-bold mb-3 flex items-center gap-2" style={{color: 'var(--text-primary)'}}>☁️ Cloud Save Sync (GitHub Gists)</h3>
            <div className="flex flex-col gap-3">
              <input
                type="password"
                placeholder="GitHub Personal Access Token (gist scope)"
                className="w-full bg-[#111111] border border-border rounded-sm px-3 py-2 text-xs focus:outline-none focus:border-primary text-foreground"
                value={localStorage.getItem("gist_pat") || ""}
                onChange={(e) => { localStorage.setItem("gist_pat", e.target.value); }}
              />
              <div className="grid grid-cols-2 gap-2">
                <button
                  onClick={async () => {
                    const pat = localStorage.getItem("gist_pat");
                    if (!pat) { toast.error("Enter a GitHub PAT first"); return; }
                    try {
                      const saves = await getAllSaves();
                      const games = await getAllGames();
                      const payload = JSON.stringify({ saves: saves.map(s => ({ ...s, data: Array.from(s.data) })), games, exportedAt: new Date().toISOString() });
                      const resp = await fetch("https://api.github.com/gists", {
                        method: "POST",
                        headers: { Authorization: `Bearer ${pat}`, "Content-Type": "application/json" },
                        body: JSON.stringify({ description: "PiStation Cloud Save", public: false, files: { "pistation-saves.json": { content: payload } } })
                      });
                      if (!resp.ok) throw new Error(await resp.text());
                      const gist = await resp.json();
                      localStorage.setItem("gist_id", gist.id);
                      toast.success(`Synced to Gist ${gist.id.slice(0, 8)}…`);
                    } catch (err) { toast.error("Upload failed: " + (err instanceof Error ? err.message : "Unknown")); }
                  }}
                  className="text-xs font-bold rounded-sm px-3 py-2 bg-muted border border-border text-foreground hover:bg-secondary transition-colors"
                >⬆️ Upload to Gist</button>
                <button
                  onClick={async () => {
                    const pat = localStorage.getItem("gist_pat");
                    const gistId = localStorage.getItem("gist_id") || prompt("Enter Gist ID:");
                    if (!pat || !gistId) { toast.error("Need PAT + Gist ID"); return; }
                    try {
                      const resp = await fetch(`https://api.github.com/gists/${gistId}`, { headers: { Authorization: `Bearer ${pat}` } });
                      if (!resp.ok) throw new Error(await resp.text());
                      const gist = await resp.json();
                      const data = JSON.parse(gist.files["pistation-saves.json"].content);
                      let count = 0;
                      for (const s of data.saves) {
                        try {
                          await db.saves.add({ ...s, data: new Uint8Array(s.data), timestamp: new Date(s.timestamp) });
                          count++;
                        } catch { /* skip duplicates */ }
                      }
                      localStorage.setItem("gist_id", gistId);
                      toast.success(`Downloaded ${count} save(s) from Gist`);
                    } catch (err) { toast.error("Download failed: " + (err instanceof Error ? err.message : "Unknown")); }
                  }}
                  className="text-xs font-bold rounded-sm px-3 py-2 bg-muted border border-border text-foreground hover:bg-secondary transition-colors"
                >⬇️ Download from Gist</button>
              </div>
              {localStorage.getItem("gist_id") && (
                <p className="text-[10px]" style={{color: 'var(--text-secondary)'}}>Last synced Gist: {localStorage.getItem("gist_id")?.slice(0, 12)}…</p>
              )}
            </div>
          </div>
        </section>
      )}

      {visibleSections.accessibility && (
        <section className="mb-10" aria-label="Accessibility settings">
          <div className="flex items-center justify-between mb-4 pb-2" style={{borderBottom: '1px solid var(--border-soft)'}}>
            <h2 className="text-base font-bold flex items-center gap-2" style={{color: 'var(--text-primary)'}}>♿ Accessibility</h2>
            <button onClick={() => resetSection("accessibility")} className="text-xs px-3 py-1 rounded-md hover:bg-zinc-700" style={{color: 'var(--text-secondary)'}}>Reset</button>
          </div>
          <div className="rounded-md shadow-sm p-6 grid gap-4" style={{background: 'var(--surface-1)', border: '1px solid var(--border-soft)'}}>
            <label className="flex items-center justify-between cursor-pointer">
              <div>
                <span className="text-sm font-medium" style={{color: 'var(--text-primary)'}}>High Contrast</span>
                <p className="text-xs" style={{color: 'var(--text-secondary)'}}>Increase contrast for better visibility</p>
              </div>
              <input type="checkbox" checked={settings.highContrast} onChange={(e) => updateSettings({ highContrast: e.target.checked })} className="w-5 h-5 accent-blue-500" />
            </label>
            <label className="flex items-center justify-between cursor-pointer">
              <div>
                <span className="text-sm font-medium" style={{color: 'var(--text-primary)'}}>Large Text</span>
                <p className="text-xs" style={{color: 'var(--text-secondary)'}}>Increase base font size for readability</p>
              </div>
              <input type="checkbox" checked={settings.largeText} onChange={(e) => updateSettings({ largeText: e.target.checked })} className="w-5 h-5 accent-blue-500" />
            </label>
            <label className="flex items-center justify-between cursor-pointer">
              <div>
                <span className="text-sm font-medium" style={{color: 'var(--text-primary)'}}>Reduced Motion</span>
                <p className="text-xs" style={{color: 'var(--text-secondary)'}}>Disable animations and transitions</p>
              </div>
              <input type="checkbox" checked={settings.reducedMotion} onChange={(e) => updateSettings({ reducedMotion: e.target.checked })} className="w-5 h-5 accent-blue-500" />
            </label>
            <label className="flex items-center justify-between">
              <div>
                <span className="text-sm font-medium" style={{color: 'var(--text-primary)'}}>Language</span>
                <p className="text-xs" style={{color: 'var(--text-secondary)'}}>Interface language</p>
              </div>
              <select
                className="bg-zinc-800 border border-zinc-600 text-white rounded-lg px-3 py-1.5 text-sm"
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
          <div className="rounded-md shadow-sm p-6" style={{background: 'var(--surface-1)', border: '1px solid var(--border-soft)'}}>
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
