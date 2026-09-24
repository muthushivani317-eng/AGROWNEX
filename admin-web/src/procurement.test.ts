import { describe, expect, it } from 'vitest';
import {
  buildProcurementPath,
  marketplaceAvailabilityLabel,
  marketplaceFarmerReference,
  marketplaceProductLabel,
  marketplacePriceLabel,
  marketplacePickupLabel,
} from './procurement';
import type { Procurement } from './types';

const listing: Procurement = {
  offer_id: 'offer-1',
  crop: 'Paddy grain',
  product_category: 'grains',
  availability_type: 'available_now',
  quantity: 12,
  unit: 'quintal',
  harvest_date: null,
  village: 'Vadaku',
  district: 'Thanjavur',
  farmer_name: 'Farmer',
  admin_status: 'new',
  buyer_name: null,
  buyer_contact: null,
  buyer_contact_masked: true,
  buyer_offer_price: null,
  follow_up_at: null,
  asking_price: 3200,
  price_unit: 'quintal',
  negotiable: true,
  packaging: '50 kg bags',
  pickup_location: 'Farm gate',
  pickup_available: true,
};

describe('admin marketplace procurement presentation', () => {
  it('sends only explicit marketplace filters to the scoped admin endpoint', () => {
    expect(buildProcurementPath({
      search: 'paddy & rice',
      category: 'grains',
      availabilityType: 'available_now',
      organicOnly: false,
    })).toBe('/admin/procurement?page=1&page_size=50&search=paddy+%26+rice&category=grains&availability_type=available_now');
  });

  it('does not add empty filters that could broaden or alter server scope', () => {
    expect(buildProcurementPath({ search: ' ', category: '', availabilityType: '', organicOnly: false }))
      .toBe('/admin/procurement?page=1&page_size=50');
  });

  it('shows product, availability and commercial terms without inventing values', () => {
    expect(marketplaceProductLabel(listing)).toBe('Paddy grain · Grains');
    expect(marketplaceAvailabilityLabel(listing)).toBe('Available now');
    expect(marketplacePriceLabel(listing)).toBe('₹3,200 / quintal · Negotiable');
    expect(marketplacePriceLabel({ ...listing, asking_price: null })).toBe('Not provided · Negotiable');
  });

  it('keeps legacy listings readable', () => {
    const legacy = { ...listing, product_category: undefined, availability_type: undefined };
    expect(marketplaceProductLabel(legacy)).toBe('Paddy grain');
    expect(marketplaceAvailabilityLabel(legacy)).toBe('Not specified');
  });

  it('uses opaque farmer references instead of names or precise coordinates', () => {
    expect(marketplaceFarmerReference({ ...listing, farmer_ref: 'AGF-2026-00001', farmer_name: 'Private name' }))
      .toBe('AGF-2026-00001');
    expect(marketplaceFarmerReference({ ...listing, farmer_ref: undefined, farmer_name: 'Private name' }))
      .toBe('Reference unavailable');
    expect(marketplacePickupLabel({ ...listing, pickup_location: '10.123456, 79.123456' }))
      .toBe('Available');
  });
});
