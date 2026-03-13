import { useState, useEffect, useRef, useCallback } from "react";

export type InputMode = "mouse" | "keyboard" | "gamepad";

export function useInputMode(): InputMode {
  const [mode, setMode] = useState<InputMode>("mouse");
  const rafRef = useRef<number>(0);

  const checkGamepads = useCallback(() => {
    const gamepads = navigator.getGamepads?.() ?? [];
    for (const gp of gamepads) {
      if (!gp) continue;
      // Check if any button is pressed or axis is significantly moved
      for (const btn of gp.buttons) {
        if (btn.pressed) {
          setMode("gamepad");
          return;
        }
      }
      for (const axis of gp.axes) {
        if (Math.abs(axis) > 0.5) {
          setMode("gamepad");
          return;
        }
      }
    }
  }, []);

  useEffect(() => {
    const onMouse = () => setMode("mouse");
    const onKeyboard = (e: KeyboardEvent) => {
      // Ignore modifier keys alone
      if (["Shift", "Control", "Alt", "Meta"].includes(e.key)) return;
      setMode("keyboard");
    };

    window.addEventListener("mousemove", onMouse, { passive: true });
    window.addEventListener("keydown", onKeyboard, { passive: true });

    // Poll gamepads
    let running = true;
    const poll = () => {
      if (!running) return;
      checkGamepads();
      rafRef.current = requestAnimationFrame(poll);
    };
    poll();

    return () => {
      running = false;
      cancelAnimationFrame(rafRef.current);
      window.removeEventListener("mousemove", onMouse);
      window.removeEventListener("keydown", onKeyboard);
    };
  }, [checkGamepads]);

  return mode;
}
