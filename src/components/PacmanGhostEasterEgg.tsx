import { useEffect, useState } from 'react';
import type { CSSProperties } from 'react';
import { toast } from 'sonner';

interface Props {
  frightenThreshold?: number;
  frightenDuration?: number;
  className?: string;
  style?: CSSProperties;
}

/* From Uiverse.io by BlackisPlay (red ghost) & moraxh (scared blue ghost) */
const GHOST_CSS = `
.pg-ghost {
  position: relative;
  scale: 0.4;
}

.pg-body {
  animation: pg-upNDown infinite 0.5s;
  position: relative;
  width: 140px;
  height: 140px;
  display: grid;
  grid-template-columns: repeat(14, 1fr);
  grid-template-rows: repeat(14, 1fr);
  grid-column-gap: 0px;
  grid-row-gap: 0px;
  grid-template-areas:
    "a1  a2  a3  a4  a5  top0  top0  top0  top0  a10 a11 a12 a13 a14"
    "b1  b2  b3  top1 top1 top1 top1 top1 top1 top1 top1 b12 b13 b14"
    "c1 c2 top2 top2 top2 top2 top2 top2 top2 top2 top2 top2 c13 c14"
    "d1 top3 top3 top3 top3 top3 top3 top3 top3 top3 top3 top3 top3 d14"
    "e1 top3 top3 top3 top3 top3 top3 top3 top3 top3 top3 top3 top3 e14"
    "f1 top3 top3 top3 top3 top3 top3 top3 top3 top3 top3 top3 top3 f14"
    "top4 top4 top4 top4 top4 top4 top4 top4 top4 top4 top4 top4 top4 top4"
    "top4 top4 top4 top4 top4 top4 top4 top4 top4 top4 top4 top4 top4 top4"
    "top4 top4 top4 top4 top4 top4 top4 top4 top4 top4 top4 top4 top4 top4"
    "top4 top4 top4 top4 top4 top4 top4 top4 top4 top4 top4 top4 top4 top4"
    "top4 top4 top4 top4 top4 top4 top4 top4 top4 top4 top4 top4 top4 top4"
    "top4 top4 top4 top4 top4 top4 top4 top4 top4 top4 top4 top4 top4 top4"
    "st0 st0 an4 st1 an7 st2 an10 an10 st3 an13 st4 an16 st5 st5"
    "an1 an2 an3 an5 an6 an8 an9 an9 an11 an12 an14 an15 an17 an18";
}

@keyframes pg-upNDown {
  0%, 49% { transform: translateY(0px); }
  50%, 100% { transform: translateY(-10px); }
}

/* Grid area assignments */
.pg-top0 { grid-area: top0; }
.pg-top1 { grid-area: top1; }
.pg-top2 { grid-area: top2; }
.pg-top3 { grid-area: top3; }
.pg-top4 { grid-area: top4; }
.pg-st0 { grid-area: st0; }
.pg-st1 { grid-area: st1; }
.pg-st2 { grid-area: st2; }
.pg-st3 { grid-area: st3; }
.pg-st4 { grid-area: st4; }
.pg-st5 { grid-area: st5; }
.pg-an1 { grid-area: an1; }
.pg-an2 { grid-area: an2; }
.pg-an3 { grid-area: an3; }
.pg-an4 { grid-area: an4; }
.pg-an5 { grid-area: an5; }
.pg-an6 { grid-area: an6; }
.pg-an7 { grid-area: an7; }
.pg-an8 { grid-area: an8; }
.pg-an9 { grid-area: an9; }
.pg-an10 { grid-area: an10; }
.pg-an11 { grid-area: an11; }
.pg-an12 { grid-area: an12; }
.pg-an13 { grid-area: an13; }
.pg-an14 { grid-area: an14; }
.pg-an15 { grid-area: an15; }
.pg-an16 { grid-area: an16; }
.pg-an17 { grid-area: an17; }
.pg-an18 { grid-area: an18; }

/* ── RED (normal) ── */
.pg-red .pg-top0, .pg-red .pg-top1, .pg-red .pg-top2,
.pg-red .pg-top3, .pg-red .pg-top4,
.pg-red .pg-st0, .pg-red .pg-st1, .pg-red .pg-st2,
.pg-red .pg-st3, .pg-red .pg-st4, .pg-red .pg-st5 {
  background-color: red;
}

.pg-red .pg-an1, .pg-red .pg-an18,
.pg-red .pg-an6, .pg-red .pg-an12,
.pg-red .pg-an7, .pg-red .pg-an13,
.pg-red .pg-an8, .pg-red .pg-an11 {
  animation: pg-flicker0-red infinite 0.5s;
}

.pg-red .pg-an2, .pg-red .pg-an17,
.pg-red .pg-an3, .pg-red .pg-an16,
.pg-red .pg-an4, .pg-red .pg-an15,
.pg-red .pg-an9, .pg-red .pg-an10 {
  animation: pg-flicker1-red infinite 0.5s;
}

@keyframes pg-flicker0-red {
  0%, 49% { background-color: red; }
  50%, 100% { background-color: transparent; }
}
@keyframes pg-flicker1-red {
  0%, 49% { background-color: transparent; }
  50%, 100% { background-color: red; }
}

/* Red ghost eyes */
.pg-red .pg-eye, .pg-red .pg-eye1 {
  width: 40px; height: 50px; position: absolute; top: 30px;
}
.pg-red .pg-eye { left: 10px; }
.pg-red .pg-eye1 { right: 30px; }
.pg-red .pg-eye::before, .pg-red .pg-eye1::before {
  content: ""; background-color: white;
  width: 20px; height: 50px; transform: translateX(10px);
  display: block; position: absolute;
}
.pg-red .pg-eye::after, .pg-red .pg-eye1::after {
  content: ""; background-color: white;
  width: 40px; height: 30px; transform: translateY(10px);
  display: block; position: absolute;
}
.pg-red .pg-pupil, .pg-red .pg-pupil1 {
  width: 20px; height: 20px; background-color: blue;
  position: absolute; top: 50px; z-index: 1;
  animation: pg-eyesMovement infinite 3s;
}
.pg-red .pg-pupil { left: 10px; }
.pg-red .pg-pupil1 { right: 50px; }

@keyframes pg-eyesMovement {
  0%, 49% { transform: translateX(0px); }
  50%, 99% { transform: translateX(10px); }
  100% { transform: translateX(0px); }
}

/* ── BLUE (scared) ── */
.pg-blue .pg-top0, .pg-blue .pg-top1, .pg-blue .pg-top2,
.pg-blue .pg-top3, .pg-blue .pg-top4,
.pg-blue .pg-st0, .pg-blue .pg-st1, .pg-blue .pg-st2,
.pg-blue .pg-st3, .pg-blue .pg-st4, .pg-blue .pg-st5 {
  background-color: blue;
}

.pg-blue .pg-an1, .pg-blue .pg-an18,
.pg-blue .pg-an6, .pg-blue .pg-an12,
.pg-blue .pg-an7, .pg-blue .pg-an13,
.pg-blue .pg-an8, .pg-blue .pg-an11 {
  animation: pg-flicker0-blue infinite 0.5s;
}

.pg-blue .pg-an2, .pg-blue .pg-an3, .pg-blue .pg-an4,
.pg-blue .pg-an5, .pg-blue .pg-an9, .pg-blue .pg-an10,
.pg-blue .pg-an15, .pg-blue .pg-an16, .pg-blue .pg-an17 {
  animation: pg-flicker1-blue infinite 0.5s;
}

@keyframes pg-flicker0-blue {
  0%, 49% { background-color: blue; }
  50%, 100% { background-color: transparent; }
}
@keyframes pg-flicker1-blue {
  0%, 49% { background-color: transparent; }
  50%, 100% { background-color: blue; }
}

/* Blue ghost eyes */
.pg-blue .pg-eye, .pg-blue .pg-eye1 {
  width: 40px; height: 50px; position: absolute; top: 30px;
}
.pg-blue .pg-eye { left: 20px; }
.pg-blue .pg-eye1 { right: 20px; }
.pg-blue .pg-eye::before, .pg-blue .pg-eye1::before {
  content: ""; background-color: blue;
  width: 20px; height: 50px; transform: translateX(10px);
  display: block; position: absolute;
}
.pg-blue .pg-eye::after, .pg-blue .pg-eye1::after {
  content: ""; background-color: blue;
  width: 40px; height: 30px; transform: translateY(10px);
  display: block; position: absolute;
}
.pg-blue .pg-pupil, .pg-blue .pg-pupil1 {
  width: 20px; height: 20px; background-color: #fcc78b;
  position: absolute; top: 50px; z-index: 1;
}
.pg-blue .pg-pupil { left: 30px; }
.pg-blue .pg-pupil1 { right: 30px; }

/* Scared mouth */
.pg-blue .pg-mouth {
  width: 20px; height: 10px; background-color: #fcc78b;
  position: absolute; z-index: 1; top: 100px;
}
.pg-blue .pg-mouthstart, .pg-blue .pg-mouthend {
  width: 10px; height: 10px; background-color: #fcc78b;
  position: absolute; z-index: 1; top: 100px;
}
.pg-blue .pg-mouthstart { left: 10px; }
.pg-blue .pg-mouth1 { top: 90px; left: 20px; }
.pg-blue .pg-mouth2 { left: 40px; }
.pg-blue .pg-mouth3 { top: 90px; left: 60px; }
.pg-blue .pg-mouth4 { left: 80px; }
.pg-blue .pg-mouth5 { top: 90px; left: 100px; }
.pg-blue .pg-mouthend { left: 120px; }

/* Shadow */
.pg-shadow {
  background-color: black;
  width: 140px; height: 140px;
  position: absolute; border-radius: 50%;
  transform: rotateX(80deg); filter: blur(20px);
  top: 80%;
  animation: pg-shadowMovement infinite 0.5s;
}

@keyframes pg-shadowMovement {
  0%, 49% { opacity: 0.5; }
  50%, 100% { opacity: 0.2; }
}
`;

