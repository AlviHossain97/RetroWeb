import { useState } from "react";
import { Search, ExternalLink, Download } from "lucide-react";

interface RomHack {
  name: string;
  baseGame: string;
  system: string;
  author: string;
  description: string;
  url: string;
  type: "improvement" | "translation" | "overhaul" | "difficulty";
}

const CURATED_HACKS: RomHack[] = [
  { name: "Super Mario Bros. 3Mix", baseGame: "Super Mario Bros. 3", system: "NES", author: "Captain Southbird", description: "Massive overhaul with new levels, power-ups, and mechanics from across the Mario series.", url: "https://www.romhacking.net/hacks/2068/", type: "overhaul" },
  { name: "Pokémon Crystal Clear", baseGame: "Pokémon Crystal", system: "GBC", author: "ShockSlayer", description: "Open-world Pokémon Crystal with all 251 Pokémon, character customization, and freedom to explore.", url: "https://pokemon-crystal-clear.com/", type: "overhaul" },
  { name: "Super Metroid: Redesign", baseGame: "Super Metroid", system: "SNES", author: "Drewseph", description: "Completely new map layout with physics changes and extended gameplay.", url: "https://www.romhacking.net/hacks/131/", type: "overhaul" },
  { name: "Zelda: Parallel Worlds", baseGame: "The Legend of Zelda: A Link to the Past", system: "SNES", author: "Euclid + SePH", description: "Entirely new overworld and dungeons with high difficulty.", url: "https://www.romhacking.net/hacks/197/", type: "overhaul" },
  { name: "Sonic 3 Complete", baseGame: "Sonic 3 & Knuckles", system: "Genesis", author: "Tiddles", description: "Definitive version combining Sonic 3 and Knuckles with fixes and options.", url: "https://www.romhacking.net/hacks/2085/", type: "improvement" },
  { name: "Final Fantasy VI: Brave New World", baseGame: "Final Fantasy VI", system: "SNES", author: "BTB + Synchysi", description: "Complete rebalance with improved scripts, mechanics, and challenge.", url: "https://www.romhacking.net/hacks/2228/", type: "overhaul" },
  { name: "Mother 3 English", baseGame: "Mother 3", system: "GBA", author: "Tomato", description: "Professional-quality fan translation of Mother 3 from Japanese to English.", url: "https://www.romhacking.net/translations/1517/", type: "translation" },
  { name: "Castlevania: Dawn of Dissonance", baseGame: "Castlevania: Harmony of Dissonance", system: "GBA", author: "Venon", description: "Major overhaul with new areas, enemies, and items.", url: "https://www.romhacking.net/hacks/5692/", type: "overhaul" },
  { name: "Kaizo Mario World", baseGame: "Super Mario World", system: "SNES", author: "T. Takemoto", description: "Infamously difficult Mario hack that spawned an entire genre of precision platforming.", url: "https://www.romhacking.net/hacks/205/", type: "difficulty" },
  { name: "Shin Megami Tensei (English)", baseGame: "Shin Megami Tensei", system: "SNES", author: "Aeon Genesis", description: "English translation of the original SMT for Super Famicom.", url: "https://www.romhacking.net/translations/475/", type: "translation" },
  { name: "Metroid: Rogue Dawn", baseGame: "Metroid", system: "NES", author: "Grimlock + Optomon", description: "Prequel to the original Metroid with entirely new content and story.", url: "https://www.romhacking.net/hacks/3419/", type: "overhaul" },
  { name: "Pokémon Prism", baseGame: "Pokémon Crystal", system: "GBC", author: "Koolboyman", description: "New region, story, and Pokémon from multiple generations.", url: "https://pokemonprism.com/", type: "overhaul" },
];

const TYPE_COLORS: Record<string, { bg: string; text: string }> = {
  improvement: { bg: "rgba(34,197,94,0.15)", text: "#22c55e" },
  translation: { bg: "rgba(59,130,246,0.15)", text: "#3b82f6" },
  overhaul: { bg: "rgba(168,85,247,0.15)", text: "#a855f7" },
  difficulty: { bg: "rgba(239,68,68,0.15)", text: "#ef4444" },
};

