import { useEffect, useState } from "react";
import { Trophy, RefreshCcw } from "lucide-react";
import { getAchievements, getUnlockedAchievements as fetchUnlocked, type AchievementDef, type UnlockedAchievement } from "@/lib/api/achievements";

export default function Achievements() {
  const [allDefs, setAllDefs] = useState<AchievementDef[]>([]);
  const [unlocked, setUnlocked] = useState<UnlockedAchievement[]>([]);
  const [loading, setLoading] = useState(true);

  const fetch = () => {
    setLoading(true);
    Promise.all([getAchievements(), fetchUnlocked()])
      .then(([defs, unl]) => { setAllDefs(defs); setUnlocked(unl); })
      .catch(() => {})
      .finally(() => setLoading(false));
  };

  useEffect(() => { fetch(); }, []);

  const unlockedCodes = new Set(unlocked.map((a) => a.code));
  const unlockedCount = unlockedCodes.size;

  // Group by category
  const categories = [...new Set(allDefs.map((a) => a.category))];

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="animate-pulse text-sm" style={{ color: "var(--text-muted)" }}>Loading achievements...</div>
      </div>
    );
  }

  return (
    <div className="flex-1 w-full max-w-4xl mx-auto p-4 md:p-8 overflow-y-auto">
      <header className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-3" style={{ color: "var(--text-primary)" }}>
            <Trophy size={28} style={{ color: "var(--accent-primary)" }} /> Achievements
          </h1>
          <p className="text-sm mt-1" style={{ color: "var(--text-muted)" }}>
            {unlockedCount} / {allDefs.length} unlocked
          </p>
          <div className="mt-3 h-2 rounded-full overflow-hidden w-64" style={{ background: "var(--surface-2)" }}>
            <div
              className="h-full rounded-full transition-all duration-500"
              style={{
                width: `${allDefs.length > 0 ? (unlockedCount / allDefs.length) * 100 : 0}%`,
                background: "linear-gradient(90deg, var(--accent-primary), #f6c90e)",
              }}
            />
          </div>
        </div>
        <button onClick={fetch} className="p-2 rounded-lg hover:opacity-80 transition-opacity" style={{ background: "var(--surface-2)" }}>
          <RefreshCcw size={16} style={{ color: "var(--text-muted)" }} />
        </button>
      </header>

      {categories.map((cat) => (
        <section key={cat} className="mb-8">
          <h2 className="text-sm font-bold uppercase tracking-wider mb-3" style={{ color: "var(--text-muted)" }}>
            {cat.replace(/_/g, " ")}
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {allDefs.filter((a) => a.category === cat).map((def) => {
              const isUnlocked = unlockedCodes.has(def.code);
              const unlockedData = unlocked.find((a) => a.code === def.code);
              return (
                <div
                  key={def.code}
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
                    <p className="text-sm font-bold" style={{ color: "var(--text-primary)" }}>{def.title}</p>
                    <p className="text-xs" style={{ color: "var(--text-muted)" }}>{def.description}</p>
                    {isUnlocked && unlockedData && (
                      <p className="text-[10px] mt-1" style={{ color: "var(--text-muted)" }}>
                        Unlocked {new Date(unlockedData.unlocked_at).toLocaleDateString()}
                      </p>
                    )}
                  </div>
                  {isUnlocked && (
                    <div className="shrink-0 text-xs font-bold px-2 py-1 rounded-full" style={{ background: "rgba(246,201,14,0.15)", color: "#f6c90e" }}>✓</div>
                  )}
                </div>
              );
            })}
          </div>
        </section>
      ))}
    </div>
  );
}
