import { formatCount, formatKg, formatShortDate } from '../components/adminMeta';

describe('adminMeta formatters', () => {
  it('formats counts compactly and surfaces null as an em dash', () => {
    expect(formatCount(null)).toBe('—');
    expect(formatCount(42)).toBe('42');
    expect(formatCount(1500)).toBe('1.5k');
    expect(formatCount(2_000_000)).toBe('2.0M');
  });

  it('formats kilograms as kg / tonnes', () => {
    expect(formatKg(500)).toBe('500 kg');
    expect(formatKg(2000)).toBe('2.0 t');
  });

  it('formats an ISO date and never guesses a missing one', () => {
    expect(formatShortDate('2026-08-01T00:00:00.000Z')).toBe('2026-08-01');
    expect(formatShortDate(null)).toBe('—');
    expect(formatShortDate('not-a-date')).toBe('—');
  });
});
