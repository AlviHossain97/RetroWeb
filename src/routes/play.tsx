import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router";
import { Nostalgist } from "nostalgist";
import { Clock, Download, Save, X } from "lucide-react";
import { toast } from "sonner";
import coreMap from "../data/coreMap.json";
import {
  getAllStates,
  loadBIOS,
  loadSRAM,
  loadState,
  markGameAutoSaved,
  recordGameplaySession,
  saveSRAM,
  saveState,
  type SaveData,
  updateGameMetadata,
} from "../lib/storage/db";
import { normalizeROM, NormalizeError } from "../lib/emulation/rom-normalizer";
import SwitchGameShell from "../components/SwitchGameShell";
import { useGamepadVisualizer } from "../hooks/useGamepadVisualizer";
import { loadMappingOverrides } from "../gamepad/overrides";
import { checkAndUnlock } from "../lib/achievements";
import NetplayPanel from "../components/NetplayPanel";
import { NetplaySession, type NetplayInput } from "../lib/netplay/session";

interface PlayLocationState {
  romFile?: File;
  coreId?: string;
  filename?: string;
  gameId?: string;
  autoLoadSlot?: number;
}

interface BootState {
  message: string;
  percent: number;
}

interface RuntimeErrorState {
  userMessage: string;
  technicalMessage?: string;
}

interface CoreMapEntry {
  preferredCore: string;
  fallbackCores: string[];
  biosRequired: string[];
  corePath: string;
}

