import { maskIndianPhone } from '../format';

describe('profile phone privacy', () => {
  it('reveals only the country code and final four digits', () => {
    const masked = maskIndianPhone('+91' + '9876543210');
    expect(masked).toBe('+91 ******3210');
    expect(masked).not.toContain('987654');
  });

  it('fails closed for malformed values', () => {
    expect(maskIndianPhone('not-a-phone')).toBe('Phone number hidden');
  });
});
