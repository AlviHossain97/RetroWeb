import { useState, useEffect, useCallback } from "react";
import { Bell, X } from "lucide-react";

export interface Notification {
  id: string;
  title: string;
  message: string;
  icon?: string;
  timestamp: number;
  read?: boolean;
}

const STORAGE_KEY = "retroweb.notifications";
const MAX = 50;

function loadNotifications(): Notification[] {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]");
  } catch { return []; }
}

function saveNotifications(ns: Notification[]) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(ns.slice(0, MAX)));
}

/** Push a notification from anywhere in the app */
export function pushNotification(title: string, message: string, icon?: string) {
  const ns = loadNotifications();
  const n: Notification = { id: crypto.randomUUID(), title, message, icon, timestamp: Date.now() };
  ns.unshift(n);
  saveNotifications(ns);
  window.dispatchEvent(new CustomEvent("retroweb:notification", { detail: n }));
}

export default function NotificationCenter() {
  const [open, setOpen] = useState(false);
  const [notifications, setNotifications] = useState<Notification[]>(loadNotifications);
  const unread = notifications.filter(n => !n.read).length;

  const refresh = useCallback(() => setNotifications(loadNotifications()), []);

  useEffect(() => {
    const handler = () => refresh();
    window.addEventListener("retroweb:notification", handler);
    return () => window.removeEventListener("retroweb:notification", handler);
  }, [refresh]);

  const markAllRead = () => {
    const updated = notifications.map(n => ({ ...n, read: true }));
    saveNotifications(updated);
    setNotifications(updated);
  };

  const clearAll = () => {
    saveNotifications([]);
    setNotifications([]);
  };

  const timeAgo = (ts: number) => {
    const s = Math.floor((Date.now() - ts) / 1000);
    if (s < 60) return "just now";
    if (s < 3600) return `${Math.floor(s / 60)}m ago`;
    if (s < 86400) return `${Math.floor(s / 3600)}h ago`;
    return `${Math.floor(s / 86400)}d ago`;
  };

  return (
    <>
      <button
        onClick={() => { setOpen(o => !o); if (!open) markAllRead(); }}
        className="relative p-2 text-zinc-400 hover:text-white transition-colors"
        title="Notifications"
      >
        <Bell size={18} />
        {unread > 0 && (
          <span className="absolute -top-0.5 -right-0.5 bg-red-500 text-white text-[10px] font-bold rounded-full w-4 h-4 flex items-center justify-center">
            {unread > 9 ? "9+" : unread}
          </span>
        )}
      </button>

      {open && (
        <div className="fixed top-12 right-4 z-50 w-80 max-h-96 bg-zinc-900 border border-zinc-700 rounded-xl shadow-2xl overflow-hidden flex flex-col">
          <div className="px-4 py-3 border-b border-zinc-700 flex items-center justify-between">
            <span className="text-sm font-semibold text-white">Notifications</span>
            <div className="flex items-center gap-2">
              {notifications.length > 0 && (
                <button onClick={clearAll} className="text-xs text-zinc-500 hover:text-red-400">Clear all</button>
              )}
              <button onClick={() => setOpen(false)}><X size={14} className="text-zinc-500" /></button>
            </div>
          </div>
          <div className="flex-1 overflow-y-auto">
            {notifications.length === 0 ? (
              <div className="p-8 text-center text-zinc-500 text-sm">No notifications yet</div>
            ) : (
              notifications.map(n => (
                <div key={n.id} className={`px-4 py-3 border-b border-zinc-800 ${n.read ? "opacity-60" : ""}`}>
                  <div className="flex items-start gap-2">
                    {n.icon && <span className="text-lg">{n.icon}</span>}
                    <div className="flex-1 min-w-0">
                      <div className="text-xs font-medium text-white truncate">{n.title}</div>
                      <div className="text-xs text-zinc-400 mt-0.5">{n.message}</div>
                      <div className="text-[10px] text-zinc-600 mt-1">{timeAgo(n.timestamp)}</div>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </>
  );
}