export default function RomHacksPage() {
  const [search, setSearch] = useState("");
  const [typeFilter, setTypeFilter] = useState<string>("all");

  const filtered = CURATED_HACKS.filter((h) => {
    if (typeFilter !== "all" && h.type !== typeFilter) return false;
    if (!search.trim()) return true;
    const q = search.toLowerCase();
    return [h.name, h.baseGame, h.system, h.author, h.description].some((s) => s.toLowerCase().includes(q));
  });

  return (
    <div className="flex-1 w-full max-w-5xl mx-auto p-4 md:p-8">
      <header className="mb-6">
        <h1 className="text-2xl font-bold flex items-center gap-3 mb-2" style={{ color: "var(--text-primary)" }}>
          <Download size={24} style={{ color: "var(--accent-primary)" }} /> ROM Hacks Directory
        </h1>
        <p className="text-sm" style={{ color: "var(--text-muted)" }}>
          Curated list of notable ROM hacks and fan translations. Download patches from the linked sites and apply them to your ROMs.
        </p>
      </header>

      <div className="flex flex-wrap gap-3 mb-6">
        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2" size={14} style={{ color: "var(--text-muted)" }} />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search hacks..."
            className="w-full pl-9 pr-3 py-2 text-sm rounded-lg"
            style={{ background: "var(--surface-1)", border: "1px solid var(--border-soft)", color: "var(--text-primary)" }}
          />
        </div>
        {["all", "overhaul", "translation", "improvement", "difficulty"].map((t) => (
          <button
            key={t}
            onClick={() => setTypeFilter(t)}
            className="px-3 py-2 text-xs font-bold rounded-lg uppercase tracking-wider transition-colors"
            style={{
              background: typeFilter === t ? "var(--accent-primary)" : "var(--surface-1)",
              color: typeFilter === t ? "#fff" : "var(--text-muted)",
              border: `1px solid ${typeFilter === t ? "var(--accent-primary)" : "var(--border-soft)"}`,
            }}
          >
            {t}
          </button>
        ))}
      </div>

      <div className="grid gap-3">
        {filtered.map((hack) => {
          const colors = TYPE_COLORS[hack.type] ?? TYPE_COLORS.overhaul;
          return (
            <div key={hack.name} className="p-4 rounded-xl flex gap-4 items-start" style={{ background: "var(--surface-1)", border: "1px solid var(--border-soft)" }}>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1 flex-wrap">
                  <h3 className="text-sm font-bold" style={{ color: "var(--text-primary)" }}>{hack.name}</h3>
                  <span className="text-[10px] px-2 py-0.5 rounded-full font-bold uppercase" style={{ background: colors.bg, color: colors.text }}>
                    {hack.type}
                  </span>
                  <span className="text-[10px] px-2 py-0.5 rounded-full font-bold uppercase" style={{ background: "var(--surface-2)", color: "var(--text-muted)" }}>
                    {hack.system}
                  </span>
                </div>
                <p className="text-xs mb-1" style={{ color: "var(--text-muted)" }}>
                  Base: <strong>{hack.baseGame}</strong> · By {hack.author}
                </p>
                <p className="text-xs leading-relaxed" style={{ color: "var(--text-secondary)" }}>{hack.description}</p>
              </div>
              <a
                href={hack.url}
                target="_blank"
                rel="noopener noreferrer"
                className="shrink-0 p-2 rounded-lg transition-colors"
                style={{ background: "var(--surface-2)", color: "var(--text-muted)" }}
                title="Visit patch page"
              >
                <ExternalLink size={16} />
              </a>
            </div>
          );
        })}
        {filtered.length === 0 && (
          <div className="text-center py-12" style={{ color: "var(--text-muted)" }}>
            <p className="text-sm">No ROM hacks found matching your search.</p>
          </div>
        )}
      </div>
    </div>
  );
}
