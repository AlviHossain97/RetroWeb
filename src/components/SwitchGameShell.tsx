import { useState } from 'react';
import type { ReactNode } from 'react';
import { Save, Download, RotateCcw, Expand, LogOut, AlertTriangle, Maximize } from 'lucide-react';
import type { ControllerButton, ControllerVisualState } from '../gamepad/types';

interface BootState { message: string; percent: number; }
interface RuntimeErrorState { userMessage: string; technicalMessage?: string; }

interface SwitchGameShellProps {
  title: string;
  bootState: BootState | null;
  runtimeError: RuntimeErrorState | null;
  showSaveIndicator: boolean;
  onSave: () => void;
  onLoad: () => void;
  onReset: () => void;
  onFullscreen: () => void;
  onExit: () => void;
  onMenu: () => void;
  onRetry: () => void;
  showOverlay: boolean;
  onOverlayToggle: () => void;
  controllerState?: ControllerVisualState | null;
  children: ReactNode;
}

/* ─── CSS ───────────────────────────────────────────────────────────────
   Based on Uiverse.io by necatimertmetin — adapted for full-viewport use.
   Key change: switch-card fills the viewport; joy-con button positions
   converted from absolute px to % so they scale with the flexible height.
─────────────────────────────────────────────────────────────────────── */
const CSS = `
@keyframes sw-spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }

.sw-outer {
  position: fixed;
  inset: 0;
  background: #0d0d10;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

/* From Uiverse.io by necatimertmetin */ 
.switch-card {
  display: flex;
  align-items: stretch;
  width: 1410px;
  height: 590px;
  margin-left: 150px;
  transform: scale(1);
  transform-origin: center center;
}
.screen-outline {
  display: flex;
  align-items: stretch;
  padding: 30px 42px;
  justify-content: center;
  border-radius: 2px;
  background: rgb(71, 77, 79);
  background: linear-gradient(
    180deg,
    rgba(71, 77, 79, 1) 0%,
    rgba(90, 97, 100, 1) 3%,
    rgba(46, 50, 51, 1) 5%,
    rgba(46, 50, 51, 1) 100%
  );
}
.screen-border {
  border-top: 51px solid black;
  border-bottom: 51px solid black;
  border-left: 75px solid black;
  border-right: 75px solid black;
  border-radius: 18px;
  flex: 1;
  background-color: black;
  width: 789px;
  display: flex;
}
.screen {
  border-radius: 2px;
  background: rgb(38, 39, 43);
  background: linear-gradient(
    135deg,
    rgba(38, 39, 43, 1) 0%,
    rgba(49, 52, 62, 1) 49%,
    rgba(38, 39, 43, 1) 100%
  );
  flex: 1;
  overflow: hidden;
  cursor: pointer;
}
.screen img {
  height: 100%;
  width: 100%;
  object-fit: cover;
}
.joy-con {
  background-color: pink;
  width: 195px;
  height: 590px;
  position: relative;
}
.joy-con.left {
  border-top-left-radius: 120px;
  border-bottom-left-radius: 120px;
  background: rgb(0, 186, 219);
  background: linear-gradient(
    148deg,
    rgba(0, 186, 219, 1) 0%,
    rgba(0, 185, 220, 1) 100%
  );
  box-shadow:
    inset 3px -4px 10px #058ca5,
    inset 0px 5px 3px #6ad9ed;
  border-top-right-radius: 12px;
  border-bottom-right-radius: 12px;
}
.joy-con.right {
  border-top-right-radius: 120px;
  border-bottom-right-radius: 120px;
  border-top-left-radius: 12px;
  border-bottom-left-radius: 12px;
  background: rgb(250, 97, 93);
  background: linear-gradient(
    148deg,
    rgba(250, 97, 93, 1) 0%,
    rgba(239, 79, 77, 1) 100%
  );
  box-shadow:
    inset -3px -4px 10px #d12621,
    inset 0px 5px 3px #fd877c;
}

.joy-con.left .minus {
  position: absolute;
  top: 54px;
  width: 30px;
  height: 6px;
  border: 2.4px solid #222;
  border-radius: 3px;
  right: 15px;
  background-color: #3c3d41;
}

.joy-con.left .joystick {
  left: 50%;
  transform: translate(-50%);
  top: 105px;
}
.joy-con.right .joystick {
  top: 263px;
  left: 42px;
  filter: contrast(130%) drop-shadow(0px 1px 2px #00000088);
}
.joystick {
  background-color: #2d2e33;
  border-radius: 100%;
  height: 84px;
  width: 84px;
  position: relative;
  border: 1px solid #2d2e33;
  overflow: hidden;
  cursor: pointer;
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  grid-template-rows: repeat(2, 1fr);
  grid-column-gap: 1px;
  grid-row-gap: 1px;
  filter: drop-shadow(0px 1px 2px #00000088);
}
.joystick-edge {
  background-color: #444;
}
.joystick-inner-border {
  position: absolute;

  top: 50%;
  left: 50%;
  background-color: #2d2e33;
  padding: 1px;
  z-index: 2;
  border-radius: 100%;
  transform: translate(-50%, -50%);
  display: flex;
  align-items: center;
  justify-content: center;
}
.joystick-inner {
  width: 66px;
  height: 66px;
  border-radius: 50%;
  background-color: #282c2f;
  box-shadow:
    inset 0px -4px 4px rgb(49, 49, 49),
    inset 0px 4px 12px rgb(124, 124, 124),
    inset 0px 4px 6px rgb(0, 0, 0);
  z-index: 3;
  position: relative;
}

.numpad-container {
  position: absolute;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  width: 132px;
  height: 132px;
}
.joy-con.left .numpad-container {
  top: 246px;
  left: 36px;
  color: #1b1b1c;
  font-size: 24px;
}
.joy-con.right .numpad-container {
  top: 86px;
  left: 24px;
  color: #d7d7d7;
  font-size: 21px;
}

.numpad-middle {
  display: flex;
  align-items: center;
  gap: 48px;
}

.plus-symbol {
  width: 30px;
  height: 30px;
  position: absolute;
  display: inline-block;
  top: 44px;
  left: 15px;
  cursor: pointer;
}
.plus-symbol-overlap-fixer {
  position: absolute;
  background-color: #333;
  width: 6px;
  height: calc(100% - 6px);
  border-radius: 1px;
  top: 50%;
  left: 50%;
  z-index: 3;
  transform: translate(-50%, -50%);
}
.plus-symbol::before,
.plus-symbol::after {
  content: "";
  position: absolute;
  background-color: #333;
  border: 0.8px solid #222;
  border-radius: 1px;
}

.plus-symbol::before {
  width: 6px;
  height: 86.5%;
  left: 50%;
  transform: translateX(-50%);
}

.plus-symbol::after {
  width: 86.5%;
  height: 6px;
  top: 50%;
  transform: translateY(-50%);
}

.numpad-button {
  width: 36px;
  height: 36px;
  background-color: #505050;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  border: 1px solid #2d2e33;
  box-shadow:
    inset -0.5px -0.5px 1.5px rgba(92, 92, 92, 0.5),
    /* İç gölgeler küçük boyuta uygun şekilde azaltıldı */ inset 0.2px 1px 0.8px
      rgba(143, 143, 143, 0.658),
    inset /* Üst kısımda hafif ışık efekti */ -1px -1px 2px
      rgba(31, 31, 31, 0.76),
    0px 0px 3px #00000055;
}
.numpad-part {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}

.record-button {
  width: 30px;
  height: 30px;
  cursor: pointer;
  border: 3px solid #2d2e33;
  border-radius: 3px;
  position: absolute;
  top: 402px;
  left: 117px;
  background: rgb(96, 95, 101);
  background: linear-gradient(135deg, #605f65 0%, rgba(60, 61, 66, 1) 100%);
  display: flex;
  align-items: center;
  justify-content: center;
}
.record-button-inner {
  width: 12px;
  height: 12px;
  background: rgb(96, 95, 101);
  background: linear-gradient(135deg, #605f65 0%, rgba(60, 61, 66, 1) 100%);
  border: 1px solid #2d2e33;
  border-radius: 50%;
}

.home-button-border {
  position: absolute;
  cursor: pointer;
  top: 398px;
  left: 36px;
  border: 1px solid #1b1b1c;
  background: linear-gradient(135deg, #a0a0a0 0%, #303030 100%);
  height: 42px;
  width: 42px;
  padding: 3px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
}
.home-button {
  width: 36px;
  height: 36px;
  border: 2.7px solid #1b1b1c;
  background: linear-gradient(180deg, #6b6b6b 0%, #303030 100%);
  border-radius: 50%;
  display: flex;
  color: black;
  align-items: center;
  justify-content: center;
  font-size: 27px;
}

.button {
  cursor: pointer;
}
.heart-card {
  position: relative;
  width: 200px;
  height: 200px;
  background-color: #ff6b6b;
  transform: rotate(-45deg);
  margin-top: 50px;
  z-index: 2;
}

.heart-card::before,
.heart-card::after {
  content: "";
  position: absolute;
  width: 200px;
  height: 200px;
  background-color: #ff6b6b;
  border-radius: 50%;
  z-index: -1;
}

.heart-card::before {
  top: -100px;
  left: 0;
}

.heart-card::after {
  left: 100px;
  top: 0;
}

.content {
  position: absolute;
  top: 50px;
  left: 50px;
  width: 100px;
  height: 100px;
  transform: rotate(40deg);
  text-align: center;
  color: white;
}

.content h2 {
  font-size: 18px;
  margin-bottom: 10px;
}

.content p {
  font-size: 14px;
}

.screen { position: relative; }
.screen canvas {
  width: 100% !important;
  height: 100% !important;
  object-fit: contain;
  display: block;
  outline: none;
}

.sw-shoulder {
  position: absolute;
  top: 0;
  left: 12px;
  right: 12px;
  height: 6px;
  border-radius: 0 0 5px 5px;
  background: rgba(0, 0, 0, 0.28);
  overflow: hidden;
}
.sw-shoulder-fill {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  border-radius: 0 0 3px 3px;
  background: rgba(0, 0, 0, 0.55);
  transition: height 70ms linear;
}

.joy-con.left .minus.btn-active,
.plus-symbol.btn-active,
.home-button-border.btn-active {
  opacity: 0.4;
}
.numpad-button.btn-active {
  transform: scale(0.82);
  filter: brightness(1.3);
}
.joystick-inner {
  transition: transform 70ms linear;
}
.numpad-button.btn-a { background-color: #8b1a14; }
.numpad-button.btn-b { background-color: #4a3a10; }
.numpad-button.btn-x { background-color: #1a2a4a; }
.numpad-button.btn-y { background-color: #1a3a1a; }

.sw-ctrl-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
  background: rgba(255, 255, 255, 0.04);
  border-top: 1px solid rgba(255, 255, 255, 0.07);
  padding: 5px 12px;
  height: 40px;
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
}
.sw-ctrl-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 8px;
  border-radius: 5px;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.09);
  color: rgba(255, 255, 255, 0.55);
  font-size: 11px;
  cursor: pointer;
  transition: all 0.15s;
  white-space: nowrap;
  font-family: system-ui, sans-serif;
  user-select: none;
}
.sw-ctrl-btn:hover {
  background: rgba(255, 255, 255, 0.12);
  color: rgba(255, 255, 255, 0.9);
}
.sw-ctrl-btn.sw-exit:hover {
  background: rgba(204, 0, 0, 0.2);
  color: #ff6666;
  border-color: rgba(204, 0, 0, 0.3);
}
.sw-game-title {
  font-family: monospace;
  font-size: 10px;
  color: rgba(255, 255, 255, 0.35);
  letter-spacing: 0.5px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 220px;
}

@media (max-width: 600px) {
  .joy-con { display: none; }
  .screen-outline { padding: 0; }
  .screen-border { border-width: 0 !important; border-radius: 0; }
}
`;

