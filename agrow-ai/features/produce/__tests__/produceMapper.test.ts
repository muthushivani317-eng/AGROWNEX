import type { Paginated } from '@/types';

import {
  apiToDetail,
  apiToInsight,
  apiToListResult,
  apiToOffer,
  imageInputToApi,
  inputToApi,
  updateInputToApi,
} from '../services/produceMapper';
import type {
  ApiProcurementInsight,
  ApiProduceDetail,
  ApiProduceSummary,
  ProduceInput,
} from '../types';

const apiInsight: ApiProcurementInsight = {
  days_to_harvest: 9,
  harvest_window: 'this_month',
  quantity_kg: 2000,
  estimated_market_value: 41000,
  estimated_asking_value: null,
  price_reference: {
    modal_price: 2050,
    minimum_price: 1950,
    maximum_price: 2150,
    unit: 'quintal',
    source: 'agmarknet',
    price_date: '2026-07-11',
    market: 'Thanjavur',
    district: 'Thanjavur',
  },
};

const apiSummary: ApiProduceSummary = {
  id: 'o1',
  farm_id: 'f1',
  crop_name: 'Paddy',
  availability_type: 'upcoming_harvest',
  category: 'grains',
  product_name: 'Paddy',
  variety: 'Ponni',
  quantity: 20,
  unit: 'quintal',
  cultivated_area_hectares: 1.2140569,
  expected_total_quantity: 30,
  available_quantity: 20,
  quantity_provenance: 'farmer_reported',
  quality_notes: 'Clean, mature grain',
  expected_harvest_date: '2026-07-20',
  expected_grade: 'a',
  asking_price: null,
  price_unit: 'quintal',
  negotiable: true,
  packaging: '50 kg bags',
  currency: 'INR',
  current_market_price_snapshot: 2050,
  district: 'Thanjavur',
  status: 'submitted',
  thumbnail_url: 'https://cdn/r2/a.jpg',
  image_count: 1,
  insight: apiInsight,
  organic_certification_status: 'verified',
  organic_certification_verified: true,
  created_at: '2026-07-11T00:00:00Z',
  updated_at: '2026-07-11T00:00:00Z',
};

describe('apiToInsight', () => {
  it('maps the engine output and price reference', () => {
    const insight = apiToInsight(apiInsight);
    expect(insight?.daysToHarvest).toBe(9);
    expect(insight?.estimatedMarketValue).toBe(41000);
    expect(insight?.priceReference?.modalPrice).toBe(2050);
  });
  it('returns null when there is no insight', () => {
    expect(apiToInsight(null)).toBeNull();
  });
});

describe('apiToOffer', () => {
  it('maps snake_case to camelCase', () => {
    const offer = apiToOffer(apiSummary);
    expect(offer.farmId).toBe('f1');
    expect(offer.cropName).toBe('Paddy');
    expect(offer.availabilityType).toBe('upcoming_harvest');
    expect(offer.category).toBe('grains');
    expect(offer.packaging).toBe('50 kg bags');
    expect(offer.currentMarketPriceSnapshot).toBe(2050);
    expect(offer.imageCount).toBe(1);
    expect(offer.cultivatedAreaHectares).toBeCloseTo(1.2140569);
    expect(offer.expectedTotalQuantity).toBe(30);
    expect(offer.availableQuantity).toBe(20);
    expect(offer.qualityNotes).toBe('Clean, mature grain');
    expect(offer.insight?.harvestWindow).toBe('this_month');
    expect(offer.syncStatus).toBe('synced');
  });
});

describe('apiToDetail', () => {
  it('maps images, status history and procurement metadata', () => {
    const dto: ApiProduceDetail = {
      ...apiSummary,
      block: 'Block-1',
      village: 'Village-1',
      latitude: 10.7,
      longitude: 79.1,
      available_from: null,
      available_until: null,
      market_price_source: 'agmarknet',
      market_price_date: '2026-07-11',
      procurement_channel: 'mock',
      procurement_reference: 'MOCK-ABC123',
      notes: 'Good crop',
      images: [
        {
          id: 'i1',
          image_url: 'https://cdn/r2/a.jpg',
          thumbnail_url: null,
          mime_type: 'image/jpeg',
          caption: null,
          display_order: 0,
          created_at: '2026-07-11T00:00:00Z',
        },
      ],
      status_history: [
        {
          id: 'h1',
          old_status: null,
          new_status: 'submitted',
          note: 'Offer created',
          created_at: '2026-07-11T00:00:00Z',
        },
      ],
    };
    const detail = apiToDetail(dto);
    expect(detail.procurementChannel).toBe('mock');
    expect(detail.procurementReference).toBe('MOCK-ABC123');
    expect(detail.images).toHaveLength(1);
    expect(detail.statusHistory[0].newStatus).toBe('submitted');
  });
});

describe('apiToListResult', () => {
  it('maps a paginated envelope', () => {
    const dto: Paginated<ApiProduceSummary> = {
      items: [apiSummary],
      page: 1,
      page_size: 20,
      total: 1,
      total_pages: 1,
    };
    const result = apiToListResult(dto);
    expect(result.pageSize).toBe(20);
    expect(result.items[0].cropName).toBe('Paddy');
  });
});

describe('inputToApi / updateInputToApi', () => {
  const input: ProduceInput = {
    farmId: 'f1',
    cropName: 'Paddy',
    availabilityType: 'available_now',
    category: 'grains',
    productName: 'Paddy',
    quantity: 20,
    unit: 'quintal',
    expectedHarvestDate: '2026-07-20',
    askingPrice: 2200,
    priceUnit: 'quintal',
    negotiable: true,
    packaging: '50 kg bags',
    cultivatedAreaAcres: 3,
    expectedTotalQuantity: 30,
    availableQuantity: 20,
    qualityNotes: 'Clean, mature grain',
    availableFrom: '2026-07-20',
    availableUntil: '2026-07-24',
    images: [{ imageUrl: 'https://cdn/r2/a.jpg' }],
  };

  it('maps a create body including images', () => {
    const body = inputToApi(input);
    expect(body.farm_id).toBe('f1');
    expect(body.crop_name).toBe('Paddy');
    expect(body.availability_type).toBe('available_now');
    expect(body.category).toBe('grains');
    expect(body.price_unit).toBe('quintal');
    expect(body.negotiable).toBe(true);
    expect(body).not.toHaveProperty('custom_product_name');
    expect(body.expected_harvest_date).toBe('2026-07-20');
    expect(body.asking_price).toBe(2200);
    expect(body.cultivated_area_hectares).toBeCloseTo(1.2140569);
    expect(body.expected_total_quantity).toBe(30);
    expect(body.available_quantity).toBe(20);
    expect(body.quantity_provenance).toBe('farmer_reported');
    expect(body.quality_notes).toBe('Clean, mature grain');
    expect(body.available_from).toBe('2026-07-20');
    expect(body.available_until).toBe('2026-07-24');
    expect(Array.isArray(body.images)).toBe(true);
  });

  it('omits images from the update body', () => {
    const body = updateInputToApi(input);
    expect(body.images).toBeUndefined();
  });

  it('forces custom other produce into draft review', () => {
    const body = inputToApi({
      ...input,
      category: 'other_produce',
      productName: 'Fresh turmeric rhizome',
      customProductName: 'Fresh turmeric rhizome',
      status: 'submitted',
    });
    expect(body.status).toBe('draft');
  });

  it('maps an image input', () => {
    expect(imageInputToApi({ imageUrl: 'x', mimeType: 'image/png' })).toMatchObject({
      image_url: 'x',
      mime_type: 'image/png',
    });
  });
});
