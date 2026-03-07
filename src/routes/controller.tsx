import { useEffect, useMemo, useState } from "react";
import { Gamepad2, Link2, RotateCcw } from "lucide-react";
import { useGamepadVisualizer } from "../hooks/useGamepadVisualizer";
import type { ControllerButton, MappingOverrides } from "../gamepad/types";
import { loadMappingOverrides, saveMappingOverrides } from "../gamepad/overrides";

const REMAPPABLE_BUTTONS: ControllerButton[] = [
  "a", "b", "x", "y",
  "dpadUp", "dpadDown", "dpadLeft", "dpadRight",
  "lb", "rb", "lt", "rt",
  "minus", "plus", "l3", "r3", "home", "capture",
];

function prettyButtonName(name: ControllerButton): string {
  return name.replace(/([A-Z])/g, " $1").replace(/^./, (s) => s.toUpperCase());
}

export default function ControllerTest() {
  const [overrides, setOverrides] = useState<MappingOverrides>(() => loadMappingOverrides());
  const [waitingFor, setWaitingFor] = useState<ControllerButton | null>(null);
  const [message, setMessage] = useState<string>("");

  const {
    supported,
    connectedPads,
    activeIndex,
    setActiveIndex,
    activePadRaw,
    visualState,
    profileLabel,
  } = useGamepadVisualizer({ overrides });

  useEffect(() => {
    saveMappingOverrides(overrides);
  }, [overrides]);

  useEffect(() => {
    if (!waitingFor || !activePadRaw) return;

    const pressedButtonIndex = activePadRaw.buttons.findIndex((value) => value > 0.65);
    if (pressedButtonIndex >= 0) {
      setOverrides((prev) => ({ ...prev, [waitingFor]: pressedButtonIndex }));
      setMessage(`${prettyButtonName(waitingFor)} mapped to button ${pressedButtonIndex}`);
      setWaitingFor(null);
    }
  }, [activePadRaw, waitingFor]);

  const activeValues = useMemo(() => {
    if (!visualState) return [] as Array<[ControllerButton, number]>;
    return Object.entries(visualState.values) as Array<[ControllerButton, number]>;
  }, [visualState]);

  return (
    <div className="w-full h-full overflow-y-auto p-4 md:p-8">
      <div className="max-w-6xl mx-auto space-y-5">
        <header className="rounded-xl p-5" style={{ background: 'var(--surface-1)', border: '1px solid var(--border-soft)' }}>
          <div className="flex items-center justify-between gap-3 flex-wrap">
            <div>
              <h1 className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>Controller Diagnostics</h1>
              <p className="text-sm mt-1" style={{ color: 'var(--text-muted)' }}>
                Live Gamepad API monitor + mapping calibration. This does not intercept gameplay input.
              </p>
            </div>
            <div className="px-3 py-2 rounded-lg text-xs font-semibold" style={{ background: supported ? 'rgba(34,197,94,0.12)' : 'rgba(239,68,68,0.12)', color: supported ? '#22c55e' : '#ef4444', border: `1px solid ${supported ? 'rgba(34,197,94,0.28)' : 'rgba(239,68,68,0.28)'}` }}>
              {supported ? 'Gamepad API available' : 'Gamepad API unavailable'}
            </div>
          </div>
        </header>

        <section className="rounded-xl p-4" style={{ background: 'var(--surface-1)', border: '1px solid var(--border-soft)' }}>
          <div className="flex items-center justify-between gap-3 flex-wrap">
            <div>
              <h2 className="text-lg font-semibold" style={{ color: 'var(--text-primary)' }}>Connected Controllers</h2>
              <p className="text-xs" style={{ color: 'var(--text-muted)' }}>Profile: {profileLabel}</p>
            </div>
            <button
              className="px-3 py-2 rounded-lg text-xs font-medium"
              style={{ background: 'var(--surface-3)', border: '1px solid var(--border-soft)', color: 'var(--text-secondary)' }}
              onClick={() => {
                setOverrides({});
                setMessage('Mapping overrides reset.');
              }}
            >
              <RotateCcw size={14} className="inline mr-1" /> Reset overrides
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mt-3">
            {connectedPads.length === 0 && (
              <div className="rounded-lg p-4 text-sm" style={{ background: 'var(--surface-2)', color: 'var(--text-muted)', border: '1px dashed var(--border-soft)' }}>
                Connect a controller and press any button to start diagnostics.
              </div>
            )}
            {connectedPads.map((pad) => (
              <button
                key={pad.index}
                onClick={() => setActiveIndex(pad.index)}
                className="text-left rounded-lg p-3 transition-colors"
                style={{
                  background: activeIndex === pad.index ? 'rgba(204,0,0,0.12)' : 'var(--surface-2)',
                  border: activeIndex === pad.index ? '1px solid rgba(204,0,0,0.35)' : '1px solid var(--border-soft)',
                }}
              >
                <p className="text-sm font-semibold truncate" style={{ color: 'var(--text-primary)' }}>
                  <Gamepad2 size={14} className="inline mr-2" />{pad.id}
                </p>
                <p className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>Index {pad.index} • {pad.mapping || 'unknown mapping'}</p>
              </button>
            ))}
          </div>
        </section>

        <section className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <div className="rounded-xl p-4" style={{ background: 'var(--surface-1)', border: '1px solid var(--border-soft)' }}>
            <h3 className="text-base font-semibold" style={{ color: 'var(--text-primary)' }}>Live Input</h3>
            <div className="grid grid-cols-2 gap-2 mt-3 text-xs">
              <div className="rounded-lg p-2" style={{ background: 'var(--surface-2)' }}>
                <p style={{ color: 'var(--text-muted)' }}>Left Stick</p>
                <p style={{ color: 'var(--text-primary)' }}>{visualState ? `${visualState.leftStick.x.toFixed(2)}, ${visualState.leftStick.y.toFixed(2)}` : '-'}</p>
              </div>
              <div className="rounded-lg p-2" style={{ background: 'var(--surface-2)' }}>
                <p style={{ color: 'var(--text-muted)' }}>Right Stick</p>
                <p style={{ color: 'var(--text-primary)' }}>{visualState ? `${visualState.rightStick.x.toFixed(2)}, ${visualState.rightStick.y.toFixed(2)}` : '-'}</p>
              </div>
              <div className="rounded-lg p-2" style={{ background: 'var(--surface-2)' }}>
                <p style={{ color: 'var(--text-muted)' }}>Left Trigger</p>
                <p style={{ color: 'var(--text-primary)' }}>{visualState ? visualState.triggers.left.toFixed(2) : '-'}</p>
              </div>
              <div className="rounded-lg p-2" style={{ background: 'var(--surface-2)' }}>
                <p style={{ color: 'var(--text-muted)' }}>Right Trigger</p>
                <p style={{ color: 'var(--text-primary)' }}>{visualState ? visualState.triggers.right.toFixed(2) : '-'}</p>
              </div>
            </div>

            <div className="mt-4 grid grid-cols-2 md:grid-cols-3 gap-2">
              {activeValues.map(([name, value]) => (
                <div key={name} className="rounded-md px-2 py-1.5 text-xs" style={{ background: value > 0.45 ? 'rgba(204,0,0,0.12)' : 'var(--surface-2)', border: `1px solid ${value > 0.45 ? 'rgba(204,0,0,0.32)' : 'var(--border-soft)'}` }}>
                  <span style={{ color: 'var(--text-secondary)' }}>{prettyButtonName(name)}</span>
                  <span className="float-right font-semibold" style={{ color: value > 0.45 ? '#ff6666' : 'var(--text-muted)' }}>{value.toFixed(2)}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="rounded-xl p-4" style={{ background: 'var(--surface-1)', border: '1px solid var(--border-soft)' }}>
            <h3 className="text-base font-semibold" style={{ color: 'var(--text-primary)' }}>Calibration / Remap</h3>
            <p className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>Choose a target control then press a physical button. Mapping is persisted locally.</p>
            {message && <p className="mt-3 text-xs" style={{ color: '#22c55e' }}><Link2 size={12} className="inline mr-1" />{message}</p>}

            <div className="mt-3 grid grid-cols-1 md:grid-cols-2 gap-2">
              {REMAPPABLE_BUTTONS.map((btn) => (
                <button
                  key={btn}
                  onClick={() => setWaitingFor(btn)}
                  className="rounded-md px-3 py-2 text-xs text-left"
                  style={{
                    background: waitingFor === btn ? 'rgba(204,0,0,0.14)' : 'var(--surface-2)',
                    border: waitingFor === btn ? '1px solid rgba(204,0,0,0.35)' : '1px solid var(--border-soft)',
                    color: 'var(--text-secondary)',
                  }}
                >
                  <span className="font-semibold" style={{ color: 'var(--text-primary)' }}>{prettyButtonName(btn)}</span>
                  <span className="ml-2" style={{ color: 'var(--text-muted)' }}>
                    {(overrides[btn] ?? '-')}
                  </span>
                  {waitingFor === btn && <span className="ml-2 text-[10px]" style={{ color: '#ff6666' }}>Waiting…</span>}
                </button>
              ))}
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
