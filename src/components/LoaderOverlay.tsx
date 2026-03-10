import { useEffect, useState } from "react";

interface LoaderOverlayProps {
  visible: boolean;
  mode?: 'init' | 'session' | 'upload' | 'library';
  message?: string;
  gameCover?: string;
  gameTitle?: string;
}

const MODE_MESSAGES: Record<NonNullable<LoaderOverlayProps['mode']>, string[]> = {
  init: ['Initializing emulator…', 'Loading WASM core…', 'Preparing environment…'],
  session: ['Loading ROM…', 'Starting game session…', 'Almost ready…'],
  upload: ['Processing file…', 'Detecting system…', 'Saving to library…'],
  library: ['Loading library…', 'Syncing games…', 'Ready soon…'],
};

/* From Uiverse.io by Novaxlo — colour-matched to app theme */
const EARTH_CSS = `
.earth-loader {
  --watercolor: #cc0000;
  --landcolor: #242433;
  width: 7.5em;
  height: 7.5em;
  background-color: var(--watercolor);
  position: relative;
  overflow: hidden;
  border-radius: 50%;
  box-shadow:
    inset 0em 0.5em rgb(255, 255, 255, 0.25),
    inset 0em -0.5em rgb(0, 0, 0, 0.25);
  border: solid 0.15em rgba(255,255,255,0.15);
  animation: startround 1s;
  animation-iteration-count: 1;
}

.earth-loader svg:nth-child(1) {
  position: absolute;
  bottom: -2em;
  width: 7em;
  height: auto;
  animation: round1 5s infinite linear 0.75s;
}

.earth-loader svg:nth-child(2) {
  position: absolute;
  top: -3em;
  width: 7em;
  height: auto;
  animation: round1 5s infinite linear;
}

.earth-loader svg:nth-child(3) {
  position: absolute;
  top: -2.5em;
  width: 7em;
  height: auto;
  animation: round2 5s infinite linear;
}

.earth-loader svg:nth-child(4) {
  position: absolute;
  bottom: -2.2em;
  width: 7em;
  height: auto;
  animation: round2 5s infinite linear 0.75s;
}

@keyframes startround {
  0% {
    filter: brightness(500%);
    box-shadow: none;
  }
  75% {
    filter: brightness(500%);
    box-shadow: none;
  }
  100% {
    filter: brightness(100%);
    box-shadow:
      inset 0em 0.5em rgb(255, 255, 255, 0.25),
      inset 0em -0.5em rgb(0, 0, 0, 0.25);
  }
}

@keyframes round1 {
  0% { left: -2em; opacity: 100%; transform: skewX(0deg) rotate(0deg); }
  30% { left: -6em; opacity: 100%; transform: skewX(-25deg) rotate(25deg); }
  31% { left: -6em; opacity: 0%; transform: skewX(-25deg) rotate(25deg); }
  35% { left: 7em; opacity: 0%; transform: skewX(25deg) rotate(-25deg); }
  45% { left: 7em; opacity: 100%; transform: skewX(25deg) rotate(-25deg); }
  100% { left: -2em; opacity: 100%; transform: skewX(0deg) rotate(0deg); }
}

@keyframes round2 {
  0% { left: 5em; opacity: 100%; transform: skewX(0deg) rotate(0deg); }
  75% { left: -7em; opacity: 100%; transform: skewX(-25deg) rotate(25deg); }
  76% { left: -7em; opacity: 0%; transform: skewX(-25deg) rotate(25deg); }
  77% { left: 8em; opacity: 0%; transform: skewX(25deg) rotate(-25deg); }
  80% { left: 8em; opacity: 100%; transform: skewX(25deg) rotate(-25deg); }
  100% { left: 5em; opacity: 100%; transform: skewX(0deg) rotate(0deg); }
}
`;

function EarthGlobe() {
  const land = "var(--landcolor, #242433)";
  return (
    <div className="earth-loader">
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 60">
        <path d="M10,30 Q30,10 50,25 T90,20 L90,60 L10,60 Z" fill={land} />
      </svg>
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 60">
        <path d="M5,35 Q25,5 55,20 T95,15 L95,55 L5,55 Z" fill={land} />
      </svg>
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 60">
        <path d="M0,30 Q20,0 50,15 T100,10 L100,60 L0,60 Z" fill={land} />
      </svg>
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 60">
        <path d="M10,25 Q35,5 60,20 T95,15 L95,55 L10,55 Z" fill={land} />
      </svg>
    </div>
  );
}

export default function LoaderOverlay({ visible, mode = 'session', message, gameCover, gameTitle }: LoaderOverlayProps) {
  const [msgIndex, setMsgIndex] = useState(0);
  const messages = MODE_MESSAGES[mode];
  const displayMessage = message || messages[msgIndex];

  useEffect(() => {
    if (!visible) return;
    const interval = setInterval(() => {
      setMsgIndex(i => (i + 1) % messages.length);
    }, 1800);
    return () => clearInterval(interval);
  }, [visible, messages.length]);

  if (!visible) return null;

  return (
    <div
      className="fixed inset-0 z-[100] flex flex-col items-center justify-center"
      style={{ background: 'rgba(13,13,16,0.92)', backdropFilter: 'blur(12px)' }}
    >
      <style>{EARTH_CSS}</style>

      <div className="mb-8">
        <EarthGlobe />
      </div>

      {gameCover && (
        <div className="w-16 h-20 rounded-lg overflow-hidden mb-4 shadow-lg" style={{ border: '2px solid var(--border-strong)' }}>
          <img src={gameCover} alt={gameTitle} className="w-full h-full object-cover" />
        </div>
      )}

      {gameTitle && (
        <h3 className="text-lg font-bold mb-2" style={{ color: 'var(--text-primary)' }}>{gameTitle}</h3>
      )}

      <p className="text-sm font-medium transition-all duration-500" style={{ color: 'var(--text-secondary)', animation: 'fadeSlideIn 0.4s ease' }}>
        {displayMessage}
      </p>

      <div className="mt-6 flex gap-1.5">
        {[0, 1, 2].map(i => (
          <div
            key={i}
            className="w-1.5 h-1.5 rounded-full"
            style={{
              background: 'var(--accent-primary)',
              animation: `glow-pulse 1.2s ease infinite`,
              animationDelay: `${i * 0.4}s`,
              opacity: 0.7,
            }}
          />
        ))}
      </div>
    </div>
  );
}