/* ── Joystick widget (preserves exact Uiverse structure) ────────── */
function JoyCon_Joystick({ x = 0, y = 0, pressed = false }: { x?: number; y?: number; pressed?: boolean }) {
  return (
    <div className="joystick">
      <div className="joystick-edge" />
      <div className="joystick-edge" />
      <div className="joystick-edge" />
      <div className="joystick-edge" />
      <div className="joystick-inner-border">
        <div
          className="joystick-inner"
          style={{
            transform: `translate(${x * 4}px, ${y * 4}px) scale(${pressed ? 0.9 : 1})`,
          }}
        />
      </div>
    </div>
  );
}

/* ── Main component ─────────────────────────────────────────────── */
export default function SwitchGameShell({
  title, bootState, runtimeError, showSaveIndicator,
  onSave, onLoad, onReset, onFullscreen, onExit, onMenu, onRetry,
  controllerState, children,
}: SwitchGameShellProps) {
  const [showTechnical, setShowTechnical] = useState(false);

  const b  = (btn: ControllerButton) => controllerState?.buttons[btn] ? 'btn-active' : '';
  const v  = (btn: ControllerButton) => controllerState?.values[btn] ?? 0;
  const ls = controllerState?.leftStick  ?? { x: 0, y: 0, pressed: false };
  const rs = controllerState?.rightStick ?? { x: 0, y: 0, pressed: false };

  return (
    <div className="sw-outer">
      <style>{CSS}</style>

      <div className="switch-card">

        {/* ── Left Joy-Con (cyan) ─────────────────────── */}
        <div className="joy-con left">
          {/* LB shoulder */}
          <div className="sw-shoulder">
            <div className="sw-shoulder-fill" style={{ height: `${Math.round(v('lb') * 100)}%` }} />
          </div>
          {/* LT depth indicator */}
          <div style={{ position: 'absolute', top: 4, right: 4, width: 5, maxHeight: 14, borderRadius: '0 0 2px 2px', background: 'rgba(0,0,0,0.55)', height: `${Math.round(14 * v('lt'))}px`, transition: 'height 70ms linear' }} />

          {/* − button */}
          <div className={`minus ${b('minus')}`} onClick={onExit} title="Exit (−)" />

          {/* Left stick */}
          <JoyCon_Joystick x={ls.x} y={ls.y} pressed={ls.pressed} />

          {/* D-pad */}
          <div className="numpad-container">
            <div className="numpad-part">
              <div className={`numpad-button ${b('dpadUp')}`}>▲</div>
            </div>
            <div className="numpad-middle">
              <div className={`numpad-button ${b('dpadLeft')}`}>◀</div>
              <div className={`numpad-button ${b('dpadRight')}`}>▶</div>
            </div>
            <div className="numpad-part">
              <div className={`numpad-button ${b('dpadDown')}`}>▼</div>
            </div>
          </div>

          {/* Capture */}
          <div className="record-button"><div className="record-button-inner" /></div>
        </div>

        {/* ── Screen ──────────────────────────────────── */}
        <div className="screen-outline">
          <div className="screen-border">
            <div className="screen" style={{ position: 'relative' }}>
              {children}

              {/* Boot overlay */}
              {bootState && !runtimeError && (
                <div style={{ position: 'absolute', inset: 0, zIndex: 10, background: 'rgba(0,0,0,0.93)', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 10 }}>
                  <div style={{ fontFamily: 'monospace', fontSize: 24, fontWeight: 900, color: '#cc0000', letterSpacing: 4 }}>RETROWEB</div>
                  <div style={{ width: 36, height: 36, border: '3px solid #333', borderTopColor: '#cc0000', borderRadius: '50%', animation: 'sw-spin 0.8s linear infinite' }} />
                  <p style={{ color: '#aaa', fontSize: 13, margin: 0 }}>{bootState.message}</p>
                  <div style={{ width: 200, height: 3, background: '#222', borderRadius: 2, overflow: 'hidden' }}>
                    <div style={{ width: `${Math.max(4, bootState.percent)}%`, height: '100%', background: 'linear-gradient(90deg, #cc0000, #ff4400)', transition: 'width 0.3s ease' }} />
                  </div>
                </div>
              )}

              {/* Error overlay */}
              {runtimeError && (
                <div style={{ position: 'absolute', inset: 0, zIndex: 10, background: 'rgba(0,0,0,0.96)', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: 24, gap: 10 }}>
                  <AlertTriangle size={36} style={{ color: '#cc0000' }} />
                  <h3 style={{ color: '#fff', fontSize: 16, fontWeight: 700, margin: 0 }}>Load Failed</h3>
                  <p style={{ color: '#aaa', fontSize: 13, textAlign: 'center', maxWidth: 300, margin: 0 }}>{runtimeError.userMessage}</p>
                  <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', justifyContent: 'center' }}>
                    <button onClick={onRetry} style={{ padding: '8px 20px', background: '#cc0000', color: '#fff', borderRadius: 6, border: 'none', cursor: 'pointer', fontWeight: 700 }}>Try Again</button>
                    <button onClick={onExit}  style={{ padding: '8px 20px', background: '#222', color: '#ccc', borderRadius: 6, border: '1px solid #333', cursor: 'pointer' }}>Exit</button>
                  </div>
                  <button onClick={() => setShowTechnical(p => !p)} style={{ color: '#555', fontSize: 11, background: 'none', border: 'none', cursor: 'pointer', textTransform: 'uppercase', letterSpacing: 1 }}>
                    {showTechnical ? 'Hide' : 'Show'} details
                  </button>
                  {showTechnical && runtimeError.technicalMessage && (
                    <pre style={{ fontSize: 10, color: '#ff6666', background: '#111', border: '1px solid #333', padding: 8, borderRadius: 4, maxHeight: 90, overflow: 'auto', maxWidth: '100%', margin: 0 }}>
                      {runtimeError.technicalMessage}
                    </pre>
                  )}
                </div>
              )}

              {/* Auto-save indicator */}
              <div style={{
                position: 'absolute', bottom: 8, right: 8, zIndex: 20,
                display: 'flex', alignItems: 'center', gap: 4,
                background: 'rgba(0,0,0,0.7)', border: '1px solid rgba(255,255,255,0.1)',
                borderRadius: 20, padding: '3px 10px', fontSize: 11, color: '#ccc',
                opacity: showSaveIndicator ? 1 : 0,
                transform: showSaveIndicator ? 'translateY(0)' : 'translateY(4px)',
                transition: 'opacity 0.3s, transform 0.3s', pointerEvents: 'none',
              }}>
                <Save size={11} style={{ color: '#cc0000' }} /> Auto-saved
              </div>
            </div>
          </div>
        </div>

        {/* ── Right Joy-Con (red) ──────────────────────── */}
        <div className="joy-con right">
          {/* RB shoulder */}
          <div className="sw-shoulder">
            <div className="sw-shoulder-fill" style={{ height: `${Math.round(v('rb') * 100)}%` }} />
          </div>
          {/* RT depth indicator */}
          <div style={{ position: 'absolute', top: 4, left: 4, width: 5, maxHeight: 14, borderRadius: '0 0 2px 2px', background: 'rgba(0,0,0,0.55)', height: `${Math.round(14 * v('rt'))}px`, transition: 'height 70ms linear' }} />

          {/* + button */}
          <div className={`plus-symbol ${b('plus')}`} onClick={onFullscreen} title="Fullscreen (+)">
            <span className="plus-symbol-overlap-fixer" />
          </div>

          {/* ABXY */}
          <div className="numpad-container">
            <div className="numpad-part">
              <div className={`numpad-button btn-x ${b('x')}`} title="X">X</div>
            </div>
            <div className="numpad-middle">
              <div className={`numpad-button btn-y ${b('y')}`} title="Y">Y</div>
              <div className={`numpad-button btn-a ${b('a')}`} onClick={onSave} title="A – Save">A</div>
            </div>
            <div className="numpad-part">
              <div className={`numpad-button btn-b ${b('b')}`} onClick={onLoad} title="B – Load">B</div>
            </div>
          </div>

          {/* Right stick */}
          <JoyCon_Joystick x={rs.x} y={rs.y} pressed={rs.pressed} />

          {/* Home → Save states */}
          <div className={`home-button-border ${b('home')}`} onClick={onMenu} title="Save States">
            <div className="home-button">⌂</div>
          </div>

          {/* Capture */}
          <div className="record-button"><div className="record-button-inner" /></div>
        </div>

      </div>{/* .switch-card */}

      {/* ── Controls bar ────────────────────────────── */}
      <div className="sw-ctrl-bar">
        <span className="sw-game-title">{title}</span>
        <div style={{ display: 'flex', gap: 4, flexWrap: 'nowrap' }}>
          <button className="sw-ctrl-btn" onClick={onSave}       title="Save state (F1)"><Save size={12} /> Save</button>
          <button className="sw-ctrl-btn" onClick={onLoad}       title="Load state (F4)"><Download size={12} /> Load</button>
          <button className="sw-ctrl-btn" onClick={onReset}      title="Reset"><RotateCcw size={12} /></button>
          <button className="sw-ctrl-btn" onClick={onMenu}       title="Save slots"><Maximize size={12} /></button>
          <button className="sw-ctrl-btn" onClick={onFullscreen} title="Fullscreen (F11)"><Expand size={12} /></button>
          <button className="sw-ctrl-btn sw-exit" onClick={onExit} title="Exit to Library"><LogOut size={12} /></button>
        </div>
      </div>

    </div>
  );
}

