import { useEffect, useState, useMemo } from "react";
import { Gamepad2, Search, TrendingUp } from "lucide-react";
import { getGames, type GameRow } from "@/lib/api/games";

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
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 30) return `${days}d ago`;
  return new Date(dateStr).toLocaleDateString();
}

export default function Games() {
  const [games, setGames] = useState<GameRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");

  useEffect(() => {
    getGames(100)
      .then(setGames)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const filtered = useMemo(() => {
    if (!search) return games;
    return games.filter((g) => g.title.toLowerCase().includes(search.toLowerCase()) || g.system_name?.toLowerCase().includes(search.toLowerCase()));
  }, [games, search]);

  const totalPlaytime = games.reduce((acc, g) => acc + g.total_seconds, 0);
  const totalSessions = games.reduce((acc, g) => acc + g.session_count, 0);

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="animate-pulse text-sm" style={{ color: "var(--text-muted)" }}>Loading games...</div>
      </div>
    );
  }

  return (
    <div className="flex-1 w-full max-w-6xl mx-auto p-4 md:p-8 overflow-y-auto">
      <header className="mb-6">
        <h1 className="text-3xl font-bold flex items-center gap-3" style={{ color: "var(--text-primary)" }}>
          <Gamepad2 size={28} style={{ color: "var(--accent-primary)" }} /> Games
        </h1>
        <p className="text-sm mt-1" style={{ color: "var(--text-muted)" }}>
          {games.length} games · {totalSessions} sessions · {formatPlaytime(totalPlaytime)} total playtime
        </p>
      </header>

      {/* Search */}
      <div className="relative mb-6">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2" size={16} style={{ color: "var(--text-muted)" }} />
        <input
          type="text"
          placeholder="Search games..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full pl-10 pr-4 py-2.5 rounded-xl text-sm focus:outline-none focus:ring-2"
          style={{ background: "var(--surface-2)", color: "var(--text-primary)", border: "1px solid var(--border-soft)" }}
        />
      </div>

      {/* Games Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {filtered.map((game, i) => (
          <div key={game.rom_path} className="p-4 rounded-xl" style={{ background: "var(--surface-1)", border: "1px solid var(--border-soft)" }}>
            <div className="flex items-start gap-3">
              <div className="w-10 h-10 rounded-lg flex items-center justify-center shrink-0" style={{ background: "var(--surface-2)" }}>
                <Gamepad2 size={20} style={{ color: "var(--accent-primary)" }} />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-semibold truncate" style={{ color: "var(--text-primary)" }}>{game.title}</p>
                <p className="text-xs" style={{ color: "var(--text-muted)" }}>{game.system_name?.toUpperCase() || "Unknown"}</p>
              </div>
              {i === 0 && (
                <TrendingUp size={14} className="shrink-0" style={{ color: "var(--accent-primary)" }} />
              )}
            </div>
            <div className="grid grid-cols-3 gap-2 mt-3">
              <div>
                <p className="text-[10px] uppercase tracking-wider" style={{ color: "var(--text-muted)" }}>Playtime</p>
                <p className="text-sm font-bold" style={{ color: "var(--text-primary)" }}>{formatPlaytime(game.total_seconds)}</p>
              </div>
              <div>
                <p className="text-[10px] uppercase tracking-wider" style={{ color: "var(--text-muted)" }}>Sessions</p>
                <p className="text-sm font-bold" style={{ color: "var(--text-primary)" }}>{game.session_count}</p>
              </div>
              <div>
                <p className="text-[10px] uppercase tracking-wider" style={{ color: "var(--text-muted)" }}>Last Played</p>
                <p className="text-sm font-bold" style={{ color: "var(--text-primary)" }}>{formatTimeAgo(game.last_played)}</p>
              </div>
            </div>
            {/* Playtime bar */}
            <div className="mt-3 h-1 rounded-full overflow-hidden" style={{ background: "var(--surface-2)" }}>
              <div className="h-full rounded-full" style={{ width: `${games[0] ? (game.total_seconds / games[0].total_seconds) * 100 : 0}%`, background: "var(--accent-primary)" }} />
            </div>
          </div>
        ))}
      </div>

      {filtered.length === 0 && (
        <div className="text-center py-12">
          <Gamepad2 size={48} className="mx-auto mb-4" style={{ color: "var(--text-muted)" }} />
          <p className="text-sm" style={{ color: "var(--text-muted)" }}>
            {search ? "No games match your search" : "No game data yet. Play some games on your PiStation!"}
          </p>
        </div>
      )}
    </div>
  );
}
