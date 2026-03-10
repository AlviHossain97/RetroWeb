import Dexie, { type EntityTable } from "dexie";
import { SYSTEMS } from "../../data/systemBrowserData";
import { md5FromUint8Array } from "../hash/md5";

export interface SaveData {
  id?: number;
  filename: string;
  system: string;
  type: "sram" | "state";
  data: Uint8Array;
  timestamp: Date;
  image?: string;
  slot?: number;
  coreId?: string;
  coreVersion?: string;
}

export interface BIOSFile {
  filename: string;
  system: string;
  data: Uint8Array;
  sourceFilename?: string;
  hashMd5?: string;
  verifiedHash?: boolean;
  expectedSize?: number;
  size: number;
  installedAt: number;
}

export interface SaveBIOSOptions {
  sourceFilename?: string;
}

export interface SaveBIOSResult {
  filename: string;
  system: string;
  size: number;
  expectedSize?: number;
  hashMd5: string;
  verifiedHash: boolean;
  sizeWarning?: string;
}

export interface BIOSStatusEntry {
  filename: string;
  system: string;
  sourceFilename?: string;
  hashMd5?: string;
  verifiedHash?: boolean;
  expectedSize?: number;
  size: number;
  installedAt: number;
}

export interface Game {
  id: string;
  title: string;
  displayTitle?: string;
  system: string;
  core: string;
  filename: string;
  size: number;
  addedAt: number;
  lastPlayed?: number;
  playtime?: number;
  isFavorite: boolean;
  coverUrl?: string;
  hasLocalRom: boolean;
  romHash?: string;
  lastAutoSaveAt?: number;
  lastSessionStartedAt?: number;
  collectionIds?: string[];
  rating?: number; // 1-5 stars, undefined = unrated
  perGameSettings?: Record<string, string>;
  cheats?: string[];
}

export interface ChatMessage {
  id?: number;
  role: "user" | "assistant";
  content: string;
  images?: string[];
  timestamp: number;
}

export interface Collection {
  id: string;
  name: string;
  description?: string;
  coverUrl?: string;
  createdAt: number;
}

export interface Achievement {
  id: string;
  title: string;
  description: string;
  icon: string;
  unlockedAt?: number;
}

class RetroWebDatabase extends Dexie {
  saves!: EntityTable<SaveData, "id">;
  bios!: EntityTable<BIOSFile, "filename">;
  games!: EntityTable<Game, "id">;
  chatMessages!: EntityTable<ChatMessage, "id">;
  collections!: EntityTable<Collection, "id">;
  achievements!: EntityTable<Achievement, "id">;

  constructor() {
    super("RetroWebDB");
    this.version(1).stores({
      saves: "++id, [filename+type], filename, system, type, slot, timestamp",
      bios: "filename, system",
    });
    this.version(2).stores({
      saves: "++id, [filename+type], filename, system, type, slot, timestamp",
      bios: "filename, system, hashMd5, verifiedHash",
      games: "id, title, system, addedAt, lastPlayed, isFavorite",
    });
    this.version(3)
      .stores({
        saves: "++id, [filename+type], filename, system, type, slot, timestamp",
        bios: "filename, system, hashMd5, verifiedHash, installedAt",
        games: "id, title, system, addedAt, lastPlayed, isFavorite, romHash, lastAutoSaveAt",
      })
      .upgrade(async (tx) => {
        const biosTable = tx.table("bios");
        const items = await biosTable.toArray();
        for (const bios of items as BIOSFile[]) {
          const filename = bios.filename.toLowerCase();
          await biosTable.put({
            ...bios,
            filename,
            size: bios.size ?? bios.data?.byteLength ?? 0,
            installedAt: bios.installedAt ?? Date.now(),
          });
        }
      });
    this.version(4).stores({
      saves: "++id, [filename+type], filename, system, type, slot, timestamp",
      bios: "filename, system, hashMd5, verifiedHash, installedAt",
      games: "id, title, system, addedAt, lastPlayed, isFavorite, romHash, lastAutoSaveAt",
      chatMessages: "++id, timestamp",
      collections: "id, name, createdAt",
      achievements: "id, unlockedAt",
    });
  }
}

