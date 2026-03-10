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

export function loadNotifications(): Notification[] {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]");
  } catch { return []; }
}

export function saveNotifications(ns: Notification[]) {
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
