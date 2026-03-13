export interface Session {
  id: number;
  pi_hostname: string;
  rom_path: string;
  system_name: string | null;
  emulator: string | null;
  core: string | null;
  started_at: string;
  ended_at: string | null;
  duration_seconds: number | null;
  live_seconds?: number;
  created_at?: string;
}

export interface TopGame {
  rom_path: string;
  system_name: string | null;
  emulator: string | null;
  core: string | null;
  total_seconds: number;
  last_played: string;
  session_count: number;
}

export interface DashboardSummary {
  active_session: Session | null;
  recent_sessions: Session[];
  top_games: TopGame[];
  total_sessions: number;
  total_seconds: number;
  fav_system_name: string;
}

export interface HealthStatus {
  ok: boolean;
}

export interface VersionInfo {
  api: string;
  version: string;
}

// Future types (placeholders for expansion)
export interface Device {
  id: number;
  hostname: string;
  display_name: string | null;
  ip_address: string | null;
  status: string;
  last_seen_at: string | null;
}

export interface GameStats {
  id: number;
  canonical_title: string;
  system_name: string | null;
  cover_url: string | null;
  total_seconds: number;
  session_count: number;
  last_played: string | null;
}

export interface SystemStats {
  system_name: string;
  total_seconds: number;
  session_count: number;
}
