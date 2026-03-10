import { useState, useEffect } from "react";

const STORAGE_KEY = "retroweb.onboardingDone";

const STEPS = [
  { title: "Welcome to RetroWeb! 🎮", description: "Your browser-based retro gaming platform. Let's take a quick tour of the key features.", icon: "🏠" },
  { title: "Game Library 📚", description: "Upload ROM files to build your collection. Drag & drop or use the upload button. We support NES, SNES, Game Boy, Genesis, PS1 and more.", icon: "📁" },
  { title: "Play Games 🕹️", description: "Select any game to launch it instantly in your browser. Use keyboard or connect a gamepad. Press F2 for fast-forward, F3 for FPS overlay.", icon: "🎮" },
  { title: "AI Assistant 🤖", description: "Chat with an AI that knows retro games. Get tips, cheats, walkthroughs, and game recommendations. Try voice mode for hands-free help!", icon: "💬" },
  { title: "Customize ⚙️", description: "Choose themes, configure controllers, set shader effects, and personalize your experience. Check Settings for all options.", icon: "🎨" },
  { title: "You're Ready! 🚀", description: "Start by uploading a ROM to your library. Have fun and enjoy the nostalgia!", icon: "✨" },
];

export default function OnboardingTutorial() {
  const [visible, setVisible] = useState(false);
  const [step, setStep] = useState(0);

  useEffect(() => {
    if (!localStorage.getItem(STORAGE_KEY)) {
      setVisible(true);
    }
  }, []);

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