const GRID_CELLS = [
  'top0','top1','top2','top3','top4',
  'st0','st1','st2','st3','st4','st5',
  'an1','an2','an3','an4','an5','an6','an7','an8','an9',
  'an10','an11','an12','an13','an14','an15','an16','an17','an18',
];

export default function PacmanGhostEasterEgg({
  frightenThreshold = 5,
  frightenDuration = 4000,
  className = '',
  style,
}: Props) {
  const [clickCount, setClickCount] = useState(0);
  const [frightened, setFrightened] = useState(false);
  const [prefersReduced, setPrefersReduced] = useState(false);

  useEffect(() => {
    const mq = window.matchMedia('(prefers-reduced-motion: reduce)');
    setPrefersReduced(mq.matches);
    const handler = (e: MediaQueryListEvent) => setPrefersReduced(e.matches);
    mq.addEventListener('change', handler);
    return () => mq.removeEventListener('change', handler);
  }, []);

  const handleClick = () => {
    const newCount = clickCount + 1;
    if (newCount >= frightenThreshold && !frightened) {
      setFrightened(true);
      setClickCount(0);
      toast.success('👻 Ghost Hunter! Pac-Man would be proud.');
      setTimeout(() => {
        setFrightened(false);
        setClickCount(0);
      }, frightenDuration);
    } else {
      setClickCount(newCount);
    }
  };

  const variant = frightened ? 'pg-blue' : 'pg-red';

  return (
    <div
      className={`hidden sm:block ${className}`}
      style={{ position: 'fixed', bottom: 80, right: 20, zIndex: 40, cursor: 'pointer', ...style }}
      title={frightened ? 'WAKA WAKA!' : `Click ${frightenThreshold - clickCount} more times...`}
      onClick={handleClick}
    >
      <style>{GHOST_CSS}</style>
      <div className="pg-ghost" style={prefersReduced ? { scale: '0.4' } : undefined}>
        <div className={`pg-body ${variant}`} style={prefersReduced ? { animation: 'none' } : undefined}>
          {GRID_CELLS.map(c => <div key={c} className={`pg-${c}`} />)}
          <div className="pg-eye" />
          <div className="pg-pupil" />
          <div className="pg-eye1" />
          <div className="pg-pupil1" />
          {frightened && (
            <>
              <div className="pg-mouth pg-mouthstart" />
              <div className="pg-mouth pg-mouth1" />
              <div className="pg-mouth pg-mouth2" />
              <div className="pg-mouth pg-mouth3" />
              <div className="pg-mouth pg-mouth4" />
              <div className="pg-mouth pg-mouth5" />
              <div className="pg-mouth pg-mouthend" />
            </>
          )}
        </div>
        <div className="pg-shadow" />
      </div>
    </div>
  );
}
