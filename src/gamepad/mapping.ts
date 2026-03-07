import type {
  ControllerButton,
  ControllerVisualState,
  MappingOverrides,
  MappingProfile,
  RawPadSnapshot,
} from "./types";

const ALL_BUTTONS: ControllerButton[] = [
  "a",
  "b",
  "x",
  "y",
  "dpadUp",
  "dpadDown",
  "dpadLeft",
  "dpadRight",
  "lb",
  "rb",
  "lt",
  "rt",
  "minus",
  "plus",
  "l3",
  "r3",
  "home",
  "capture",
];

const STANDARD_PROFILE: MappingProfile = {
  id: "standard",
  label: "Standard (Xbox-like)",
  buttonMap: {
    a: 0,
    b: 1,
    x: 2,
    y: 3,
    lb: 4,
    rb: 5,
    lt: 6,
    rt: 7,
    minus: 8,
    plus: 9,
    l3: 10,
    r3: 11,
    dpadUp: 12,
    dpadDown: 13,
    dpadLeft: 14,
    dpadRight: 15,
    home: 16,
    capture: 17,
  },
  axisMap: { leftX: 0, leftY: 1, rightX: 2, rightY: 3, leftTriggerAxis: 4, rightTriggerAxis: 5 },
};

const NINTENDO_PROFILE: MappingProfile = {
  ...STANDARD_PROFILE,
  id: "nintendo",
  label: "Nintendo / Switch",
  buttonMap: {
    ...STANDARD_PROFILE.buttonMap,
    a: 1,
    b: 0,
    x: 3,
    y: 2,
  },
};

const PLAYSTATION_PROFILE: MappingProfile = {
  ...STANDARD_PROFILE,
  id: "playstation",
  label: "PlayStation",
  buttonMap: {
    ...STANDARD_PROFILE.buttonMap,
    a: 1,
    b: 0,
    x: 3,
    y: 2,
  },
};

const GENERIC_PROFILE: MappingProfile = {
  ...STANDARD_PROFILE,
  id: "generic",
  label: "Generic Controller",
};

function detectProfile(id: string, mapping: string): MappingProfile {
  const low = id.toLowerCase();
  if (mapping === "standard") {
    if (low.includes("nintendo") || low.includes("switch") || low.includes("joy-con")) return NINTENDO_PROFILE;
    if (low.includes("dualshock") || low.includes("dualsense") || low.includes("playstation") || low.includes("wireless controller")) return PLAYSTATION_PROFILE;
    return STANDARD_PROFILE;
  }
  if (low.includes("nintendo") || low.includes("switch")) return NINTENDO_PROFILE;
  if (low.includes("playstation") || low.includes("dualshock") || low.includes("dualsense")) return PLAYSTATION_PROFILE;
  return GENERIC_PROFILE;
}

function clampAxis(value: number | undefined, deadZone = 0.12): number {
  if (typeof value !== "number" || Number.isNaN(value)) return 0;
  if (Math.abs(value) < deadZone) return 0;
  return Math.max(-1, Math.min(1, value));
}

function buttonValue(snapshot: RawPadSnapshot, index: number | undefined): number {
  if (index === undefined || index < 0) return 0;
  return snapshot.buttons[index] ?? 0;
}

function axisValue(snapshot: RawPadSnapshot, index: number | undefined): number {
  if (index === undefined || index < 0) return 0;
  return snapshot.axes[index] ?? 0;
}

export function resolveMappingProfile(snapshot: RawPadSnapshot, overrides?: MappingOverrides): MappingProfile {
  const base = detectProfile(snapshot.id, snapshot.mapping);
  return {
    ...base,
    buttonMap: {
      ...base.buttonMap,
      ...(overrides ?? {}),
    },
  };
}

export function buildVisualState(snapshot: RawPadSnapshot, profile: MappingProfile): ControllerVisualState {
  const values = Object.fromEntries(ALL_BUTTONS.map((btn) => [btn, 0])) as Record<ControllerButton, number>;

  for (const button of ALL_BUTTONS) {
    const idx = profile.buttonMap[button];
    values[button] = buttonValue(snapshot, idx);
  }

  if (profile.axisMap.leftTriggerAxis !== undefined) {
    values.lt = Math.max(values.lt, Math.max(0, (axisValue(snapshot, profile.axisMap.leftTriggerAxis) + 1) / 2));
  }

  if (profile.axisMap.rightTriggerAxis !== undefined) {
    values.rt = Math.max(values.rt, Math.max(0, (axisValue(snapshot, profile.axisMap.rightTriggerAxis) + 1) / 2));
  }

  const buttons = Object.fromEntries(ALL_BUTTONS.map((btn) => [btn, values[btn] > 0.45])) as Record<ControllerButton, boolean>;

  const leftX = clampAxis(axisValue(snapshot, profile.axisMap.leftX));
  const leftY = clampAxis(axisValue(snapshot, profile.axisMap.leftY));
  const rightX = clampAxis(axisValue(snapshot, profile.axisMap.rightX));
  const rightY = clampAxis(axisValue(snapshot, profile.axisMap.rightY));

  return {
    connected: snapshot.connected,
    profileName: profile.label,
    gamepadName: snapshot.id,
    leftStick: { x: leftX, y: leftY, pressed: buttons.l3 },
    rightStick: { x: rightX, y: rightY, pressed: buttons.r3 },
    triggers: {
      left: Math.max(0, Math.min(1, values.lt)),
      right: Math.max(0, Math.min(1, values.rt)),
    },
    buttons,
    values,
  };
}
