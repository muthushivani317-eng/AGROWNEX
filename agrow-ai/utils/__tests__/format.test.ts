import { clamp, formatIndianPhone, greetingKey, initials } from '../format';

describe('format utils', () => {
  it('formatIndianPhone formats a 10-digit number', () => {
    expect(formatIndianPhone('9876543210')).toBe('+91 98765 43210');
    expect(formatIndianPhone('+919876543210')).toBe('+91 98765 43210');
  });

  it('initials derives up to two letters', () => {
    expect(initials('Muthu Kumar')).toBe('MK');
    expect(initials('Muthu')).toBe('M');
    expect(initials(undefined)).toBe('?');
    expect(initials(null)).toBe('?');
  });

  it('greetingKey maps time of day', () => {
    expect(greetingKey(new Date(2026, 0, 1, 8))).toBe('greetingMorning');
    expect(greetingKey(new Date(2026, 0, 1, 14))).toBe('greetingAfternoon');
    expect(greetingKey(new Date(2026, 0, 1, 20))).toBe('greetingEvening');
  });

  it('clamp bounds a value', () => {
    expect(clamp(5, 0, 10)).toBe(5);
    expect(clamp(-1, 0, 10)).toBe(0);
    expect(clamp(11, 0, 10)).toBe(10);
  });
});
