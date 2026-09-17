import { formatClock, relativeTimeKey } from '../utils/time';

const NOW = Date.parse('2026-07-10T12:00:00Z');

describe('relativeTimeKey', () => {
  it('buckets recent times', () => {
    expect(relativeTimeKey('2026-07-10T11:59:40Z', NOW).key).toBe('home.timeJustNow');
    expect(relativeTimeKey('2026-07-10T11:30:00Z', NOW)).toEqual({
      key: 'home.timeMinutesAgo',
      params: { n: 30 },
    });
    expect(relativeTimeKey('2026-07-10T09:00:00Z', NOW)).toEqual({
      key: 'home.timeHoursAgo',
      params: { n: 3 },
    });
  });

  it('buckets days and weeks', () => {
    expect(relativeTimeKey('2026-07-09T12:00:00Z', NOW).key).toBe('home.timeYesterday');
    expect(relativeTimeKey('2026-07-07T12:00:00Z', NOW)).toEqual({
      key: 'home.timeDaysAgo',
      params: { n: 3 },
    });
    expect(relativeTimeKey('2026-06-20T12:00:00Z', NOW).key).toBe('home.timeWeeksAgo');
  });

  it('handles missing/invalid input', () => {
    expect(relativeTimeKey(null, NOW).key).toBe('home.timeUnknown');
    expect(relativeTimeKey('not-a-date', NOW).key).toBe('home.timeUnknown');
  });
});

describe('formatClock', () => {
  it('formats HH:mm with zero padding', () => {
    expect(formatClock(new Date(2026, 6, 10, 9, 5))).toBe('09:05');
    expect(formatClock(new Date(2026, 6, 10, 18, 40))).toBe('18:40');
  });
});
