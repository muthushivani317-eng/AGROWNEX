import {
  computeProcurementAnalytics,
  seasonForMonth,
  toKilograms,
  type ProcurementFact,
} from '../services/procurementAnalytics';

describe('toKilograms', () => {
  it('converts known units and rejects unconvertible ones', () => {
    expect(toKilograms(2, 'tonne')).toBe(2000);
    expect(toKilograms(5, 'quintal')).toBe(500);
    expect(toKilograms(100, 'kg')).toBe(100);
    // A bag is not convertible → null, never guessed.
    expect(toKilograms(3, 'bag')).toBeNull();
  });
});

describe('seasonForMonth (Tamil Nadu)', () => {
  it('classifies kharif / rabi / summer', () => {
    expect(seasonForMonth(7)).toBe('kharif');
    expect(seasonForMonth(12)).toBe('rabi');
    expect(seasonForMonth(1)).toBe('rabi');
    expect(seasonForMonth(4)).toBe('summer');
  });
});

describe('computeProcurementAnalytics', () => {
  const facts: ProcurementFact[] = [
    { village: 'Kabisthalam', crop: 'paddy', harvestDate: '2026-07-15', quantity: 2, unit: 'tonne' },
    { village: 'Kabisthalam', crop: 'paddy', harvestDate: '2026-12-01', quantity: 100, unit: 'kg' },
    { village: 'Papanasam', crop: 'banana', harvestDate: '2026-08-10', quantity: 5, unit: 'quintal' },
  ];

  it('buckets and totals like the backend engine', () => {
    const out = computeProcurementAnalytics(facts);
    expect(out.totalOffers).toBe(3);
    expect(out.totalQuantityKg).toBe(2600);

    const byCrop = Object.fromEntries(out.byCrop.map((b) => [b.label, b]));
    expect(byCrop.paddy.count).toBe(2);
    expect(byCrop.paddy.quantityKg).toBe(2100);
    expect(byCrop.banana.quantityKg).toBe(500);

    const bySeason = Object.fromEntries(out.bySeason.map((b) => [b.label, b]));
    expect(bySeason.kharif.count).toBe(2);

    // Trend is chronologically sorted.
    const labels = out.quantityTrend.map((p) => p.label);
    expect(labels).toEqual([...labels].sort());
  });

  it('handles unknowns and unconvertible units honestly', () => {
    const out = computeProcurementAnalytics([
      { village: null, crop: null, harvestDate: null, quantity: 3, unit: 'bag' },
    ]);
    expect(out.totalOffers).toBe(1);
    expect(out.totalQuantityKg).toBe(0);
    expect(out.byVillage[0].label).toBe('unknown');
    expect(out.byCrop[0].label).toBe('unknown');
    // No harvest date → excluded from the dated trend, never fabricated.
    expect(out.quantityTrend).toEqual([]);
  });
});
