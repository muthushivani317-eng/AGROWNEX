import {
  classifyWindow,
  computeInsight,
  daysBetween,
  toKilograms,
  type OfferFacts,
} from '../services/produceEngine';
import type { PriceReference } from '../types';

const TODAY = new Date('2026-07-11T00:00:00');

function ref(modal: number, unit = 'quintal'): PriceReference {
  return {
    modalPrice: modal,
    minimumPrice: modal - 100,
    maximumPrice: modal + 100,
    unit,
    source: 'agmarknet',
    priceDate: '2026-07-11',
    market: 'Thanjavur',
    district: 'Thanjavur',
  };
}

describe('daysBetween', () => {
  it('counts whole days, positive and negative', () => {
    expect(daysBetween('2026-07-18', TODAY)).toBe(7);
    expect(daysBetween('2026-07-11', TODAY)).toBe(0);
    expect(daysBetween('2026-07-01', TODAY)).toBe(-10);
  });
});

describe('classifyWindow', () => {
  it('buckets by how soon the harvest is due', () => {
    expect(classifyWindow(-1)).toBe('overdue');
    expect(classifyWindow(0)).toBe('this_week');
    expect(classifyWindow(7)).toBe('this_week');
    expect(classifyWindow(8)).toBe('this_month');
    expect(classifyWindow(30)).toBe('this_month');
    expect(classifyWindow(31)).toBe('later');
  });
});

describe('toKilograms', () => {
  it('converts standard units', () => {
    expect(toKilograms(2, 'quintal')).toBe(200);
    expect(toKilograms(1.5, 'tonne')).toBe(1500);
    expect(toKilograms(50, 'kg')).toBe(50);
  });
  it('returns null for non-standard units (bag)', () => {
    expect(toKilograms(10, 'bag')).toBeNull();
  });
});

describe('computeInsight', () => {
  const base: OfferFacts = {
    quantity: 20,
    unit: 'quintal',
    expectedHarvestDate: '2026-07-20',
  };

  it('produces no market value without a verified price', () => {
    const insight = computeInsight(base, null, TODAY);
    expect(insight.daysToHarvest).toBe(9);
    expect(insight.harvestWindow).toBe('this_month');
    expect(insight.quantityKg).toBe(2000);
    expect(insight.estimatedMarketValue).toBeNull();
  });

  it('estimates market value from a verified price (same unit)', () => {
    const insight = computeInsight(base, ref(2000), TODAY);
    expect(insight.estimatedMarketValue).toBe(40000);
    expect(insight.priceReference).not.toBeNull();
  });

  it('converts units for the value estimate', () => {
    const insight = computeInsight(
      { quantity: 2, unit: 'tonne', expectedHarvestDate: '2026-07-15' },
      ref(2000, 'quintal'),
      TODAY,
    );
    expect(insight.estimatedMarketValue).toBe(40000);
  });

  it('has no value for a non-convertible unit', () => {
    const insight = computeInsight(
      { quantity: 5, unit: 'bag', expectedHarvestDate: '2026-07-15' },
      ref(2000),
      TODAY,
    );
    expect(insight.quantityKg).toBeNull();
    expect(insight.estimatedMarketValue).toBeNull();
  });

  it('computes the asking value from the farmer price', () => {
    const insight = computeInsight({ ...base, askingPrice: 2200 }, null, TODAY);
    expect(insight.estimatedAskingValue).toBe(44000);
  });

  it('flags an overdue harvest', () => {
    const insight = computeInsight(
      { ...base, expectedHarvestDate: '2026-07-01' },
      null,
      TODAY,
    );
    expect(insight.daysToHarvest).toBe(-10);
    expect(insight.harvestWindow).toBe('overdue');
  });
});
