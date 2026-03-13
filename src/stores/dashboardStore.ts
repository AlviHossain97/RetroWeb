import { create } from 'zustand';
import type { Session, TopGame } from '@/lib/types/api';
import { getDashboardData } from '@/lib/api/dashboard';

interface DashboardState {
  activeSession: Session | null;
  recentSessions: Session[];
  topGames: TopGame[];
  loading: boolean;
  error: string | null;
  lastFetched: number | null;
  fetchDashboard: () => Promise<void>;
}

export const useDashboardStore = create<DashboardState>((set) => ({
  activeSession: null,
  recentSessions: [],
  topGames: [],
  loading: false,
  error: null,
  lastFetched: null,
  fetchDashboard: async () => {
    set({ loading: true, error: null });
    try {
      const data = await getDashboardData();
      set({
        activeSession: data.active_session,
        recentSessions: data.recent_sessions,
        topGames: data.top_games,
        loading: false,
        lastFetched: Date.now(),
      });
    } catch (e) {
      set({ loading: false, error: e instanceof Error ? e.message : 'Failed to fetch dashboard data' });
    }
  },
}));
