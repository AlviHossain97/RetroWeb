import { useEffect, useState } from "react";
import { Cpu, Clock, Gamepad2 } from "lucide-react";
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

const SYSTEM_COLORS: Record<string, string> = {
  nes: "#e60012",
  snes: "#7b43a1",
  gb: "#306230",
  gbc: "#663399",
  gba: "#5a2d82",
  n64: "#008000",
  genesis: "#0060a8",
  megadrive: "#0060a8",
  psx: "#003087",
  pce: "#ff6600",
  zmachine: "#00cc00",
};

export default function Systems() {
  const [systems, setSystems] = useState<SystemStats[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getSystemStats(30)
      .then(setSystems)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const totalPlaytime = systems.reduce((acc, s) => acc + s.total_seconds, 0);
  const totalSessions = systems.reduce((acc, s) => acc + s.session_count, 0);

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="animate-pulse text-sm" style={{ color: "var(--text-muted)" }}>Loading systems...</div>
      </div>
    );
  }

  return (
    <div className="flex-1 w-full max-w-5xl mx-auto p-4 md:p-8 overflow-y-auto">
      <header className="mb-8">
        <h1 className="text-3xl font-bold flex items-center gap-3" style={{ color: "var(--text-primary)" }}>
          <Cpu size={28} style={{ color: "var(--accent-primary)" }} /> Systems
        </h1>
        <p className="text-sm mt-1" style={{ color: "var(--text-muted)" }}>
          {systems.length} platforms · {totalSessions} sessions · {formatPlaytime(totalPlaytime)} total playtime
        </p>
      </header>

      {/* System Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-8">
        {systems.map((sys) => {
          const color = SYSTEM_COLORS[sys.system_name] || "var(--accent-primary)";
          const pctOfTotal = totalPlaytime > 0 ? ((sys.total_seconds / totalPlaytime) * 100).toFixed(1) : "0";
          return (
            <div key={sys.system_name} className="p-5 rounded-xl" style={{ background: "var(--surface-1)", border: "1px solid var(--border-soft)" }}>
              <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 rounded-lg flex items-center justify-center" style={{ background: `${color}22` }}>
                  <Cpu size={20} style={{ color }} />
                </div>
                <div>
                  <p className="text-lg font-bold" style={{ color: "var(--text-primary)" }}>{sys.system_name.toUpperCase()}</p>
                  <p className="text-xs" style={{ color: "var(--text-muted)" }}>{pctOfTotal}% of total playtime</p>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4 mb-3">
                <div>
                  <div className="flex items-center gap-1 mb-1" style={{ color: "var(--text-muted)" }}>
                    <Clock size={12} />
                    <span className="text-[10px] uppercase tracking-wider font-bold">Playtime</span>
                  </div>
                  <p className="text-xl font-bold" style={{ color: "var(--text-primary)" }}>{formatPlaytime(sys.total_seconds)}</p>
                </div>
                <div>
                  <div className="flex items-center gap-1 mb-1" style={{ color: "var(--text-muted)" }}>
                    <Gamepad2 size={12} />
                    <span className="text-[10px] uppercase tracking-wider font-bold">Sessions</span>
                  </div>
                  <p className="text-xl font-bold" style={{ color: "var(--text-primary)" }}>{sys.session_count}</p>
                </div>
              </div>
              <div className="h-2 rounded-full overflow-hidden" style={{ background: "var(--surface-2)" }}>
                <div className="h-full rounded-full transition-all duration-500" style={{ width: `${Number(pctOfTotal)}%`, background: color }} />
              </div>
            </div>
          );
        })}
      </div>

      {systems.length === 0 && (
        <div className="text-center py-12">
          <Cpu size={48} className="mx-auto mb-4" style={{ color: "var(--text-muted)" }} />
          <p className="text-sm" style={{ color: "var(--text-muted)" }}>No system data yet. Play some games on your PiStation!</p>
        </div>
      )}
    </div>
  );
}