export const db = new RetroWebDatabase();

const PS1_BIOS_VARIANTS = ["scph5501.bin", "scph5500.bin", "scph5502.bin", "scph1001.bin"];

const BIOS_VARIANT_BY_SYSTEM: Record<string, string[]> = {
  ps1: PS1_BIOS_VARIANTS,
};

const BIOS_FAMILY: Record<string, string[]> = Object.fromEntries(
  PS1_BIOS_VARIANTS.map((name) => [name, PS1_BIOS_VARIANTS])
);

const BIOS_EXPECTED_SIZE: Record<string, number> = {
  "scph5501.bin": 512 * 1024,
  "scph5500.bin": 512 * 1024,
  "scph5502.bin": 512 * 1024,
  "scph1001.bin": 512 * 1024,
};

const BIOS_HASHES: Record<string, Set<string>> = {
  "scph5501.bin": new Set(["490f666e1afb15b7362b406ed1cea246"]),
  "scph5500.bin": new Set(["8dd7d5296a650fac7319bce665a6a53c"]),
  "scph5502.bin": new Set(["32736f17079d0b2b7024407c39bd3050"]),
  "scph1001.bin": new Set(["924e392ed05558ffdb115408c263dccf"]),
};

function normalizeBiosName(filename: string) {
  return filename.trim().split("/").pop()?.toLowerCase() ?? filename.toLowerCase();
}

function getSystemBiosCandidates(systemId: string) {
  const system = SYSTEMS.find((entry) => entry.id === systemId);
  const required = (system?.bios ?? []).map((name) => name.toLowerCase());
  const variants = BIOS_VARIANT_BY_SYSTEM[systemId] ?? [];
  return Array.from(new Set([...required, ...variants]));
}

function resolveCanonicalBiosName(filename: string, systemId?: string) {
  const normalized = normalizeBiosName(filename);

  if (systemId) {
    const candidates = getSystemBiosCandidates(systemId);
    const matched = candidates.find((candidate) => candidate === normalized);
    if (matched) return { canonicalName: matched, systemId };
  }

  for (const system of SYSTEMS) {
    const candidates = getSystemBiosCandidates(system.id);
    const matched = candidates.find((candidate) => candidate === normalized);
    if (matched) {
      return { canonicalName: matched, systemId: system.id };
    }
  }

  return null;
}

export async function saveSRAM(filename: string, system: string, data: Uint8Array) {
  const existing = await db.saves.where({ filename, type: "sram" }).first();
  if (existing?.id) {
    await db.saves.update(existing.id, {
      data,
      timestamp: new Date(),
      system,
    });
    return;
  }

  await db.saves.add({
    filename,
    system,
    type: "sram",
    data,
    timestamp: new Date(),
  });
}

export async function loadSRAM(filename: string): Promise<Uint8Array | null> {
  const save = await db.saves.where({ filename, type: "sram" }).first();
  return save?.data ?? null;
}

export async function saveState(
  filename: string,
  system: string,
  data: Uint8Array,
  image?: string,
  slot = 0,
  coreVersion?: string
) {
  const existing = await db.saves
    .where({ filename, type: "state" })
    .filter((entry) => (entry.slot ?? 0) === slot)
    .first();

  if (existing?.id) {
    await db.saves.update(existing.id, {
      data,
      timestamp: new Date(),
      image,
      slot,
      system,
      coreVersion,
    });
    return;
  }

  await db.saves.add({
    filename,
    system,
    type: "state",
    data,
    timestamp: new Date(),
    image,
    slot,
    coreVersion,
  });
}

export async function loadState(filename: string, slot = 0): Promise<SaveData | null> {
  const state = await db.saves
    .where({ filename, type: "state" })
    .filter((entry) => (entry.slot ?? 0) === slot)
    .first();
  return state ?? null;
}

export async function getAllStates(filename: string): Promise<SaveData[]> {
  return db.saves.where({ filename, type: "state" }).toArray();
}

export async function getAllSaves(): Promise<SaveData[]> {
  return db.saves.toArray();
}

export async function getSavesForGame(filename: string): Promise<SaveData[]> {
  return db.saves.where("filename").equals(filename).toArray();
}

