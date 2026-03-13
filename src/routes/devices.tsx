import { useEffect, useState } from "react";
import { MonitorSmartphone, Wifi, WifiOff, Clock, RefreshCcw } from "lucide-react";
import { getDevices } from "@/lib/api/devices";
import type { Device } from "@/lib/types/api";

function formatTimeAgo(dateStr: string | null): string {
  if (!dateStr) return "never";
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

export default function Devices() {
  const [devices, setDevices] = useState<Device[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchDevices = () => {
    setLoading(true);
    getDevices(50)
      .then(setDevices)
      .catch(() => {})
      .finally(() => setLoading(false));
  };

  useEffect(() => { fetchDevices(); }, []);

  return (
    <div className="flex-1 w-full max-w-5xl mx-auto p-4 md:p-8 overflow-y-auto">
      <header className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-3" style={{ color: "var(--text-primary)" }}>
            <MonitorSmartphone size={28} style={{ color: "var(--accent-primary)" }} /> Devices
          </h1>
          <p className="text-sm mt-1" style={{ color: "var(--text-muted)" }}>
            {devices.length} registered device{devices.length !== 1 ? "s" : ""}
          </p>
        </div>
        <button onClick={fetchDevices} className="p-2 rounded-lg hover:opacity-80 transition-opacity" style={{ background: "var(--surface-2)" }}>
          <RefreshCcw size={16} style={{ color: "var(--text-muted)" }} />
        </button>
      </header>

      {loading ? (
        <div className="animate-pulse text-sm text-center py-12" style={{ color: "var(--text-muted)" }}>Loading devices...</div>
      ) : devices.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {devices.map((dev) => (
            <div key={dev.id} className="p-5 rounded-xl" style={{ background: "var(--surface-1)", border: "1px solid var(--border-soft)" }}>
              <div className="flex items-center gap-3 mb-3">
                {dev.status === "online" ? (
                  <Wifi size={18} className="text-green-400" />
                ) : (
                  <WifiOff size={18} style={{ color: "var(--text-muted)" }} />
                )}
                <div className="flex-1">
                  <p className="font-semibold" style={{ color: "var(--text-primary)" }}>{dev.display_name || dev.hostname}</p>
                  <p className="text-xs" style={{ color: "var(--text-muted)" }}>{dev.hostname}</p>
                </div>
                <span
                  className="text-[10px] font-bold uppercase px-2 py-0.5 rounded-full"
                  style={{
                    background: dev.status === "online" ? "rgba(34,197,94,0.15)" : "var(--surface-2)",
                    color: dev.status === "online" ? "#22c55e" : "var(--text-muted)",
                  }}
                >
                  {dev.status}
                </span>
              </div>
              <div className="grid grid-cols-2 gap-3 text-xs">
                <div>
                  <span style={{ color: "var(--text-muted)" }}>IP Address</span>
                  <p className="font-mono" style={{ color: "var(--text-primary)" }}>{dev.ip_address || "—"}</p>
                </div>
                <div>
                  <span style={{ color: "var(--text-muted)" }}>Last Seen</span>
                  <p style={{ color: "var(--text-primary)" }}>
                    <Clock size={10} className="inline mr-1" />
                    {formatTimeAgo(dev.last_seen_at)}
                  </p>
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="text-center py-12">
          <MonitorSmartphone size={48} className="mx-auto mb-4" style={{ color: "var(--text-muted)" }} />
          <p className="text-sm" style={{ color: "var(--text-muted)" }}>No devices registered yet</p>
          <p className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>Devices will appear here when they send heartbeats to the PiStation API</p>
        </div>
      )}
    </div>
  );
}
