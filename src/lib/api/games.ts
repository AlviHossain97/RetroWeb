import { request } from '@/lib/api/client';
import type { TopGame } from '@/lib/types/api';

export interface GameRow {
  rom_path: string;
  system_name: string | null;
  total_seconds: number;
  last_played: string;
  session_count: number;
  title: string;
}

export const getTopGames = (limit = 20) =>
  request<TopGame[]>(`/stats/top?limit=${limit}`);

export const getGames = (limit = 50) =>
  request<GameRow[]>(`/games?limit=${limit}`);
