import { Link } from "react-router";
import { BarChart3, Gamepad2, Cpu, Clock, Activity, MessageCircle, Trophy, Settings, MonitorSmartphone } from "lucide-react";
import { useEffect, useState } from "react";
import { getDashboardData } from "@/lib/api/dashboard";
import type { Session, TopGame } from "@/lib/types/api";

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
    <div className="flex-1 overflow-y-auto">
      {/* Hero */}
      <section className="relative flex flex-col items-center justify-center text-center px-6 py-16 overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-b from-purple-900/20 via-transparent to-transparent pointer-events-none" />
        <h1 className="text-5xl md:text-6xl font-black tracking-tight mb-4 relative" style={{ color: "var(--text-primary)" }}>
          <span className="bg-gradient-to-r from-red-500 via-purple-500 to-blue-500 bg-clip-text text-transparent">
            PiStation
          </span>
        </h1>
        <p className="text-lg md:text-xl max-w-2xl mb-8 relative" style={{ color: "var(--text-muted)" }}>
          Your retro gaming command center. Track sessions, analyze playtime, and monitor your PiStation devices — all in one place.
        </p>
        <div className="flex gap-3 relative">
          <Link to="/dashboard" className="px-6 py-3 rounded-xl bg-gradient-to-r from-red-600 to-purple-600 text-white font-semibold hover:scale-105 transition-transform shadow-lg shadow-purple-500/25">
            View Dashboard
          </Link>
          <Link to="/sessions" className="px-6 py-3 rounded-xl font-semibold hover:opacity-80 transition-colors" style={{ background: "var(--surface-2)", color: "var(--text-primary)", border: "1px solid var(--border-soft)" }}>
            View Sessions
          </Link>
        </div>
      </section>

      {/* Now Playing */}
      {activeSession && (
        <section className="px-6 pb-6 max-w-6xl mx-auto">
          <div className="p-5 rounded-xl relative overflow-hidden" style={{ background: "linear-gradient(135deg, rgba(139,92,246,0.15), rgba(239,68,68,0.1))", border: "1px solid rgba(139,92,246,0.3)" }}>
            <div className="flex items-center gap-2 mb-2">
              <Activity size={16} className="text-green-400 animate-pulse" />
              <span className="text-xs font-bold uppercase tracking-wider text-green-400">Now Playing</span>
            </div>
            <p className="text-lg font-bold" style={{ color: "var(--text-primary)" }}>{extractTitle(activeSession.rom_path)}</p>
            <p className="text-sm" style={{ color: "var(--text-muted)" }}>
              {activeSession.system_name?.toUpperCase()} · on {activeSession.pi_hostname} · started {formatTimeAgo(activeSession.started_at)}
            </p>
          </div>
        </section>
      )}

      {/* Quick Stats */}
      {!loading && (
        <section className="px-6 pb-8 max-w-6xl mx-auto">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {[
              { icon: <Gamepad2 size={18} />, label: "Top Games", value: String(topGames.length) },
              { icon: <Clock size={18} />, label: "Total Playtime", value: formatPlaytime(totalPlaytime) },
              { icon: <Activity size={18} />, label: "Recent Sessions", value: String(totalSessions) },
              { icon: <Trophy size={18} />, label: "Status", value: activeSession ? "Playing" : "Idle" },
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
        </section>
      )}

      {/* Recent Sessions */}
      {recentSessions.length > 0 && (
        <section className="px-6 pb-8 max-w-6xl mx-auto">
          <h2 className="text-xl font-bold mb-4 flex items-center gap-2" style={{ color: "var(--text-primary)" }}>
            <Clock size={20} style={{ color: "var(--accent-primary)" }} /> Recent Sessions
          </h2>
          <div className="space-y-2">
            {recentSessions.slice(0, 5).map((s) => (
              <div key={s.id} className="flex items-center gap-4 p-3 rounded-xl" style={{ background: "var(--surface-1)", border: "1px solid var(--border-soft)" }}>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-semibold truncate" style={{ color: "var(--text-primary)" }}>{extractTitle(s.rom_path)}</p>
                  <p className="text-xs" style={{ color: "var(--text-muted)" }}>
                    {s.system_name?.toUpperCase()} · {s.pi_hostname} · {formatTimeAgo(s.started_at)}
                  </p>
                </div>
                <span className="text-xs font-mono shrink-0" style={{ color: "var(--accent-primary)" }}>
                  {s.duration_seconds ? formatPlaytime(s.duration_seconds) : "—"}
                </span>
              </div>
            ))}
          </div>
          <Link to="/sessions" className="block text-center text-sm mt-3 hover:underline" style={{ color: "var(--accent-primary)" }}>
            View all sessions →
          </Link>
        </section>
      )}

      {/* Navigation Grid */}
      <section className="px-6 pb-16 max-w-6xl mx-auto">
        <h2 className="text-xl font-bold mb-6 text-center" style={{ color: "var(--text-primary)" }}>Explore</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {navCards.map((f) => (
            <Link key={f.title} to={f.to} className="group p-5 rounded-xl transition-all duration-300" style={{ background: "var(--surface-1)", border: "1px solid var(--border-soft)" }}>
              <div className="mb-3 group-hover:scale-110 transition-transform" style={{ color: "var(--accent-primary)" }}>
                {f.icon}
              </div>
              <h3 className="font-semibold mb-1" style={{ color: "var(--text-primary)" }}>{f.title}</h3>
              <p className="text-sm leading-relaxed" style={{ color: "var(--text-muted)" }}>{f.desc}</p>
            </Link>
          ))}
        </div>
      </section>

      {/* Footer */}
      <footer className="text-center py-6 text-xs" style={{ color: "var(--text-muted)", borderTop: "1px solid var(--border-soft)" }}>
        PiStation — Retro Gaming Dashboard · Built with React, FastAPI, and NVIDIA NIM
      </footer>
    </div>
  );
}
