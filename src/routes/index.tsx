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
  type Collection,
  updateGameMetadata,
  getAllCollections,
  saveCollection,
  removeCollection,
  addGameToCollection,
  removeGameFromCollection,
} from "../lib/storage/db";
import { normalizeROM, NormalizeError, type ZipRomCandidate } from "../lib/emulation/rom-normalizer";
import coreMap from "../data/coreMap.json";
import { UploadCloud, AlertCircle, Save, HardDrive, Search, ArrowUpDown, Gamepad2, FolderPlus, Folder, X, ImageDown } from "lucide-react";
import { toast } from "sonner";
import LibraryGrid from "../components/LibraryGrid";
import GameDetailsDrawer from "../components/GameDetailsDrawer";
import LoaderOverlay from "../components/LoaderOverlay";
import { cleanGameTitleFromFilename, getSystemLabel } from "../lib/library/title-utils";
import { md5FromUint8Array } from "../lib/hash/md5";
import { SYSTEMS } from "../data/systemBrowserData";
import { scrapeGameMetadata, scrapeAllMissingMetadata } from "../lib/metadata/scraper";

type SortKey = "name" | "system" | "lastPlayed" | "dateAdded" | "playtime" | "rating";

/* From Uiverse.io by akshat-patel28 — neon upload circle, colour-matched */
const UPLOAD_CSS = `
.rw-upload-div {
  position: relative;
  width: 100px;
  height: 100px;
  border-radius: 50%;
  border: 2px solid var(--accent-primary);
  display: flex;
  justify-content: center;
  align-items: center;
  overflow: hidden;
  box-shadow: 0px 0px 100px var(--accent-primary), inset 0px 0px 10px var(--accent-primary), 0px 0px 5px rgb(255, 255, 255);
  animation: rw-flicker 2s linear infinite;
  cursor: pointer;
}

.rw-upload-icon {
  color: var(--accent-primary);
  font-size: 2rem;
  cursor: pointer;
  animation: rw-iconflicker 2s linear infinite;
}

.rw-upload-div .rw-upload-input {
  position: absolute;
  opacity: 0;
  width: 100%;
  height: 100%;
  cursor: pointer !important;
}

@keyframes rw-flicker {
  0% {
    border: 2px solid var(--accent-primary);
    box-shadow: 0px 0px 100px var(--accent-primary), inset 0px 0px 10px var(--accent-primary), 0px 0px 5px rgb(255, 255, 255);
  }
  5% {
    border: none;
    box-shadow: none;
  }
  10% {
    border: 2px solid var(--accent-primary);
    box-shadow: 0px 0px 100px var(--accent-primary), inset 0px 0px 10px var(--accent-primary), 0px 0px 5px rgb(255, 255, 255);
  }
  25% {
    border: none;
    box-shadow: none;
  }
  30% {
    border: 2px solid var(--accent-primary);
    box-shadow: 0px 0px 100px var(--accent-primary), inset 0px 0px 10px var(--accent-primary), 0px 0px 5px rgb(255, 255, 255);
  }
  100% {
    border: 2px solid var(--accent-primary);
    box-shadow: 0px 0px 100px var(--accent-primary), inset 0px 0px 10px var(--accent-primary), 0px 0px 5px rgb(255, 255, 255);
  }
}

@keyframes rw-iconflicker {
  0% { opacity: 1; }
  5% { opacity: 0.2; }
  10% { opacity: 1; }
  25% { opacity: 0.2; }
  30% { opacity: 1; }
  100% { opacity: 1; }
}
`;

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
  const [viewMode, setViewMode] = useState<"grid" | "list" | "carousel">(() => {
    const stored = localStorage.getItem(VIEW_MODE_STORAGE_KEY);
    return (stored === "list" || stored === "carousel") ? stored as "list" | "carousel" : "grid";
  });
  const [sortBy, setSortBy] = useState<SortKey>(() => {
    const stored = localStorage.getItem(SORT_STORAGE_KEY);
    return stored === "name" || stored === "system" || stored === "lastPlayed" || stored === "dateAdded" || stored === "playtime" || stored === "rating"
      ? stored
      : "dateAdded";
  });
  const [processingState, setProcessingState] = useState<LibraryProcessingState>(null);
  const [zipPicker, setZipPicker] = useState<ZipPickerState | null>(null);
  const [coverTargetGameId, setCoverTargetGameId] = useState<string | null>(null);
  const [selectedGame, setSelectedGame] = useState<Game | null>(null);

  // Collections
  const [collections, setCollections] = useState<Collection[]>([]);
  const [activeCollectionId, setActiveCollectionId] = useState<string | null>(null);
  const [showNewCollection, setShowNewCollection] = useState(false);
  const [newCollectionName, setNewCollectionName] = useState("");
  const [scrapingArt, setScrapingArt] = useState(false);

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

  const fetchCollections = async () => {
    const cols = await getAllCollections();
    setCollections(cols);
  };

  useEffect(() => {
    fetchGames();
    fetchCollections();
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
        // Auto-scrape cover art in background
        void scrapeGameMetadata(newGame).then((found) => {
          if (found) fetchGames();
        });
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

  const handleCreateCollection = async () => {
    const name = newCollectionName.trim();
    if (!name) return;
    const col: Collection = { id: crypto.randomUUID(), name, createdAt: Date.now() };
    await saveCollection(col);
    setNewCollectionName("");
    setShowNewCollection(false);
    await fetchCollections();
    toast.success(`Collection "${name}" created`);
  };

  const handleDeleteCollection = async (id: string) => {
    await removeCollection(id);
    if (activeCollectionId === id) setActiveCollectionId(null);
    await fetchCollections();
    await fetchGames();
  };

  const handleAddToCollection = async (gameId: string, collectionId: string) => {
    await addGameToCollection(gameId, collectionId);
    await fetchGames();
    toast.success("Added to collection");
  };

  const handleRemoveFromCollection = async (gameId: string, collectionId: string) => {
    await removeGameFromCollection(gameId, collectionId);
    await fetchGames();
  };

  const handleScrapeAllArt = async () => {
    setScrapingArt(true);
    try {
      const count = await scrapeAllMissingMetadata(games, (done, total) => {
        toast.loading(`Fetching artwork... ${done}/${total}`, { id: "scrape-art" });
      });
      toast.dismiss("scrape-art");
      toast.success(count > 0 ? `Found artwork for ${count} game${count > 1 ? "s" : ""}` : "No new artwork found");
      if (count > 0) await fetchGames();
    } finally {
      setScrapingArt(false);
    }
  };

  const searchSuggestions = useMemo(() => {
    if (searchQuery.trim().length < 2) return [];
    const q = searchQuery.toLowerCase();
    return SYSTEMS.filter((system) => system.name.toLowerCase().includes(q)).slice(0, 4);
  }, [searchQuery]);

  const filteredGames = useMemo(() => {
    let result = games;
    // Smart playlists
    if (activeCollectionId === "__unplayed") {
      result = result.filter((game) => !game.lastPlayed);
    } else if (activeCollectionId === "__most_played") {
      result = [...result].sort((a, b) => (b.playtime ?? 0) - (a.playtime ?? 0)).slice(0, 20);
    } else if (activeCollectionId === "__stale") {
      const thirtyDaysAgo = Date.now() - 30 * 24 * 60 * 60 * 1000;
      result = result.filter((game) => game.lastPlayed && game.lastPlayed < thirtyDaysAgo);
    } else if (activeCollectionId === "__top_rated") {
      result = result.filter((game) => (game.rating ?? 0) >= 4);
    } else if (activeCollectionId === "__duplicates") {
      const hashCounts = new Map<string, number>();
      for (const g of result) { if (g.romHash) hashCounts.set(g.romHash, (hashCounts.get(g.romHash) ?? 0) + 1); }
      result = result.filter((g) => g.romHash && (hashCounts.get(g.romHash) ?? 0) > 1);
    } else if (activeCollectionId) {
      result = result.filter((game) => game.collectionIds?.includes(activeCollectionId));
    }
    if (!searchQuery.trim()) return result;
    const q = searchQuery.toLowerCase();
    return result.filter((game) => {
      const systemName = SYSTEMS.find((system) => system.id === game.system)?.name ?? game.system;
      return [game.title, game.displayTitle, game.system, systemName, game.filename]
        .filter(Boolean)
        .some((token) => token!.toLowerCase().includes(q));
    });
  }, [games, searchQuery, activeCollectionId]);

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
        case "rating":
          return (b.rating ?? 0) - (a.rating ?? 0);
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
      <style dangerouslySetInnerHTML={{ __html: UPLOAD_CSS }} />
      {isDragging && (
        <div className="absolute inset-0 z-40 bg-black/85 backdrop-blur-sm border border-dashed border-muted-foreground m-8 flex flex-col items-center justify-center pointer-events-none">
          <UploadCloud size={80} className="text-primary mb-6 animate-pulse" strokeWidth={1.5} />
          <h2 className="text-[32px] font-serif tracking-tight text-foreground drop-shadow-lg">Import ROMs</h2>
          <p className="text-muted-foreground font-sans mt-2">Release files anywhere to add to library</p>
        </div>
      )}

      <LoaderOverlay
        visible={processingState !== null}
        mode="upload"
        message={processingState?.message}
      />

      {zipPicker && (
        <div className="absolute inset-0 z-50 bg-black/80 backdrop-blur-sm p-4 flex items-center justify-center">
          <div className="w-full max-w-xl bg-card border border-border p-8 shadow-2xl animate-in fade-in zoom-in duration-300">
            <h3 className="text-3xl font-serif text-foreground mb-4">Multiple ROMs found in ZIP</h3>
            <p className="font-sans text-[15px] text-muted-foreground mb-8">Choose one file or import all from {zipPicker.sourceFile.name}.</p>
            {zipPicker.candidates.length > 1 && (
              <button
                className="w-full mb-4 p-3 border border-blue-500/30 bg-blue-500/10 hover:bg-blue-500/20 text-blue-400 text-sm font-medium transition-colors rounded-lg"
                onClick={async () => {
                  const source = zipPicker.sourceFile;
                  const candidates = zipPicker.candidates;
                  setZipPicker(null);
                  for (const candidate of candidates) {
                    await processFile(source, { autoLaunch: false, selectedZipEntry: candidate.id });
                  }
                  toast.success(`Imported ${candidates.length} ROMs from ${source.name}`);
                }}
              >
                📦 Import All ({zipPicker.candidates.length} ROMs)
              </button>
            )}
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

      <div className="flex flex-col md:flex-row justify-between items-start md:items-center w-full mb-6 gap-3 p-4 rounded-xl" style={{background: 'var(--surface-1)', border: '1px solid var(--border-soft)'}}>
        <div className="flex flex-col gap-2 w-full md:w-auto">
          {hasGames && (
            <div className="relative w-full max-w-md">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2" size={16} style={{color: 'var(--text-muted)'}} />
                <input
                  type="text"
                  placeholder="Search library..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full rounded-xl text-sm focus:outline-none focus:ring-2 transition-colors placeholder:opacity-50"
                  style={{ background: 'var(--surface-2)', border: '1px solid var(--border-soft)', color: 'var(--text-primary)', padding: '10px 12px 10px 40px' }}
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

        <div className="flex flex-col sm:flex-row items-center gap-3 w-full md:w-auto">
          <div className="rw-upload-div" style={{ width: 50, height: 50 }}>
            <UploadCloud className="rw-upload-icon" size={22} strokeWidth={1.5} />
            <input
              className="rw-upload-input"
              type="file"
              multiple
              onChange={handleFileInput}
              accept=".nes,.zip,.smc,.sfc,.gb,.gbc,.gba,.md,.smd,.gen,.bin,.chd,.pbp,.n64,.z64,.v64"
            />
          </div>

          <div className="flex items-center gap-2 px-3 py-2 rounded-xl text-sm" style={{background: 'var(--surface-2)', border: '1px solid var(--border-soft)', color: 'var(--text-primary)'}}>
            <ArrowUpDown size={15} style={{color: 'var(--text-muted)'}} />
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as SortKey)}
              className="bg-transparent focus:outline-none cursor-pointer"
              style={{color: 'var(--text-primary)'}}
            >
              <option value="dateAdded">Sort: Date Added</option>
              <option value="name">Sort: Name</option>
              <option value="system">Sort: System</option>
              <option value="lastPlayed">Sort: Last Played</option>
              <option value="playtime">Sort: Playtime</option>
              <option value="rating">Sort: Rating</option>
            </select>
          </div>

          <button
            onClick={() => void handleScrapeAllArt()}
            disabled={scrapingArt || games.filter(g => !g.coverUrl).length === 0}
            className="flex items-center gap-2 px-3 py-2 rounded-xl text-sm font-medium transition-colors disabled:opacity-40"
            style={{background: 'var(--surface-2)', border: '1px solid var(--border-soft)', color: 'var(--text-primary)'}}
            title="Auto-fetch cover art from LibRetro"
          >
            <ImageDown size={15} style={{color: 'var(--text-muted)'}} />
            {scrapingArt ? "Fetching..." : "Fetch Art"}
          </button>

          <div className="flex items-center gap-3 p-1 rounded-xl w-full sm:w-auto" style={{background: 'var(--surface-2)', border: '1px solid var(--border-soft)'}}>
            <button
              onClick={() => setPersistGame(true)}
              className={`flex flex-1 justify-center items-center gap-2 px-3 py-1.5 text-sm font-sans transition-colors rounded-lg ${persistGame ? "font-medium" : ""}`}
              style={persistGame ? {background: 'var(--accent-primary)', color: '#fff'} : {color: 'var(--text-muted)'}}
            >
              <HardDrive size={16} />
              Add to Library
            </button>
            <button
              onClick={() => setPersistGame(false)}
              className={`flex flex-1 justify-center items-center gap-2 px-3 py-1.5 text-sm font-sans transition-colors rounded-lg ${!persistGame ? "font-medium" : ""}`}
              style={!persistGame ? {background: 'var(--accent-primary)', color: '#fff'} : {color: 'var(--text-muted)'}}
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
            <div className="grid grid-cols-3 gap-4 mb-6">
              {[
                { label: 'Total Games', value: games.length, color: 'var(--text-primary)' },
                { label: 'Favorites', value: favoriteGames.length, color: 'var(--accent-primary)' },
                { label: 'Played', value: recentGames.length, color: 'var(--success)' },
              ].map(stat => (
                <div key={stat.label} className="p-4 rounded-xl" style={{background: 'var(--surface-1)', border: '1px solid var(--border-soft)'}}>
                  <p className="text-2xl font-bold" style={{color: stat.color}}>{stat.value}</p>
                  <p className="text-xs mt-0.5" style={{color: 'var(--text-muted)'}}>{stat.label}</p>
                </div>
              ))}
            </div>
          )}

          {/* Collections filter bar */}
          {!searchQuery.trim() && (
            <div className="flex items-center gap-2 flex-wrap mb-2">
              <button
                onClick={() => setActiveCollectionId(null)}
                className="px-3 py-1.5 text-xs rounded-lg font-medium transition-colors"
                style={!activeCollectionId ? {background: 'var(--accent-primary)', color: '#fff'} : {background: 'var(--surface-2)', color: 'var(--text-muted)', border: '1px solid var(--border-soft)'}}
              >
                All Games
              </button>
              {/* Smart playlists */}
              {[
                { id: "__unplayed", label: "Unplayed" },
                { id: "__most_played", label: "Most Played" },
                { id: "__stale", label: "Forgotten (30d+)" },
                { id: "__top_rated", label: "Top Rated ★" },
                { id: "__duplicates", label: "Duplicates" },
              ].map(sp => (
                <button
                  key={sp.id}
                  onClick={() => setActiveCollectionId(activeCollectionId === sp.id ? null : sp.id)}
                  className="px-3 py-1.5 text-xs rounded-lg font-medium transition-colors italic"
                  style={activeCollectionId === sp.id ? {background: 'var(--accent-primary)', color: '#fff'} : {background: 'var(--surface-2)', color: 'var(--text-muted)', border: '1px solid var(--border-soft)'}}
                >
                  {sp.label}
                </button>
              ))}
              {collections.map(col => (
                <div key={col.id} className="flex items-center gap-0.5">
                  <button
                    onClick={() => setActiveCollectionId(activeCollectionId === col.id ? null : col.id)}
                    className="px-3 py-1.5 text-xs rounded-l-lg font-medium transition-colors flex items-center gap-1"
                    style={activeCollectionId === col.id ? {background: 'var(--accent-primary)', color: '#fff'} : {background: 'var(--surface-2)', color: 'var(--text-muted)', border: '1px solid var(--border-soft)'}}
                  >
                    <Folder size={12} /> {col.name}
                  </button>
                  <button
                    onClick={() => handleDeleteCollection(col.id)}
                    className="px-1.5 py-1.5 text-xs rounded-r-lg transition-colors"
                    style={{background: 'var(--surface-2)', color: 'var(--text-muted)', border: '1px solid var(--border-soft)', borderLeft: 'none'}}
                    title="Delete collection"
                  >
                    <X size={10} />
                  </button>
                </div>
              ))}
              {showNewCollection ? (
                <div className="flex items-center gap-1">
                  <input
                    autoFocus
                    value={newCollectionName}
                    onChange={(e) => setNewCollectionName(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && handleCreateCollection()}
                    placeholder="Name..."
                    className="px-2 py-1 text-xs rounded-lg w-32"
                    style={{background: 'var(--surface-2)', color: 'var(--text-primary)', border: '1px solid var(--border-soft)'}}
                  />
                  <button onClick={handleCreateCollection} className="px-2 py-1 text-xs rounded-lg" style={{background: 'var(--accent-primary)', color: '#fff'}}>Add</button>
                  <button onClick={() => setShowNewCollection(false)} className="px-1 py-1 text-xs" style={{color: 'var(--text-muted)'}}>
                    <X size={12} />
                  </button>
                </div>
              ) : (
                <button
                  onClick={() => setShowNewCollection(true)}
                  className="px-2 py-1.5 text-xs rounded-lg transition-colors flex items-center gap-1"
                  style={{background: 'var(--surface-2)', color: 'var(--text-muted)', border: '1px dashed var(--border-soft)'}}
                >
                  <FolderPlus size={12} /> New Collection
                </button>
              )}
            </div>
          )}

          {!searchQuery.trim() && recentGames.length > 0 && (
            <div className="mb-6">
              <h3 className="text-sm font-bold uppercase tracking-wider mb-3" style={{color: 'var(--text-muted)'}}>Recently Played</h3>
              <div className="flex gap-3 overflow-x-auto pb-2">
                {recentGames.map(game => (
                  <div
                    key={game.id}
                    className="shrink-0 cursor-pointer rounded-lg overflow-hidden"
                    style={{width: 80, border: '1px solid var(--border-soft)'}}
                    onClick={() => setSelectedGame(game)}
                  >
                    {game.coverUrl ? (
                      <img src={game.coverUrl} alt={game.title} className="w-full aspect-[3/4] object-cover" />
                    ) : (
                      <div className="w-full aspect-[3/4] flex items-center justify-center" style={{background: 'var(--surface-2)'}}>
                        <Gamepad2 size={20} style={{color: 'var(--text-muted)'}} />
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="w-full flex-1">
            <div className="flex items-end gap-3 mb-4">
              <h2 className="text-xl font-bold text-neutral-300">{searchQuery.trim() ? "Search Results" : "All Games"}</h2>
            </div>
            {sortedGames.length > 0 ? (
              <LibraryGrid
                games={sortedGames}
                viewMode={viewMode}
                onViewModeChange={setViewMode}
                onLaunch={handleLaunchGame}
                onToggleFavorite={handleToggleFavorite}
                onRemove={handleRemoveGame}
                onSetCover={handleSetCover}
                onSelectGame={setSelectedGame}
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
          <div className="rw-upload-div mb-8">
            <UploadCloud className="rw-upload-icon" size={40} strokeWidth={1.5} />
            <input
              className="rw-upload-input"
              type="file"
              multiple
              onChange={handleFileInput}
              accept=".nes,.zip,.smc,.sfc,.gb,.gbc,.gba,.md,.smd,.gen,.bin,.chd,.pbp,.n64,.z64,.v64"
            />
          </div>
          <h2 className="text-3xl font-bold mb-3" style={{color: 'var(--text-primary)'}}>Your library is empty</h2>
          <p className="text-center max-w-sm mb-8" style={{color: 'var(--text-secondary)'}}>
            Drag and drop ROM files anywhere, or click the circle above to browse files.
          </p>
        </div>
      )}

      <input
        ref={coverInputRef}
        type="file"
        accept="image/png,image/jpeg,image/webp"
        className="hidden"
        onChange={handleCoverInput}
      />

      <GameDetailsDrawer
        game={selectedGame}
        onClose={() => setSelectedGame(null)}
        onLaunch={(game) => { setSelectedGame(null); handleLaunchGame(game); }}
        onToggleFavorite={handleToggleFavorite}
        onRemove={handleRemoveGame}
        onSetCover={handleSetCover}
        collections={collections}
        onAddToCollection={handleAddToCollection}
        onRemoveFromCollection={handleRemoveFromCollection}
        onRate={async (gameId, rating) => { await updateGameMetadata(gameId, { rating: rating || undefined }); await fetchGames(); }}
        onUpdateSettings={async (gameId, settings) => { await updateGameMetadata(gameId, { perGameSettings: settings }); await fetchGames(); }}
        onUpdateCheats={async (gameId, cheats) => { await updateGameMetadata(gameId, { cheats }); await fetchGames(); }}
      />
    </div>
  );
}
