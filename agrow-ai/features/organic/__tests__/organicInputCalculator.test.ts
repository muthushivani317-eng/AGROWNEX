import { calculateInputQuantity, practiceTypeForCategory } from '../services/organicInputCalculator';

describe('organic input quantity calculator', () => {
  it('computes a per-farm quantity for a valid kg/ha rate', () => {
    expect(calculateInputQuantity({ application_rate: { value: 2500, unit: 'kg/ha' } }, 1.5)).toEqual({
      rateValue: 2500,
      rateUnit: 'kg/ha',
      quantity: 3750,
      unit: 'kg',
    });
  });

  it('computes a per-farm quantity for a valid tonne/ha rate', () => {
    expect(calculateInputQuantity({ application_rate: { value: 5, unit: 'tonne/ha' } }, 2)).toEqual({
      rateValue: 5,
      rateUnit: 'tonne/ha',
      quantity: 10,
      unit: 'tonne',
    });
  });

  it('returns null when there is no farm area', () => {
    expect(calculateInputQuantity({ application_rate: { value: 2500, unit: 'kg/ha' } }, null)).toBeNull();
    expect(calculateInputQuantity({ application_rate: { value: 2500, unit: 'kg/ha' } }, 0)).toBeNull();
  });

  it('returns null when guidance has no application_rate', () => {
    expect(calculateInputQuantity({}, 1.5)).toBeNull();
  });

  it('returns null for a rate unit the backend never emits (never invents a conversion)', () => {
    expect(calculateInputQuantity({ application_rate: { value: 10, unit: 'ml/L' } }, 1.5)).toBeNull();
  });

  it('returns null for a malformed application_rate', () => {
    expect(calculateInputQuantity({ application_rate: { value: 'a lot', unit: 'kg/ha' } }, 1.5)).toBeNull();
    expect(calculateInputQuantity({ application_rate: 'not an object' }, 1.5)).toBeNull();
  });

  it('maps the exact soil-amendment categories the backend plan engine recognizes', () => {
    expect(practiceTypeForCategory('compost')).toBe('amendment');
    expect(practiceTypeForCategory('farmyard_manure')).toBe('amendment');
    expect(practiceTypeForCategory('vermicompost')).toBe('amendment');
    expect(practiceTypeForCategory('green_manure')).toBe('amendment');
  });

  it('falls back to custom for any other category rather than guessing', () => {
    expect(practiceTypeForCategory('botanical_spray')).toBe('custom');
    expect(practiceTypeForCategory('unknown_future_category')).toBe('custom');
  });
});
