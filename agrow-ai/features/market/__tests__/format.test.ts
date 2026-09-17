import { filterCacheKey } from '../services/marketStorage';
import { formatRupees, updatedAgo } from '../utils/format';

describe('formatRupees', () => {
  it('formats with the rupee symbol and Indian grouping', () => {
    expect(formatRupees(2050)).toBe('₹2,050');
    expect(formatRupees(100000)).toBe('₹1,00,000');
  });

  it('rounds fractional amounts', () => {
    expect(formatRupees(2050.6)).toBe('₹2,051');
  });
});

describe('updatedAgo', () => {
  const now = new Date('2026-07-11T10:00:00Z');

  it('detects today', () => {
    expect(updatedAgo('2026-07-11', now).key).toBe('today');
  });

  it('detects yesterday', () => {
    expect(updatedAgo('2026-07-10', now).key).toBe('yesterday');
  });

  it('counts older days', () => {
    const result = updatedAgo('2026-07-05', now);
    expect(result.key).toBe('daysAgo');
    expect(result.days).toBe(6);
  });
});

describe('filterCacheKey', () => {
  it('is stable and case-insensitive', () => {
    const a = filterCacheKey({ crop: 'Paddy', district: 'Thanjavur' });
    const b = filterCacheKey({ crop: 'paddy', district: 'thanjavur' });
    expect(a).toBe(b);
  });

  it('separates today from all', () => {
    const all = filterCacheKey({ crop: 'paddy' });
    const today = filterCacheKey({ crop: 'paddy', todayOnly: true });
    expect(all).not.toBe(today);
  });
});
