import { useColorScheme as useNativeWindColorScheme } from 'nativewind';
import { useEffect } from 'react';
import { useColorScheme as useSystemColorScheme } from 'react-native';

import { useThemeStore } from '@/stores/themeStore';
import { resolveColorScheme } from '@/theme';

/**
 * Bridges the persisted theme preference into NativeWind's color scheme, so both
 * `className` dark variants and the JS palette resolve to the same scheme.
 * Renders nothing.
 */
export function ThemeController() {
  const preference = useThemeStore((state) => state.preference);
  const sunlightEnabled = useThemeStore((state) => state.sunlightEnabled);
  const hydrated = useThemeStore((state) => state.hydrated);
  const systemScheme = useSystemColorScheme();
  const { setColorScheme } = useNativeWindColorScheme();
  const resolvedScheme = sunlightEnabled
    ? 'light'
    : resolveColorScheme(preference, systemScheme);

  useEffect(() => {
    if (!hydrated) return;
    setColorScheme(resolvedScheme);
  }, [hydrated, resolvedScheme, setColorScheme]);

  return null;
}
