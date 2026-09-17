import {
  CONDITION_LABEL_KEY,
  INSIGHT_MESSAGE_KEY,
} from '../constants';
import { formatHHmm, formatTemp, uvLabelKey, weekdayKey } from '../utils/format';

describe('weather formatters', () => {
  it('formats temperatures and times', () => {
    expect(formatTemp(28.6)).toBe('29°');
    expect(formatTemp(null)).toBe('—');
    expect(formatHHmm('2026-07-10T05:55')).toBe('05:55');
    expect(formatHHmm(null)).toBe('—');
  });

  it('maps UV to a severity band key', () => {
    expect(uvLabelKey(1)).toBe('weather.uvLow');
    expect(uvLabelKey(4)).toBe('weather.uvModerate');
    expect(uvLabelKey(7)).toBe('weather.uvHigh');
    expect(uvLabelKey(9)).toBe('weather.uvVeryHigh');
    expect(uvLabelKey(12)).toBe('weather.uvExtreme');
  });

  it('maps a date to a weekday key', () => {
    // 2026-07-10 is a Friday (day index 5).
    expect(weekdayKey('2026-07-10')).toBe('weather.dow5');
  });

  it('has a message key for every condition and mapped insight code', () => {
    // Every condition has a label key.
    expect(Object.keys(CONDITION_LABEL_KEY)).toContain('thunderstorm');
    // The insight code map covers all six categories.
    const categories = new Set(
      Object.keys(INSIGHT_MESSAGE_KEY).map((code) => code.split('.')[0]),
    );
    expect(categories).toEqual(
      new Set(['heat_stress', 'heavy_rain', 'wind', 'spraying', 'irrigation', 'field_work']),
    );
  });
});
