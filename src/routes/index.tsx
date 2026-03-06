import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router";
import {
  hasBIOS,
  saveBIOS,
  getAllGames,
  saveGameMetadata,
  removeGameMetadata,
  saveRomToOPFS,
  loadRomFromOPFS,
  removeRomFromOPFS,
  type Game,
  updateGameMetadata,
} from "../lib/storage/db";
import { normalizeROM, NormalizeError, type ZipRomCandidate } from "../lib/emulation/rom-normalizer";
import coreMap from "../data/coreMap.json";
import { UploadCloud, AlertCircle, Save, HardDrive, Search, ArrowUpDown } from "lucide-react";
import { toast } from "sonner";
import LibraryGrid from "../components/LibraryGrid";
import { cleanGameTitleFromFilename, getSystemLabel } from "../lib/library/title-utils";
import { md5FromUint8Array } from "../lib/hash/md5";
import { SYSTEMS } from "../data/systemBrowserData";

type SortKey = "name" | "system" | "lastPlayed" | "dateAdded" | "playtime";

const VIEW_MODE_STORAGE_KEY = "retroweb.library.viewMode";
const SORT_STORAGE_KEY = "retroweb.library.sort";

type LibraryProcessingState = { message: string; percent: number } | null;

interface PendingROM {
  file: File;
  systemId: string;
  coreId: string;
  dbId?: string;
}

interface ZipPickerState {
  sourceFile: File;
  candidates: ZipRomCandidate[];
}

