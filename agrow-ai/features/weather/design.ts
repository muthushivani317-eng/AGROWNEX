export const WEATHER_UI = {
  canvas: "#F5F2E8",
  surface: "#FFFDF7",
  surfaceSoft: "#EAF2E5",
  sky: "#D9ECF2",
  skyDeep: "#176B72",
  field: "#175D36",
  fieldBright: "#2F7A49",
  sun: "#E5A51A",
  rain: "#2B7187",
  text: "#173B2B",
  muted: "#5C6A62",
  border: "#DCD7C8",
  warning: "#9A5C14",
  danger: "#A93A2D",
  white: "#FFFFFF",
} as const;

export const WEATHER_SHADOW = {
  shadowColor: "#173B2B",
  shadowOpacity: 0.08,
  shadowRadius: 10,
  shadowOffset: { width: 0, height: 4 },
  elevation: 2,
} as const;
