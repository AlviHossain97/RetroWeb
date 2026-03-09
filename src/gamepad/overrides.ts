import type { MappingOverrides } from "./types";

const STORAGE_KEY = "retroweb_gamepad_overrides";

export function loadMappingOverrides(): MappingOverrides {
  if (typeof window === "undefined") return {};
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return {};
    const parsed = JSON.parse(raw) as MappingOverrides;
    return parsed ?? {};
  } catch {
    return {};
  }
}

export function saveMappingOverrides(overrides: MappingOverrides): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(STORAGE_KEY, JSON.stringify(overrides));
}

export const GAMEPAD_OVERRIDES_STORAGE_KEY = STORAGE_KEY;
