import { request } from '@/lib/api/client';
import type { Session, TopGame } from '@/lib/types/api';

export async function getDashboardData() {
  const [active, recent, top] = await Promise.all([
    request<Session[]>('/stats/active?limit=1'),
    request<Session[]>('/stats/recent?limit=8'),
    request<TopGame[]>('/stats/top?limit=6'),
  ]);
  return {
    active_session: active[0] || null,
    recent_sessions: recent,
    top_games: top,
  };
}
