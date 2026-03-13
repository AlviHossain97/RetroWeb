import { request } from '@/lib/api/client';
import type { Device } from '@/lib/types/api';

export const getDevices = (limit = 20) =>
  request<Device[]>(`/devices?limit=${limit}`);
