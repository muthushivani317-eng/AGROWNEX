/**
 * JS mirror of the CSS design tokens (docs/DESIGN_SYSTEM.md). NativeWind
 * `className`s consume the CSS variables directly; this object exists for the
 * imperative surface — StatusBar, navigation themes, Lucide icon colors,
 * gradients, charts — anywhere a raw color string is required.
 */
export type ColorScheme = 'light' | 'dark';

export interface Palette {
  primary: string;
  primaryLight: string;
  primaryDark: string;
  success: string;
  warning: string;
  danger: string;
  info: string;
  bg: string;
  surface: string;
  card: string;
  border: string;
  text: string;
  textMuted: string;
  textDisabled: string;
  onPrimary: string;
}

export const lightPalette: Palette = {
  primary: '#2E7D32',
  primaryLight: '#4CAF50',
  primaryDark: '#1B5E20',
  success: '#43A047',
  warning: '#F9A825',
  danger: '#E53935',
  info: '#1E88E5',
  bg: '#F7F9F4',
  surface: '#FFFFFF',
  card: '#FFFFFF',
  border: '#E5E7EB',
  text: '#111827',
  textMuted: '#6B7280',
  textDisabled: '#9CA3AF',
  onPrimary: '#FFFFFF',
};

export const darkPalette: Palette = {
  primary: '#4CAF50',
  primaryLight: '#81C784',
  primaryDark: '#2E7D32',
  success: '#66BB6A',
  warning: '#FFCA28',
  danger: '#EF5350',
  info: '#42A5F5',
  bg: '#121212',
  surface: '#1E1E1E',
  card: '#252525',
  border: '#333333',
  text: '#FFFFFF',
  textMuted: '#BDBDBD',
  textDisabled: '#757575',
  onPrimary: '#0C140F',
};

export const palettes: Record<ColorScheme, Palette> = {
  light: lightPalette,
  dark: darkPalette,
};
