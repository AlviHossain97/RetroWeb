import { BlobReader, BlobWriter, ZipReader } from "@zip.js/zip.js";

export type DetectedSystemKind =
  | "nes"
  | "snes"
  | "gb"
  | "gbc"
  | "gba"
  | "genesis"
  | "ps1"
  | "n64"
  | "unknown";

export interface ZipRomCandidate {
  id: string;
  filename: string;
  displayName: string;
  size: number;
  extension: string;
  detectedSystem: DetectedSystemKind;
}

interface ZipFileEntry {
  directory: false;
  filename: string;
  uncompressedSize?: number;
  getData: (
    writer: BlobWriter,
    options?: {
      onprogress?: (loaded: number, total: number) => void;
    }
  ) => Promise<Blob>;
}

export interface NormalizeOptions {
  selectedZipEntry?: string;
  onProgress?: (percent: number, message: string) => void;
}

export interface NormalizedROM {
  blob: Blob;
  filename: string;
  originalFilename: string;
  extension: string;
  detectedSystem: DetectedSystemKind;
  systemId: string;
  systemLabel: string;
  detectionSource: "header" | "extension" | "fallback";
  warning?: string;
}

export type NormalizeErrorCode =
  | "unsupported_format"
  | "disc_format_requires_chd"
  | "zip_no_rom"
  | "zip_multiple_roms"
  | "zip_entry_not_found"
  | "zip_extract_failed";

export class NormalizeError extends Error {
  code: NormalizeErrorCode;
  userMessage: string;
  candidates?: ZipRomCandidate[];

  constructor(code: NormalizeErrorCode, userMessage: string, candidates?: ZipRomCandidate[]) {
    super(userMessage);
    this.name = "NormalizeError";
    this.code = code;
    this.userMessage = userMessage;
    this.candidates = candidates;
  }
}

const CARTRIDGE_EXTENSIONS = new Set([
  ".nes",
  ".smc",
  ".sfc",
  ".gb",
  ".gbc",
  ".gba",
  ".md",
  ".smd",
  ".gen",
  ".bin",
  ".n64",
  ".z64",
  ".v64",
  ".nds",
  ".pce",
  ".ngp",
  ".ngc",
  ".ws",
  ".wsc",
  ".a26",
  ".a78",
  ".lnx",
  ".jag",
  ".col",
  ".sg",
  ".sms",
  ".gg",
]);

const DISC_EXTENSIONS = new Set([".chd", ".pbp"]);
const DISCOURAGED_DISC_EXTENSIONS = new Set([".cue", ".iso"]);
const MAX_BIN_AS_CARTRIDGE_SIZE = 16 * 1024 * 1024;

const IGNORE_EXTENSIONS = new Set([
  ".txt",
  ".nfo",
  ".jpg",
  ".jpeg",
  ".png",
  ".gif",
  ".bmp",
  ".pdf",
  ".url",
  ".htm",
  ".html",
  ".xml",
  ".srm",
  ".sav",
  ".db",
  ".m3u",
]);

function basename(pathname: string) {
  const parts = pathname.split("/");
  return parts[parts.length - 1] || pathname;
}

function getExtension(filename: string): string {
  const clean = basename(filename).toLowerCase();
  const index = clean.lastIndexOf(".");
  if (index < 0) return "";
  return clean.slice(index);
}

function getDetectedSystemFromExtension(ext: string): DetectedSystemKind {
  const map: Record<string, DetectedSystemKind> = {
    ".nes": "nes",
    ".smc": "snes",
    ".sfc": "snes",
    ".gb": "gb",
    ".gbc": "gbc",
    ".gba": "gba",
    ".md": "genesis",
    ".smd": "genesis",
    ".gen": "genesis",
    ".chd": "ps1",
    ".pbp": "ps1",
    ".n64": "n64",
    ".z64": "n64",
    ".v64": "n64",
  };

  return map[ext] ?? "unknown";
}

function mapDetectedSystemToRuntimeSystem(system: DetectedSystemKind): string {
  switch (system) {
    case "gb":
    case "gbc":
    case "gba":
      return "gb";
    default:
      return system;
  }
}

