import { PRODUCE_CATEGORIES, PRODUCE_LISTING_TYPES, resolveProduceProduct } from '../constants';
import { produceFormSchema } from '../schemas';

const base = {
  farmId: 'farm-1',
  availabilityType: 'available_now',
  category: 'vegetables',
  productName: 'Tomato',
  customProductName: '',
  variety: '',
  cultivatedAreaAcres: '',
  expectedTotalQuantity: '10',
  availableQuantity: '10',
  unit: 'kg',
  expectedHarvestDate: '',
  availableFrom: '2026-08-28',
  availableUntil: '2026-09-01',
  expectedGrade: 'ungraded',
  packaging: 'Crates',
  askingPrice: '35',
  priceUnit: 'kg',
  negotiable: true,
  pickupLocation: 'Farm gate',
  notes: '',
  qualityNotes: '',
  status: 'submitted',
} as const;

describe('agricultural produce marketplace contract', () => {
  it('defines the approved listing types and agricultural categories', () => {
    expect(PRODUCE_LISTING_TYPES).toEqual(['available_now', 'upcoming_harvest']);
    expect(PRODUCE_CATEGORIES.map((item) => item.value)).toEqual([
      'grains', 'pulses', 'vegetables', 'fruits', 'spices', 'plantation_crops', 'flowers', 'other_produce',
    ]);
  });

  it('accepts available produce without inventing a harvest date', () => {
    const result = produceFormSchema.safeParse(base);
    expect(result.success).toBe(true);
  });

  it('requires a future date for an upcoming harvest', () => {
    const result = produceFormSchema.safeParse({
      ...base,
      availabilityType: 'upcoming_harvest',
      expectedHarvestDate: '',
    });
    expect(result.success).toBe(false);
  });

  it('requires a safe custom name when Other is selected', () => {
    expect(resolveProduceProduct('other_produce', 'Other', '')).toBeNull();
    expect(resolveProduceProduct('other_produce', 'Other', '  Fresh turmeric rhizome  ')).toBe(
      'Fresh turmeric rhizome',
    );
    expect(resolveProduceProduct('other_produce', 'Other', 'Pesticide spray')).toBeNull();
  });
});
