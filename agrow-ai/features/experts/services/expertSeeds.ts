import type { ExpertDetail } from '../types';

/**
 * Client-side mirror of the backend's verified expert desks
 * (backend: app/modules/experts/provider._SEED_EXPERTS). Real institutional
 * advisory desks — never fabricated individuals (docs/PRODUCT_RULES.md). Used by
 * the local/offline provider so Expert Connect works in dev / without a backend.
 * Slugs double as stable ids so local consultations reference a fixed desk.
 */
function desk(
  id: string,
  fullName: string,
  expertType: ExpertDetail['expertType'],
  organization: string,
  title: string,
  bio: string,
  categories: string[],
  extra: Partial<ExpertDetail> = {},
): ExpertDetail {
  return {
    id,
    fullName,
    expertType,
    organization,
    title,
    photoUrl: null,
    districts: [],
    languages: ['ta', 'en'],
    yearsExperience: null,
    rating: null,
    ratingCount: 0,
    verified: true,
    categories,
    bio,
    source: null,
    contact: null,
    specializations: categories.map((category) => ({ category, crop: null })),
    availability: [],
    ...extra,
  };
}

export function expertSeeds(): ExpertDetail[] {
  return [
    desk(
      'tnau-agritech-helpline',
      'TNAU Agri-Tech Advisory',
      'tnau',
      'Tamil Nadu Agricultural University',
      'University Advisory Desk',
      'Advisory desk of Tamil Nadu Agricultural University covering crop management, pest and disease guidance and good agricultural practices.',
      ['general', 'crop_disease', 'pest_control', 'fertilizer', 'seed', 'organic'],
      { source: 'https://tnau.ac.in' },
    ),
    desk(
      'tnau-plant-clinic',
      'TNAU Plant Health Clinic',
      'tnau',
      'Tamil Nadu Agricultural University',
      'Plant Health Specialist Desk',
      'Diagnoses crop diseases and pest problems from farmer photos and notes.',
      ['crop_disease', 'pest_control'],
      { source: 'https://tnau.ac.in' },
    ),
    desk(
      'kvk-farm-advisory',
      'Krishi Vigyan Kendra Farm Advisory',
      'kvk',
      'Krishi Vigyan Kendra (ICAR)',
      'District Farm Science Centre',
      'District-level Krishi Vigyan Kendra advisory for soil health, irrigation, seeds and location-specific crop guidance.',
      ['soil_health', 'irrigation', 'seed', 'fertilizer', 'general'],
      { source: 'https://kvk.icar.gov.in' },
    ),
    desk(
      'kisan-call-centre',
      'Kisan Call Centre',
      'kisan_call_centre',
      'Ministry of Agriculture & Farmers Welfare',
      'National Farmer Helpline',
      'National toll-free farmer helpline for all agricultural queries.',
      ['general', 'scheme', 'market', 'weather'],
      { languages: ['ta', 'en', 'hi'], contact: '1800-180-1551', source: 'https://mkisan.gov.in' },
    ),
    desk(
      'state-agriculture-officer',
      'State Agriculture Officer Desk',
      'govt_officer',
      'Tamil Nadu Department of Agriculture',
      'Block Agriculture Officer',
      'State agriculture department desk for schemes, subsidies, input supply and field-level guidance.',
      ['scheme', 'fertilizer', 'seed', 'general'],
      { source: 'https://www.tn.gov.in/department/1' },
    ),
  ];
}
