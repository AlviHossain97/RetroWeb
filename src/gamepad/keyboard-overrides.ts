import type { ControllerButton } from "./types";

export type KeyboardOverrides = Partial<Record<ControllerButton, string>>;

const STORAGE_KEY = "retroweb_keyboard_overrides";

const DEFAULT_KEYBOARD_MAP: KeyboardOverrides = {
  a: "KeyX",
  b: "KeyZ",
  x: "KeyS",
  y: "KeyA",
  dpadUp: "ArrowUp",
  dpadDown: "ArrowDown",
  dpadLeft: "ArrowLeft",
  dpadRight: "ArrowRight",
  lb: "KeyQ",
  rb: "KeyW",
  lt: "Digit1",
  rt: "Digit2",
  minus: "ShiftRight",
  plus: "Enter",
  l3: "Digit3",
  r3: "Digit4",
  home: "Escape",
  capture: "F12",
};

export function getDefaultKeyboardMap(): KeyboardOverrides {
  return { ...DEFAULT_KEYBOARD_MAP };
}

export function loadKeyboardOverrides(): KeyboardOverrides {
  if (typeof window === "undefined") return {};
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return {};
    return JSON.parse(raw) as KeyboardOverrides;
  } catch {
    return {};
  }
}

export function saveKeyboardOverrides(overrides: KeyboardOverrides): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(STORAGE_KEY, JSON.stringify(overrides));
}

export function getEffectiveKeyboardMap(): KeyboardOverrides {
  return { ...DEFAULT_KEYBOARD_MAP, ...loadKeyboardOverrides() };
}

export function keyCodeToLabel(code: string): string {
  if (code.startsWith("Key")) return code.slice(3);
  if (code.startsWith("Digit")) return code.slice(5);
  if (code.startsWith("Arrow")) return "↑↓←→".charAt(["ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight"].indexOf(code)) || code.slice(5);
  const labels: Record<string, string> = {
    Space: "Space", Enter: "Enter", ShiftLeft: "L Shift", ShiftRight: "R Shift",
    ControlLeft: "L Ctrl", ControlRight: "R Ctrl", AltLeft: "L Alt", AltRight: "R Alt",
    Backspace: "Backspace", Tab: "Tab", Escape: "Esc", CapsLock: "Caps",
    ArrowUp: "↑", ArrowDown: "↓", ArrowLeft: "←", ArrowRight: "→",
    F1: "F1", F2: "F2", F3: "F3", F4: "F4", F5: "F5", F6: "F6",
    F7: "F7", F8: "F8", F9: "F9", F10: "F10", F11: "F11", F12: "F12",
    BracketLeft: "[", BracketRight: "]", Semicolon: ";", Quote: "'",
    Comma: ",", Period: ".", Slash: "/", Backslash: "\\", Minus: "-", Equal: "=",
    Backquote: "`",
  };
  return labels[code] ?? code;
}
