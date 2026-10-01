import { farmerToProfileForm } from '../hooks/useEditProfileDefaults';
import type { ApiFarmerMe } from '@/features/profile/types';

const base: ApiFarmerMe = {
  id: 'f1', user_id: 'u1', full_name: 'Murugan', gender: 'male', language: 'ta',
  district: 'thanjavur', block: 'Orathanadu', village: 'Pappanadu', profile_photo: null,
  experience_years: 12, education: 'primary', primary_crop: null, secondary_crop: null,
  preferred_crops: ['paddy'], phone_number: '+919999999999', email: null,
  land_holding_acres: 2.5, farmer_type: 'small_farmer', landmark: 'near temple',
  latitude: 10.6, longitude: 79.1, wants_fpo_support: true, wants_kvk_support: false,
  farm_products: [
    { product_id: 'paddy', category: 'crops', expected_harvest_month: '2026-12', approximate_quantity: 20, unit: 'quintal', available_for_sale: true },
    { product_id: 'honey', category: 'other_products', expected_harvest_month: null, approximate_quantity: null, unit: 'litre', available_for_sale: false },
  ],
  created_at: '', updated_at: '',
};

describe('Edit profile pre-fill', () => {
  it('maps every saved onboarding field back into the form', () => {
    const form = farmerToProfileForm(base, 'en');
    expect(form).toMatchObject({
      name: 'Murugan', language: 'ta', district: 'thanjavur', block: 'Orathanadu', village: 'Pappanadu',
      experienceYears: '12', landHoldingAcres: '2.5', farmerType: 'small', landmark: 'near temple',
      latitude: 10.6, longitude: 79.1, wantsFpoSupport: true, wantsKvkSupport: false, preferredCrops: ['paddy'],
    });
    expect(form.farmProducts).toEqual([
      { productId: 'paddy', category: 'crops', expectedHarvestMonth: '2026-12', approximateQuantity: 20, unit: 'quintal', availableForSale: true },
      { productId: 'honey', category: 'other', expectedHarvestMonth: null, approximateQuantity: null, unit: 'litre', availableForSale: false },
    ]);
  });

  it('handles a sparse record without inventing values', () => {
    const form = farmerToProfileForm({ ...base, full_name: null, experience_years: null, land_holding_acres: null,
      farmer_type: 'unknown', farm_products: undefined, latitude: undefined, language: 'xx' }, 'en');
    expect(form).toMatchObject({ name: '', experienceYears: '', landHoldingAcres: '', farmerType: null,
      farmProducts: [], latitude: null, language: 'en' });
  });
});