function getSystemLabel(system: DetectedSystemKind): string {
  const labels: Record<DetectedSystemKind, string> = {
    nes: "NES",
    snes: "SNES",
    gb: "GB",
    gbc: "GBC",
    gba: "GBA",
    genesis: "Genesis",
    ps1: "PS1",
    n64: "N64",
    unknown: "Unknown",
  };

  return labels[system] ?? "Unknown";
}

function looksLikeSnesHeader(view: Uint8Array, offset: number) {
  if (view.length < offset + 0x20) return false;
  const mapMode = view[offset + 0x15];
  return [0x20, 0x21, 0x23, 0x30, 0x31, 0x35].includes(mapMode);
}

export async function detectSystemFromHeader(blob: Blob): Promise<DetectedSystemKind | null> {
  const buffer = await blob.slice(0, 0x11000).arrayBuffer();
  const view = new Uint8Array(buffer);

  if (view.length >= 4 && view[0] === 0x4e && view[1] === 0x45 && view[2] === 0x53 && view[3] === 0x1a) {
    return "nes";
  }

  if (view.length >= 4 && view[0] === 0x2e && view[1] === 0x00 && view[2] === 0x00 && view[3] === 0xea) {
    return "gba";
  }

  if (view.length >= 0x104) {
    const sega = String.fromCharCode(view[0x100], view[0x101], view[0x102], view[0x103]);
    if (sega === "SEGA") {
      return "genesis";
    }
  }

  if (view.length >= 0x0144 && view[0x0104] === 0xce && view[0x0105] === 0xed) {
    return view[0x0143] === 0x80 || view[0x0143] === 0xc0 ? "gbc" : "gb";
  }

  if (looksLikeSnesHeader(view, 0x7fc0) || looksLikeSnesHeader(view, 0xffc0)) {
    return "snes";
  }

  if (view.length >= 4) {
    const b0 = view[0];
    const b1 = view[1];
    const b2 = view[2];
    const b3 = view[3];
    const isN64 =
      (b0 === 0x80 && b1 === 0x37 && b2 === 0x12 && b3 === 0x40) ||
      (b0 === 0x37 && b1 === 0x80 && b2 === 0x40 && b3 === 0x12) ||
      (b0 === 0x40 && b1 === 0x12 && b2 === 0x37 && b3 === 0x80);
    if (isN64) return "n64";
  }

  return null;
}

function buildNormalizedROM(params: {
  blob: Blob;
  filename: string;
  originalFilename: string;
  extension: string;
  extensionSystem: DetectedSystemKind;
  headerSystem: DetectedSystemKind | null;
}): NormalizedROM {
  const { blob, filename, originalFilename, extension, extensionSystem, headerSystem } = params;

  let detectedSystem = extensionSystem;
  let detectionSource: NormalizedROM["detectionSource"] = "extension";
  let warning: string | undefined;

  if (headerSystem && headerSystem !== "unknown") {
    detectedSystem = headerSystem;
    detectionSource = "header";
    if (extensionSystem !== "unknown" && extensionSystem !== headerSystem) {
      warning = `Detected as ${getSystemLabel(headerSystem)} from ROM header (extension suggested ${getSystemLabel(
        extensionSystem
      )}).`;
    }
  }

  if (!detectedSystem || detectedSystem === "unknown") {
    detectionSource = "fallback";
  }

  const systemId = mapDetectedSystemToRuntimeSystem(detectedSystem);

  return {
    blob,
    filename,
    originalFilename,
    extension,
    detectedSystem,
    systemId,
    systemLabel: getSystemLabel(detectedSystem),
    detectionSource,
    warning,
  };
}

function assertDiscCompatible(ext: string, size: number) {
  if (DISCOURAGED_DISC_EXTENSIONS.has(ext)) {
    throw new NormalizeError(
      "disc_format_requires_chd",
      "Disc images in .cue/.iso format are not supported in browser runtime. Please convert to .chd and try again."
    );
  }

  if (ext === ".bin" && size > MAX_BIN_AS_CARTRIDGE_SIZE) {
    throw new NormalizeError(
      "disc_format_requires_chd",
      "Large .bin disc images are not supported directly. Please convert your game to .chd first."
    );
  }
}

