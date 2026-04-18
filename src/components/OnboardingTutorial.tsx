import { useState } from "react";

const STORAGE_KEY = "retroweb.onboardingDone";

const STEPS = [
  { title: "Welcome to RetroWeb! 🎮", description: "A companion dashboard for your RetroPie setup. It tracks what you play on the Pi and surfaces the stats here. Quick tour below.", icon: "🏠" },
  { title: "Analytics & Sessions 📊", description: "The Dashboard, Sessions, Games, and Systems pages break down your playtime, session history, most-played titles, and per-platform usage.", icon: "📈" },
  { title: "Devices & Achievements 🏆", description: "Devices shows live heartbeat status and last-seen info for each Pi. Achievements tracks unlocks as you hit playtime, streak, and exploration milestones.", icon: "🕹️" },
  { title: "AI Assistant 🤖", description: "Chat with a local AI (Ollama) that knows your library and activity. Voice mode, attachments, and optional web-grounded answers with sources are supported.", icon: "💬" },
  { title: "Controllers & Customize ⚙️", description: "Run controller diagnostics, remap buttons, and save profiles. Settings covers themes, audio, accessibility, language, and kiosk mode for TV displays.", icon: "🎨" },
  { title: "You're Ready! 🚀", description: "Games are played on the Pi itself — not in the browser. This site is where you watch the stats, health, and history come in. Enjoy!", icon: "✨" },
];

export default function OnboardingTutorial() {
  const [visible, setVisible] = useState(() => !localStorage.getItem(STORAGE_KEY));
  const [step, setStep] = useState(0);

  const finish = () => {
    localStorage.setItem(STORAGE_KEY, "true");
    setVisible(false);
  };

  if (!visible) return null;

  const s = STEPS[step];
  const isLast = step === STEPS.length - 1;

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/70 backdrop-blur-sm">
      <div className="bg-zinc-900 border border-zinc-700 rounded-2xl shadow-2xl max-w-md w-full mx-4 overflow-hidden">
        {/* Progress bar */}
        <div className="h-1 bg-zinc-800">
          <div className="h-full bg-blue-500 transition-all duration-300" style={{ width: `${((step + 1) / STEPS.length) * 100}%` }} />
        </div>

        <div className="p-8 text-center">
          <div className="text-5xl mb-4">{s.icon}</div>
          <h2 className="text-xl font-bold text-white mb-3">{s.title}</h2>
          <p className="text-sm text-zinc-400 leading-relaxed">{s.description}</p>
        </div>

        <div className="px-8 pb-6 flex items-center justify-between">
          <button
            onClick={finish}
            className="text-xs text-zinc-500 hover:text-zinc-300 transition-colors"
          >
            Skip tour
          </button>
          <div className="flex items-center gap-2">
            {step > 0 && (
              <button
                onClick={() => setStep(s => s - 1)}
                className="px-4 py-2 text-sm rounded-lg bg-zinc-700 text-white hover:bg-zinc-600 transition-colors"
              >
                Back
              </button>
            )}
            <button
              onClick={isLast ? finish : () => setStep(s => s + 1)}
              className="px-4 py-2 text-sm rounded-lg bg-blue-600 text-white hover:bg-blue-500 transition-colors font-medium"
            >
              {isLast ? "Get Started" : "Next"}
            </button>
          </div>
        </div>

        {/* Step dots */}
        <div className="pb-4 flex justify-center gap-1.5">
          {STEPS.map((_, i) => (
            <div key={i} className={`w-2 h-2 rounded-full transition-colors ${i === step ? "bg-blue-500" : "bg-zinc-700"}`} />
          ))}
        </div>
      </div>
    </div>
  );
}
