import { unlockAchievement, type Achievement } from "./storage/db";
import { toast } from "sonner";
import { pushNotification } from "../lib/notifications";

const ACHIEVEMENT_DEFS: Achievement[] = [
  { id: "first_game", title: "First Steps", description: "Play your first game", icon: "🎮" },
  { id: "five_games", title: "Getting Started", description: "Play 5 different games", icon: "🕹️" },
  { id: "ten_games", title: "Retro Explorer", description: "Play 10 different games", icon: "🗺️" },
  { id: "hour_played", title: "Time Flies", description: "Accumulate 1 hour of playtime", icon: "⏰" },
  { id: "ten_hours", title: "Dedicated Gamer", description: "Accumulate 10 hours of playtime", icon: "🏆" },
  { id: "five_systems", title: "System Hopper", description: "Play games from 5 different systems", icon: "📺" },
  { id: "first_save", title: "Safety First", description: "Create your first save state", icon: "💾" },
  { id: "first_favorite", title: "Collector", description: "Add a game to favorites", icon: "⭐" },
  { id: "bios_installed", title: "Power Up", description: "Install a BIOS file", icon: "🔌" },
  { id: "ai_chat", title: "AI Assistant", description: "Send a message to the AI chat", icon: "🤖" },
  { id: "voice_mode", title: "Voice Commander", description: "Use voice mode in AI chat", icon: "🎤" },
  { id: "screenshot_ai", title: "Show & Tell", description: "Send a screenshot to the AI", icon: "📸" },
  { id: "theme_changed", title: "Style Points", description: "Change the app theme", icon: "🎨" },
  { id: "speed_demon", title: "Speed Demon", description: "Use fast forward mode", icon: "⚡" },
];

export function getAchievementDefs(): Achievement[] {
  return ACHIEVEMENT_DEFS;
}

export async function checkAndUnlock(id: string): Promise<boolean> {
  const def = ACHIEVEMENT_DEFS.find((a) => a.id === id);
  if (!def) return false;
  const unlocked = await unlockAchievement(def);
  if (unlocked) {
    toast.success(`🏆 Achievement Unlocked: ${def.title}`, {
      description: def.description,
      duration: 4000,
    });
    pushNotification(`Achievement: ${def.title}`, def.description, def.icon);
  }
  return unlocked;
}
