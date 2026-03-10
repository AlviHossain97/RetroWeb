import { useEffect, useState } from "react";
import { Trophy } from "lucide-react";
import { getAchievementDefs } from "../lib/achievements";
import { getUnlockedAchievements, type Achievement } from "../lib/storage/db";

export default function Achievements() {
  const [unlocked, setUnlocked] = useState<Achievement[]>([]);
  const allDefs = getAchievementDefs();

  useEffect(() => {
    getUnlockedAchievements().then(setUnlocked);
  }, []);

  const unlockedIds = new Set(unlocked.map((a) => a.id));
  const unlockedCount = unlockedIds.size;

  return (
    <div className="flex-1 w-full max-w-4xl mx-auto p-4 md:p-8">
      <header className="mb-8">
        <h1 className="text-3xl font-bold flex items-center gap-3" style={{ color: "var(--text-primary)" }}>
          <Trophy size={28} style={{ color: "var(--accent-primary)" }} /> Achievements
        </h1>
        <p className="text-sm mt-1" style={{ color: "var(--text-muted)" }}>
          {unlockedCount} / {allDefs.length} unlocked
        </p>
        {/* Progress bar */}
        <div className="mt-3 h-2 rounded-full overflow-hidden" style={{ background: "var(--surface-2)" }}>
          <div
            className="h-full rounded-full transition-all duration-500"
            style={{
              width: `${allDefs.length > 0 ? (unlockedCount / allDefs.length) * 100 : 0}%`,
              background: "linear-gradient(90deg, var(--accent-primary), #f6c90e)",
            }}
          />
        </div>
      </header>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {allDefs.map((def) => {
          const isUnlocked = unlockedIds.has(def.id);
          const unlockedData = unlocked.find((a) => a.id === def.id);
          return (
            <div
              key={def.id}
              className="flex items-center gap-4 p-4 rounded-xl transition-all"
              style={{
                background: isUnlocked ? "var(--surface-1)" : "var(--surface-2)",
                border: isUnlocked ? "1px solid var(--accent-primary)" : "1px solid var(--border-soft)",
                opacity: isUnlocked ? 1 : 0.5,
              }}
            >
              <div className="text-3xl shrink-0" style={{ filter: isUnlocked ? "none" : "grayscale(1)" }}>
                {def.icon}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-bold" style={{ color: "var(--text-primary)" }}>
                  {def.title}
                </p>
                <p className="text-xs" style={{ color: "var(--text-muted)" }}>
                  {def.description}
                </p>
                {isUnlocked && unlockedData?.unlockedAt && (
                  <p className="text-[10px] mt-1" style={{ color: "var(--text-muted)" }}>
                    Unlocked {new Date(unlockedData.unlockedAt).toLocaleDateString()}
                  </p>
                )}
              </div>
              {isUnlocked && (
                <div className="shrink-0 text-xs font-bold px-2 py-1 rounded-full" style={{ background: "rgba(246,201,14,0.15)", color: "#f6c90e" }}>
                  ✓
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
