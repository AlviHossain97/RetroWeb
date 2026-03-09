import { useRef } from 'react';
import type { CSSProperties } from 'react';
import { toast } from 'sonner';

interface Props {
  scale?: number;
  className?: string;
  style?: CSSProperties;
}

/*
 * From Uiverse.io by Pinparker — Mario brick easter egg.
 *
 * Two bricks visible. Hover the gap → ? block pops out.
 * Uses CSS adjacent-sibling selector: .mario-ee-box:hover + .mario-ee-mush
 *
 * Layout (all elements share origin at left=60):
 *   - Left brick:  translateX(-60px)  → shadows at x 2–32
 *   - Right brick: no transform       → shadows at x 62–92
 *   - Gap between: x 32–62 (invisible .box hover zone)
 *   - ? block:     inside .mush, pops up on hover
 */
const CSS = `
.mario-ee-scene {
  position: relative;
  width: 94px;
  height: 34px;
}

.mario-ee-brick {
  height: 2px;
  width: 2px;
  position: absolute;
  left: 60px;
  top: 0;
  box-shadow: 2px 2px 0px #ff9999, 4px 2px 0px #ff9999, 6px 2px 0px #ff9999,
    8px 2px 0px #ff9999, 10px 2px 0px #ff9999, 12px 2px 0px #ff9999,
    14px 2px 0px #ff9999, 16px 2px 0px #ff9999, 18px 2px 0px #ff9999,
    20px 2px 0px #ff9999, 22px 2px 0px #ff9999, 24px 2px 0px #ff9999,
    26px 2px 0px #ff9999, 28px 2px 0px #ff9999, 30px 2px 0px #ff9999,
    32px 2px 0px #ff9999, 2px 4px 0px #cc3300, 4px 4px 0px #cc3300,
    6px 4px 0px #cc3300, 8px 4px 0px #cc3300, 10px 4px 0px #cc3300,
    12px 4px 0px #cc3300, 14px 4px 0px #cc3300, 16px 4px 0px #000,
    18px 4px 0px #cc3300, 20px 4px 0px #cc3300, 22px 4px 0px #cc3300,
    24px 4px 0px #cc3300, 26px 4px 0px #cc3300, 28px 4px 0px #cc3300,
    30px 4px 0px #cc3300, 32px 4px 0px #000, 2px 6px 0px #cc3300,
    4px 6px 0px #cc3300, 6px 6px 0px #cc3300, 8px 6px 0px #cc3300,
    10px 6px 0px #cc3300, 12px 6px 0px #cc3300, 14px 6px 0px #cc3300,
    16px 6px 0px #000, 18px 6px 0px #cc3300, 20px 6px 0px #cc3300,
    22px 6px 0px #cc3300, 24px 6px 0px #cc3300, 26px 6px 0px #cc3300,
    28px 6px 0px #cc3300, 30px 6px 0px #cc3300, 32px 6px 0px #000,
    2px 8px 0px #000, 4px 8px 0px #000, 6px 8px 0px #000, 8px 8px 0px #000,
    10px 8px 0px #000, 12px 8px 0px #000, 14px 8px 0px #000, 16px 8px 0px #000,
    18px 8px 0px #000, 20px 8px 0px #000, 22px 8px 0px #000, 24px 8px 0px #000,
    26px 8px 0px #000, 28px 8px 0px #000, 30px 8px 0px #000, 32px 8px 0px #000,
    2px 10px 0px #cc3300, 4px 10px 0px #cc3300, 6px 10px 0px #cc3300,
    8px 10px 0px #000, 10px 10px 0px #cc3300, 12px 10px 0px #cc3300,
    14px 10px 0px #cc3300, 16px 10px 0px #cc3300, 18px 10px 0px #cc3300,
    20px 10px 0px #cc3300, 22px 10px 0px #cc3300, 24px 10px 0px #000,
    26px 10px 0px #cc3300, 28px 10px 0px #cc3300, 30px 10px 0px #cc3300,
    32px 10px 0px #cc3300, 2px 12px 0px #cc3300, 4px 12px 0px #cc3300,
    6px 12px 0px #cc3300, 8px 12px 0px #000, 10px 12px 0px #cc3300,
    12px 12px 0px #cc3300, 14px 12px 0px #cc3300, 16px 12px 0px #cc3300,
    18px 12px 0px #cc3300, 20px 12px 0px #cc3300, 22px 12px 0px #cc3300,
    24px 12px 0px #000, 26px 12px 0px #cc3300, 28px 12px 0px #cc3300,
    30px 12px 0px #cc3300, 32px 12px 0px #cc3300, 2px 14px 0px #cc3300,
    4px 14px 0px #cc3300, 6px 14px 0px #cc3300, 8px 14px 0px #000,
    10px 14px 0px #cc3300, 12px 14px 0px #cc3300, 14px 14px 0px #cc3300,
    16px 14px 0px #cc3300, 18px 14px 0px #cc3300, 20px 14px 0px #cc3300,
    22px 14px 0px #cc3300, 24px 14px 0px #000, 26px 14px 0px #cc3300,
    28px 14px 0px #cc3300, 30px 14px 0px #cc3300, 32px 14px 0px #cc3300,
    2px 16px 0px #000, 4px 16px 0px #000, 6px 16px 0px #000, 8px 16px 0px #000,
    10px 16px 0px #000, 12px 16px 0px #000, 14px 16px 0px #000,
    16px 16px 0px #000, 18px 16px 0px #000, 20px 16px 0px #000,
    22px 16px 0px #000, 24px 16px 0px #000, 26px 16px 0px #000,
    28px 16px 0px #000, 30px 16px 0px #000, 32px 16px 0px #000,
    2px 18px 0px #cc3300, 4px 18px 0px #cc3300, 6px 18px 0px #cc3300,
    8px 18px 0px #cc3300, 10px 18px 0px #cc3300, 12px 18px 0px #cc3300,
    14px 18px 0px #cc3300, 16px 18px 0px #000, 18px 18px 0px #cc3300,
    20px 18px 0px #cc3300, 22px 18px 0px #cc3300, 24px 18px 0px #cc3300,
    26px 18px 0px #cc3300, 28px 18px 0px #cc3300, 30px 18px 0px #cc3300,
    32px 18px 0px #000, 2px 20px 0px #cc3300, 4px 20px 0px #cc3300,
    6px 20px 0px #cc3300, 8px 20px 0px #cc3300, 10px 20px 0px #cc3300,
    12px 20px 0px #cc3300, 14px 20px 0px #cc3300, 16px 20px 0px #000,
    18px 20px 0px #cc3300, 20px 20px 0px #cc3300, 22px 20px 0px #cc3300,
    24px 20px 0px #cc3300, 26px 20px 0px #cc3300, 28px 20px 0px #cc3300,
    30px 20px 0px #cc3300, 32px 20px 0px #000, 2px 22px 0px #cc3300,
    4px 22px 0px #cc3300, 6px 22px 0px #cc3300, 8px 22px 0px #cc3300,
    10px 22px 0px #cc3300, 12px 22px 0px #cc3300, 14px 22px 0px #cc3300,
    16px 22px 0px #000, 18px 22px 0px #cc3300, 20px 22px 0px #cc3300,
    22px 22px 0px #cc3300, 24px 22px 0px #cc3300, 26px 22px 0px #cc3300,
    28px 22px 0px #cc3300, 30px 22px 0px #cc3300, 32px 22px 0px #000,
    2px 24px 0px #000, 4px 24px 0px #000, 6px 24px 0px #000, 8px 24px 0px #000,
    10px 24px 0px #000, 12px 24px 0px #000, 14px 24px 0px #000,
    16px 24px 0px #000, 18px 24px 0px #000, 20px 24px 0px #000,
    22px 24px 0px #000, 24px 24px 0px #000, 26px 24px 0px #000,
    28px 24px 0px #000, 30px 24px 0px #000, 32px 24px 0px #000,
    2px 26px 0px #cc3300, 4px 26px 0px #cc3300, 6px 26px 0px #cc3300,
    8px 26px 0px #000, 10px 26px 0px #cc3300, 12px 26px 0px #cc3300,
    14px 26px 0px #cc3300, 16px 26px 0px #cc3300, 18px 26px 0px #cc3300,
    20px 26px 0px #cc3300, 22px 26px 0px #cc3300, 24px 26px 0px #000,
    26px 26px 0px #cc3300, 28px 26px 0px #cc3300, 30px 26px 0px #cc3300,
    32px 26px 0px #cc3300, 2px 28px 0px #cc3300, 4px 28px 0px #cc3300,
    6px 28px 0px #cc3300, 8px 28px 0px #000, 10px 28px 0px #cc3300,
    12px 28px 0px #cc3300, 14px 28px 0px #cc3300, 16px 28px 0px #cc3300,
    18px 28px 0px #cc3300, 20px 28px 0px #cc3300, 22px 28px 0px #cc3300,
    24px 28px 0px #000, 26px 28px 0px #cc3300, 28px 28px 0px #cc3300,
    30px 28px 0px #cc3300, 32px 28px 0px #cc3300, 2px 30px 0px #cc3300,
    4px 30px 0px #cc3300, 6px 30px 0px #cc3300, 8px 30px 0px #000,
    10px 30px 0px #cc3300, 12px 30px 0px #cc3300, 14px 30px 0px #cc3300,
    16px 30px 0px #cc3300, 18px 30px 0px #cc3300, 20px 30px 0px #cc3300,
    22px 30px 0px #cc3300, 24px 30px 0px #000, 26px 30px 0px #cc3300,
    28px 30px 0px #cc3300, 30px 30px 0px #cc3300, 32px 30px 0px #cc3300,
    2px 32px 0px #000, 4px 32px 0px #000, 6px 32px 0px #000, 8px 32px 0px #000,
    10px 32px 0px #000, 12px 32px 0px #000, 14px 32px 0px #000,
    16px 32px 0px #000, 18px 32px 0px #000, 20px 32px 0px #000,
    22px 32px 0px #000, 24px 32px 0px #000, 26px 32px 0px #000,
    28px 32px 0px #000, 30px 32px 0px #000, 32px 32px 0px #000;
}

.mario-ee-brick-left {
  transform: translateX(-60px);
}

/* Invisible hover zone over the gap between bricks */
.mario-ee-box {
  position: absolute;
  left: 30px;
  top: 0;
  background-color: transparent;
  z-index: 5;
  width: 34px;
  height: 34px;
  cursor: pointer;
}

/* Pop-out wrapper — hidden until hover */
.mario-ee-mush {
  position: absolute;
  left: 30px;
  top: 0;
  height: 2px;
  width: 2px;
  opacity: 0;
  z-index: -1;
  pointer-events: none;
}

/* ? block pixel art (inside .mush) */
.mario-ee-qblock {
  height: 2px;
  width: 2px;
  box-shadow: 4px 2px 0px #ce3100, 6px 2px 0px #ce3100, 8px 2px 0px #ce3100,
    10px 2px 0px #ce3100, 12px 2px 0px #ce3100, 14px 2px 0px #ce3100,
    16px 2px 0px #ce3100, 18px 2px 0px #ce3100, 20px 2px 0px #ce3100,
    22px 2px 0px #ce3100, 24px 2px 0px #ce3100, 26px 2px 0px #ce3100,
    28px 2px 0px #ce3100, 30px 2px 0px #ce3100, 2px 4px 0px #ce3100,
    4px 4px 0px #ff9c31, 6px 4px 0px #ff9c31, 8px 4px 0px #ff9c31,
    10px 4px 0px #ff9c31, 12px 4px 0px #ff9c31, 14px 4px 0px #ff9c31,
    16px 4px 0px #ff9c31, 18px 4px 0px #ff9c31, 20px 4px 0px #ff9c31,
    22px 4px 0px #ff9c31, 24px 4px 0px #ff9c31, 26px 4px 0px #ff9c31,
    28px 4px 0px #ff9c31, 30px 4px 0px #ff9c31, 32px 4px 0px #000,
    2px 6px 0px #ce3100, 4px 6px 0px #ff9c31, 6px 6px 0px #000,
    8px 6px 0px #ff9c31, 10px 6px 0px #ff9c31, 12px 6px 0px #ff9c31,
    14px 6px 0px #ff9c31, 16px 6px 0px #ff9c31, 18px 6px 0px #ff9c31,
    20px 6px 0px #ff9c31, 22px 6px 0px #ff9c31, 24px 6px 0px #ff9c31,
    26px 6px 0px #ff9c31, 28px 6px 0px #000, 30px 6px 0px #ff9c31,
    32px 6px 0px #000, 2px 8px 0px #ce3100, 4px 8px 0px #ff9c31,
    6px 8px 0px #ff9c31, 8px 8px 0px #ff9c31, 10px 8px 0px #ff9c31,
    12px 8px 0px #ce3100, 14px 8px 0px #ce3100, 16px 8px 0px #ce3100,
    18px 8px 0px #ce3100, 20px 8px 0px #ce3100, 22px 8px 0px #ff9c31,
    24px 8px 0px #ff9c31, 26px 8px 0px #ff9c31, 28px 8px 0px #ff9c31,
    30px 8px 0px #ff9c31, 32px 8px 0px #000, 2px 10px 0px #ce3100,
    4px 10px 0px #ff9c31, 6px 10px 0px #ff9c31, 8px 10px 0px #ff9c31,
    10px 10px 0px #ce3100, 12px 10px 0px #ce3100, 14px 10px 0px #000,
    16px 10px 0px #000, 18px 10px 0px #000, 20px 10px 0px #ce3100,
    22px 10px 0px #ce3100, 24px 10px 0px #ff9c31, 26px 10px 0px #ff9c31,
    28px 10px 0px #ff9c31, 30px 10px 0px #ff9c31, 32px 10px 0px #000,
    2px 12px 0px #ce3100, 4px 12px 0px #ff9c31, 6px 12px 0px #ff9c31,
    8px 12px 0px #ff9c31, 10px 12px 0px #ce3100, 12px 12px 0px #ce3100,
    14px 12px 0px #000, 16px 12px 0px #ff9c31, 18px 12px 0px #ff9c31,
    20px 12px 0px #ce3100, 22px 12px 0px #ce3100, 24px 12px 0px #000,
    26px 12px 0px #ff9c31, 28px 12px 0px #ff9c31, 30px 12px 0px #ff9c31,
    32px 12px 0px #000, 2px 14px 0px #ce3100, 4px 14px 0px #ff9c31,
    6px 14px 0px #ff9c31, 8px 14px 0px #ff9c31, 10px 14px 0px #ce3100,
    12px 14px 0px #ce3100, 14px 14px 0px #000, 16px 14px 0px #ff9c31,
    18px 14px 0px #ff9c31, 20px 14px 0px #ce3100, 22px 14px 0px #ce3100,
    24px 14px 0px #000, 26px 14px 0px #ff9c31, 28px 14px 0px #ff9c31,
    30px 14px 0px #ff9c31, 32px 14px 0px #000, 2px 16px 0px #ce3100,
    4px 16px 0px #ff9c31, 6px 16px 0px #ff9c31, 8px 16px 0px #ff9c31,
    10px 16px 0px #ff9c31, 12px 16px 0px #000, 14px 16px 0px #000,
    16px 16px 0px #ff9c31, 18px 16px 0px #ce3100, 20px 16px 0px #ce3100,
    22px 16px 0px #ce3100, 24px 16px 0px #000, 26px 16px 0px #ff9c31,
    28px 16px 0px #ff9c31, 30px 16px 0px #ff9c31, 32px 16px 0px #000,
    2px 18px 0px #ce3100, 4px 18px 0px #ff9c31, 6px 18px 0px #ff9c31,
    8px 18px 0px #ff9c31, 10px 18px 0px #ff9c31, 12px 18px 0px #ff9c31,
    14px 18px 0px #ff9c31, 16px 18px 0px #ce3100, 18px 18px 0px #ce3100,
    20px 18px 0px #000, 22px 18px 0px #000, 24px 18px 0px #000,
    26px 18px 0px #ff9c31, 28px 18px 0px #ff9c31, 30px 18px 0px #ff9c31,
    32px 18px 0px #000, 2px 20px 0px #ce3100, 4px 20px 0px #ff9c31,
    6px 20px 0px #ff9c31, 8px 20px 0px #ff9c31, 10px 20px 0px #ff9c31,
    12px 20px 0px #ff9c31, 14px 20px 0px #ff9c31, 16px 20px 0px #ce3100,
    18px 20px 0px #ce3100, 20px 20px 0px #000, 22px 20px 0px #ff9c31,
    24px 20px 0px #ff9c31, 26px 20px 0px #ff9c31, 28px 20px 0px #ff9c31,
    30px 20px 0px #ff9c31, 32px 20px 0px #000, 2px 22px 0px #ce3100,
    4px 22px 0px #ff9c31, 6px 22px 0px #ff9c31, 8px 22px 0px #ff9c31,
    10px 22px 0px #ff9c31, 12px 22px 0px #ff9c31, 14px 22px 0px #ff9c31,
    16px 22px 0px #ff9c31, 18px 22px 0px #000, 20px 22px 0px #000,
    22px 22px 0px #ff9c31, 24px 22px 0px #ff9c31, 26px 22px 0px #ff9c31,
    28px 22px 0px #ff9c31, 30px 22px 0px #ff9c31, 32px 22px 0px #000,
    2px 24px 0px #ce3100, 4px 24px 0px #ff9c31, 6px 24px 0px #ff9c31,
    8px 24px 0px #ff9c31, 10px 24px 0px #ff9c31, 12px 24px 0px #ff9c31,
    14px 24px 0px #ff9c31, 16px 24px 0px #ce3100, 18px 24px 0px #ce3100,
    20px 24px 0px #ff9c31, 22px 24px 0px #ff9c31, 24px 24px 0px #ff9c31,
    26px 24px 0px #ff9c31, 28px 24px 0px #ff9c31, 30px 24px 0px #ff9c31,
    32px 24px 0px #000, 2px 26px 0px #ce3100, 4px 26px 0px #ff9c31,
    6px 26px 0px #ff9c31, 8px 26px 0px #ff9c31, 10px 26px 0px #ff9c31,
    12px 26px 0px #ff9c31, 14px 26px 0px #ff9c31, 16px 26px 0px #ce3100,
    18px 26px 0px #ce3100, 20px 26px 0px #000, 22px 26px 0px #ff9c31,
    24px 26px 0px #ff9c31, 26px 26px 0px #ff9c31, 28px 26px 0px #ff9c31,
    30px 26px 0px #ff9c31, 32px 26px 0px #000, 2px 28px 0px #ce3100,
    4px 28px 0px #ff9c31, 6px 28px 0px #000, 8px 28px 0px #ff9c31,
    10px 28px 0px #ff9c31, 12px 28px 0px #ff9c31, 14px 28px 0px #ff9c31,
    16px 28px 0px #ff9c31, 18px 28px 0px #000, 20px 28px 0px #000,
    22px 28px 0px #ff9c31, 24px 28px 0px #ff9c31, 26px 28px 0px #ff9c31,
    28px 28px 0px #000, 30px 28px 0px #ff9c31, 32px 28px 0px #000,
    2px 30px 0px #ce3100, 4px 30px 0px #ff9c31, 6px 30px 0px #ff9c31,
    8px 30px 0px #ff9c31, 10px 30px 0px #ff9c31, 12px 30px 0px #ff9c31,
    14px 30px 0px #ff9c31, 16px 30px 0px #ff9c31, 18px 30px 0px #ff9c31,
    20px 30px 0px #ff9c31, 22px 30px 0px #ff9c31, 24px 30px 0px #ff9c31,
    26px 30px 0px #ff9c31, 28px 30px 0px #ff9c31, 30px 30px 0px #ff9c31,
    32px 30px 0px #000, 2px 32px 0px #000, 4px 32px 0px #000, 6px 32px 0px #000,
    8px 32px 0px #000, 10px 32px 0px #000, 12px 32px 0px #000,
    14px 32px 0px #000, 16px 32px 0px #000, 18px 32px 0px #000,
    20px 32px 0px #000, 22px 32px 0px #000, 24px 32px 0px #000,
    26px 32px 0px #000, 28px 32px 0px #000, 30px 32px 0px #000,
    32px 32px 0px #000;
  z-index: 3;
}

/* CSS sibling selector: hover box triggers pop-out of adjacent .mush */
.mario-ee-box:hover + .mario-ee-mush {
  animation: mario-ee-pop 0.5s linear forwards;
  opacity: 1;
}

@keyframes mario-ee-pop {
  0%   { transform: scale(0.8) translate(-8px, 0px); }
  50%  { transform: scale(1.1) translate(-8px, -80px); }
  100% { transform: scale(1.1) translate(-8px, -45px); }
}
`;

export default function MarioBrickEasterEgg({ scale = 1.5, className = '', style }: Props) {
  const achieved = useRef(false);

  const handlePop = () => {
    if (!achieved.current) {
      achieved.current = true;
      toast.success('🍄 1-UP! Hidden achievement unlocked.');
    }
  };

  return (
    <div
      className={className}
      style={{
        display: 'inline-block',
        transform: `scale(${scale})`,
        transformOrigin: 'center center',
        ...style,
      }}
    >
      <style>{CSS}</style>
      <div className="mario-ee-scene">
        {/* Left brick — shifted 60px left from origin */}
        <div className="mario-ee-brick mario-ee-brick-left" />
        {/* Right brick — at origin */}
        <div className="mario-ee-brick" />
        {/* Invisible hover zone (must be immediately before .mush for CSS + selector) */}
        <div className="mario-ee-box" onMouseEnter={handlePop} />
        {/* Pop-out wrapper: ? block inside, hidden until hover */}
        <div className="mario-ee-mush">
          <div className="mario-ee-qblock" />
        </div>
      </div>
    </div>
  );
}
