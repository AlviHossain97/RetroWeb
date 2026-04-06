import { useEffect, useState, useCallback } from "react";
import { Activity, Clock, Gamepad2, Cpu, Maximize, Minimize } from "lucide-react";
import { getDashboardData } from "@/lib/api/dashboard";
import { getSystemStats } from "@/lib/api/systems";
import type { Session, TopGame, SystemStats } from "@/lib/types/api";
import { useGamepadNavigation } from "@/hooks/useGamepadNavigation";
import { RetroPiece } from "@/components/RetroPiece";
import SynthwaveBackground from "@/components/SynthwaveBackground";

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

  // Lite mode for low-power devices (Pi)
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.get("lite") === "1") {
      document.documentElement.classList.add("lite-mode");
    }
    return () => document.documentElement.classList.remove("lite-mode");
  }, []);

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
      className="fixed inset-0 flex flex-col overflow-hidden relative"
      style={{ background: "linear-gradient(180deg, rgba(13,13,16,0.72), rgba(13,13,16,0.88))", color: "var(--text-primary)" }}
    >
      <SynthwaveBackground />

      {/* Top Bar */}
      <div className="retro-chat-header relative z-10 flex items-center justify-between px-8 py-5" style={{ borderBottom: "3px solid rgba(204, 0, 0, 0.18)" }}>
        <div className="flex items-center gap-4">
          <div className="retro-piece-frame" style={{ minWidth: "4rem", minHeight: "4rem", padding: "0.75rem" }}>
            <RetroPiece size="lg" />
          </div>
          <div>
            <h1 className="retro-heading text-[2rem]">
              <span className="retro-title-gradient">PiStation</span>
            </h1>
            <p className="text-xs uppercase tracking-[0.18em]" style={{ color: "var(--text-muted)" }}>Kiosk Broadcast</p>
          </div>
        </div>
        <div className="flex items-center gap-6">
          <span className="text-2xl font-mono tabular-nums" style={{ color: "var(--accent-secondary)" }}>
            {formatTime(time)}
          </span>
          <button
            onClick={toggleFullscreen}
            className="retro-button retro-button--ghost retro-icon-button min-h-0 text-[0.56rem]"
          >
            {isFullscreen ? <Minimize size={20} /> : <Maximize size={20} />}
          </button>
        </div>
      </div>

      {/* Main Content */}
      <div className="relative z-10 flex-1 grid grid-cols-3 gap-6 p-8 overflow-hidden">
        {/* Left Column — Now Playing + Stats */}
        <div className="flex flex-col gap-6">
          {/* Now Playing */}
          {activeSession ? (
            <div
              className="retro-panel retro-panel--highlight p-6 rounded-[1.6rem]"
            >
              <div className="flex items-center gap-2 mb-3">
                <Activity size={20} className="animate-pulse" style={{ color: "var(--success)" }} />
                <span className="text-sm font-bold uppercase tracking-wider" style={{ color: "var(--success)" }}>Now Playing</span>
              </div>
              <p className="text-2xl font-bold mb-1">{extractTitle(activeSession.rom_path)}</p>
              <p className="text-lg" style={{ color: "var(--text-muted)" }}>
                {activeSession.system_name?.toUpperCase()} · {activeSession.pi_hostname}
              </p>
            </div>
          ) : (
            <div className="retro-panel p-6 rounded-[1.6rem]">
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
              <div key={s.label} className="retro-stat-card">
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
          <h2 className="retro-section-title text-lg mb-4" style={{ color: "var(--accent-secondary)" }}>
            Top Games
          </h2>
          <div className="flex-1 space-y-3 overflow-y-auto">
            {topGames.map((game, i) => (
              <div key={game.rom_path} className="retro-list-item flex items-center gap-4 p-4">
                <span className="text-lg font-bold w-8 text-center" style={{ color: "var(--accent-secondary)" }}>
                  #{i + 1}
                </span>
                <div className="flex-1 min-w-0">
                  <p className="text-lg font-semibold truncate">{extractTitle(game.rom_path)}</p>
                  <p className="text-sm" style={{ color: "var(--text-muted)" }}>
                    {game.system_name?.toUpperCase()} · {game.session_count} sessions
                  </p>
                </div>
                <span className="text-lg font-mono" style={{ color: "var(--accent-secondary)" }}>
                  {formatPlaytime(game.total_seconds)}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Right Column — Recent Sessions + Systems */}
        <div className="flex flex-col gap-6">
          <div className="flex-1 flex flex-col">
            <h2 className="retro-section-title text-lg mb-4" style={{ color: "var(--accent-secondary)" }}>
              Recent Sessions
            </h2>
            <div className="flex-1 space-y-2 overflow-y-auto">
              {recentSessions.slice(0, 6).map((s) => (
                <div key={s.id} className="retro-list-item p-3">
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
            <h2 className="retro-section-title text-lg mb-3" style={{ color: "var(--accent-secondary)" }}>
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
                    <div className="retro-meter h-3">
                      <div
                        className="retro-meter__fill"
                        style={{ width: `${(sys.total_seconds / maxPt) * 100}%` }}
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
