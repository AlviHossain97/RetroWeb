import { request } from '@/lib/api/client';
import type { HealthStatus, VersionInfo } from '@/lib/types/api';

export const checkHealth = () => request<HealthStatus>('/health');
export const getVersion = () => request<VersionInfo>('/version');
