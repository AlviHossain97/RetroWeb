import { useEffect, useState, useMemo } from "react";
import { Clock, Activity, Filter, Search } from "lucide-react";
import { getRecentSessions, getActiveSessions } from "@/lib/api/sessions";
import type { Session } from "@/lib/types/api";

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
      <div className="flex-1 flex items-center justify-center">
        <div className="animate-pulse text-sm" style={{ color: "var(--text-muted)" }}>Loading sessions...</div>
      </div>
    );
  }

  return (
    <div className="flex-1 w-full max-w-6xl mx-auto p-4 md:p-8 overflow-y-auto">
      <header className="mb-6">
        <h1 className="text-3xl font-bold flex items-center gap-3" style={{ color: "var(--text-primary)" }}>
          <Clock size={28} style={{ color: "var(--accent-primary)" }} /> Sessions
        </h1>
        <p className="text-sm mt-1" style={{ color: "var(--text-muted)" }}>
          {active.length} active · {recent.length} recent
        </p>
      </header>

      {/* Active Sessions */}
      {active.length > 0 && (
        <section className="mb-8">
          <h2 className="text-sm font-bold uppercase tracking-wider mb-3 flex items-center gap-2" style={{ color: "var(--text-muted)" }}>
            <Activity size={14} className="text-green-400" /> Active Sessions
          </h2>
          <div className="space-y-2">
            {active.map((s) => (
              <div key={s.id} className="flex items-center gap-4 p-4 rounded-xl" style={{ background: "linear-gradient(135deg, rgba(34,197,94,0.08), rgba(139,92,246,0.05))", border: "1px solid rgba(34,197,94,0.2)" }}>
                <Activity size={16} className="text-green-400 animate-pulse shrink-0" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-semibold truncate" style={{ color: "var(--text-primary)" }}>{extractTitle(s.rom_path)}</p>
                  <p className="text-xs" style={{ color: "var(--text-muted)" }}>
                    {s.system_name?.toUpperCase()} · {s.pi_hostname} · started {new Date(s.started_at).toLocaleTimeString()}
                  </p>
                </div>
                <span className="text-xs font-mono text-green-400 shrink-0">LIVE</span>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-3 mb-6">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2" size={16} style={{ color: "var(--text-muted)" }} />
          <input
            type="text"
            placeholder="Search by game or device..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-10 pr-4 py-2.5 rounded-xl text-sm focus:outline-none focus:ring-2"
            style={{ background: "var(--surface-2)", color: "var(--text-primary)", border: "1px solid var(--border-soft)" }}
          />
        </div>
        <div className="relative min-w-[160px]">
          <Filter className="absolute left-3 top-1/2 -translate-y-1/2" size={16} style={{ color: "var(--text-muted)" }} />
          <select
            value={systemFilter}
            onChange={(e) => setSystemFilter(e.target.value)}
            className="w-full pl-10 pr-4 py-2.5 rounded-xl text-sm appearance-none cursor-pointer focus:outline-none"
            style={{ background: "var(--surface-2)", color: "var(--text-primary)", border: "1px solid var(--border-soft)" }}
          >
            <option value="all">All Systems</option>
            {allSystems.map((sys) => <option key={sys} value={sys}>{sys.toUpperCase()}</option>)}
          </select>
        </div>
      </div>

      {/* Recent Sessions Table */}
      <div className="rounded-xl overflow-hidden" style={{ border: "1px solid var(--border-soft)" }}>
        <div className="grid grid-cols-[1fr_auto_auto_auto] gap-4 p-3 text-[10px] font-bold uppercase tracking-wider" style={{ background: "var(--surface-2)", color: "var(--text-muted)" }}>
          <span>Game</span>
          <span>System</span>
          <span>Device</span>
          <span className="text-right">Duration</span>
        </div>
        <div className="divide-y" style={{ borderColor: "var(--border-soft)" }}>
          {filteredRecent.map((s) => (
            <div key={s.id} className="grid grid-cols-[1fr_auto_auto_auto] gap-4 p-3 items-center hover:opacity-80 transition-opacity" style={{ background: "var(--surface-1)" }}>
              <div className="min-w-0">
                <p className="text-sm font-medium truncate" style={{ color: "var(--text-primary)" }}>{extractTitle(s.rom_path)}</p>
                <p className="text-[10px]" style={{ color: "var(--text-muted)" }}>{new Date(s.started_at).toLocaleDateString()} {new Date(s.started_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</p>
              </div>
              <span className="text-xs px-2 py-0.5 rounded-full" style={{ background: "var(--surface-2)", color: "var(--text-muted)" }}>
                {s.system_name?.toUpperCase() || "—"}
              </span>
              <span className="text-xs" style={{ color: "var(--text-muted)" }}>{s.pi_hostname}</span>
              <span className="text-xs font-mono text-right" style={{ color: "var(--accent-primary)" }}>
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
