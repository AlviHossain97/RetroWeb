export type ControllerButton =
  | "a"
  | "b"
  | "x"
  | "y"
  | "dpadUp"
  | "dpadDown"
  | "dpadLeft"
  | "dpadRight"
  | "lb"
  | "rb"
  | "lt"
  | "rt"
  | "minus"
  | "plus"
  | "l3"
  | "r3"
  | "home"
  | "capture";

export interface StickState {
  x: number;
  y: number;
  pressed: boolean;
}

export interface ControllerVisualState {
  connected: boolean;
  profileName: string;
  gamepadName: string;
  leftStick: StickState;
  rightStick: StickState;
  triggers: {
    left: number;
    right: number;
  };
  buttons: Record<ControllerButton, boolean>;
  values: Record<ControllerButton, number>;
}

export interface RawPadSnapshot {
  id: string;
  index: number;
  mapping: string;
  connected: boolean;
  axes: number[];
  buttons: number[];
  timestamp: number;
}

export interface GamepadSummary {
  id: string;
  index: number;
  connected: boolean;
  mapping: string;
}

export interface MappingProfile {
  id: string;
  label: string;
  buttonMap: Partial<Record<ControllerButton, number>>;
  axisMap: {
    leftX: number;
    leftY: number;
    rightX: number;
    rightY: number;
    leftTriggerAxis?: number;
    rightTriggerAxis?: number;
  };
}

export type MappingOverrides = Partial<Record<ControllerButton, number>>;
