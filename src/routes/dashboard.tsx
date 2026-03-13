import { useEffect } from "react";
import { BarChart3, Clock, Gamepad2, Activity, Cpu, TrendingUp } from "lucide-react";
import { useDashboardStore } from "@/stores/dashboardStore";
import { getSystemStats } from "@/lib/api/systems";
import { useState } from "react";
import type { SystemStats } from "@/lib/types/api";

function formatPlaytime(seconds: number): string {
  if (!seconds || seconds <= 0) return "0m";
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

export default function Dashboard() {
  const { activeSession, recentSessions, topGames, loading, error, fetchDashboard } = useDashboardStore();
  const [systems, setSystems] = useState<SystemStats[]>([]);

  useEffect(() => {
    fetchDashboard();
    getSystemStats().then(setSystems).catch(() => {});
  }, [fetchDashboard]);

  const totalPlaytime = topGames.reduce((acc, g) => acc + (g.total_seconds || 0), 0);
  const totalSessions = topGames.reduce((acc, g) => acc + (g.session_count || 0), 0);
  const uniqueSystems = new Set(topGames.map((g) => g.system_name).filter(Boolean)).size;

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="animate-pulse text-sm" style={{ color: "var(--text-muted)" }}>Loading dashboard...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center">
          <p className="text-sm mb-2" style={{ color: "var(--accent-secondary)" }}>Failed to load dashboard</p>
          <button onClick={fetchDashboard} className="text-xs px-4 py-2 rounded-lg" style={{ background: "var(--surface-2)", color: "var(--text-primary)" }}>
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 w-full max-w-6xl mx-auto p-4 md:p-8 overflow-y-auto">
      <header className="mb-8">
        <h1 className="text-3xl font-bold flex items-center gap-3" style={{ color: "var(--text-primary)" }}>
          <BarChart3 size={28} style={{ color: "var(--accent-primary)" }} /> Dashboard
        </h1>
        <p className="text-sm mt-1" style={{ color: "var(--text-muted)" }}>
          Your PiStation gaming analytics at a glance
        </p>
      </header>

      {/* Now Playing Banner */}
      {activeSession && (
        <div className="mb-6 p-5 rounded-xl relative overflow-hidden" style={{ background: "linear-gradient(135deg, rgba(139,92,246,0.15), rgba(239,68,68,0.1))", border: "1px solid rgba(139,92,246,0.3)" }}>
          <div className="flex items-center gap-2 mb-2">
            <Activity size={16} className="text-green-400 animate-pulse" />
            <span className="text-xs font-bold uppercase tracking-wider text-green-400">Now Playing</span>
          </div>
          <p className="text-lg font-bold" style={{ color: "var(--text-primary)" }}>{extractTitle(activeSession.rom_path)}</p>
          <p className="text-sm" style={{ color: "var(--text-muted)" }}>
            {activeSession.system_name?.toUpperCase()} · {activeSession.pi_hostname}
          </p>
        </div>
      )}

      {/* Summary Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-8">
        {[
          { icon: <Clock size={20} />, label: "Total Playtime", value: formatPlaytime(totalPlaytime) },
          { icon: <Gamepad2 size={20} />, label: "Total Sessions", value: String(totalSessions) },
          { icon: <TrendingUp size={20} />, label: "Games Tracked", value: String(topGames.length) },
          { icon: <Cpu size={20} />, label: "Systems Used", value: String(uniqueSystems) },
        ].map((card) => (
          <div key={card.label} className="p-4 rounded-xl" style={{ background: "var(--surface-1)", border: "1px solid var(--border-soft)" }}>
            <div className="flex items-center gap-2 mb-2" style={{ color: "var(--text-muted)" }}>
              {card.icon}
              <span className="text-[10px] uppercase tracking-wider font-bold">{card.label}</span>
            </div>
            <p className="text-2xl font-bold" style={{ color: "var(--text-primary)" }}>{card.value}</p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Top Games */}
        <div className="rounded-xl p-5" style={{ background: "var(--surface-1)", border: "1px solid var(--border-soft)" }}>
          <h2 className="text-sm font-bold uppercase tracking-wider mb-4" style={{ color: "var(--text-muted)" }}>Most Played Games</h2>
          <div className="space-y-2">
            {topGames.slice(0, 8).map((game, i) => {
              const maxPt = topGames[0]?.total_seconds || 1;
              return (
                <div key={game.rom_path} className="p-3 rounded-lg" style={{ background: "var(--surface-2)" }}>
                  <div className="flex items-center gap-3 mb-2">
                    <span className="text-xs font-bold w-5 text-center" style={{ color: "var(--text-muted)" }}>#{i + 1}</span>
                    <div className="flex-1 min-w-0">
                      <p className="text-xs font-medium truncate" style={{ color: "var(--text-primary)" }}>{extractTitle(game.rom_path)}</p>
                      <p className="text-[10px]" style={{ color: "var(--text-muted)" }}>
                        {game.system_name?.toUpperCase()} · {game.session_count} sessions
                      </p>
                    </div>
                    <span className="text-xs font-mono shrink-0" style={{ color: "var(--accent-primary)" }}>{formatPlaytime(game.total_seconds)}</span>
                  </div>
                  <div className="h-1 rounded-full overflow-hidden" style={{ background: "var(--surface-1)" }}>
                    <div className="h-full rounded-full" style={{ width: `${(game.total_seconds / maxPt) * 100}%`, background: "var(--accent-primary)" }} />
                  </div>
                </div>
              );
            })}
            {topGames.length === 0 && <p className="text-xs" style={{ color: "var(--text-muted)" }}>No game data yet. Play some games on your PiStation!</p>}
          </div>
        </div>

        {/* Playtime by System */}
        <div className="rounded-xl p-5" style={{ background: "var(--surface-1)", border: "1px solid var(--border-soft)" }}>
          <h2 className="text-sm font-bold uppercase tracking-wider mb-4" style={{ color: "var(--text-muted)" }}>Playtime by System</h2>
          <div className="space-y-3">
            {systems.map((sys) => {
              const maxPt = systems[0]?.total_seconds || 1;
              return (
                <div key={sys.system_name}>
                  <div className="flex justify-between text-xs mb-1">
                    <span style={{ color: "var(--text-primary)" }}>{sys.system_name.toUpperCase()}</span>
                    <span style={{ color: "var(--text-muted)" }}>{sys.session_count} sessions · {formatPlaytime(sys.total_seconds)}</span>
                  </div>
                  <div className="h-2 rounded-full overflow-hidden" style={{ background: "var(--surface-2)" }}>
                    <div className="h-full rounded-full" style={{ width: `${(sys.total_seconds / maxPt) * 100}%`, background: "var(--accent-primary)" }} />
                  </div>
                </div>
              );
            })}
            {systems.length === 0 && <p className="text-xs" style={{ color: "var(--text-muted)" }}>No system data yet</p>}
          </div>
        </div>

        {/* Recent Sessions */}
        <div className="rounded-xl p-5 lg:col-span-2" style={{ background: "var(--surface-1)", border: "1px solid var(--border-soft)" }}>
          <h2 className="text-sm font-bold uppercase tracking-wider mb-4" style={{ color: "var(--text-muted)" }}>Recent Sessions</h2>
          <div className="space-y-2">
            {recentSessions.map((s) => (
              <div key={s.id} className="flex items-center gap-4 p-3 rounded-lg" style={{ background: "var(--surface-2)" }}>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium truncate" style={{ color: "var(--text-primary)" }}>{extractTitle(s.rom_path)}</p>
                  <p className="text-xs" style={{ color: "var(--text-muted)" }}>
                    {s.system_name?.toUpperCase()} · {s.pi_hostname} · {new Date(s.started_at).toLocaleDateString()}
                  </p>
                </div>
                <span className="text-xs font-mono shrink-0" style={{ color: "var(--accent-primary)" }}>
                  {s.duration_seconds ? formatPlaytime(s.duration_seconds) : "active"}
                </span>
              </div>
            ))}
            {recentSessions.length === 0 && <p className="text-xs" style={{ color: "var(--text-muted)" }}>No sessions yet</p>}
          </div>
        </div>
      </div>
    </div>
  );
}
