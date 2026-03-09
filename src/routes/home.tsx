import { Link } from "react-router";
import { LibraryBig, Gamepad2, Cpu, Save, MessageCircle, Upload, Wifi } from "lucide-react";

/* From Uiverse.io by TemRevil — Pong animation, colour-matched, slowed */
const PONG_CSS = `
.pong-bg {
  position: absolute;
  inset: 0;
  display: flex;
  justify-content: center;
  align-items: center;
  pointer-events: none;
  opacity: 0.15;
  z-index: 0;
}
.pong-box {
  width: 250px;
  height: 100px;
  display: flex;
  justify-content: space-around;
  align-items: center;
  position: relative;
}
.pong-color {
  background-color: #a855f7;
}
.pong-WH {
  width: 10px;
  height: 70px;
  position: absolute;
}
.pong-l1 {
  left: 0;
  animation: pong-l1 8s infinite linear;
}
.pong-l2 {
  right: 0;
  animation: pong-l2 8s infinite linear;
}
.pong-ball {
  width: 15px;
  height: 15px;
  border-radius: 50%;
  position: absolute;
  background-color: #ef4444;
  box-shadow: 0 0 12px #ef4444, 0 0 24px rgba(239,68,68,0.4);
  animation: pong-ball 8s infinite linear;
}
@keyframes pong-l1 {
  0% { top: 0%; }
  10% { top: -20%; }
  20% { top: 0%; }
  30% { top: 40%; }
  40% { top: 0%; }
  50% { top: 30%; }
  60% { top: 40%; }
  70% { top: 60%; }
  80% { top: -10%; }
  90% { top: 10%; }
  100% { top: 0%; }
}
@keyframes pong-l2 {
  0% { bottom: 0%; }
  10% { bottom: -20%; }
  20% { bottom: 40%; }
  30% { bottom: 60%; }
  40% { bottom: 20%; }
  50% { bottom: 30%; }
  60% { bottom: 40%; }
  70% { bottom: 60%; }
  80% { bottom: -10%; }
  90% { bottom: 10%; }
  100% { bottom: 0%; }
}
@keyframes pong-ball {
  0% { top: 80%; left: 96%; }
  10% { top: 10%; left: 3%; }
  20% { top: 10%; left: 90%; }
  30% { top: 60%; left: 3%; }
  40% { top: 10%; left: 90%; }
  50% { top: 50%; left: 3%; }
  60% { top: 10%; left: 90%; }
  70% { top: 93%; left: 3%; }
  80% { top: 83%; left: 90%; }
  90% { top: 10%; left: 3%; }
  100% { top: 80%; left: 90%; }
}
`;

function PongBackground() {
  return (
    <>
      <style dangerouslySetInnerHTML={{ __html: PONG_CSS }} />
      <div className="pong-bg">
        <div className="pong-box">
          <div className="pong-WH pong-color pong-l1" />
          <div className="pong-WH pong-color pong-l2" />
          <div className="pong-ball" />
        </div>
      </div>
    </>
  );
}

const features = [
  {
    icon: <LibraryBig size={28} />,
    title: "Game Library",
    desc: "Browse, search, and launch your retro game collection right in the browser. Upload ROMs and they're ready to play instantly.",
    to: "/library",
  },
  {
    icon: <Gamepad2 size={28} />,
    title: "Supported Systems",
    desc: "NES, SNES, Game Boy, GBA, N64, PlayStation, Sega Genesis, and more — all powered by RetroArch cores compiled for the web.",
    to: "/systems",
  },
  {
    icon: <Upload size={28} />,
    title: "Drag & Drop Upload",
    desc: "Drop ROMs directly onto the library page or BIOS files anywhere. We auto-detect the system and get everything set up for you.",
    to: "/library",
  },
  {
    icon: <Cpu size={28} />,
    title: "BIOS Vault",
    desc: "Some systems need BIOS files to run. Upload them once and they're stored locally in your browser — no server needed.",
    to: "/bios",
  },
  {
    icon: <Save size={28} />,
    title: "Save States",
    desc: "Your save states and SRAM data persist in the browser. Export and import saves to keep your progress safe.",
    to: "/saves",
  },
  {
    icon: <Gamepad2 size={28} />,
    title: "Controller Support",
    desc: "Plug in a gamepad and play. The controller test page lets you verify your inputs and check button mappings.",
    to: "/controller",
  },
  {
    icon: <MessageCircle size={28} />,
    title: "AI Chat Assistant",
    desc: "Ask the built-in AI anything about retro gaming. Supports voice conversations, image analysis, and file uploads.",
    to: "/chat",
  },
  {
    icon: <Wifi size={28} />,
    title: "Fully Local",
    desc: "Everything runs in your browser and on your local network. No cloud, no accounts, no tracking. Your games, your rules.",
    to: "/settings",
  },
];

