import { request } from '@/lib/api/client';

export interface AchievementDef {
  id: number;
  code: string;
  title: string;
  description: string;
  icon: string;
  category: string;
}

export interface UnlockedAchievement extends AchievementDef {
  unlocked_at: string;
}

export const getAchievements = () =>
  request<AchievementDef[]>(`/achievements`);

export const getUnlockedAchievements = () =>
  request<UnlockedAchievement[]>(`/achievements/unlocked`);