export default function Library() {
  const [isDragging, setIsDragging] = useState(false);
  const [games, setGames] = useState<Game[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [persistGame, setPersistGame] = useState(true);
  const [pendingRom, setPendingRom] = useState<PendingROM | null>(null);
  const [missingBiosList, setMissingBiosList] = useState<string[]>([]);
  const [showChdGuide, setShowChdGuide] = useState(false);
  const [viewMode, setViewMode] = useState<"grid" | "list">(() => {
    const stored = localStorage.getItem(VIEW_MODE_STORAGE_KEY);
    return stored === "list" ? "list" : "grid";
  });
  const [sortBy, setSortBy] = useState<SortKey>(() => {
    const stored = localStorage.getItem(SORT_STORAGE_KEY);
    return stored === "name" || stored === "system" || stored === "lastPlayed" || stored === "dateAdded" || stored === "playtime"
      ? stored
      : "dateAdded";
  });
  const [processingState, setProcessingState] = useState<LibraryProcessingState>(null);
  const [zipPicker, setZipPicker] = useState<ZipPickerState | null>(null);
  const [coverTargetGameId, setCoverTargetGameId] = useState<string | null>(null);

  const coverInputRef = useRef<HTMLInputElement>(null);
  const navigate = useNavigate();

  const map = coreMap as Record<
    string,
    {
      preferredCore: string;
      fallbackCores?: string[];
      biosRequired?: string[];
    }
  >;

  const fetchGames = async () => {
    const allGames = await getAllGames();
    setGames(allGames);
  };

  useEffect(() => {
    fetchGames();
  }, []);

  useEffect(() => {
    localStorage.setItem(VIEW_MODE_STORAGE_KEY, viewMode);
  }, [viewMode]);

  useEffect(() => {
    localStorage.setItem(SORT_STORAGE_KEY, sortBy);
  }, [sortBy]);

  const resolveCoreForSystem = (systemId: string) => {
    const systemInfo = map[systemId];
    if (!systemInfo) return { systemInfo: null, coreId: "" };
    return {
      systemInfo,
      coreId: systemInfo.preferredCore || systemInfo.fallbackCores?.[0] || "",
    };
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const launchGameFromFile = (payload: { romFile: File; coreId: string; filename: string; gameId?: string; autoLoadSlot?: number }) => {
    navigate("/play", {
      state: {
        romFile: payload.romFile,
        coreId: payload.coreId,
        filename: payload.filename,
        gameId: payload.gameId,
        autoLoadSlot: payload.autoLoadSlot,
      },
    });
  };

  const processFile = async (
    file: File,
    options: { autoLaunch: boolean; selectedZipEntry?: string }
  ): Promise<{ status: "added" | "duplicate" | "launched" | "failed"; systemId?: string }> => {
    setShowChdGuide(false);
    setProcessingState({ message: "Preparing ROM...", percent: 0 });

    let normalized;
    try {
      normalized = await normalizeROM(file, {
        selectedZipEntry: options.selectedZipEntry,
        onProgress: (percent, message) => setProcessingState({ percent, message }),
      });
    } catch (error) {
      setProcessingState(null);
      if (error instanceof NormalizeError) {
        if (error.code === "zip_multiple_roms" && error.candidates?.length && !options.selectedZipEntry) {
          setZipPicker({ sourceFile: file, candidates: error.candidates });
          return { status: "failed" };
        }
        if (error.code === "disc_format_requires_chd") {
          setShowChdGuide(true);
          return { status: "failed" };
        }
        toast.error(error.userMessage);
      } else {
        toast.error(`Could not parse ${file.name}`);
      }
      return { status: "failed" };
    }

    if (normalized.warning) {
      toast.info(normalized.warning);
    }

    const actualFile = new File([normalized.blob], normalized.filename, { type: "application/octet-stream" });
    const systemId = normalized.systemId;
    const { systemInfo, coreId } = resolveCoreForSystem(systemId);

    if (!systemInfo || !coreId) {
      setProcessingState(null);
      toast.error(`Unable to determine emulator core for ${actualFile.name}`);
      return { status: "failed" };
    }

    if (!persistGame && !options.autoLaunch) {
      setProcessingState(null);
      toast.warning("Memory Only mode is single-launch only. Use Add to Library for batch imports.");
      return { status: "failed", systemId };
    }

    let romHash: string | undefined;
    if (persistGame) {
      const romBuffer = await actualFile.arrayBuffer();
      romHash = md5FromUint8Array(new Uint8Array(romBuffer));
    }

    const duplicate = games.find(
      (game) => game.system === systemId && (game.filename === actualFile.name || (romHash && game.romHash === romHash))
    );

    if (duplicate) {
      setProcessingState(null);
      toast.info(`${duplicate.displayTitle || duplicate.title} is already in your library.`);
      if (options.autoLaunch) {
        await handleLaunchGame(duplicate);
      }
      return { status: "duplicate", systemId };
    }

    let dbId: string | undefined;

    if (persistGame) {
      dbId = crypto.randomUUID();
      const cleanedTitle = cleanGameTitleFromFilename(actualFile.name);
      const newGame: Game = {
        id: dbId,
        title: actualFile.name.replace(/\.[^.]+$/, ""),
        displayTitle: cleanedTitle,
        system: systemId,
        core: coreId,
        filename: actualFile.name,
        size: actualFile.size,
        addedAt: Date.now(),
        isFavorite: false,
        hasLocalRom: true,
        romHash,
      };

      try {
        setProcessingState({ message: "Saving to library...", percent: 100 });
        await saveRomToOPFS(dbId, actualFile);
        await saveGameMetadata(newGame);
        await fetchGames();
      } catch (error) {
        console.error(error);
        dbId = undefined;
        toast.error("Could not save game to library. Continuing in memory mode.");
      }
    }

    const requiredBios = systemInfo.biosRequired ?? [];
    const missing: string[] = [];

    for (const biosName of requiredBios) {
      if (!(await hasBIOS(biosName))) {
        missing.push(biosName);
      }
    }

    if (missing.length > 0) {
      setProcessingState(null);
      if (options.autoLaunch) {
        setMissingBiosList(missing);
        setPendingRom({ file: actualFile, systemId, coreId, dbId });
      } else {
        toast.warning(`${actualFile.name} added, but BIOS is still required before launch.`);
      }
      return { status: dbId ? "added" : "failed", systemId };
    }

    if (options.autoLaunch) {
      setProcessingState({ message: "Starting game...", percent: 100 });
      launchGameFromFile({ romFile: actualFile, coreId, filename: actualFile.name, gameId: dbId });
      setTimeout(() => setProcessingState(null), 250);
      return { status: "launched", systemId };
    }

    setProcessingState(null);
    return { status: "added", systemId };
  };

  const processManyFiles = async (files: File[]) => {
    const autoLaunch = files.length === 1;
    const summaryBySystem: Record<string, number> = {};
    let added = 0;
    let duplicate = 0;
    let failed = 0;

    for (const file of files) {
      const result = await processFile(file, { autoLaunch });
      if (result.status === "added") {
        added++;
      } else if (result.status === "duplicate") {
        duplicate++;
      } else if (result.status === "failed") {
        failed++;
      }

      if (result.systemId) {
        summaryBySystem[result.systemId] = (summaryBySystem[result.systemId] ?? 0) + (result.status === "added" ? 1 : 0);
      }
    }

    if (files.length > 1) {
      const breakdown = Object.entries(summaryBySystem)
        .filter(([, count]) => count > 0)
        .map(([systemId, count]) => `${count} ${getSystemLabel(systemId)}`)
        .join(", ");
      const summary = [`Added ${added} game${added === 1 ? "" : "s"}`];
      if (duplicate) summary.push(`${duplicate} duplicate${duplicate === 1 ? "" : "s"} skipped`);
      if (failed) summary.push(`${failed} failed`);

      toast.success(`${summary.join(" · ")}${breakdown ? ` (${breakdown})` : ""}`);
    }
  };

  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);

    const files = Array.from(e.dataTransfer.files ?? []);
    if (!files.length) return;
    await processManyFiles(files);
  };

  const handleFileInput = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files ?? []);
    if (!files.length) return;
    await processManyFiles(files);
    e.target.value = "";
  };

  const handleBiosUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!pendingRom || !e.target.files?.length) return;
    const file = e.target.files[0];

    const uploadedName = file.name.toLowerCase();
    const acceptedNames = missingBiosList.map((name) => name.toLowerCase());
    if (!acceptedNames.includes(uploadedName)) {
      toast.error(`Unexpected BIOS. Expected: ${missingBiosList.join(", ")}`);
      return;
    }

    try {
      const buffer = await file.arrayBuffer();
      const result = await saveBIOS(file.name, pendingRom.systemId, new Uint8Array(buffer), {
        sourceFilename: file.name,
      });
      if (result.sizeWarning) {
        toast.warning(`Installed ${result.filename}, but size seems unusual: ${result.sizeWarning}`);
      } else if (result.verifiedHash) {
        toast.success(`✅ ${result.filename} verified and installed`);
      } else {
        toast.success(`✅ ${result.filename} installed (hash not recognized)`);
      }

      const remaining = [];
      for (const biosName of missingBiosList) {
        if (!(await hasBIOS(biosName))) {
          remaining.push(biosName);
        }
      }

      setMissingBiosList(remaining);

      if (remaining.length === 0) {
        launchGameFromFile({
          romFile: pendingRom.file,
          coreId: pendingRom.coreId,
          filename: pendingRom.file.name,
          gameId: pendingRom.dbId,
        });
      }
    } catch (error) {
      console.error(error);
      toast.error("Failed to save BIOS file.");
    }
  };

  const handleLaunchGame = async (game: Game) => {
    let romFile: File | null = null;
    if (game.hasLocalRom) {
      romFile = await loadRomFromOPFS(game.id, game.filename);
    }

    if (!romFile) {
      toast.error("Could not find the ROM file in local storage.");
      return;
    }

    const { systemInfo } = resolveCoreForSystem(game.system);
    const requiredBios = systemInfo?.biosRequired ?? [];
    const missing: string[] = [];
    for (const biosName of requiredBios) {
      if (!(await hasBIOS(biosName))) {
        missing.push(biosName);
      }
    }

    if (missing.length > 0) {
      setMissingBiosList(missing);
      setPendingRom({
        file: romFile,
        systemId: game.system,
        coreId: game.core,
        dbId: game.id,
      });
      return;
    }

    await updateGameMetadata(game.id, { lastSessionStartedAt: Date.now() });

    launchGameFromFile({
      romFile,
      coreId: game.core,
      filename: game.filename,
      gameId: game.id,
      autoLoadSlot: game.lastAutoSaveAt ? 0 : undefined,
    });
  };

  const handleToggleFavorite = async (id: string, isFavorite: boolean) => {
    await updateGameMetadata(id, { isFavorite });
    fetchGames();
  };

  const handleRemoveGame = async (id: string) => {
    if (!window.confirm("Are you sure you want to remove this game from your library?")) return;
    await removeRomFromOPFS(id);
    await removeGameMetadata(id);
    toast.success("Game removed from library");
    fetchGames();
  };

  const handleSetCover = (id: string) => {
    setCoverTargetGameId(id);
    coverInputRef.current?.click();
  };

  const handleCoverInput = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!coverTargetGameId || !e.target.files?.length) return;
    const imageFile = e.target.files[0];

    try {
      const base64 = await new Promise<string>((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(String(reader.result));
        reader.onerror = reject;
        reader.readAsDataURL(imageFile);
      });

      await updateGameMetadata(coverTargetGameId, { coverUrl: base64 });
      toast.success("Cover art updated");
      fetchGames();
    } catch (error) {
      console.error(error);
      toast.error("Failed to save cover art");
    } finally {
      setCoverTargetGameId(null);
      e.target.value = "";
    }
  };

  const searchSuggestions = useMemo(() => {
    if (searchQuery.trim().length < 2) return [];
    const q = searchQuery.toLowerCase();
    return SYSTEMS.filter((system) => system.name.toLowerCase().includes(q)).slice(0, 4);
  }, [searchQuery]);

  const filteredGames = useMemo(() => {
    if (!searchQuery.trim()) return games;
    const q = searchQuery.toLowerCase();
    return games.filter((game) => {
      const systemName = SYSTEMS.find((system) => system.id === game.system)?.name ?? game.system;
      return [game.title, game.displayTitle, game.system, systemName, game.filename]
        .filter(Boolean)
        .some((token) => token!.toLowerCase().includes(q));
    });
  }, [games, searchQuery]);

  const sortedGames = useMemo(() => {
    const list = [...filteredGames];
    list.sort((a, b) => {
      switch (sortBy) {
        case "name":
          return (a.displayTitle || a.title).localeCompare(b.displayTitle || b.title);
        case "system":
          return a.system.localeCompare(b.system) || (a.displayTitle || a.title).localeCompare(b.displayTitle || b.title);
        case "lastPlayed":
          return (b.lastPlayed ?? 0) - (a.lastPlayed ?? 0);
        case "playtime":
          return (b.playtime ?? 0) - (a.playtime ?? 0);
        case "dateAdded":
        default:
          return b.addedAt - a.addedAt;
      }
    });
    return list;
  }, [filteredGames, sortBy]);

  const favoriteGames = useMemo(() => sortedGames.filter((game) => game.isFavorite), [sortedGames]);
  const recentGames = useMemo(
    () => [...sortedGames].filter((game) => game.lastPlayed).sort((a, b) => (b.lastPlayed ?? 0) - (a.lastPlayed ?? 0)).slice(0, 8),
    [sortedGames]
  );

  const hasGames = games.length > 0;

  if (pendingRom && missingBiosList.length > 0) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-8">
        <div className="w-full max-w-lg p-10 mt-8 border border-[#C9A962]/30 bg-[#1A1A0A] flex flex-col items-center justify-center text-center shadow-2xl">
          <AlertCircle size={48} className="text-[#C9A962] mb-4" />
          <h2 className="text-3xl font-serif text-foreground mb-4">BIOS Required</h2>
          <p className="font-sans text-[15px] text-muted-foreground mb-6">
            To play <strong className="text-foreground">{pendingRom.file.name}</strong>, upload the required BIOS file(s):
          </p>
          <ul className="bg-[#0A0A0A] border border-[#222222] p-4 w-full mb-8 font-mono text-sm text-[#C9A962] text-left">
            {missingBiosList.map((name) => (
              <li key={name}>{name}</li>
            ))}
          </ul>

          <button
            className="w-full bg-[#C9A962] hover:bg-[#B3934B] text-[#0A0A0A] py-4 px-6 font-sans text-xs uppercase tracking-widest font-bold transition-colors"
            onClick={() => document.getElementById("bios-upload")?.click()}
          >
            Upload Missing BIOS
          </button>
          <input id="bios-upload" type="file" className="hidden" onChange={handleBiosUpload} />

          <button className="mt-6 font-sans text-[10px] uppercase tracking-widest text-muted-foreground hover:text-foreground transition-colors" onClick={() => { setPendingRom(null); setMissingBiosList([]); }}>
            Cancel and return to Library
          </button>
        </div>
      </div>
    );
  }

  if (showChdGuide) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-8">
        <div className="w-full max-w-xl p-10 mt-8 border border-destructive/30 bg-[#1A0A0A] flex flex-col items-start shadow-2xl">
          <div className="flex items-center gap-5 mb-6">
            <UploadCloud size={40} className="text-destructive" />
            <h2 className="text-3xl font-serif text-foreground">CHD Format Required</h2>
          </div>
          <p className="font-sans text-[15px] text-muted-foreground mb-8 leading-relaxed">
            Disc-based games must be converted to <strong className="text-foreground">.chd</strong> before launching in browser. Please convert your image and try again.
          </p>
          <button
            className="w-full font-sans text-xs uppercase tracking-widest font-bold text-muted-foreground hover:text-foreground border border-border bg-[#111111] hover:bg-[#1A1A1A] py-4 transition-colors"
            onClick={() => setShowChdGuide(false)}
          >
            Got it
          </button>
        </div>
      </div>
    );
  }

  return (
    <div
      className="flex-1 flex flex-col items-start p-4 md:p-8 w-full h-full relative"
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      {isDragging && (
        <div className="absolute inset-0 z-40 bg-black/85 backdrop-blur-sm border border-dashed border-muted-foreground m-8 flex flex-col items-center justify-center pointer-events-none">
          <UploadCloud size={80} className="text-primary mb-6 animate-pulse" strokeWidth={1.5} />
          <h2 className="text-[32px] font-serif tracking-tight text-foreground drop-shadow-lg">Import ROMs</h2>
          <p className="text-muted-foreground font-sans mt-2">Release files anywhere to add to library</p>
        </div>
      )}

      {processingState && (
        <div className="absolute top-4 right-4 z-50 bg-black/70 border border-neutral-700 rounded-lg px-4 py-3 w-80">
          <p className="text-sm text-neutral-200 mb-2">{processingState.message}</p>
          <div className="w-full bg-neutral-800 rounded-full h-2 overflow-hidden">
            <div className="h-2 bg-primary transition-all" style={{ width: `${Math.max(5, processingState.percent)}%` }} />
          </div>
        </div>
      )}

      {zipPicker && (
        <div className="absolute inset-0 z-50 bg-black/80 backdrop-blur-sm p-4 flex items-center justify-center">
          <div className="w-full max-w-xl bg-card border border-border p-8 shadow-2xl animate-in fade-in zoom-in duration-300">
            <h3 className="text-3xl font-serif text-foreground mb-4">Multiple ROMs found in ZIP</h3>
            <p className="font-sans text-[15px] text-muted-foreground mb-8">Choose one file to import from {zipPicker.sourceFile.name}.</p>
            <div className="max-h-80 overflow-y-auto space-y-3 pr-2 scrollbar-thin">
              {zipPicker.candidates.map((candidate) => (
                <button
                  key={candidate.id}
                  className="w-full text-left p-4 border border-border bg-[#111111] hover:border-primary/50 hover:bg-[#1A1A1A] transition-colors flex flex-col gap-1"
                  onClick={async () => {
                    const source = zipPicker.sourceFile;
                    setZipPicker(null);
                    await processFile(source, { autoLaunch: true, selectedZipEntry: candidate.id });
                  }}
                >
                  <div className="font-serif text-lg text-foreground">{candidate.displayName}</div>
                  <div className="font-sans text-[10px] uppercase tracking-widest text-muted-foreground">
                    {getSystemLabel(candidate.detectedSystem)} • {(candidate.size / (1024 * 1024)).toFixed(2)} MB
                  </div>
                </button>
              ))}
            </div>
            <button className="mt-8 font-sans text-xs uppercase tracking-widest font-bold text-muted-foreground hover:text-foreground w-full text-center py-4 border border-transparent hover:border-border transition-colors" onClick={() => setZipPicker(null)}>
              Cancel
            </button>
          </div>
        </div>
      )}

      <div className="flex flex-col md:flex-row justify-between items-start md:items-center w-full mb-8 gap-4">
        <div className="flex flex-col gap-2 w-full md:w-auto">
          {hasGames && (
            <div className="relative w-full max-w-md">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" size={16} />
              <input
                type="text"
                placeholder="Search library..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full bg-[#111111] border border-border text-foreground pl-10 pr-4 py-2 font-sans text-sm focus:outline-none focus:border-primary transition-colors placeholder:text-muted-foreground"
              />
            </div>
          )}

          {searchSuggestions.length > 0 && (
            <div className="flex flex-wrap gap-2 mt-1">
              {searchSuggestions.map((system) => (
                <button
                  key={system.id}
                  className="text-xs px-2 py-1 rounded-sm border border-border text-muted-foreground hover:text-foreground hover:border-primary"
                  onClick={() => setSearchQuery(system.name)}
                >
                  {system.name}
                </button>
              ))}
            </div>
          )}
        </div>

        <div className="flex flex-col sm:flex-row gap-3 w-full md:w-auto">
          <div className="flex items-center gap-2 bg-[#111111] border border-border px-3 py-2 text-sm font-sans text-foreground">
            <ArrowUpDown size={15} className="text-muted-foreground" />
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as SortKey)}
              className="bg-transparent focus:outline-none cursor-pointer"
            >
              <option value="dateAdded">Sort: Date Added</option>
              <option value="name">Sort: Name</option>
              <option value="system">Sort: System</option>
              <option value="lastPlayed">Sort: Last Played</option>
              <option value="playtime">Sort: Playtime</option>
            </select>
          </div>

          <div className="flex items-center gap-3 bg-[#111111] border border-border p-1 w-full sm:w-auto">
            <button
              onClick={() => setPersistGame(true)}
              className={`flex flex-1 justify-center items-center gap-2 px-3 py-1.5 text-sm font-sans transition-colors ${persistGame ? "bg-primary text-black font-medium" : "text-muted-foreground hover:text-foreground"
                }`}
            >
              <HardDrive size={16} />
              Add to Library
            </button>
            <button
              onClick={() => setPersistGame(false)}
              className={`flex flex-1 justify-center items-center gap-2 px-3 py-1.5 text-sm font-sans transition-colors ${!persistGame ? "bg-primary text-black font-medium" : "text-muted-foreground hover:text-foreground"
                }`}
            >
              <Save size={16} />
              Memory Only
            </button>
          </div>
        </div>
      </div>

      {hasGames ? (
        <div className="w-full flex-1 flex flex-col gap-6">
          {!searchQuery.trim() && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="bg-card border border-border p-5">
                <p className="font-sans text-xs text-muted-foreground uppercase tracking-widest mb-2">Recently Played</p>
                <p className="font-serif text-[28px] text-foreground leading-none mb-1">{recentGames.length}</p>
                <p className="font-sans text-xs text-muted-foreground">Top games with play history</p>
              </div>
              <div className="bg-card border border-border p-5">
                <p className="font-sans text-xs text-muted-foreground uppercase tracking-widest mb-2">Favorites</p>
                <p className="font-serif text-[28px] text-primary leading-none mb-1">{favoriteGames.length}</p>
                <p className="font-sans text-xs text-muted-foreground">Marked with a star</p>
              </div>
            </div>
          )}

          <div className="w-full flex-1">
            <h2 className="text-xl font-bold mb-4 text-neutral-300">{searchQuery.trim() ? "Search Results" : "All Games"}</h2>
            {sortedGames.length > 0 ? (
              <LibraryGrid
                games={sortedGames}
                viewMode={viewMode}
                onViewModeChange={setViewMode}
                onLaunch={handleLaunchGame}
                onToggleFavorite={handleToggleFavorite}
                onRemove={handleRemoveGame}
                onSetCover={handleSetCover}
              />
            ) : (
              <div className="text-neutral-500 py-8 text-center bg-neutral-900/50 rounded-xl border border-neutral-800">
                No games found matching "{searchQuery}"
              </div>
            )}
          </div>
        </div>
      ) : (
        <div className="flex-1 w-full flex flex-col items-center justify-center p-8">
          <div
            className="w-full max-w-xl p-12 mt-8 flex flex-col items-center justify-center cursor-pointer group"
            onClick={() => document.getElementById("file-upload")?.click()}
          >
            <UploadCloud size={64} className="text-muted-foreground mb-6 group-hover:text-primary transition-colors" strokeWidth={1.5} />
            <h2 className="text-[32px] font-serif tracking-tight text-foreground mb-4">Your library is empty</h2>
            <p className="font-sans text-muted-foreground text-center max-w-md mb-8">
              Drag and drop ROM files anywhere to import them, or click to browse files.
            </p>
            <span className="bg-primary hover:bg-[#B3934B] text-[#0A0A0A] px-6 py-3 font-sans font-medium transition-colors">
              Browse Files
            </span>
          </div>
        </div>
      )}

      <input
        id="file-upload"
        type="file"
        className="hidden"
        multiple
        onChange={handleFileInput}
        accept=".nes,.zip,.smc,.sfc,.gb,.gbc,.gba,.md,.smd,.gen,.bin,.chd,.pbp,.n64,.z64,.v64"
      />

      <input
        ref={coverInputRef}
        type="file"
        accept="image/png,image/jpeg,image/webp"
        className="hidden"
        onChange={handleCoverInput}
      />
    </div>
  );
}