export default function Play() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const emulatorRef = useRef<Nostalgist | null>(null);
  const autosaveTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const saveIndicatorTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const sessionStartedAtRef = useRef<number>(Date.now());
  const activeFilenameRef = useRef<string>("");
  const activeCoreIdRef = useRef<string>("");

  const [bootState, setBootState] = useState<BootState | null>({ message: "Preparing player...", percent: 5 });
  const [runtimeError, setRuntimeError] = useState<RuntimeErrorState | null>(null);
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const [slots, setSlots] = useState<SaveData[]>([]);
  const [showSaveIndicator, setShowSaveIndicator] = useState(false);
  const [retryToken, setRetryToken] = useState(0);
  const [requiresTapToStart, setRequiresTapToStart] = useState(false);
  const [didTapToStart, setDidTapToStart] = useState(false);
  const [showOverlay, setShowOverlay] = useState(true);
  const [speedMultiplier, setSpeedMultiplier] = useState(1);
  const [showFps, setShowFps] = useState(false);
  const [fps, setFps] = useState(0);
  const [mappingOverrides] = useState(() => loadMappingOverrides());
  const { visualState } = useGamepadVisualizer({ overrides: mappingOverrides });
  const [showNetplay, setShowNetplay] = useState(false);
  const netplaySessionRef = useRef<NetplaySession | null>(null);
  const [netplayConnected, setNetplayConnected] = useState(false);
  const [turboEnabled, setTurboEnabled] = useState(false);
  const [rewindActive, setRewindActive] = useState(false);
  const [speedrunTimer, setSpeedrunTimer] = useState(false);
  const [speedrunTime, setSpeedrunTime] = useState(0);
  const [speedrunSplits, setSpeedrunSplits] = useState<number[]>([]);
  const speedrunIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const location = useLocation();
  const navigate = useNavigate();
  const routeState = (location.state as PlayLocationState | null) ?? null;

  const romFile = routeState?.romFile;
  const requestedCoreId = routeState?.coreId;
  const gameId = routeState?.gameId;
  const autoLoadSlot = routeState?.autoLoadSlot;

  const map = useMemo(() => coreMap as Record<string, CoreMapEntry>, []);

  const refreshSlots = useCallback(async () => {
    const activeFilename = activeFilenameRef.current;
    if (!activeFilename) return;
    const allStates = await getAllStates(activeFilename);
    setSlots(allStates);
  }, []);

  const showAutosavePulse = useCallback(() => {
    setShowSaveIndicator(true);
    if (saveIndicatorTimerRef.current) {
      clearTimeout(saveIndicatorTimerRef.current);
    }
    saveIndicatorTimerRef.current = setTimeout(() => setShowSaveIndicator(false), 1800);
  }, []);

  const resolveCoreByCoreId = useCallback((coreId: string) => {
    for (const [systemId, entry] of Object.entries(map)) {
      if (entry.preferredCore === coreId || entry.fallbackCores.includes(coreId)) {
        return { systemId, entry };
      }
    }
    return null;
  }, [map]);

  const flushAutoSave = useCallback(async (reason: string) => {
    const emulator = emulatorRef.current as unknown as {
      saveSRAM?: () => Promise<Blob | null>;
    } | null;
    if (!emulator?.saveSRAM) return;
    if (!activeFilenameRef.current || !activeCoreIdRef.current) return;

    try {
      const sramBlob = await emulator.saveSRAM();
      if (!sramBlob || sramBlob.size === 0) return;

      const buffer = await sramBlob.arrayBuffer();
      await saveSRAM(activeFilenameRef.current, activeCoreIdRef.current, new Uint8Array(buffer));

      if (gameId) {
        await markGameAutoSaved(gameId);
      }

      if (reason !== "unmount") {
        showAutosavePulse();
      }
    } catch (error) {
      console.error(`Auto-save failed (${reason})`, error);
    }
  }, [gameId, showAutosavePulse]);

  const captureThumbnail = useCallback(async (): Promise<string | undefined> => {
    if (!canvasRef.current) return undefined;
    const canvas = canvasRef.current;
    const targetWidth = 320;
    const scale = targetWidth / Math.max(canvas.width || 1, 1);
    const targetHeight = Math.max(1, Math.round((canvas.height || 240) * scale));

    const tempCanvas = document.createElement("canvas");
    tempCanvas.width = targetWidth;
    tempCanvas.height = targetHeight;
    const ctx = tempCanvas.getContext("2d");
    if (!ctx) return undefined;
    ctx.drawImage(canvas, 0, 0, targetWidth, targetHeight);
    return tempCanvas.toDataURL("image/jpeg", 0.62);
  }, []);

  const handleSaveState = useCallback(async (slotIndex: number) => {
    const emulator = emulatorRef.current as unknown as {
      saveState?: () => Promise<{ state: Blob; thumbnail?: Blob }>;
    } | null;
    if (!emulator?.saveState || !activeFilenameRef.current || !activeCoreIdRef.current) return;

    try {
      const result = await emulator.saveState();
      if (!result?.state) return;
      const buffer = await result.state.arrayBuffer();
      const image = await captureThumbnail();
      await saveState(activeFilenameRef.current, activeCoreIdRef.current, new Uint8Array(buffer), image, slotIndex);
      await refreshSlots();
      toast.success(`Saved to slot ${slotIndex}`);
      showAutosavePulse();
      void checkAndUnlock("first_save");
    } catch (error) {
      console.error("Failed to save state", error);
      toast.error("Could not save state.");
    }
  }, [activeCoreIdRef, activeFilenameRef, captureThumbnail, refreshSlots, showAutosavePulse]);

  const handleLoadState = useCallback(async (slotIndex: number) => {
    const emulator = emulatorRef.current as unknown as {
      loadState?: (blob: Blob) => Promise<void>;
    } | null;
    if (!emulator?.loadState || !activeFilenameRef.current) return;

    try {
      const slot = await loadState(activeFilenameRef.current, slotIndex);
      if (!slot?.data) {
        toast.error(`Slot ${slotIndex} is empty.`);
        return;
      }

      const stateBlob = new Blob([new Uint8Array(slot.data).buffer]);
      await emulator.loadState(stateBlob);
      setIsMenuOpen(false);
      toast.success(`Loaded slot ${slotIndex}`);
    } catch (error) {
      console.error("Failed to load state", error);
      toast.error("Could not load state.");
    }
  }, [activeFilenameRef]);

  const handleReset = useCallback(async () => {
    const emulator = emulatorRef.current as unknown as {
      reset?: () => Promise<void>;
      restart?: () => Promise<void>;
    } | null;

    try {
      if (emulator?.reset) {
        await emulator.reset();
        toast.success("Game reset");
        return;
      }
      if (emulator?.restart) {
        await emulator.restart();
        toast.success("Game restarted");
      }
    } catch (error) {
      console.error("Reset failed", error);
      toast.error("Reset failed for this core.");
    }
  }, []);

  const handleFullscreenToggle = useCallback(async () => {
    try {
      if (document.fullscreenElement) {
        await document.exitFullscreen();
      } else {
        await document.documentElement.requestFullscreen();
      }
    } catch {
      toast.error("Fullscreen is unavailable in this browser.");
    }
  }, []);

  const handlePiP = useCallback(async () => {
    try {
      const canvas = canvasRef.current;
      if (!canvas) return;
      // @ts-expect-error - requestPictureInPicture not yet in canvas types
      if (document.pictureInPictureElement) { await document.exitPictureInPicture(); return; }
      const video = document.createElement("video");
      video.srcObject = canvas.captureStream(30);
      video.muted = true;
      await video.play();
      await video.requestPictureInPicture();
    } catch {
      toast.error("Picture-in-Picture unavailable.");
    }
  }, []);

  const handleAskAI = useCallback(async () => {
    if (!canvasRef.current) return;
    const thumbnail = await captureThumbnail();
    if (thumbnail) {
      const base64 = thumbnail.replace(/^data:image\/\w+;base64,/, "");
      sessionStorage.setItem("retroweb.screenshotForAI", base64);
    }
    navigate("/chat");
  }, [captureThumbnail, navigate]);

  const cycleSpeed = useCallback(() => {
    setSpeedMultiplier((prev) => {
      const speeds = [0.5, 1, 2, 4];
      const idx = speeds.indexOf(prev);
      const next = speeds[(idx + 1) % speeds.length];
      if (next > 1) void checkAndUnlock("speed_demon");
      return next;
    });
  }, []);

  // Apply speed multiplier to emulator via RetroArch
  useEffect(() => {
    const emulator = emulatorRef.current as unknown as {
      sendCommand?: (cmd: string) => void;
    } | null;
    if (emulator?.sendCommand) {
      emulator.sendCommand(`SET fastforward_ratio ${speedMultiplier}`);
    }
  }, [speedMultiplier]);

  // FPS counter
  useEffect(() => {
    if (!showFps || !canvasRef.current) return;
    let frameCount = 0;
    let lastTime = performance.now();
    let rafId: number;
    const measure = () => {
      frameCount++;
      const now = performance.now();
      if (now - lastTime >= 1000) {
        setFps(frameCount);
        frameCount = 0;
        lastTime = now;
      }
      rafId = requestAnimationFrame(measure);
    };
    rafId = requestAnimationFrame(measure);
    return () => cancelAnimationFrame(rafId);
  }, [showFps]);

  // Netplay callbacks
  const handleNetplayRemoteInput = useCallback((_input: NetplayInput) => {
    // In a full implementation, this would inject input into the emulator's Player 2 port.
    // Nostalgist.js doesn't expose per-player input injection directly,
    // so this serves as the integration point for future implementation.
  }, []);

  const handleNetplaySessionChange = useCallback((session: NetplaySession | null) => {
    netplaySessionRef.current = session;
    setNetplayConnected(!!session?.isConnected);
  }, []);

  useEffect(() => {
    const userAgent = navigator.userAgent;
    const isIOS = /iPad|iPhone|iPod/.test(userAgent);
    const isSafari = /Safari/.test(userAgent) && !/CriOS|FxiOS|EdgiOS/.test(userAgent);
    const needsTap = isIOS && isSafari;

    setRequiresTapToStart(needsTap);
    setDidTapToStart(!needsTap);
  }, []);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        if (isMenuOpen) {
          setIsMenuOpen(false);
        } else {
          setShowOverlay((prev) => !prev);
        }
      }

      if (event.key === "F1") {
        event.preventDefault();
        void handleSaveState(0);
      }

      if (event.key === "F4") {
        event.preventDefault();
        void handleLoadState(0);
      }

      if (event.key === "F11") {
        event.preventDefault();
        void handleFullscreenToggle();
      }

      if (event.key === "F2") {
        event.preventDefault();
        cycleSpeed();
      }

      if (event.key === "F3") {
        event.preventDefault();
        setShowFps((p) => !p);
      }

      if (event.key === "F4") {
        event.preventDefault();
        setTurboEnabled((p) => !p);
      }

      if (event.key === "F5") {
        event.preventDefault();
        setRewindActive(true);
        const emulator = emulatorRef.current;
        if (emulator) {
          try { emulator.sendCommand("REWIND"); } catch { /* rewind may not be supported */ }
        }
      }

      // F6: Toggle speedrun timer
      if (event.key === "F6") {
        event.preventDefault();
        setSpeedrunTimer((on) => {
          if (!on) {
            setSpeedrunTime(0);
            setSpeedrunSplits([]);
            const iv = setInterval(() => setSpeedrunTime((t) => t + 10), 10);
            speedrunIntervalRef.current = iv;
            return true;
          } else {
            if (speedrunIntervalRef.current) clearInterval(speedrunIntervalRef.current);
            speedrunIntervalRef.current = null;
            return false;
          }
        });
      }
      // F7: Record split
      if (event.key === "F7") {
        event.preventDefault();
        if (speedrunTimer) setSpeedrunSplits((s) => [...s, speedrunTime]);
      }
    };

    const onKeyUp = (event: KeyboardEvent) => {
      if (event.key === "F5") {
        setRewindActive(false);
      }
    };

    window.addEventListener("keydown", onKeyDown);
    window.addEventListener("keyup", onKeyUp);
    return () => { window.removeEventListener("keydown", onKeyDown); window.removeEventListener("keyup", onKeyUp); };
  }, [handleFullscreenToggle, handleLoadState, handleSaveState, isMenuOpen, cycleSpeed]);

  useEffect(() => {
    let isMounted = true;

    if (!romFile || !requestedCoreId) {
      navigate("/library");
      return;
    }

    if (!didTapToStart) {
      setBootState({ message: "Waiting for user gesture...", percent: 0 });
      return;
    }

    const launch = async () => {
      try {
        setRuntimeError(null);
        setBootState({ message: "Preparing ROM...", percent: 5 });

        const normalized = await normalizeROM(romFile, {
          onProgress: (percent, message) => setBootState({ message, percent: Math.min(45, percent) }),
        });

        const requestedEntry = resolveCoreByCoreId(requestedCoreId);
        const normalizedEntry = map[normalized.systemId];

        const activeCoreId = normalizedEntry?.preferredCore || requestedCoreId;
        const activeCorePath = normalizedEntry?.corePath || requestedEntry?.entry.corePath;
        const biosRequired = normalizedEntry?.biosRequired || requestedEntry?.entry.biosRequired || [];

        if (!activeCorePath) {
          throw new Error(`No core path was resolved for ${activeCoreId}`);
        }

        const activeFilename = routeState?.filename || normalized.filename;
        activeFilenameRef.current = activeFilename;
        activeCoreIdRef.current = activeCoreId;

        setBootState({ message: "Loading previous save...", percent: 55 });
        const previousSram = await loadSRAM(activeFilename);
        const sramBlob = previousSram ? new Blob([new Uint8Array(previousSram).buffer]) : undefined;

        setBootState({ message: "Mounting BIOS files...", percent: 68 });
        const biosFiles: File[] = [];
        for (const biosName of biosRequired) {
          const biosData = await loadBIOS(biosName);
          if (biosData) {
            biosFiles.push(new File([new Uint8Array(biosData).buffer], biosName));
          }
        }

        setBootState({ message: `Downloading ${activeCoreId.toUpperCase()} core…`, percent: 78 });
        // Check if core is cached already
        const coreUrl = `${activeCorePath}.wasm`;
        const coreCache = await caches.open("retroweb-cores").catch(() => null);
        const cached = coreCache ? await coreCache.match(coreUrl).catch(() => null) : null;
        if (cached) {
          setBootState({ message: `${activeCoreId.toUpperCase()} core loaded (cached)`, percent: 85 });
        } else {
          setBootState({ message: `First-time download: ${activeCoreId.toUpperCase()} core…`, percent: 80 });
        }
        const launchArgs = {
          core: activeCoreId,
          rom: new File([normalized.blob], normalized.filename),
          ...(sramBlob ? { sram: sramBlob } : {}),
          ...(biosFiles.length ? { bios: biosFiles } : {}),
          element: canvasRef.current as HTMLCanvasElement,
          resolveCoreJs: () => `${activeCorePath}.js`,
          resolveCoreWasm: () => `${activeCorePath}.wasm`,
          retroarchConfig: {
            menu_driver: "null",
            network_buildbot_auto_extract_archive: "false",
          },
        };

        const launched = await Promise.race([
          Nostalgist.launch(launchArgs),
          new Promise<never>((_, reject) =>
            setTimeout(() => reject(new Error("Emulator boot timed out after 20 seconds.")), 20_000)
          ),
        ]);

        if (!isMounted) return;

        emulatorRef.current = launched as Nostalgist;
        setBootState(null);
        sessionStartedAtRef.current = Date.now();
        // Focus canvas so keyboard input reaches RetroArch
        setTimeout(() => canvasRef.current?.focus(), 100);
        await refreshSlots();

        // Store last played game for AI chat context
        const gameName = routeState?.filename || normalized.filename;
        sessionStorage.setItem("retroweb.lastPlayedGame", gameName);

        // Achievement: first game
        void checkAndUnlock("first_game");

        if (gameId) {
          void updateGameMetadata(gameId, { lastSessionStartedAt: sessionStartedAtRef.current });
        }

        if (typeof autoLoadSlot === "number") {
          try {
            const state = await loadState(activeFilename, autoLoadSlot);
            if (state?.data) {
              const emulator = emulatorRef.current as unknown as { loadState?: (blob: Blob) => Promise<void> } | null;
              if (emulator?.loadState) {
                await emulator.loadState(new Blob([new Uint8Array(state.data).buffer]));
                toast.success(`Quick resume loaded (slot ${autoLoadSlot})`);
              }
            }
          } catch (error) {
            console.error("Auto-load state failed", error);
          }
        }

        autosaveTimerRef.current = setInterval(() => {
          void flushAutoSave("interval");
        }, 45_000);
      } catch (error) {
        console.error("Boot error", error);

        if (!isMounted) return;

        if (error instanceof NormalizeError) {
          setRuntimeError({
            userMessage: error.userMessage,
            technicalMessage: `${error.code}: ${error.message}`,
          });
        } else {
          const message = error instanceof Error ? error.message : "Unknown emulator error";
          setRuntimeError({
            userMessage: "The emulator failed to start.",
            technicalMessage: message,
          });
        }
        setBootState(null);
      }
    };

    void launch();

    const onVisibilityChange = () => {
      if (document.hidden) {
        void flushAutoSave("visibility");
      }
    };

    const onBeforeUnload = () => {
      void flushAutoSave("beforeunload");
    };

    document.addEventListener("visibilitychange", onVisibilityChange);
    window.addEventListener("beforeunload", onBeforeUnload);

    return () => {
      isMounted = false;
      document.removeEventListener("visibilitychange", onVisibilityChange);
      window.removeEventListener("beforeunload", onBeforeUnload);

      if (autosaveTimerRef.current) {
        clearInterval(autosaveTimerRef.current);
        autosaveTimerRef.current = null;
      }

      if (saveIndicatorTimerRef.current) {
        clearTimeout(saveIndicatorTimerRef.current);
      }

      void flushAutoSave("unmount");

      if (gameId && sessionStartedAtRef.current) {
        void recordGameplaySession(gameId, sessionStartedAtRef.current, Date.now());
      }

      if (emulatorRef.current) {
        emulatorRef.current.exit({ removeCanvas: false });
      }
    };
  }, [
    autoLoadSlot,
    didTapToStart,
    flushAutoSave,
    gameId,
    map,
    navigate,
    refreshSlots,
    requestedCoreId,
    resolveCoreByCoreId,
    retryToken,
    romFile,
    routeState?.filename,
  ]);

  const playingTitle = routeState?.filename || romFile?.name || "Emulator";
  const isPSX = requestedCoreId?.includes("pcsx") || requestedCoreId?.includes("beetle_psx") || requestedCoreId?.includes("mednafen_psx");

  const handleDiscSwap = useCallback(() => {
    const emulator = emulatorRef.current;
    if (!emulator) return;
    try {
      emulator.sendCommand("DISK_EJECT_TOGGLE");
      setTimeout(() => {
        emulator.sendCommand("DISK_NEXT");
        setTimeout(() => emulator.sendCommand("DISK_EJECT_TOGGLE"), 200);
      }, 200);
      toast.success("Disc swapped to next disc");
    } catch {
      toast.error("Disc swap failed");
    }
  }, []);

  return (
    <>
      <SwitchGameShell
        title={playingTitle}
        bootState={bootState}
        runtimeError={runtimeError}
        showSaveIndicator={showSaveIndicator}
        onSave={() => void handleSaveState(0)}
        onLoad={() => void handleLoadState(0)}
        onReset={() => void handleReset()}
        onFullscreen={() => void handleFullscreenToggle()}
        onExit={() => navigate("/library")}
        onMenu={() => setIsMenuOpen(true)}
        onRetry={() => { setRuntimeError(null); setRetryToken(p => p + 1); }}
        onAskAI={() => void handleAskAI()}
        onCycleSpeed={cycleSpeed}
        onToggleFps={() => setShowFps((p) => !p)}
        speedMultiplier={speedMultiplier}
        showFps={showFps}
        fps={fps}
        showOverlay={showOverlay}
        onOverlayToggle={() => setShowOverlay(p => !p)}
        controllerState={visualState}
        onNetplay={() => setShowNetplay(p => !p)}
        netplayConnected={netplayConnected}
        onToggleTurbo={() => setTurboEnabled(p => !p)}
        turboEnabled={turboEnabled}
        rewindActive={rewindActive}
        onPiP={() => void handlePiP()}
        speedrunTimer={speedrunTimer}
        speedrunTime={speedrunTime}
        speedrunSplits={speedrunSplits}
        onDiscSwap={isPSX ? handleDiscSwap : undefined}
      >
        {/* iOS tap-to-start overlay */}
        {requiresTapToStart && !didTapToStart && (
          <div style={{ position: 'absolute', inset: 0, zIndex: 70, background: 'rgba(0,0,0,0.9)', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
            <h2 style={{ color: '#fff', fontSize: 24, marginBottom: 8 }}>Tap to Start</h2>
            <button style={{ padding: '12px 24px', background: '#cc0000', color: '#fff', borderRadius: 8, border: 'none', cursor: 'pointer', fontWeight: 700 }} onClick={async () => {
              try {
                const Ctx = window.AudioContext || (window as typeof window & { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
                if (Ctx) { const c = new Ctx(); if (c.state === 'suspended') await c.resume(); }
              } catch {}
              setDidTapToStart(true);
            }}>Start Game</button>
          </div>
        )}
        <canvas
          ref={canvasRef}
          tabIndex={0}
          style={{ width: '100%', height: '100%', objectFit: 'contain', display: 'block', outline: 'none' }}
          onClick={() => { setShowOverlay(false); canvasRef.current?.focus(); }}
          onMouseMove={() => setShowOverlay(true)}
        />
      </SwitchGameShell>

      {isMenuOpen && (
        <div style={{ position: 'fixed', inset: 0, zIndex: 60, background: 'rgba(0,0,0,0.85)', backdropFilter: 'blur(4px)', padding: 24, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <div className="w-full max-w-5xl h-[90vh] bg-card border border-border shadow-2xl flex flex-col rounded-lg">
            <div className="flex items-center justify-between p-6 border-b border-border">
              <h2 className="text-3xl font-bold text-foreground">Save States</h2>
              <button onClick={() => setIsMenuOpen(false)} className="text-muted-foreground hover:text-foreground transition-colors p-2 bg-muted hover:bg-secondary rounded-sm">
                <X size={20} />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto p-6">
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
                {Array.from({ length: 9 }).map((_, index) => {
                  const slotState = slots.find((slot) => slot.slot === index);

                  return (
                    <div key={index} className="border border-border bg-[#111111] overflow-hidden group">
                      <div className="aspect-[4/3] bg-[#0A0A0A] relative flex items-center justify-center overflow-hidden">
                        {slotState?.image ? (
                          <img src={slotState.image} alt={`Slot ${index}`} className="w-full h-full object-cover opacity-80 group-hover:opacity-100 transition-opacity" />
                        ) : (
                          <span className="font-sans text-muted-foreground text-sm uppercase tracking-widest">Empty</span>
                        )}
                        <div className="absolute top-2 left-2 bg-[#1F1F1F]/80 px-2 py-1 text-xs font-sans font-bold text-foreground">SLOT {index}</div>
                      </div>

                      <div className="p-4">
                        {slotState ? (
                          <div className="flex items-center gap-1.5 font-sans text-xs text-muted-foreground mb-4">
                            <Clock size={12} className="text-primary" />
                            {new Date(slotState.timestamp).toLocaleString(undefined, {
                              month: "short",
                              day: "numeric",
                              hour: "2-digit",
                              minute: "2-digit",
                            })}
                          </div>
                        ) : (
                          <div className="h-4 mb-4" />
                        )}

                        <div className="flex gap-2">
                          <button
                            onClick={() => void handleSaveState(index)}
                            className="flex-1 py-2 font-sans text-xs font-bold bg-muted hover:bg-secondary text-foreground transition-colors flex items-center justify-center gap-1.5 rounded-sm"
                          >
                            <Save size={13} /> Save
                          </button>
                          <button
                            onClick={() => void handleLoadState(index)}
                            disabled={!slotState}
                            className={`flex-1 py-2 font-sans text-xs font-bold flex items-center justify-center gap-1.5 transition-colors rounded-sm ${slotState ? "bg-primary text-primary-foreground hover:bg-destructive" : "bg-muted text-muted-foreground opacity-50 cursor-not-allowed"
                              }`}
                          >
                            <Download size={13} /> Load
                          </button>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Netplay panel */}
      {showNetplay && (
        <div style={{ position: 'fixed', top: 0, right: 0, bottom: 0, width: 360, zIndex: 65, background: 'var(--bg-primary)', borderLeft: '1px solid var(--border-soft)', padding: 16, overflowY: 'auto' }}>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-bold" style={{ color: 'var(--text-primary)' }}>Netplay</h2>
            <button onClick={() => setShowNetplay(false)} className="p-1" style={{ color: 'var(--text-muted)' }}>
              <X size={18} />
            </button>
          </div>
          <NetplayPanel
            onRemoteInput={handleNetplayRemoteInput}
            onSessionChange={handleNetplaySessionChange}
          />
        </div>
      )}
    </>
  );
}