export async function deleteSave(id: number): Promise<void> {
  await db.saves.delete(id);
}

export function validateBiosFilename(filename: string): {
  isValid: boolean;
  systemId?: string;
  expectedName?: string;
  acceptedVariants?: string[];
} {
  const resolved = resolveCanonicalBiosName(filename);
  if (!resolved) return { isValid: false };

  return {
    isValid: true,
    systemId: resolved.systemId,
    expectedName: resolved.canonicalName,
    acceptedVariants: getSystemBiosCandidates(resolved.systemId),
  };
}

export function getExpectedBiosSize(filename: string): number | undefined {
  return BIOS_EXPECTED_SIZE[normalizeBiosName(filename)];
}

export function getKnownBiosHashes(filename: string): string[] {
  return Array.from(BIOS_HASHES[normalizeBiosName(filename)] ?? []);
}

export async function saveBIOS(
  filename: string,
  system: string,
  data: Uint8Array,
  options: SaveBIOSOptions = {}
): Promise<SaveBIOSResult> {
  const resolved = resolveCanonicalBiosName(filename, system);
  const canonicalName = resolved?.canonicalName ?? normalizeBiosName(filename);
  const canonicalSystem = resolved?.systemId ?? system;

  const hashMd5 = md5FromUint8Array(data).toLowerCase();
  const knownHashes = BIOS_HASHES[canonicalName] ?? new Set<string>();
  const verifiedHash = knownHashes.size > 0 ? knownHashes.has(hashMd5) : false;
  const expectedSize = BIOS_EXPECTED_SIZE[canonicalName];

  let sizeWarning: string | undefined;
  if (expectedSize) {
    const delta = Math.abs(data.byteLength - expectedSize);
    if (delta > expectedSize * 0.15) {
      sizeWarning = `Expected ~${Math.round(expectedSize / 1024)}KB, got ${Math.round(data.byteLength / 1024)}KB.`;
    }
  }

  await db.bios.put({
    filename: canonicalName,
    system: canonicalSystem,
    data,
    sourceFilename: options.sourceFilename ?? filename,
    hashMd5,
    verifiedHash,
    expectedSize,
    size: data.byteLength,
    installedAt: Date.now(),
  });

  return {
    filename: canonicalName,
    system: canonicalSystem,
    size: data.byteLength,
    expectedSize,
    hashMd5,
    verifiedHash,
    sizeWarning,
  };
}

export async function hasBIOS(filename: string): Promise<boolean> {
  const canonical = normalizeBiosName(filename);
  const direct = await db.bios.get(canonical);
  if (direct) return true;

  const family = BIOS_FAMILY[canonical];
  if (!family) return false;

  for (const candidate of family) {
    if (await db.bios.get(candidate)) return true;
  }
  return false;
}

export async function loadBIOS(filename: string): Promise<Uint8Array | null> {
  const canonical = normalizeBiosName(filename);
  const direct = await db.bios.get(canonical);
  if (direct) return direct.data;

  const family = BIOS_FAMILY[canonical];
  if (!family) return null;

  for (const candidate of family) {
    const found = await db.bios.get(candidate);
    if (found) return found.data;
  }

  return null;
}

export async function getAllBIOSFiles(): Promise<BIOSStatusEntry[]> {
  const entries = await db.bios.toArray();
  return entries.map((entry) => ({
    filename: entry.filename,
    system: entry.system,
    sourceFilename: entry.sourceFilename,
    hashMd5: entry.hashMd5,
    verifiedHash: entry.verifiedHash,
    expectedSize: entry.expectedSize,
    size: entry.size,
    installedAt: entry.installedAt,
  }));
}

export async function removeBIOS(filename: string): Promise<void> {
  await db.bios.delete(normalizeBiosName(filename));
}

export async function saveGameMetadata(game: Game) {
  await db.games.put(game);
}

export async function loadGameMetadata(id: string): Promise<Game | undefined> {
  return db.games.get(id);
}

export async function getAllGames(): Promise<Game[]> {
  return db.games.orderBy("addedAt").reverse().toArray();
}

export async function removeGameMetadata(id: string) {
  await db.games.delete(id);
}