function isROMCandidate(entryName: string, size: number) {
  const ext = getExtension(entryName);
  if (!ext || IGNORE_EXTENSIONS.has(ext)) return false;
  if (DISCOURAGED_DISC_EXTENSIONS.has(ext)) return false;
  if (!CARTRIDGE_EXTENSIONS.has(ext) && !DISC_EXTENSIONS.has(ext)) return false;
  if (ext === ".bin" && size > MAX_BIN_AS_CARTRIDGE_SIZE) return false;
  return true;
}

function isZipFileEntry(entry: unknown): entry is ZipFileEntry {
  if (!entry || typeof entry !== "object") return false;
  const candidate = entry as Record<string, unknown>;
  return candidate.directory === false && typeof candidate.filename === "string" && typeof candidate.getData === "function";
}

export async function normalizeROM(file: File | Blob, options: NormalizeOptions = {}): Promise<NormalizedROM> {
  const originalFilename = file instanceof File ? file.name : "game.rom";
  const ext = getExtension(originalFilename);

  if (ext === ".zip") {
    return extractROMFromZip(file, originalFilename, options);
  }

  assertDiscCompatible(ext, file.size);

  if (!CARTRIDGE_EXTENSIONS.has(ext) && !DISC_EXTENSIONS.has(ext)) {
    throw new NormalizeError(
      "unsupported_format",
      `"${ext || "(no extension)"}" is not a supported ROM format. Try .nes, .gba, .sfc, .chd or .zip.`
    );
  }

  options.onProgress?.(15, "Inspecting ROM...");
  const extensionSystem = getDetectedSystemFromExtension(ext);
  const headerSystem = await detectSystemFromHeader(file);
  options.onProgress?.(100, "ROM ready");

  return buildNormalizedROM({
    blob: file,
    filename: originalFilename,
    originalFilename,
    extension: ext,
    extensionSystem,
    headerSystem,
  });
}

async function extractROMFromZip(file: File | Blob, originalFilename: string, options: NormalizeOptions): Promise<NormalizedROM> {
  const reader = new ZipReader(new BlobReader(file));

  try {
    options.onProgress?.(5, "Reading ZIP archive...");
    const entries = await reader.getEntries();

    const fileEntries = entries.filter(isZipFileEntry);

    const candidates = fileEntries
      .filter((entry) => isROMCandidate(entry.filename, entry.uncompressedSize ?? 0))
      .map<ZipRomCandidate>((entry) => {
        const extension = getExtension(entry.filename);
        return {
          id: entry.filename,
          filename: entry.filename,
          displayName: basename(entry.filename),
          size: entry.uncompressedSize ?? 0,
          extension,
          detectedSystem: getDetectedSystemFromExtension(extension),
        };
      });

    if (candidates.length === 0) {
      throw new NormalizeError("zip_no_rom", "This ZIP file does not contain any recognized ROM files.");
    }

    let selected = candidates[0];
    if (options.selectedZipEntry) {
      const byId = candidates.find((candidate) => candidate.id === options.selectedZipEntry);
      if (!byId) {
        throw new NormalizeError("zip_entry_not_found", "Selected ROM entry was not found in this ZIP archive.");
      }
      selected = byId;
    } else if (candidates.length > 1) {
      throw new NormalizeError("zip_multiple_roms", "Multiple ROM files found in ZIP. Please choose one.", candidates);
    }

    const selectedEntry = fileEntries.find((entry) => entry.filename === selected.id) as ZipFileEntry | undefined;
    if (!selectedEntry) {
      throw new NormalizeError("zip_extract_failed", "Failed to read ROM entry from ZIP archive.");
    }

    options.onProgress?.(20, "Extracting ROM from ZIP...");

    const blob = await selectedEntry.getData(
      new BlobWriter(),
      {
        onprogress: (current: number, total: number) => {
          if (!total) return;
          const extraction = Math.round((current / total) * 75);
          options.onProgress?.(20 + extraction, `Extracting ${selected.displayName}...`);
        },
      } as never
    );

    const extensionSystem = getDetectedSystemFromExtension(selected.extension);
    const headerSystem = await detectSystemFromHeader(blob);
    options.onProgress?.(100, "ROM extracted");

    return buildNormalizedROM({
      blob,
      filename: selected.displayName,
      originalFilename,
      extension: selected.extension,
      extensionSystem,
      headerSystem,
    });
  } finally {
    await reader.close();
  }
}
