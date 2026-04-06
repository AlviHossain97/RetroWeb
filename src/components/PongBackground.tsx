/* From Uiverse.io by TemRevil — Pong animation, colour-matched, slowed */
const PONG_CSS = `
.pong-bg {
  position: fixed;
  inset: 0;
  display: flex;
  justify-content: center;
  align-items: center;
  pointer-events: none;
  user-select: none;
  opacity: 0.32;
  z-index: 20;
  mix-blend-mode: screen;
}
.pong-box {
  width: min(30vw, 360px);
  height: min(12vw, 145px);
  min-width: 220px;
  min-height: 90px;
  display: flex;
  justify-content: space-around;
  align-items: center;
  position: relative;
  filter: drop-shadow(0 0 12px rgba(204, 0, 0, 0.25));
}
.pong-color {
  background-color: #a855f7;
  box-shadow: 0 0 14px rgba(168, 85, 247, 0.45);
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

@media (max-width: 768px) {
  .pong-bg {
    opacity: 0.24;
  }

  .pong-box {
    width: min(72vw, 300px);
    height: min(30vw, 120px);
    min-width: 180px;
    min-height: 72px;
  }

  .pong-WH {
    width: 8px;
    height: 54px;
  }

  .pong-ball {
    width: 12px;
    height: 12px;
  }
}
`;

export default function PongBackground() {
  return (
    <>
      <style dangerouslySetInnerHTML={{ __html: PONG_CSS }} />
      <div className="pong-bg" aria-hidden="true">
        <div className="pong-box">
          <div className="pong-WH pong-color pong-l1" />
          <div className="pong-WH pong-color pong-l2" />
          <div className="pong-ball" />
        </div>
      </div>
    </>
  );
}
