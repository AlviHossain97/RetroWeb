import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router";
import { Nostalgist } from "nostalgist";
import { Clock, Download, Menu, RotateCcw, Save, X, Expand, AlertTriangle } from "lucide-react";
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
  const [showTechnicalDetails, setShowTechnicalDetails] = useState(false);
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const [isOverlayVisible, setIsOverlayVisible] = useState(true);
  const [slots, setSlots] = useState<SaveData[]>([]);
  const [showSaveIndicator, setShowSaveIndicator] = useState(false);
  const [retryToken, setRetryToken] = useState(0);
  const [requiresTapToStart, setRequiresTapToStart] = useState(false);
  const [didTapToStart, setDidTapToStart] = useState(false);

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
          setIsOverlayVisible((prev) => !prev);
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
    };

    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [handleFullscreenToggle, handleLoadState, handleSaveState, isMenuOpen]);

  useEffect(() => {
    let isMounted = true;

    if (!romFile || !requestedCoreId) {
      navigate("/");
      return;
    }

    if (!didTapToStart) {
      setBootState({ message: "Waiting for user gesture...", percent: 0 });
      return;
    }

    const launch = async () => {
      try {
        setRuntimeError(null);
        setShowTechnicalDetails(false);
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

        setBootState({ message: `Loading ${activeCoreId.toUpperCase()} core...`, percent: 82 });
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
        await refreshSlots();

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

  return (
    <div className="relative h-[100dvh] w-full bg-black overflow-hidden">
      {requiresTapToStart && !didTapToStart && (
        <div className="absolute inset-0 z-[70] bg-black/90 backdrop-blur-sm flex flex-col items-center justify-center text-center px-6">
          <h2 className="text-4xl font-bold text-white mb-4">Tap to Start</h2>
          <p className="font-sans text-muted-foreground max-w-md mb-8">
            iOS Safari requires a user gesture to start audio and gameplay.
          </p>
          <button
            className="px-8 py-3 bg-primary text-primary-foreground font-sans font-medium transition-colors hover:bg-destructive rounded-md"
            onClick={async () => {
              try {
                const Ctx = (window.AudioContext || (window as typeof window & { webkitAudioContext?: typeof AudioContext }).webkitAudioContext);
                if (Ctx) {
                  const ctx = new Ctx();
                  if (ctx.state === "suspended") {
                    await ctx.resume();
                  }
                }
              } catch {
                // best-effort only
              }
              setDidTapToStart(true);
            }}
          >
            Start Game
          </button>
        </div>
      )}

      {isOverlayVisible && (
        <div className="absolute top-0 left-0 right-0 z-40 p-4 bg-gradient-to-b from-black/90 via-black/50 to-transparent flex items-center justify-between gap-3 h-24">
          <h2 className="text-xl md:text-2xl font-bold truncate text-white drop-shadow-md pb-4">{playingTitle}</h2>
          <div className="flex items-center gap-3 pb-4">
            <button
              onClick={() => {
                setIsMenuOpen(true);
                setIsOverlayVisible(true);
              }}
              className="bg-primary text-primary-foreground px-4 py-2 font-sans font-medium text-sm flex items-center gap-2 hover:bg-destructive transition-colors rounded-sm shadow-md"
            >
              <Menu size={16} /> Menu (Esc)
            </button>
            <button
              onClick={() => navigate("/")}
              className="bg-card border border-border text-foreground px-4 py-2 flex items-center justify-center transition-colors hover:bg-muted rounded-sm shadow-md"
              title="Back to Library"
            >
              <X size={16} />
            </button>
          </div>
        </div>
      )}

      {(bootState || runtimeError) && (
        <div className="absolute inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-6">
          {!runtimeError && bootState && (
            <div className="w-full max-w-md bg-card border border-border p-8 text-center shadow-2xl rounded-md">
              <div className="w-14 h-14 border-4 border-[#333333] border-t-primary rounded-full animate-spin mx-auto mb-6" />
              <p className="font-sans text-foreground font-bold text-lg mb-4">{bootState.message}</p>
              <div className="w-full bg-[#111111] h-2 overflow-hidden rounded-full">
                <div className="h-full bg-primary transition-all" style={{ width: `${Math.max(4, bootState.percent)}%` }} />
              </div>
            </div>
          )}

          {runtimeError && (
            <div className="w-full max-w-xl bg-card border-t-4 border-t-primary p-8 shadow-2xl rounded-md">
              <div className="flex items-center gap-3 mb-4">
                <AlertTriangle className="text-primary" size={28} />
                <h3 className="text-2xl font-bold text-white">Load Failed</h3>
              </div>
              <p className="font-sans text-muted-foreground mb-6">{runtimeError.userMessage}</p>
              <div className="flex flex-wrap gap-3">
                <button
                  onClick={() => {
                    setRuntimeError(null);
                    setRetryToken((prev) => prev + 1);
                  }}
                  className="px-6 py-2 bg-primary text-primary-foreground font-sans font-medium hover:bg-destructive transition-colors rounded-sm"
                >
                  Try Again
                </button>
                <button
                  onClick={() => navigate("/")}
                  className="px-6 py-2 bg-muted border border-border text-foreground hover:bg-secondary transition-colors rounded-sm"
                >
                  Back to Library
                </button>
              </div>
              <button
                onClick={() => setShowTechnicalDetails((prev) => !prev)}
                className="text-xs text-muted-foreground mt-6 hover:text-foreground font-sans uppercase tracking-widest transition-colors"
              >
                {showTechnicalDetails ? "Hide Details" : "Show Details"}
              </button>
              {showTechnicalDetails && runtimeError.technicalMessage && (
                <pre className="mt-4 text-xs text-destructive/90 bg-[#111111] border border-border p-4 overflow-auto max-h-44 font-mono">
                  {runtimeError.technicalMessage}
                </pre>
              )}
            </div>
          )}
        </div>
      )}

      <div className="absolute inset-x-0 bottom-4 z-30 flex justify-center pointer-events-none">
        <div
          className={`pointer-events-auto transition-all duration-300 flex items-center gap-2 bg-black/65 border border-neutral-700 rounded-full px-3 py-2 ${isOverlayVisible ? "opacity-100" : "opacity-0 translate-y-3"
            }`}
        >
          <button onClick={() => void handleSaveState(0)} className="px-3 py-1.5 rounded-full text-xs bg-neutral-800 hover:bg-neutral-700">
            Save
          </button>
          <button onClick={() => void handleLoadState(0)} className="px-3 py-1.5 rounded-full text-xs bg-neutral-800 hover:bg-neutral-700">
            Load
          </button>
          <button onClick={() => void handleReset()} className="px-3 py-1.5 rounded-full text-xs bg-neutral-800 hover:bg-neutral-700 flex items-center gap-1">
            <RotateCcw size={13} /> Reset
          </button>
          <button onClick={() => void handleFullscreenToggle()} className="px-3 py-1.5 rounded-full text-xs bg-neutral-800 hover:bg-neutral-700 flex items-center gap-1">
            <Expand size={13} /> Fullscreen
          </button>
          <button onClick={() => navigate("/")} className="px-3 py-1.5 rounded-full text-xs bg-neutral-800 hover:bg-neutral-700">
            Library
          </button>
        </div>
      </div>

      <div
        className={`absolute bottom-4 right-4 z-40 transition-all duration-500 flex items-center gap-2 bg-black/65 border border-neutral-700 rounded-full px-3 py-1.5 ${showSaveIndicator ? "opacity-100 translate-y-0" : "opacity-0 translate-y-2 pointer-events-none"
          }`}
      >
        <Save size={15} className="text-primary" />
        <span className="text-xs uppercase tracking-wide">Auto-saved</span>
      </div>

      <canvas
        ref={canvasRef}
        className="w-full h-full object-contain"
        onMouseMove={() => setIsOverlayVisible(true)}
        onClick={() => {
          setIsOverlayVisible(false);
          setIsMenuOpen(false);
        }}
      />

      {isMenuOpen && (
        <div className="absolute inset-0 z-[60] bg-black/85 backdrop-blur-sm p-4 sm:p-8 flex items-center justify-center">
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
    </div>
  );
}
