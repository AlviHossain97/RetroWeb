import { useEffect, useRef, useCallback } from "react";

interface GamepadNavOptions {
  enabled?: boolean;
  onNavigate?: (direction: "up" | "down" | "left" | "right") => void;
  onConfirm?: () => void;
  onBack?: () => void;
}

const AXIS_THRESHOLD = 0.5;
const REPEAT_DELAY = 400;
const REPEAT_RATE = 120;

export function useGamepadNavigation(options: GamepadNavOptions = {}) {
  const { enabled = true, onNavigate, onConfirm, onBack } = options;
  const lastNavTime = useRef<Record<string, number>>({});
  const repeatHeld = useRef<Record<string, boolean>>({});
  const rafRef = useRef<number>(0);

  const canFire = useCallback((key: string) => {
    const now = Date.now();
    const last = lastNavTime.current[key] || 0;
    const isHeld = repeatHeld.current[key];
    const delay = isHeld ? REPEAT_RATE : REPEAT_DELAY;
    if (now - last < delay) return false;
    lastNavTime.current[key] = now;
    repeatHeld.current[key] = true;
    return true;
  }, []);

  const resetKey = useCallback((key: string) => {
    repeatHeld.current[key] = false;
  }, []);

  useEffect(() => {
    if (!enabled) return;

    const navigate = (dir: "up" | "down" | "left" | "right") => {
      if (onNavigate) {
        onNavigate(dir);
        return;
      }
      // Default: simulate arrow key for native focus navigation
      const focusable = Array.from(
        document.querySelectorAll<HTMLElement>(
          'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])'
        )
      ).filter((el) => el.offsetParent !== null);

      if (focusable.length === 0) return;

      const active = document.activeElement as HTMLElement;
      const idx = focusable.indexOf(active);

      if (dir === "down" || dir === "right") {
        const next = idx < focusable.length - 1 ? idx + 1 : 0;
        focusable[next]?.focus();
      } else {
        const prev = idx > 0 ? idx - 1 : focusable.length - 1;
        focusable[prev]?.focus();
      }
    };

    const confirm = () => {
      if (onConfirm) {
        onConfirm();
        return;
      }
      const el = document.activeElement as HTMLElement;
      el?.click();
    };

    const back = () => {
      if (onBack) {
        onBack();
        return;
      }
      window.history.back();
    };

    let running = true;
    const poll = () => {
      if (!running) return;
      const gamepads = navigator.getGamepads?.() ?? [];

      for (const gp of gamepads) {
        if (!gp) continue;

        // D-pad buttons (standard mapping: 12=up, 13=down, 14=left, 15=right)
        if (gp.buttons[12]?.pressed && canFire("up")) navigate("up");
        else if (!gp.buttons[12]?.pressed) resetKey("up");

        if (gp.buttons[13]?.pressed && canFire("down")) navigate("down");
        else if (!gp.buttons[13]?.pressed) resetKey("down");

        if (gp.buttons[14]?.pressed && canFire("left")) navigate("left");
        else if (!gp.buttons[14]?.pressed) resetKey("left");

        if (gp.buttons[15]?.pressed && canFire("right")) navigate("right");
        else if (!gp.buttons[15]?.pressed) resetKey("right");

        // Left stick
        if (gp.axes[1] < -AXIS_THRESHOLD && canFire("stick-up")) navigate("up");
        else if (gp.axes[1] >= -AXIS_THRESHOLD) resetKey("stick-up");

        if (gp.axes[1] > AXIS_THRESHOLD && canFire("stick-down")) navigate("down");
        else if (gp.axes[1] <= AXIS_THRESHOLD) resetKey("stick-down");

        if (gp.axes[0] < -AXIS_THRESHOLD && canFire("stick-left")) navigate("left");
        else if (gp.axes[0] >= -AXIS_THRESHOLD) resetKey("stick-left");

        if (gp.axes[0] > AXIS_THRESHOLD && canFire("stick-right")) navigate("right");
        else if (gp.axes[0] <= AXIS_THRESHOLD) resetKey("stick-right");

        // A/Cross = confirm (button 0)
        if (gp.buttons[0]?.pressed && canFire("confirm")) confirm();
        else if (!gp.buttons[0]?.pressed) resetKey("confirm");

        // B/Circle = back (button 1)
        if (gp.buttons[1]?.pressed && canFire("back")) back();
        else if (!gp.buttons[1]?.pressed) resetKey("back");
      }

      rafRef.current = requestAnimationFrame(poll);
    };

    poll();

    return () => {
      running = false;
      cancelAnimationFrame(rafRef.current);
    };
  }, [enabled, onNavigate, onConfirm, onBack, canFire, resetKey]);
}
