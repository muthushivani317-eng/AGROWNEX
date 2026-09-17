/** 8-point spacing grid (docs/DESIGN_SYSTEM.md). */
export const spacing = {
  xs: 4,
  sm: 8,
  md: 12,
  lg: 16,
  xl: 20,
  '2xl': 24,
  '3xl': 32,
  '4xl': 40,
  '5xl': 48,
  '6xl': 64,
} as const;

export const radius = {
  sm: 8,
  md: 12,
  lg: 20,
  card: 24,
  full: 999,
} as const;

/** Type scale (docs/DESIGN_SYSTEM.md), line-height 1.5. */
export const typography = {
  headingXL: { fontSize: 32, lineHeight: 40 },
  headingL: { fontSize: 28, lineHeight: 36 },
  headingM: { fontSize: 24, lineHeight: 32 },
  headingS: { fontSize: 20, lineHeight: 28 },
  bodyLarge: { fontSize: 18, lineHeight: 27 },
  body: { fontSize: 16, lineHeight: 24 },
  bodySmall: { fontSize: 14, lineHeight: 21 },
  caption: { fontSize: 12, lineHeight: 18 },
  button: { fontSize: 16, lineHeight: 24 },
} as const;

/** Elevation (dp) → cross-platform shadow. */
export const elevation = {
  low: 2,
  medium: 6,
  high: 12,
  dialog: 24,
} as const;

export const shadow = (dp: number) => ({
  elevation: dp,
  shadowColor: '#000000',
  shadowOffset: { width: 0, height: Math.round(dp * 0.5) },
  shadowOpacity: 0.12,
  shadowRadius: dp,
});

/** Minimum accessible touch target (docs: 48dp). Buttons use 56dp. */
export const A11Y_MIN_TARGET = 48;
export const BUTTON_MIN_HEIGHT = 56;
