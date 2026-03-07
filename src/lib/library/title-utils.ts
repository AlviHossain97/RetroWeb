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

export function getSystemGradient(systemId: string) {
  const gradients: Record<string, string> = {
    nes: "from-red-700/70 via-amber-600/30 to-zinc-900",
    snes: "from-purple-700/70 via-indigo-700/30 to-zinc-900",
    gb: "from-emerald-700/70 via-lime-700/30 to-zinc-900",
    genesis: "from-sky-700/70 via-cyan-700/30 to-zinc-900",
    ps1: "from-slate-700/70 via-blue-700/30 to-zinc-900",
    n64: "from-orange-700/70 via-yellow-700/30 to-zinc-900",
  };

  return gradients[systemId] ?? "from-zinc-700/70 via-zinc-700/30 to-zinc-900";
}

export function hasRecentAutoSave(lastAutoSaveAt?: number) {
  if (!lastAutoSaveAt) return false;
  return Date.now() - lastAutoSaveAt < 24 * 60 * 60 * 1000;
}
