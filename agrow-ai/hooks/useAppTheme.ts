import { useColorScheme as useSystemColorScheme } from 'react-native';

import { useThemeStore } from '@/stores/themeStore';
import {
  darkPalette,
  lightPalette,
  resolveColorScheme,
  type ColorScheme,
  type Palette,
} from '@/theme';

export interface AppTheme {
  scheme: ColorScheme;
  colors: Palette;
  isDark: boolean;
  isSunlight: boolean;
}

/**
 * Resolves the active color scheme (following the user's theme preference, which
 * `ThemeController` pushes into NativeWind) and returns the matching JS palette
 * for imperative styling.
 */
export function useAppTheme(): AppTheme {
  const preference = useThemeStore((state) => state.preference);
  const sunlightEnabled = useThemeStore((state) => state.sunlightEnabled);
  const systemScheme = useSystemColorScheme();
  const scheme = sunlightEnabled
    ? 'light'
    : resolveColorScheme(preference, systemScheme);
  const isDark = scheme === 'dark';
  const basePalette = isDark ? darkPalette : lightPalette;
  const colors = sunlightEnabled
    ? { ...basePalette, text: '#000000', textMuted: '#1A1A1A' }
    : basePalette;
  return { scheme, colors, isDark, isSunlight: sunlightEnabled };
}
