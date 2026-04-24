import { useEffect, useState, useCallback } from "react";
import { Shield, Activity, Database, Server, RefreshCcw, CheckCircle, XCircle } from "lucide-react";
import { request } from "@/lib/api/client";

interface ServiceStatus {
  name: string;
  url: string;
  status: "online" | "offline" | "checking";
}

export default function Admin() {
  const [services, setServices] = useState<ServiceStatus[]>([
    { name: "PiStation API", url: "/api/pistation/health", status: "checking" },
    { name: "NVIDIA (LLM)", url: "/api/nvidia/v1/models", status: "checking" },
    { name: "Voice Gateway", url: "/api/pistation/ai/voice/health", status: "checking" },
  ]);
  const [dbStats, setDbStats] = useState<Record<string, number>>({});
  const [loading, setLoading] = useState(true);

  const checkServices = useCallback(async () => {
    const updated = await Promise.all(
      services.map(async (svc) => {
        try {
          const res = await fetch(svc.url, { signal: AbortSignal.timeout(3000) });
          return { ...svc, status: res.ok ? "online" as const : "offline" as const };
        } catch {
          return { ...svc, status: "offline" as const };
        }
      })
    );
    setServices(updated);
  }, []);

  const fetchStats = useCallback(async () => {
    try {
      const games = await request<unknown[]>("/games?limit=1000");
      const systems = await request<unknown[]>("/systems?limit=100");
      const achievements = await request<unknown[]>("/achievements");
      const devices = await request<unknown[]>("/devices?limit=100");
      setDbStats({
        games: games.length,
        systems: systems.length,
        achievements: achievements.length,
        devices: devices.length,
      });
    } catch {
      // API might be down
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    checkServices();
    fetchStats();
  }, [checkServices, fetchStats]);

  const onlineCount = services.filter((s) => s.status === "online").length;

  return (
    <div className="flex-1 w-full max-w-5xl mx-auto p-4 md:p-8 overflow-y-auto">
      <header className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-3" style={{ color: "var(--text-primary)" }}>
            <Shield size={28} style={{ color: "var(--accent-primary)" }} /> Admin
          </h1>
          <p className="text-sm mt-1" style={{ color: "var(--text-muted)" }}>
            System diagnostics and service health
          </p>
        </div>
        <button
          onClick={() => { checkServices(); fetchStats(); }}
          className="p-2 rounded-lg hover:opacity-80"
          style={{ background: "var(--surface-2)" }}
        >
          <RefreshCcw size={16} style={{ color: "var(--text-muted)" }} />
        </button>
      </header>

      {/* Service Health */}
      <section className="mb-8">
        <h2 className="text-sm font-bold uppercase tracking-wider mb-4 flex items-center gap-2" style={{ color: "var(--text-muted)" }}>
          <Activity size={14} /> Service Health ({onlineCount}/{services.length} online)
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {services.map((svc) => (
            <div key={svc.name} className="flex items-center gap-4 p-4 rounded-xl" style={{ background: "var(--surface-1)", border: "1px solid var(--border-soft)" }}>
              {svc.status === "online" ? (
                <CheckCircle size={20} className="text-green-400 shrink-0" />
              ) : svc.status === "offline" ? (
                <XCircle size={20} className="text-red-400 shrink-0" />
              ) : (
                <Activity size={20} className="animate-pulse shrink-0" style={{ color: "var(--text-muted)" }} />
              )}
              <div className="flex-1">
                <p className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>{svc.name}</p>
                <p className="text-xs font-mono" style={{ color: "var(--text-muted)" }}>{svc.url}</p>
              </div>
              <span
                className="text-[10px] font-bold uppercase px-2 py-0.5 rounded-full"
                style={{
                  background: svc.status === "online" ? "rgba(34,197,94,0.15)" : svc.status === "offline" ? "rgba(239,68,68,0.15)" : "var(--surface-2)",
                  color: svc.status === "online" ? "#22c55e" : svc.status === "offline" ? "#ef4444" : "var(--text-muted)",
                }}
              >
                {svc.status}
              </span>
            </div>
          ))}
        </div>
      </section>

      {/* Database Stats */}
      <section className="mb-8">
        <h2 className="text-sm font-bold uppercase tracking-wider mb-4 flex items-center gap-2" style={{ color: "var(--text-muted)" }}>
          <Database size={14} /> Database Stats
        </h2>
        {loading ? (
          <div className="animate-pulse text-sm" style={{ color: "var(--text-muted)" }}>Loading...</div>
        ) : (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {[
              { label: "Games Tracked", value: dbStats.games ?? 0, icon: <Server size={18} /> },
              { label: "Systems", value: dbStats.systems ?? 0, icon: <Database size={18} /> },
              { label: "Achievements", value: dbStats.achievements ?? 0, icon: <Activity size={18} /> },
              { label: "Devices", value: dbStats.devices ?? 0, icon: <Shield size={18} /> },
            ].map((stat) => (
              <div key={stat.label} className="p-4 rounded-xl" style={{ background: "var(--surface-1)", border: "1px solid var(--border-soft)" }}>
                <div className="flex items-center gap-2 mb-2" style={{ color: "var(--text-muted)" }}>
                  {stat.icon}
                  <span className="text-[10px] uppercase tracking-wider font-bold">{stat.label}</span>
                </div>
                <p className="text-2xl font-bold" style={{ color: "var(--text-primary)" }}>{stat.value}</p>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Quick Links */}
      <section>
        <h2 className="text-sm font-bold uppercase tracking-wider mb-4" style={{ color: "var(--text-muted)" }}>
          Backend Endpoints
        </h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
          {["/health", "/games", "/systems", "/devices", "/achievements", "/stats/recent", "/stats/active", "/ai/context", "/ai/voice/health"].map((ep) => (
            <a
              key={ep}
              href={`/api/pistation${ep}`}
              target="_blank"
              rel="noopener"
              className="text-xs font-mono p-2 rounded-lg text-center hover:opacity-80 transition-opacity"
              style={{ background: "var(--surface-2)", color: "var(--accent-primary)" }}
            >
              {ep}
            </a>
          ))}
        </div>
      </section>
    </div>
  );
}
