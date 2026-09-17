import dayjs from 'dayjs';

/** Locale-neutral weather formatters. Weekday names come from i18n (`weather.dowN`). */

export function formatHHmm(iso: string | null): string {
  if (!iso) return '—';
  const d = dayjs(iso);
  return d.isValid() ? d.format('HH:mm') : '—';
}

/** i18n key for the weekday of an ISO date (0=Sunday … 6=Saturday). */
export function weekdayKey(iso: string | null): string {
  if (!iso) return 'weather.dow0';
  const d = dayjs(iso);
  const day = d.isValid() ? d.day() : 0;
  return `weather.dow${day}`;
}

export function formatTemp(value: number | null): string {
  return value == null ? '—' : `${Math.round(value)}°`;
}

export function formatTempUnit(value: number | null): string {
  return value == null ? '—' : `${Math.round(value)}°C`;
}

export function formatInt(value: number | null): string {
  return value == null ? '—' : `${Math.round(value)}`;
}

/** UV index → severity band i18n key. */
export function uvLabelKey(uv: number | null): string {
  if (uv == null) return 'weather.uvLow';
  if (uv < 3) return 'weather.uvLow';
  if (uv < 6) return 'weather.uvModerate';
  if (uv < 8) return 'weather.uvHigh';
  if (uv < 11) return 'weather.uvVeryHigh';
  return 'weather.uvExtreme';
}