export async function updateGameMetadata(id: string, updates: Partial<Game>) {
  await db.games.update(id, updates);
}

export async function recordGameplaySession(gameId: string, startedAt: number, endedAt = Date.now()) {
  const game = await db.games.get(gameId);
  if (!game) return;

  const elapsedSeconds = Math.max(0, Math.floor((endedAt - startedAt) / 1000));
  await db.games.update(gameId, {
    lastPlayed: endedAt,
    playtime: (game.playtime ?? 0) + elapsedSeconds,
    lastSessionStartedAt: undefined,
  });
}

export async function markGameAutoSaved(gameId: string) {
  await db.games.update(gameId, { lastAutoSaveAt: Date.now() });
}

export async function saveRomToOPFS(id: string, file: File) {
  const root = await navigator.storage.getDirectory();
  const romsDir = await root.getDirectoryHandle("roms", { create: true });
  const fileHandle = await romsDir.getFileHandle(id, { create: true });

  if (!("createWritable" in fileHandle)) {
    throw new Error("createWritable is not supported in this browser.");
  }

  const writable = await (fileHandle as FileSystemFileHandle).createWritable();
  await writable.write(file);
  await writable.close();
}

export async function loadRomFromOPFS(id: string, originalFilename: string): Promise<File | null> {
  try {
    const root = await navigator.storage.getDirectory();
    const romsDir = await root.getDirectoryHandle("roms");
    const fileHandle = await romsDir.getFileHandle(id);
    const file = await fileHandle.getFile();
    return new File([file], originalFilename, { type: file.type || "application/octet-stream" });
  } catch {
    return null;
  }
}

export async function removeRomFromOPFS(id: string) {
  try {
    const root = await navigator.storage.getDirectory();
    const romsDir = await root.getDirectoryHandle("roms");
    await romsDir.removeEntry(id);
  } catch {
    // noop
  }
}

// ── Recently Played ──
export async function getRecentGames(limit = 8): Promise<Game[]> {
  return db.games
    .where("lastPlayed")
    .above(0)
    .reverse()
    .sortBy("lastPlayed")
    .then((games) => games.slice(0, limit));
}

// ── Chat Messages ──
export async function saveChatMessages(messages: ChatMessage[]) {
  await db.chatMessages.clear();
  await db.chatMessages.bulkAdd(messages);
}

export async function loadChatMessages(): Promise<ChatMessage[]> {
  return db.chatMessages.orderBy("timestamp").toArray();
}

export async function clearChatMessages() {
  await db.chatMessages.clear();
}

// ── Collections ──
export async function getAllCollections(): Promise<Collection[]> {
  return db.collections.orderBy("createdAt").reverse().toArray();
}

export async function saveCollection(collection: Collection) {
  await db.collections.put(collection);
}

export async function removeCollection(id: string) {
  await db.collections.delete(id);
  // Remove collection reference from games
  const games = await db.games.toArray();
  for (const game of games) {
    if (game.collectionIds?.includes(id)) {
      await db.games.update(game.id, {
        collectionIds: game.collectionIds.filter((cid) => cid !== id),
      });
    }
  }
}

export async function addGameToCollection(gameId: string, collectionId: string) {
  const game = await db.games.get(gameId);
  if (!game) return;
  const ids = new Set(game.collectionIds ?? []);
  ids.add(collectionId);
  await db.games.update(gameId, { collectionIds: [...ids] });
}

export async function removeGameFromCollection(gameId: string, collectionId: string) {
  const game = await db.games.get(gameId);
  if (!game) return;
  await db.games.update(gameId, {
    collectionIds: (game.collectionIds ?? []).filter((id) => id !== collectionId),
  });
}

// ── Achievements ──
export async function getAllAchievements(): Promise<Achievement[]> {
  return db.achievements.toArray();
}

export async function unlockAchievement(achievement: Achievement) {
  const existing = await db.achievements.get(achievement.id);
  if (existing?.unlockedAt) return false; // already unlocked
  await db.achievements.put({ ...achievement, unlockedAt: Date.now() });
  return true;
}

export async function getUnlockedAchievements(): Promise<Achievement[]> {
  return db.achievements.where("unlockedAt").above(0).toArray();
}
