import { useEffect, useState, useMemo } from "react";
import { BarChart3, Clock, Gamepad2, Trophy, Calendar } from "lucide-react";
import { getAllGames, type Game } from "../lib/storage/db";
import { SYSTEMS } from "../data/systemBrowserData";

function formatTime(seconds: number): string {
  if (seconds < 60) return `${seconds}s`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m`;
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  return `${h}h ${m}m`;
}

export default function StatsPage() {
  const [games, setGames] = useState<Game[]>([]);

  useEffect(() => {
    getAllGames().then(setGames);
  }, []);

  const stats = useMemo(() => {
    const totalPlaytime = games.reduce((acc, g) => acc + (g.playtime ?? 0), 0);
    const playedGames = games.filter((g) => g.lastPlayed);
    const systemCounts: Record<string, { count: number; playtime: number }> = {};
    for (const g of games) {
      if (!systemCounts[g.system]) systemCounts[g.system] = { count: 0, playtime: 0 };
      systemCounts[g.system].count++;
      systemCounts[g.system].playtime += g.playtime ?? 0;
    }
    const systemStats = Object.entries(systemCounts)
      .map(([id, data]) => ({
        id,
        name: SYSTEMS.find((s) => s.id === id)?.name ?? id,
        ...data,
      }))
      .sort((a, b) => b.playtime - a.playtime);

    const topGames = [...games]
      .filter((g) => (g.playtime ?? 0) > 0)
      .sort((a, b) => (b.playtime ?? 0) - (a.playtime ?? 0))
      .slice(0, 10);

    const avgRating = games.filter((g) => g.rating).reduce((acc, g, _, arr) => acc + (g.rating ?? 0) / arr.length, 0);

    // Activity by day of week
    const dayActivity = [0, 0, 0, 0, 0, 0, 0]; // Sun-Sat
    for (const g of playedGames) {
      if (g.lastPlayed) dayActivity[new Date(g.lastPlayed).getDay()] += g.playtime ?? 0;
    }
    const dayNames = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
    const maxDayActivity = Math.max(...dayActivity, 1);

    // Heatmap: 52 weeks of daily play activity
    const heatmapWeeks: { date: string; count: number }[][] = [];
    const dayCounts = new Map<string, number>();
    for (const g of playedGames) {
      if (g.lastPlayed) {
        const dateStr = new Date(g.lastPlayed).toISOString().slice(0, 10);
        dayCounts.set(dateStr, (dayCounts.get(dateStr) ?? 0) + 1);
      }
    }
    const today = new Date();
    const startDay = new Date(today);
    startDay.setDate(startDay.getDate() - 52 * 7 - startDay.getDay());
    let week: { date: string; count: number }[] = [];
    for (let d = new Date(startDay); d <= today; d.setDate(d.getDate() + 1)) {
      const dateStr = d.toISOString().slice(0, 10);
      week.push({ date: dateStr, count: dayCounts.get(dateStr) ?? 0 });
      if (week.length === 7) { heatmapWeeks.push(week); week = []; }
    }
    if (week.length) heatmapWeeks.push(week);

    return { totalPlaytime, playedGames: playedGames.length, systemStats, topGames, avgRating, dayActivity, dayNames, maxDayActivity, heatmapWeeks };
  }, [games]);

  return (
    <div className="flex-1 w-full max-w-5xl mx-auto p-4 md:p-8">
      <header className="mb-8">
        <h1 className="text-3xl font-bold flex items-center gap-3" style={{ color: "var(--text-primary)" }}>
          <BarChart3 size={28} style={{ color: "var(--accent-primary)" }} /> Play Statistics
        </h1>
      </header>

      {/* Summary cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-8">
        {[
          { icon: <Gamepad2 size={20} />, label: "Total Games", value: games.length },
          { icon: <Clock size={20} />, label: "Total Playtime", value: formatTime(stats.totalPlaytime) },
          { icon: <Trophy size={20} />, label: "Games Played", value: stats.playedGames },
          { icon: <Calendar size={20} />, label: "Avg Rating", value: stats.avgRating ? `${stats.avgRating.toFixed(1)} ★` : "—" },
        ].map((card) => (
          <div key={card.label} className="p-4 rounded-xl" style={{ background: "var(--surface-1)", border: "1px solid var(--border-soft)" }}>
            <div className="flex items-center gap-2 mb-2" style={{ color: "var(--text-muted)" }}>{card.icon}<span className="text-[10px] uppercase tracking-wider font-bold">{card.label}</span></div>
            <p className="text-2xl font-bold" style={{ color: "var(--text-primary)" }}>{card.value}</p>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Playtime by system */}
        <div className="rounded-xl p-5" style={{ background: "var(--surface-1)", border: "1px solid var(--border-soft)" }}>
          <h2 className="text-sm font-bold uppercase tracking-wider mb-4" style={{ color: "var(--text-muted)" }}>Playtime by System</h2>
          <div className="space-y-3">
            {stats.systemStats.map((sys) => {
              const maxPt = stats.systemStats[0]?.playtime || 1;
              return (
                <div key={sys.id}>
                  <div className="flex justify-between text-xs mb-1">
                    <span style={{ color: "var(--text-primary)" }}>{sys.name}</span>
                    <span style={{ color: "var(--text-muted)" }}>{sys.count} games · {formatTime(sys.playtime)}</span>
                  </div>
                  <div className="h-2 rounded-full overflow-hidden" style={{ background: "var(--surface-2)" }}>
                    <div className="h-full rounded-full" style={{ width: `${(sys.playtime / maxPt) * 100}%`, background: "var(--accent-primary)" }} />
                  </div>
                </div>
              );
            })}
            {stats.systemStats.length === 0 && <p className="text-xs" style={{ color: "var(--text-muted)" }}>No data yet</p>}
          </div>
        </div>

        {/* Top games by playtime */}
        <div className="rounded-xl p-5" style={{ background: "var(--surface-1)", border: "1px solid var(--border-soft)" }}>
          <h2 className="text-sm font-bold uppercase tracking-wider mb-4" style={{ color: "var(--text-muted)" }}>Most Played Games</h2>
          <div className="space-y-2">
            {stats.topGames.map((game, i) => (
              <div key={game.id} className="flex items-center gap-3 p-2 rounded-lg" style={{ background: "var(--surface-2)" }}>
                <span className="text-xs font-bold w-5 text-center" style={{ color: "var(--text-muted)" }}>#{i + 1}</span>
                <div className="flex-1 min-w-0">
                  <p className="text-xs font-medium truncate" style={{ color: "var(--text-primary)" }}>{game.displayTitle || game.title}</p>
                  <p className="text-[10px]" style={{ color: "var(--text-muted)" }}>{SYSTEMS.find(s => s.id === game.system)?.name ?? game.system}</p>
                </div>
                <span className="text-xs font-mono" style={{ color: "var(--accent-primary)" }}>{formatTime(game.playtime ?? 0)}</span>
              </div>
            ))}
            {stats.topGames.length === 0 && <p className="text-xs" style={{ color: "var(--text-muted)" }}>Play some games first!</p>}
          </div>
        </div>

        {/* Activity by day of week */}
        <div className="rounded-xl p-5 lg:col-span-2" style={{ background: "var(--surface-1)", border: "1px solid var(--border-soft)" }}>
          <h2 className="text-sm font-bold uppercase tracking-wider mb-4" style={{ color: "var(--text-muted)" }}>Activity by Day</h2>
          <div className="flex items-end gap-2 h-32">
            {stats.dayActivity.map((val, i) => (
              <div key={i} className="flex-1 flex flex-col items-center gap-1">
                <div className="w-full rounded-t-md" style={{ height: `${(val / stats.maxDayActivity) * 100}%`, minHeight: 2, background: "var(--accent-primary)" }} />
                <span className="text-[10px]" style={{ color: "var(--text-muted)" }}>{stats.dayNames[i]}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Play Calendar Heatmap */}
        <div className="rounded-xl p-5 lg:col-span-2" style={{ background: "var(--surface-1)", border: "1px solid var(--border-soft)" }}>
          <h2 className="text-sm font-bold uppercase tracking-wider mb-4" style={{ color: "var(--text-muted)" }}>Play Calendar (Last 52 Weeks)</h2>
          <div className="overflow-x-auto">
            <div className="flex gap-[3px]" style={{ minWidth: 700 }}>
              {stats.heatmapWeeks.map((week, wi) => (
                <div key={wi} className="flex flex-col gap-[3px]">
                  {week.map((day, di) => (
                    <div
                      key={di}
                      className="w-[11px] h-[11px] rounded-[2px]"
                      title={day.date ? `${day.date}: ${day.count} session${day.count !== 1 ? "s" : ""}` : ""}
                      style={{
                        background: !day.date ? "transparent" : day.count === 0 ? "var(--surface-2)" : day.count <= 1 ? "#0e4429" : day.count <= 3 ? "#006d32" : day.count <= 6 ? "#26a641" : "#39d353",
                      }}
                    />
                  ))}
                </div>
              ))}
            </div>
            <div className="flex items-center gap-2 mt-3 text-[10px]" style={{ color: "var(--text-muted)" }}>
              <span>Less</span>
              {["var(--surface-2)", "#0e4429", "#006d32", "#26a641", "#39d353"].map((c, i) => (
                <div key={i} className="w-[11px] h-[11px] rounded-[2px]" style={{ background: c }} />
              ))}
              <span>More</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
