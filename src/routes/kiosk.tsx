import { useEffect, useState, useCallback } from "react";
import { Activity, Clock, Gamepad2, Cpu, Maximize, Minimize } from "lucide-react";
import { getDashboardData } from "@/lib/api/dashboard";
import { getSystemStats } from "@/lib/api/systems";
import type { Session, TopGame, SystemStats } from "@/lib/types/api";
import { useGamepadNavigation } from "@/hooks/useGamepadNavigation";

function formatPlaytime(seconds: number): string {
  if (!seconds || seconds <= 0) return "0m";
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m`;
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  return `${h}h ${m}m`;
}

function extractTitle(romPath: string): string {
  const filename = romPath.split("/").pop() || romPath;
  return filename
    .replace(/\.(zip|7z|nes|sfc|smc|gba|gb|gbc|bin|cue|iso|md|gen|dat)$/i, "")
    .replace(/\s*\([^)]*\)/g, "")
    .trim();
}

function formatTime(d: Date): string {
  return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

export default function Kiosk() {
  const [activeSession, setActiveSession] = useState<Session | null>(null);
  const [recentSessions, setRecentSessions] = useState<Session[]>([]);
  const [topGames, setTopGames] = useState<TopGame[]>([]);
  const [systems, setSystems] = useState<SystemStats[]>([]);
  const [time, setTime] = useState(new Date());
  const [isFullscreen, setIsFullscreen] = useState(false);

  useGamepadNavigation({ enabled: true });

  const fetchData = useCallback(() => {
    getDashboardData()
      .then((data) => {
        setActiveSession(data.active_session);
        setRecentSessions(data.recent_sessions);
        setTopGames(data.top_games);
      })
      .catch(() => {});
    getSystemStats().then(setSystems).catch(() => {});
  }, []);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 15000);
    return () => clearInterval(interval);
  }, [fetchData]);

  useEffect(() => {
    const tick = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(tick);
  }, []);

  const toggleFullscreen = () => {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen().then(() => setIsFullscreen(true));
    } else {
      document.exitFullscreen().then(() => setIsFullscreen(false));
    }
  };

  const totalPlaytime = topGames.reduce((acc, g) => acc + (g.total_seconds || 0), 0);
  const totalSessions = topGames.reduce((acc, g) => acc + (g.session_count || 0), 0);

  return (
    <div
      className="fixed inset-0 flex flex-col overflow-hidden"
      style={{ background: "var(--bg-primary, #0a0a0a)", color: "var(--text-primary)" }}
    >
      {/* Top Bar */}
      <div className="flex items-center justify-between px-8 py-4" style={{ borderBottom: "1px solid var(--border-soft)" }}>
        <h1 className="text-3xl font-black tracking-tight">
          <span className="bg-gradient-to-r from-red-500 via-purple-500 to-blue-500 bg-clip-text text-transparent">
            PiStation
          </span>
        </h1>
        <div className="flex items-center gap-6">
          <span className="text-2xl font-mono tabular-nums" style={{ color: "var(--text-muted)" }}>
            {formatTime(time)}
          </span>
          <button
            onClick={toggleFullscreen}
            className="p-2 rounded-lg hover:opacity-80"
            style={{ background: "var(--surface-2)" }}
          >
            {isFullscreen ? <Minimize size={20} /> : <Maximize size={20} />}
          </button>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 grid grid-cols-3 gap-6 p-8 overflow-hidden">
        {/* Left Column — Now Playing + Stats */}
        <div className="flex flex-col gap-6">
          {/* Now Playing */}
          {activeSession ? (
            <div
              className="p-6 rounded-2xl"
              style={{
                background: "linear-gradient(135deg, rgba(139,92,246,0.15), rgba(239,68,68,0.1))",
                border: "1px solid rgba(139,92,246,0.3)",
              }}
            >
              <div className="flex items-center gap-2 mb-3">
                <Activity size={20} className="text-green-400 animate-pulse" />
                <span className="text-sm font-bold uppercase tracking-wider text-green-400">Now Playing</span>
              </div>
              <p className="text-2xl font-bold mb-1">{extractTitle(activeSession.rom_path)}</p>
              <p className="text-lg" style={{ color: "var(--text-muted)" }}>
                {activeSession.system_name?.toUpperCase()} · {activeSession.pi_hostname}
              </p>
            </div>
          ) : (
            <div className="p-6 rounded-2xl" style={{ background: "var(--surface-1)", border: "1px solid var(--border-soft)" }}>
              <div className="flex items-center gap-2 mb-3">
                <Gamepad2 size={20} style={{ color: "var(--text-muted)" }} />
                <span className="text-sm font-bold uppercase tracking-wider" style={{ color: "var(--text-muted)" }}>
                  Idle
                </span>
              </div>
              <p className="text-xl" style={{ color: "var(--text-muted)" }}>No active session</p>
            </div>
          )}

          {/* Summary Stats */}
          <div className="grid grid-cols-2 gap-4">
            {[
              { icon: <Clock size={24} />, label: "Playtime", value: formatPlaytime(totalPlaytime) },
              { icon: <Gamepad2 size={24} />, label: "Sessions", value: String(totalSessions) },
              { icon: <Cpu size={24} />, label: "Systems", value: String(systems.length) },
              { icon: <Activity size={24} />, label: "Games", value: String(topGames.length) },
            ].map((s) => (
              <div key={s.label} className="p-4 rounded-xl" style={{ background: "var(--surface-1)", border: "1px solid var(--border-soft)" }}>
                <div className="flex items-center gap-2 mb-2" style={{ color: "var(--text-muted)" }}>
                  {s.icon}
                  <span className="text-xs uppercase tracking-wider font-bold">{s.label}</span>
                </div>
                <p className="text-3xl font-bold">{s.value}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Center Column — Top Games */}
        <div className="flex flex-col">
          <h2 className="text-lg font-bold uppercase tracking-wider mb-4" style={{ color: "var(--text-muted)" }}>
            Top Games
          </h2>
          <div className="flex-1 space-y-3 overflow-y-auto">
            {topGames.map((game, i) => (
              <div key={game.rom_path} className="flex items-center gap-4 p-4 rounded-xl" style={{ background: "var(--surface-1)", border: "1px solid var(--border-soft)" }}>
                <span className="text-lg font-bold w-8 text-center" style={{ color: "var(--accent-primary)" }}>
                  #{i + 1}
                </span>
                <div className="flex-1 min-w-0">
                  <p className="text-lg font-semibold truncate">{extractTitle(game.rom_path)}</p>
                  <p className="text-sm" style={{ color: "var(--text-muted)" }}>
                    {game.system_name?.toUpperCase()} · {game.session_count} sessions
                  </p>
                </div>
                <span className="text-lg font-mono" style={{ color: "var(--accent-primary)" }}>
                  {formatPlaytime(game.total_seconds)}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Right Column — Recent Sessions + Systems */}
        <div className="flex flex-col gap-6">
          <div className="flex-1 flex flex-col">
            <h2 className="text-lg font-bold uppercase tracking-wider mb-4" style={{ color: "var(--text-muted)" }}>
              Recent Sessions
            </h2>
            <div className="flex-1 space-y-2 overflow-y-auto">
              {recentSessions.slice(0, 6).map((s) => (
                <div key={s.id} className="p-3 rounded-lg" style={{ background: "var(--surface-1)", border: "1px solid var(--border-soft)" }}>
                  <p className="text-base font-medium truncate">{extractTitle(s.rom_path)}</p>
                  <p className="text-sm" style={{ color: "var(--text-muted)" }}>
                    {s.system_name?.toUpperCase()} · {s.duration_seconds ? formatPlaytime(s.duration_seconds) : "active"}
                  </p>
                </div>
              ))}
            </div>
          </div>

          {/* System Bars */}
          <div>
            <h2 className="text-lg font-bold uppercase tracking-wider mb-3" style={{ color: "var(--text-muted)" }}>
              Systems
            </h2>
            <div className="space-y-2">
              {systems.slice(0, 5).map((sys) => {
                const maxPt = systems[0]?.total_seconds || 1;
                return (
                  <div key={sys.system_name}>
                    <div className="flex justify-between text-sm mb-1">
                      <span>{sys.system_name.toUpperCase()}</span>
                      <span style={{ color: "var(--text-muted)" }}>{formatPlaytime(sys.total_seconds)}</span>
                    </div>
                    <div className="h-3 rounded-full overflow-hidden" style={{ background: "var(--surface-2)" }}>
                      <div
                        className="h-full rounded-full"
                        style={{ width: `${(sys.total_seconds / maxPt) * 100}%`, background: "var(--accent-primary)" }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
