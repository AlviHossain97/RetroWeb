import { useEffect, useMemo, useRef, useState } from "react";
import { buildVisualState, resolveMappingProfile } from "../gamepad/mapping";
import type {
  ControllerVisualState,
  GamepadSummary,
  MappingOverrides,
  RawPadSnapshot,
} from "../gamepad/types";

interface UseGamepadVisualizerOptions {
  overrides?: MappingOverrides;
  preferredIndex?: number;
}

interface UseGamepadVisualizerResult {
  supported: boolean;
  connectedPads: GamepadSummary[];
  activeIndex: number | null;
  setActiveIndex: (index: number | null) => void;
  activePadRaw: RawPadSnapshot | null;
  visualState: ControllerVisualState | null;
  profileLabel: string;
}

const EMPTY_VISUAL: ControllerVisualState = {
  connected: false,
  profileName: "No controller",
  gamepadName: "",
  leftStick: { x: 0, y: 0, pressed: false },
  rightStick: { x: 0, y: 0, pressed: false },
  triggers: { left: 0, right: 0 },
  buttons: {
    a: false,
    b: false,
    x: false,
    y: false,
    dpadUp: false,
    dpadDown: false,
    dpadLeft: false,
    dpadRight: false,
    lb: false,
    rb: false,
    lt: false,
    rt: false,
    minus: false,
    plus: false,
    l3: false,
    r3: false,
    home: false,
    capture: false,
  },
  values: {
    a: 0,
    b: 0,
    x: 0,
    y: 0,
    dpadUp: 0,
    dpadDown: 0,
    dpadLeft: 0,
    dpadRight: 0,
    lb: 0,
    rb: 0,
    lt: 0,
    rt: 0,
    minus: 0,
    plus: 0,
    l3: 0,
    r3: 0,
    home: 0,
    capture: 0,
  },
};

function snapshotPad(pad: Gamepad): RawPadSnapshot {
  return {
    id: pad.id,
    index: pad.index,
    mapping: pad.mapping,
    connected: pad.connected,
    axes: Array.from(pad.axes),
    buttons: pad.buttons.map((btn) => btn.value),
    timestamp: pad.timestamp,
  };
}

export function useGamepadVisualizer(options: UseGamepadVisualizerOptions = {}): UseGamepadVisualizerResult {
  const supported = typeof navigator !== "undefined" && typeof navigator.getGamepads === "function";
  const [connectedPads, setConnectedPads] = useState<GamepadSummary[]>([]);
  const [activeIndex, setActiveIndex] = useState<number | null>(options.preferredIndex ?? null);
  const [activePadRaw, setActivePadRaw] = useState<RawPadSnapshot | null>(null);
  const frameRef = useRef<number | null>(null);

  useEffect(() => {
    if (!supported) return;

    const tick = () => {
      const pads = Array.from(navigator.getGamepads()).filter((p): p is Gamepad => Boolean(p && p.connected));
      const summaries = pads.map((pad) => ({
        id: pad.id,
        index: pad.index,
        connected: pad.connected,
        mapping: pad.mapping,
      }));
      setConnectedPads(summaries);

      const resolvedIndex = activeIndex ?? summaries[0]?.index ?? null;
      const activePad = resolvedIndex === null ? null : pads.find((pad) => pad.index === resolvedIndex) ?? null;

      if (resolvedIndex !== activeIndex) {
        setActiveIndex(resolvedIndex);
      }

      setActivePadRaw(activePad ? snapshotPad(activePad) : null);
      frameRef.current = requestAnimationFrame(tick);
    };

    frameRef.current = requestAnimationFrame(tick);

    const onConnect = () => {
      const firstConnected = Array.from(navigator.getGamepads()).find((p) => p?.connected);
      if (firstConnected && activeIndex === null) {
        setActiveIndex(firstConnected.index);
      }
    };

    const onDisconnect = () => {
      const nextConnected = Array.from(navigator.getGamepads()).find((p) => p?.connected);
      if (!nextConnected) {
        setActiveIndex(null);
        setActivePadRaw(null);
      }
    };

    window.addEventListener("gamepadconnected", onConnect);
    window.addEventListener("gamepaddisconnected", onDisconnect);

    return () => {
      window.removeEventListener("gamepadconnected", onConnect);
      window.removeEventListener("gamepaddisconnected", onDisconnect);
      if (frameRef.current !== null) cancelAnimationFrame(frameRef.current);
    };
  }, [activeIndex, supported]);

  const visualState = useMemo(() => {
    if (!activePadRaw) return null;
    const profile = resolveMappingProfile(activePadRaw, options.overrides);
    return buildVisualState(activePadRaw, profile);
  }, [activePadRaw, options.overrides]);

  return {
    supported,
    connectedPads,
    activeIndex,
    setActiveIndex,
    activePadRaw,
    visualState: visualState ?? EMPTY_VISUAL,
    profileLabel: visualState?.profileName ?? "No controller",
  };
}
