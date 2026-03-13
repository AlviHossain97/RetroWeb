import { request } from '@/lib/api/client';
import type { Session } from '@/lib/types/api';

export const getRecentSessions = (limit = 20) =>
  request<Session[]>(`/stats/recent?limit=${limit}`);

export const getActiveSessions = (limit = 10) =>
  request<Session[]>(`/stats/active?limit=${limit}`);
