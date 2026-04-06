import { Link } from "react-router";
import { BarChart3, Gamepad2, Cpu, Clock, Activity, MessageCircle, Trophy, Settings, MonitorSmartphone } from "lucide-react";
import { useEffect, useState } from "react";
import { getDashboardData } from "@/lib/api/dashboard";
import type { Session, TopGame } from "@/lib/types/api";
import { RetroPiece } from "@/components/RetroPiece";

function formatPlaytime(seconds: number): string {
  if (!seconds || seconds <= 0) return "0m";
  if (seconds < 60) return `${seconds}s`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m`;
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  return `${h}h ${m}m`;
}

function formatTimeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

function extractTitle(romPath: string): string {
  const filename = romPath.split("/").pop() || romPath;
  return filename.replace(/\.(zip|7z|nes|sfc|smc|gba|gb|gbc|bin|cue|iso|md|gen|dat)$/i, "").replace(/\s*\([^)]*\)/g, "").trim();
}

const navCards = [
  { icon: <BarChart3 size={28} />, title: "Dashboard", desc: "Full analytics and playtime breakdowns", to: "/dashboard" },
  { icon: <Clock size={28} />, title: "Sessions", desc: "Live and historical gaming sessions", to: "/sessions" },
  { icon: <Gamepad2 size={28} />, title: "Games", desc: "Your game library with play statistics", to: "/games" },
  { icon: <Cpu size={28} />, title: "Systems", desc: "Platform analytics and breakdowns", to: "/systems" },
  { icon: <MonitorSmartphone size={28} />, title: "Devices", desc: "Monitor your PiStation devices", to: "/devices" },
  { icon: <MessageCircle size={28} />, title: "AI Assistant", desc: "Ask questions about your gaming stats with voice support", to: "/chat" },
  { icon: <Trophy size={28} />, title: "Achievements", desc: "Track your gaming milestones", to: "/achievements" },
  { icon: <Settings size={28} />, title: "Settings", desc: "Theme, display, and preferences", to: "/settings" },
];

export default function Home() {
  const [activeSession, setActiveSession] = useState<Session | null>(null);
  const [recentSessions, setRecentSessions] = useState<Session[]>([]);
  const [topGames, setTopGames] = useState<TopGame[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getDashboardData()
      .then((data) => {
        setActiveSession(data.active_session);
        setRecentSessions(data.recent_sessions);
        setTopGames(data.top_games);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const totalPlaytime = topGames.reduce((acc, g) => acc + (g.total_seconds || 0), 0);
  const totalSessions = recentSessions.length;

  return (
    <div className="retro-page-shell flex-1 overflow-y-auto">
      <section className="grid gap-6 lg:grid-cols-[minmax(0,1.35fr)_minmax(320px,0.8fr)]">
        <div className="retro-panel retro-panel--hero rounded-[1.8rem] p-7 md:p-10">
          <span className="retro-kicker mb-6">
            <RetroPiece size="sm" />
            Retro Command Center
          </span>
          <div className="flex flex-col gap-6 md:flex-row md:items-center md:justify-between">
            <div className="max-w-3xl">
              <h1 className="retro-heading mb-4">
                <span className="retro-title-gradient">PiStation</span>
              </h1>
              <p className="retro-subtitle mb-8">
                A neon arcade dashboard for your retro world. Track live sessions, scan playtime trends, monitor devices, and chat with your AI copilot in one cabinet.
              </p>
              <div className="flex flex-wrap gap-3">
                <Link to="/dashboard" className="retro-button">
                  <RetroPiece size="sm" />
                  View Dashboard
                </Link>
                <Link to="/sessions" className="retro-button retro-button--secondary">
                  View Sessions
                </Link>
              </div>
            </div>
            <div className="retro-piece-frame self-start md:self-center">
              <RetroPiece size="lg" />
            </div>
          </div>
        </div>

        <aside className="retro-panel retro-panel--highlight rounded-[1.6rem] p-6 flex flex-col gap-4">
          <div className="retro-section-title mb-0">
            <Activity size={18} />
            Live Signal
          </div>
          {loading ? (
            <p className="text-sm animate-pulse" style={{ color: "var(--text-muted)" }}>
              Syncing arcade telemetry...
            </p>
          ) : activeSession ? (
            <>
              <span className="retro-chip retro-chip--success">
                <Activity size={12} />
                Now Playing
              </span>
              <div>
                <p className="text-xl font-bold mb-1" style={{ color: "var(--text-primary)" }}>{extractTitle(activeSession.rom_path)}</p>
                <p className="text-sm" style={{ color: "var(--text-muted)" }}>
                  {activeSession.system_name?.toUpperCase()} · {activeSession.pi_hostname}
                </p>
                <p className="text-xs mt-2" style={{ color: "var(--text-muted)" }}>
                  Started {formatTimeAgo(activeSession.started_at)}
                </p>
              </div>
            </>
          ) : (
            <>
              <span className="retro-chip">Standby</span>
              <p className="text-xl font-bold" style={{ color: "var(--text-primary)" }}>No active session</p>
              <p className="text-sm" style={{ color: "var(--text-muted)" }}>
                Fire up a game and PiStation will beam it in here.
              </p>
            </>
          )}
          <div className="grid grid-cols-2 gap-3 pt-2">
            {[
              { label: "Tracked Games", value: String(topGames.length || 0) },
              { label: "Recent Runs", value: String(totalSessions) },
              { label: "Total Time", value: formatPlaytime(totalPlaytime) },
              { label: "Status", value: activeSession ? "Live" : "Idle" },
            ].map((item) => (
              <div key={item.label} className="retro-stat-card">
                <p className="text-[0.58rem] uppercase tracking-[0.16em]" style={{ color: "var(--text-muted)" }}>{item.label}</p>
                <p className="text-lg font-bold mt-2" style={{ color: "var(--text-primary)" }}>{item.value}</p>
              </div>
            ))}
          </div>
        </aside>
      </section>

      {!loading && (
        <section className="mt-6">
          <div className="retro-section-title">
            <Gamepad2 size={18} />
            Arcade Snapshot
          </div>
          <div className="retro-stat-grid grid grid-cols-2 md:grid-cols-4">
            {[
              { icon: <Gamepad2 size={18} />, label: "Top Games", value: String(topGames.length) },
              { icon: <Clock size={18} />, label: "Total Playtime", value: formatPlaytime(totalPlaytime) },
              { icon: <Activity size={18} />, label: "Recent Sessions", value: String(totalSessions) },
              { icon: <Trophy size={18} />, label: "Cabinet", value: activeSession ? "Live" : "Idle" },
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
        </section>
      )}

      {recentSessions.length > 0 && (
        <section className="mt-8">
          <div className="retro-panel rounded-[1.6rem] p-6">
            <div className="flex items-center justify-between gap-4 mb-5">
              <div className="retro-section-title mb-0">
                <Clock size={18} />
                Recent Sessions
              </div>
              <Link to="/sessions" className="retro-button retro-button--ghost px-4 py-2 min-h-0 text-[0.56rem]">
                View All
              </Link>
            </div>
            <div className="space-y-3">
              {recentSessions.slice(0, 5).map((s) => (
                <div key={s.id} className="retro-list-item p-4 flex items-center gap-4">
                  <div className="retro-piece-frame" style={{ minWidth: "3.8rem", minHeight: "3.8rem", padding: "0.75rem" }}>
                    <RetroPiece size="sm" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-semibold truncate" style={{ color: "var(--text-primary)" }}>{extractTitle(s.rom_path)}</p>
                    <p className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>
                      {s.system_name?.toUpperCase()} · {s.pi_hostname} · {formatTimeAgo(s.started_at)}
                    </p>
                  </div>
                  <span className="text-xs font-mono shrink-0" style={{ color: "var(--accent-secondary)" }}>
                    {s.duration_seconds ? formatPlaytime(s.duration_seconds) : "—"}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </section>
      )}

      <section className="mt-8 pb-10">
        <div className="retro-section-title">
          <Cpu size={18} />
          Explore Cabinets
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {navCards.map((feature) => (
            <Link key={feature.title} to={feature.to} className="retro-card-link">
              <div className="mb-4 flex items-center justify-between">
                <div className="retro-piece-frame" style={{ minWidth: "3.4rem", minHeight: "3.4rem", padding: "0.75rem" }}>
                  {feature.icon}
                </div>
                <RetroPiece size="sm" />
              </div>
              <h3 className="font-semibold mb-2 uppercase text-sm tracking-[0.12em]" style={{ color: "var(--text-primary)" }}>{feature.title}</h3>
              <p className="text-sm leading-relaxed" style={{ color: "var(--text-muted)" }}>{feature.desc}</p>
            </Link>
          ))}
        </div>
      </section>

      <footer className="text-center py-6 text-[0.62rem] uppercase tracking-[0.18em]" style={{ color: "var(--text-muted)", borderTop: "1px solid var(--border-soft)" }}>
        PiStation Retro Dashboard · React · FastAPI · NVIDIA NIM
      </footer>
    </div>
  );
}
