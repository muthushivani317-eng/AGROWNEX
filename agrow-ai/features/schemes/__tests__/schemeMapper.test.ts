import {
  apiToDetail,
  apiToEligibility,
  apiToEligible,
  apiToRecommended,
  apiToSummary,
} from '../services/schemeMapper';
import type {
  ApiEligibleSchemes,
  ApiSchemeDetail,
  ApiSchemeSummary,
} from '../types';

const apiSummary: ApiSchemeSummary = {
  id: 's1',
  slug: 'pm-kisan',
  title: 'PM-KISAN Samman Nidhi',
  category: 'income_support',
  description: 'Income support for farmers.',
  departments: ['Ministry of Agriculture & Farmers Welfare'],
  state: 'all',
  official_url: 'https://pmkisan.gov.in',
  last_date: null,
  status: 'active',
  bookmarked: false,
  eligibility: {
    status: 'eligible',
    score: 79,
    matched: ['crop'],
    unmet: [],
    unknown: [],
  },
};

describe('apiToEligibility', () => {
  it('maps a verdict and defaults missing arrays', () => {
    expect(apiToEligibility(apiSummary.eligibility)).toEqual({
      status: 'eligible',
      score: 79,
      matched: ['crop'],
      unmet: [],
      unknown: [],
    });
    expect(apiToEligibility(null)).toBeNull();
  });
});

describe('apiToSummary', () => {
  it('maps snake_case to camelCase', () => {
    const summary = apiToSummary(apiSummary);
    expect(summary.officialUrl).toBe('https://pmkisan.gov.in');
    expect(summary.lastDate).toBeNull();
    expect(summary.eligibility?.score).toBe(79);
    expect(summary.departments).toHaveLength(1);
  });
});

describe('apiToDetail', () => {
  it('maps documents, steps and verification metadata', () => {
    const dto: ApiSchemeDetail = {
      ...apiSummary,
      benefits: '₹6,000 per year.',
      eligibility_summary: 'All landholding farmers.',
      application_steps: ['Register.', 'Complete e-KYC.'],
      documents: [
        { name: 'Aadhaar card', required: true, document_type: 'aadhaar', has_document: true },
        { name: 'Sowing certificate', required: false, document_type: 'sowing_certificate', has_document: false },
      ],
      document_readiness: { ready_count: 1, total_count: 2 },
      source: 'mock',
      verified_at: '2026-07-11T00:00:00Z',
    };
    const detail = apiToDetail(dto);
    expect(detail.applicationSteps).toHaveLength(2);
    expect(detail.documents[1].required).toBe(false);
    expect(detail.documentReadiness).toEqual({ readyCount: 1, totalCount: 2 });
    expect(detail.eligibilitySummary).toBe('All landholding farmers.');
    expect(detail.verifiedAt).toBe('2026-07-11T00:00:00Z');
  });
});

describe('apiToEligible', () => {
  it('maps the paginated results + context envelope', () => {
    const dto: ApiEligibleSchemes = {
      results: {
        items: [apiSummary],
        page: 1,
        page_size: 20,
        total: 1,
        total_pages: 1,
      },
      context: {
        district: 'Thanjavur',
        crop: 'paddy',
        land_hectares: 1.5,
        farmer_category: 'small',
      },
    };
    const result = apiToEligible(dto);
    expect(result.results.pageSize).toBe(20);
    expect(result.results.items[0].slug).toBe('pm-kisan');
    expect(result.context.landHectares).toBe(1.5);
    expect(result.context.farmerCategory).toBe('small');
  });
});

describe('apiToRecommended', () => {
  it('maps items + context', () => {
    const result = apiToRecommended({
      items: [apiSummary],
      context: {
        district: null,
        crop: null,
        land_hectares: null,
        farmer_category: null,
      },
    });
    expect(result.items).toHaveLength(1);
    expect(result.context.district).toBeNull();
  });
});
