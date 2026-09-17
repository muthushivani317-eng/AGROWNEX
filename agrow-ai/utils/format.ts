/** Time-of-day greeting key into the `home` namespace. */
export function greetingKey(
  date = new Date(),
): 'greetingMorning' | 'greetingAfternoon' | 'greetingEvening' {
  const h = date.getHours();
  if (h < 12) return 'greetingMorning';
  if (h < 17) return 'greetingAfternoon';
  return 'greetingEvening';
}

/** Format a 10-digit Indian mobile as `+91 98765 43210`. */
export function formatIndianPhone(raw: string): string {
  const digits = raw.replace(/\D/g, '').slice(-10);
  if (digits.length !== 10) return raw;
  return `+91 ${digits.slice(0, 5)} ${digits.slice(5)}`;
}

/** Privacy-safe phone display for normal profile surfaces. */
export function maskIndianPhone(raw: string): string {
  const digits = raw.replace(/\D/g, '').slice(-10);
  if (digits.length !== 10) return 'Phone number hidden';
  return `+91 ******${digits.slice(-4)}`;
}

/** Two-letter initials from a display name. */
export function initials(name?: string | null): string {
  if (!name) return '?';
  const parts = name.trim().split(/\s+/);
  const first = parts[0]?.[0] ?? '';
  const last = parts.length > 1 ? parts[parts.length - 1][0] : '';
  return (first + last).toUpperCase();
}

export const clamp = (n: number, min: number, max: number) =>
  Math.min(Math.max(n, min), max);
