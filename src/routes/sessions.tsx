import { useEffect, useState, useMemo } from "react";
import { Activity, Filter, Search } from "lucide-react";
import { getRecentSessions, getActiveSessions } from "@/lib/api/sessions";
import type { Session } from "@/lib/types/api";
import { RetroPiece } from "@/components/RetroPiece";

function formatPlaytime(seconds: number): string {
  if (!seconds || seconds <= 0) return "—";
  if (seconds < 60) return `${seconds}s`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m`;
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  return `${h}h ${m}m`;
}

function extractTitle(romPath: string): string {
  const filename = romPath.split("/").pop() || romPath;
  return filename.replace(/\.(zip|7z|nes|sfc|smc|gba|gb|gbc|bin|cue|iso|md|gen|dat)$/i, "").replace(/\s*\([^)]*\)/g, "").trim();
}

export default function Sessions() {
  const [active, setActive] = useState<Session[]>([]);
  const [recent, setRecent] = useState<Session[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [systemFilter, setSystemFilter] = useState("all");

  useEffect(() => {
    Promise.all([getActiveSessions(20), getRecentSessions(50)])
      .then(([a, r]) => { setActive(a); setRecent(r); })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const allSystems = useMemo(() => {
    const set = new Set<string>();
    [...active, ...recent].forEach((s) => { if (s.system_name) set.add(s.system_name); });
    return Array.from(set).sort();
  }, [active, recent]);

  const filteredRecent = useMemo(() => {
    return recent.filter((s) => {
      const matchesSearch = !search || extractTitle(s.rom_path).toLowerCase().includes(search.toLowerCase()) || s.pi_hostname.toLowerCase().includes(search.toLowerCase());
      const matchesSystem = systemFilter === "all" || s.system_name === systemFilter;
      return matchesSearch && matchesSystem;
    });
  }, [recent, search, systemFilter]);

  if (loading) {
    return (
      <div className="retro-page-shell flex-1 flex items-center justify-center">
        <div className="retro-panel rounded-[1.5rem] p-8 text-center">
          <div className="animate-pulse text-sm" style={{ color: "var(--text-muted)" }}>Loading sessions...</div>
        </div>
      </div>
    );
  }

  return (
    <div className="retro-page-shell flex-1 overflow-y-auto">
      <header className="retro-panel retro-panel--hero rounded-[1.7rem] p-7 md:p-8 mb-6">
        <span className="retro-kicker mb-5">
          <RetroPiece size="sm" />
          Session Archive
        </span>
        <h1 className="retro-heading mb-3">
          <span className="retro-title-gradient">Sessions</span>
        </h1>
        <p className="retro-subtitle">
          {active.length} active · {recent.length} recent
        </p>
      </header>

      {/* Active Sessions */}
      {active.length > 0 && (
        <section className="mb-8">
          <div className="retro-section-title">
            <Activity size={16} style={{ color: "var(--success)" }} />
            Active Sessions
          </div>
          <div className="space-y-2">
            {active.map((s) => (
              <div key={s.id} className="retro-list-item p-4 flex items-center gap-4" style={{ borderColor: "rgba(125, 255, 176, 0.24)" }}>
                <div className="retro-piece-frame" style={{ minWidth: "3.4rem", minHeight: "3.4rem", padding: "0.75rem", borderColor: "rgba(125, 255, 176, 0.22)" }}>
                  <Activity size={16} className="animate-pulse" style={{ color: "var(--success)" }} />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-semibold truncate" style={{ color: "var(--text-primary)" }}>{extractTitle(s.rom_path)}</p>
                  <p className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>
                    {s.system_name?.toUpperCase()} · {s.pi_hostname} · started {new Date(s.started_at).toLocaleTimeString()}
                  </p>
                </div>
                <span className="retro-chip retro-chip--success shrink-0">Live</span>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-3 mb-6">
        <div className="retro-input-shell relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2" size={16} style={{ color: "var(--text-muted)" }} />
          <input
            type="text"
            placeholder="Search by game or device..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="retro-input pl-10 pr-4 py-3 text-sm rounded-[1.1rem]"
          />
        </div>
        <div className="retro-input-shell relative min-w-[160px]">
          <Filter className="absolute left-3 top-1/2 -translate-y-1/2" size={16} style={{ color: "var(--text-muted)" }} />
          <select
            value={systemFilter}
            onChange={(e) => setSystemFilter(e.target.value)}
            className="retro-select w-full pl-10 pr-4 py-3 rounded-[1.1rem] text-sm appearance-none cursor-pointer"
          >
            <option value="all">All Systems</option>
            {allSystems.map((sys) => <option key={sys} value={sys}>{sys.toUpperCase()}</option>)}
          </select>
        </div>
      </div>

      {/* Recent Sessions Table */}
      <div className="retro-table rounded-[1.5rem]">
        <div className="retro-table__head grid grid-cols-[1fr_auto_auto_auto] gap-4 p-4 text-[0.58rem] font-bold uppercase tracking-[0.18em]">
          <span>Game</span>
          <span>System</span>
          <span>Device</span>
          <span className="text-right">Duration</span>
        </div>
        <div>
          {filteredRecent.map((s) => (
            <div key={s.id} className="retro-table__row grid grid-cols-[1fr_auto_auto_auto] gap-4 p-4 items-center">
              <div className="min-w-0">
                <p className="text-sm font-medium truncate" style={{ color: "var(--text-primary)" }}>{extractTitle(s.rom_path)}</p>
                <p className="text-[0.64rem] mt-1" style={{ color: "var(--text-muted)" }}>{new Date(s.started_at).toLocaleDateString()} {new Date(s.started_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</p>
              </div>
              <span className="retro-chip">
                {s.system_name?.toUpperCase() || "—"}
              </span>
              <span className="text-xs" style={{ color: "var(--text-muted)" }}>{s.pi_hostname}</span>
              <span className="text-xs font-mono text-right" style={{ color: "var(--accent-secondary)" }}>
                {formatPlaytime(s.duration_seconds || 0)}
              </span>
            </div>
          ))}
          {filteredRecent.length === 0 && (
            <div className="p-8 text-center text-sm" style={{ color: "var(--text-muted)" }}>
              {search || systemFilter !== "all" ? "No sessions match your filters" : "No sessions recorded yet"}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
