import { updateGameMetadata, type Game } from "../storage/db";

// Map internal system IDs to LibRetro thumbnail repo names
const SYSTEM_TO_REPO: Record<string, string> = {
  nes: "Nintendo - Nintendo Entertainment System",
  snes: "Nintendo - Super Nintendo Entertainment System",
  gb: "Nintendo - Game Boy",
  gbc: "Nintendo - Game Boy Color",
  gba: "Nintendo - Game Boy Advance",
  genesis: "Sega - Mega Drive - Genesis",
  ps1: "Sony - PlayStation",
  n64: "Nintendo - Nintendo 64",
};

const THUMBNAIL_BASE = "https://raw.githubusercontent.com/libretro-thumbnails";

function cleanForLibretro(filename: string): string {
  return filename
    .replace(/\.[^.]+$/, "")
    .replace(/[[{].*?[}\]]/g, "")
    .replace(/\s+/g, " ")
    .trim();
}

async function tryThumbnailUrl(repo: string, title: string): Promise<string | null> {
  const encoded = encodeURIComponent(title).replace(/%20/g, " ");
  const url = `${THUMBNAIL_BASE}/${encodeURIComponent(repo)}/master/Named_Boxarts/${encoded}.png`;
  try {
    const resp = await fetch(url, { method: "HEAD" });
    if (resp.ok) return url;
  } catch {
    // Network error
  }
  return null;
}

function generateTitleVariants(title: string): string[] {
  const variants = [title];
  for (const region of ["(USA)", "(USA, Europe)", "(Europe)", "(Japan)", "(World)"]) {
    if (!title.includes("(")) {
      variants.push(`${title} ${region}`);
    }
  }
  const noParens = title.replace(/\s*\(.*?\)\s*/g, "").trim();
  if (noParens !== title) {
    variants.push(noParens);
    for (const region of ["(USA)", "(USA, Europe)", "(Europe)"]) {
      variants.push(`${noParens} ${region}`);
    }
  }
  return variants;
}

/** Scrape cover art for a single game. Returns true if found. */
export async function scrapeGameMetadata(game: Game): Promise<boolean> {
  if (game.coverUrl) return false;
  const repo = SYSTEM_TO_REPO[game.system];
  if (!repo) return false;

  const cleanTitle = cleanForLibretro(game.displayTitle || game.title);
  const variants = generateTitleVariants(cleanTitle);

  for (const variant of variants) {
    const url = await tryThumbnailUrl(repo, variant);
    if (url) {
      await updateGameMetadata(game.id, { coverUrl: url });
      return true;
    }
  }
  return false;
}

/** Scrape metadata for all games missing cover art. Returns count updated. */
export async function scrapeAllMissingMetadata(
  games: Game[],
  onProgress?: (done: number, total: number) => void,
): Promise<number> {
  const missing = games.filter((g) => !g.coverUrl);
  let updated = 0;
  for (let i = 0; i < missing.length; i++) {
    try {
      const found = await scrapeGameMetadata(missing[i]);
      if (found) updated++;
    } catch { /* skip */ }
    onProgress?.(i + 1, missing.length);
  }
  return updated;
}
