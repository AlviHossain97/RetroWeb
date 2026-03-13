import { request } from '@/lib/api/client';
import type { SystemStats } from '@/lib/types/api';

export const getSystemStats = (limit = 20) =>
  request<SystemStats[]>(`/systems?limit=${limit}`);
