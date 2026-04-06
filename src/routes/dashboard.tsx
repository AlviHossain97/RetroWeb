import { useEffect } from "react";
import { Clock, Gamepad2, Activity, Cpu, TrendingUp } from "lucide-react";
import { useDashboardStore } from "@/stores/dashboardStore";
import { getSystemStats } from "@/lib/api/systems";
import { useState } from "react";
import type { SystemStats } from "@/lib/types/api";
import { RetroPiece } from "@/components/RetroPiece";

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
      <div className="retro-page-shell flex-1 flex items-center justify-center">
        <div className="retro-panel retro-panel--highlight rounded-[1.6rem] p-8 text-center">
          <div className="retro-piece-frame mx-auto mb-4">
            <RetroPiece size="lg" />
          </div>
          <div className="animate-pulse text-sm" style={{ color: "var(--text-muted)" }}>Loading dashboard...</div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="retro-page-shell flex-1 flex items-center justify-center">
        <div className="retro-panel retro-panel--highlight rounded-[1.6rem] p-8 text-center max-w-md">
          <p className="text-sm mb-4 uppercase tracking-[0.16em]" style={{ color: "var(--danger)" }}>Failed to load dashboard</p>
          <button onClick={fetchDashboard} className="retro-button retro-button--danger">
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="retro-page-shell flex-1 overflow-y-auto">
      <header className="grid gap-6 lg:grid-cols-[minmax(0,1.2fr)_minmax(320px,0.8fr)] mb-8">
        <div className="retro-panel retro-panel--hero rounded-[1.75rem] p-7 md:p-8">
          <span className="retro-kicker mb-5">
            <RetroPiece size="sm" />
            Analytics Core
          </span>
          <div className="flex items-start justify-between gap-4">
            <div>
              <h1 className="retro-heading mb-3">
                <span className="retro-title-gradient">Dashboard</span>
              </h1>
              <p className="retro-subtitle">
                High-score tables, system telemetry, and session history tuned to the new cabinet skin.
              </p>
            </div>
            <div className="retro-piece-frame hidden sm:inline-flex">
              <RetroPiece size="lg" />
            </div>
          </div>
        </div>

        <div className="retro-panel retro-panel--highlight rounded-[1.6rem] p-6">
          <div className="retro-section-title mb-4">
            <Activity size={18} />
            Live Feed
          </div>
          {activeSession ? (
            <>
              <span className="retro-chip retro-chip--success mb-3">
                <Activity size={12} />
                Now Playing
              </span>
              <p className="text-xl font-bold mb-1" style={{ color: "var(--text-primary)" }}>{extractTitle(activeSession.rom_path)}</p>
              <p className="text-sm mb-4" style={{ color: "var(--text-muted)" }}>
                {activeSession.system_name?.toUpperCase()} · {activeSession.pi_hostname}
              </p>
            </>
          ) : (
            <>
              <span className="retro-chip mb-3">Standby</span>
              <p className="text-xl font-bold mb-1" style={{ color: "var(--text-primary)" }}>No active session</p>
              <p className="text-sm mb-4" style={{ color: "var(--text-muted)" }}>
                Start a game to light up the live feed.
              </p>
            </>
          )}
          <div className="grid grid-cols-2 gap-3">
            {[
              { label: "Playtime", value: formatPlaytime(totalPlaytime) },
              { label: "Sessions", value: String(totalSessions) },
              { label: "Games", value: String(topGames.length) },
              { label: "Systems", value: String(uniqueSystems) },
            ].map((item) => (
              <div key={item.label} className="retro-stat-card">
                <p className="text-[0.56rem] uppercase tracking-[0.16em]" style={{ color: "var(--text-muted)" }}>{item.label}</p>
                <p className="text-lg font-bold mt-2" style={{ color: "var(--text-primary)" }}>{item.value}</p>
              </div>
            ))}
          </div>
        </div>
      </header>

      <div className="retro-stat-grid grid grid-cols-2 md:grid-cols-4 mb-8">
        {[
          { icon: <Clock size={20} />, label: "Total Playtime", value: formatPlaytime(totalPlaytime) },
          { icon: <Gamepad2 size={20} />, label: "Total Sessions", value: String(totalSessions) },
          { icon: <TrendingUp size={20} />, label: "Games Tracked", value: String(topGames.length) },
          { icon: <Cpu size={20} />, label: "Systems Used", value: String(uniqueSystems) },
        ].map((card) => (
          <div key={card.label} className="retro-stat-card">
            <div className="flex items-center gap-2 mb-2" style={{ color: "var(--accent-secondary)" }}>
              {card.icon}
              <span className="text-[0.58rem] uppercase tracking-[0.16em]">{card.label}</span>
            </div>
            <p className="text-2xl font-bold" style={{ color: "var(--text-primary)" }}>{card.value}</p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="retro-panel rounded-[1.5rem] p-5">
          <div className="retro-section-title">
            <Gamepad2 size={18} />
            Most Played Games
          </div>
          <div className="space-y-3">
            {topGames.slice(0, 8).map((game, i) => {
              const maxPt = topGames[0]?.total_seconds || 1;
              return (
                <div key={game.rom_path} className="retro-list-item p-4">
                  <div className="flex items-center gap-3 mb-3">
                    <span className="text-xs font-bold w-7 text-center" style={{ color: "var(--accent-secondary)" }}>#{i + 1}</span>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium truncate" style={{ color: "var(--text-primary)" }}>{extractTitle(game.rom_path)}</p>
                      <p className="text-[0.65rem] mt-1" style={{ color: "var(--text-muted)" }}>
                        {game.system_name?.toUpperCase()} · {game.session_count} sessions
                      </p>
                    </div>
                    <span className="text-xs font-mono shrink-0" style={{ color: "var(--accent-secondary)" }}>{formatPlaytime(game.total_seconds)}</span>
                  </div>
                  <div className="retro-meter">
                    <div className="retro-meter__fill" style={{ width: `${(game.total_seconds / maxPt) * 100}%` }} />
                  </div>
                </div>
              );
            })}
            {topGames.length === 0 && <p className="text-xs" style={{ color: "var(--text-muted)" }}>No game data yet. Play some games on your PiStation.</p>}
          </div>
        </div>

        <div className="retro-panel rounded-[1.5rem] p-5">
          <div className="retro-section-title">
            <Cpu size={18} />
            Playtime by System
          </div>
          <div className="space-y-4">
            {systems.map((sys) => {
              const maxPt = systems[0]?.total_seconds || 1;
              return (
                <div key={sys.system_name}>
                  <div className="flex justify-between text-xs mb-2 gap-4">
                    <span style={{ color: "var(--text-primary)" }}>{sys.system_name.toUpperCase()}</span>
                    <span style={{ color: "var(--text-muted)" }}>{sys.session_count} sessions · {formatPlaytime(sys.total_seconds)}</span>
                  </div>
                  <div className="retro-meter">
                    <div className="retro-meter__fill" style={{ width: `${(sys.total_seconds / maxPt) * 100}%` }} />
                  </div>
                </div>
              );
            })}
            {systems.length === 0 && <p className="text-xs" style={{ color: "var(--text-muted)" }}>No system data yet.</p>}
          </div>
        </div>

        <div className="retro-panel rounded-[1.5rem] p-5 lg:col-span-2">
          <div className="retro-section-title">
            <Clock size={18} />
            Recent Sessions
          </div>
          <div className="space-y-3">
            {recentSessions.map((s) => (
              <div key={s.id} className="retro-list-item p-4 flex items-center gap-4">
                <div className="retro-piece-frame" style={{ minWidth: "3.6rem", minHeight: "3.6rem", padding: "0.75rem" }}>
                  <RetroPiece size="sm" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium truncate" style={{ color: "var(--text-primary)" }}>{extractTitle(s.rom_path)}</p>
                  <p className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>
                    {s.system_name?.toUpperCase()} · {s.pi_hostname} · {new Date(s.started_at).toLocaleDateString()}
                  </p>
                </div>
                <span className="text-xs font-mono shrink-0" style={{ color: "var(--accent-secondary)" }}>
                  {s.duration_seconds ? formatPlaytime(s.duration_seconds) : "active"}
                </span>
              </div>
            ))}
            {recentSessions.length === 0 && <p className="text-xs" style={{ color: "var(--text-muted)" }}>No sessions yet.</p>}
          </div>
        </div>
      </div>
    </div>
  );
}
