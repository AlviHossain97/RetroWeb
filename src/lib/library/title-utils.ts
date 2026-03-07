const REGION_TAGS = [
  /\((usa|europe|japan|world|en,fr,de,es,it|en,ja|en,fr|fr,de|beta|proto)\)/gi,
  /\[(usa|europe|japan|world|!|b|h|t\+eng|t\+spa|beta|proto)\]/gi,
  /\((rev\s?[a-z0-9]+)\)/gi,
  /\((v\d+(?:\.\d+)*)\)/gi,
  /\([a-z]{2}(,[a-z]{2})+\)/gi,
];

export function cleanGameTitleFromFilename(filename: string) {
  const withoutExtension = filename.replace(/\.[^.]+$/, "");
  const withoutTags = REGION_TAGS.reduce((current, pattern) => current.replace(pattern, ""), withoutExtension);
  return withoutTags.replace(/[_.]+/g, " ").replace(/\s{2,}/g, " ").trim();
}

export function getSystemLabel(systemId: string) {
  const labels: Record<string, string> = {
    nes: "NES",
    snes: "SNES",
    gb: "GB/GBC/GBA",
    genesis: "Genesis",
    ps1: "PS1",
    n64: "N64",
  };

  return labels[systemId] ?? systemId.toUpperCase();
}

export function getSystemGradient(systemId: string): string {
  const gradients: Record<string, string> = {
    nes: "linear-gradient(135deg, rgba(185,28,28,0.5), rgba(217,119,6,0.2), transparent)",
    snes: "linear-gradient(135deg, rgba(126,34,206,0.5), rgba(79,70,229,0.2), transparent)",
    gb: "linear-gradient(135deg, rgba(4,120,87,0.5), rgba(101,163,13,0.2), transparent)",
    genesis: "linear-gradient(135deg, rgba(3,105,161,0.5), rgba(6,182,212,0.2), transparent)",
    ps1: "linear-gradient(135deg, rgba(71,85,105,0.5), rgba(37,99,235,0.2), transparent)",
    n64: "linear-gradient(135deg, rgba(194,65,12,0.5), rgba(202,138,4,0.2), transparent)",
  };

  return gradients[systemId] ?? "linear-gradient(135deg, rgba(63,63,70,0.5), rgba(63,63,70,0.2), transparent)";
}

export function getSystemColor(systemId: string): string {
  const colors: Record<string, string> = {
    nes: "#ef4444",
    snes: "#a855f7",
    gb: "#10b981",
    genesis: "#06b6d4",
    ps1: "#3b82f6",
    n64: "#f59e0b",
  };
  return colors[systemId] ?? "#8b5cf6";
}

export function hasRecentAutoSave(lastAutoSaveAt?: number) {
  if (!lastAutoSaveAt) return false;
  return Date.now() - lastAutoSaveAt < 24 * 60 * 60 * 1000;
}