export default function Home() {
  return (
    <div className="flex-1 overflow-y-auto">
      {/* Hero */}
      <section className="relative flex flex-col items-center justify-center text-center px-6 py-20 overflow-hidden">
        <PongBackground />
        <div className="absolute inset-0 bg-gradient-to-b from-purple-900/20 via-transparent to-transparent pointer-events-none" />
        <h1 className="text-5xl md:text-6xl font-black tracking-tight text-white mb-4 relative">
          <span className="bg-gradient-to-r from-red-500 via-purple-500 to-blue-500 bg-clip-text text-transparent">
            RetroWeb
          </span>
        </h1>
        <p className="text-lg md:text-xl text-zinc-400 max-w-2xl mb-8 relative">
          A premium browser-based retro gaming platform. Upload your ROMs, launch games instantly, 
          and relive the classics — all from your browser, no installs required.
        </p>
        <div className="flex gap-3 relative">
          <Link
            to="/library"
            className="px-6 py-3 rounded-xl bg-gradient-to-r from-red-600 to-purple-600 text-white font-semibold hover:scale-105 transition-transform shadow-lg shadow-purple-500/25"
          >
            Open Library
          </Link>
          <Link
            to="/systems"
            className="px-6 py-3 rounded-xl bg-zinc-800 text-zinc-300 font-semibold hover:bg-zinc-700 transition-colors border border-zinc-700"
          >
            View Systems
          </Link>
        </div>
      </section>

      {/* Features grid */}
      <section className="px-6 pb-20 max-w-6xl mx-auto">
        <h2 className="text-2xl font-bold text-white mb-8 text-center">Everything You Need</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {features.map((f) => (
            <Link
              key={f.title}
              to={f.to}
              className="group p-5 rounded-xl bg-zinc-900/60 border border-zinc-800 hover:border-purple-500/50 hover:bg-zinc-800/80 transition-all duration-300"
            >
              <div className="text-purple-400 mb-3 group-hover:scale-110 transition-transform">
                {f.icon}
              </div>
              <h3 className="text-white font-semibold mb-1">{f.title}</h3>
              <p className="text-zinc-400 text-sm leading-relaxed">{f.desc}</p>
            </Link>
          ))}
        </div>
      </section>

      {/* Quick start */}
      <section className="px-6 pb-20 max-w-3xl mx-auto text-center">
        <h2 className="text-2xl font-bold text-white mb-6">Quick Start</h2>
        <div className="flex flex-col sm:flex-row gap-4 justify-center">
          {[
            { step: "1", text: "Upload a ROM to the Library" },
            { step: "2", text: "Install BIOS if needed" },
            { step: "3", text: "Click Play and enjoy" },
          ].map((s) => (
            <div
              key={s.step}
              className="flex-1 p-4 rounded-xl bg-zinc-900/60 border border-zinc-800"
            >
              <div className="w-8 h-8 rounded-full bg-purple-600 text-white font-bold flex items-center justify-center mx-auto mb-2">
                {s.step}
              </div>
              <p className="text-zinc-300 text-sm">{s.text}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Footer */}
      <footer className="text-center py-6 text-zinc-600 text-xs border-t border-zinc-800/50">
        RetroWeb — Final Year Project &middot; Built with React, RetroArch, and Ollama
      </footer>
    </div>
  );
}
