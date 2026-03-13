import { useEffect, useState } from "react";
import { BarChart3, Clock, Gamepad2, Cpu } from "lucide-react";
import { getGames, type GameRow } from "@/lib/api/games";
import { getSystemStats } from "@/lib/api/systems";
import type { SystemStats } from "@/lib/types/api";

function formatPlaytime(seconds: number): string {
  if (!seconds || seconds <= 0) return "0m";
  if (seconds < 60) return `${seconds}s`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m`;
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  return `${h}h ${m}m`;
}

export default function StatsPage() {
  const [games, setGames] = useState<GameRow[]>([]);
  const [systems, setSystems] = useState<SystemStats[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([getGames(100), getSystemStats(30)])
      .then(([g, s]) => { setGames(g); setSystems(s); })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const totalPlaytime = games.reduce((acc, g) => acc + g.total_seconds, 0);
  const totalSessions = games.reduce((acc, g) => acc + g.session_count, 0);

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="animate-pulse text-sm" style={{ color: "var(--text-muted)" }}>Loading statistics...</div>
      </div>
    );
  }

  return (
    <div className="flex-1 w-full max-w-5xl mx-auto p-4 md:p-8 overflow-y-auto">
      <header className="mb-8">
        <h1 className="text-3xl font-bold flex items-center gap-3" style={{ color: "var(--text-primary)" }}>
          <BarChart3 size={28} style={{ color: "var(--accent-primary)" }} /> Statistics
        </h1>
      </header>

      {/* Summary Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-8">
        {[
          { icon: <Gamepad2 size={20} />, label: "Games Tracked", value: String(games.length) },
          { icon: <Clock size={20} />, label: "Total Playtime", value: formatPlaytime(totalPlaytime) },
          { icon: <BarChart3 size={20} />, label: "Total Sessions", value: String(totalSessions) },
          { icon: <Cpu size={20} />, label: "Platforms", value: String(systems.length) },
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
            {systems.length === 0 && <p className="text-xs" style={{ color: "var(--text-muted)" }}>No data yet</p>}
          </div>
        </div>

        {/* Top Games */}
        <div className="rounded-xl p-5" style={{ background: "var(--surface-1)", border: "1px solid var(--border-soft)" }}>
          <h2 className="text-sm font-bold uppercase tracking-wider mb-4" style={{ color: "var(--text-muted)" }}>Most Played Games</h2>
          <div className="space-y-2">
            {games.slice(0, 10).map((game, i) => (
              <div key={game.rom_path} className="flex items-center gap-3 p-2 rounded-lg" style={{ background: "var(--surface-2)" }}>
                <span className="text-xs font-bold w-5 text-center" style={{ color: "var(--text-muted)" }}>#{i + 1}</span>
                <div className="flex-1 min-w-0">
                  <p className="text-xs font-medium truncate" style={{ color: "var(--text-primary)" }}>{game.title}</p>
                  <p className="text-[10px]" style={{ color: "var(--text-muted)" }}>{game.system_name?.toUpperCase()} · {game.session_count} sessions</p>
                </div>
                <span className="text-xs font-mono" style={{ color: "var(--accent-primary)" }}>{formatPlaytime(game.total_seconds)}</span>
              </div>
            ))}
            {games.length === 0 && <p className="text-xs" style={{ color: "var(--text-muted)" }}>Play some games first!</p>}
          </div>
        </div>
      </div>
    </div>
  );
}
