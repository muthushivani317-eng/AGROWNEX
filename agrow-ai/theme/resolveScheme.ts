import type { ColorScheme } from './colors';

/** Resolve an explicit theme preference against the current OS appearance. */
export function resolveColorScheme(
  preference: 'system' | ColorScheme,
  systemScheme: ColorScheme | 'unspecified' | null | undefined,
): ColorScheme {
  if (preference !== 'system') return preference;
  return systemScheme === 'dark' ? 'dark' : 'light';
}
