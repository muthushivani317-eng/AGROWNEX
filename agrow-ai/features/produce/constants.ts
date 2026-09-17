import type {
  HarvestWindow,
  ProduceGrade,
  ProduceStatus,
  ProduceUnit,
  ProduceView,
  ProduceCategory,
  ProduceAvailabilityType,
} from './types';

export const PRODUCE_CACHE_KEY = 'agrowai.produce.cache';
export const PRODUCE_LOCAL_KEY = 'agrowai.produce.local';
export const PRODUCE_OUTBOX_KEY = 'agrowai.produce.outbox';

export const DEFAULT_PAGE_SIZE = 20;
export const DEFAULT_CURRENCY = 'INR';

export const produceKeys = {
  all: ['produce'] as const,
  list: (key: string) => ['produce', 'list', key] as const,
  upcoming: (key: string) => ['produce', 'upcoming', key] as const,
  history: (key: string) => ['produce', 'history', key] as const,
  detail: (id: string) => ['produce', 'detail', id] as const,
};

export const PRODUCE_VIEWS: ProduceView[] = ['all', 'available', 'upcoming', 'history'];

export const VIEW_LABEL_KEY: Record<ProduceView, string> = {
  all: 'produce.viewAll',
  available: 'produce.viewAvailable',
  upcoming: 'produce.viewUpcoming',
  history: 'produce.viewHistory',
};

export const PRODUCE_LISTING_TYPES: ProduceAvailabilityType[] = ['available_now', 'upcoming_harvest'];
export const LISTING_TYPE_LABEL_KEY: Record<ProduceAvailabilityType, string> = {
  available_now: 'produce.availableNow',
  upcoming_harvest: 'produce.upcomingHarvest',
};

export const PRODUCE_CATEGORIES: Array<{ value: ProduceCategory; labelKey: string }> = [
  { value: 'grains', labelKey: 'produce.categoryGrains' },
  { value: 'pulses', labelKey: 'produce.categoryPulses' },
  { value: 'vegetables', labelKey: 'produce.categoryVegetables' },
  { value: 'fruits', labelKey: 'produce.categoryFruits' },
  { value: 'spices', labelKey: 'produce.categorySpices' },
  { value: 'plantation_crops', labelKey: 'produce.categoryPlantation' },
  { value: 'flowers', labelKey: 'produce.categoryFlowers' },
  { value: 'other_produce', labelKey: 'produce.categoryOther' },
];

export const PRODUCE_PRODUCTS: Record<Exclude<ProduceCategory, 'other_produce'>, string[]> = {
  grains: ['Paddy', 'Wheat', 'Maize', 'Millet', 'Sorghum'],
  pulses: ['Black gram', 'Green gram', 'Red gram', 'Chickpea'],
  vegetables: ['Tomato', 'Onion', 'Potato', 'Brinjal', 'Okra', 'Chilli'],
  fruits: ['Banana', 'Mango', 'Guava', 'Papaya', 'Watermelon'],
  spices: ['Turmeric', 'Pepper', 'Cardamom', 'Coriander'],
  plantation_crops: ['Coconut', 'Arecanut', 'Tea', 'Coffee', 'Sugarcane'],
  flowers: ['Jasmine', 'Marigold', 'Rose', 'Chrysanthemum'],
};

const BLOCKED_PRODUCT_TERMS = /\b(pesticide|insecticide|fertili[sz]er|medicine|tractor|livestock|animal|seed)\b/i;
export function resolveProduceProduct(category: ProduceCategory, product: string, custom: string): string | null {
  const value = (category === 'other_produce' ? custom : product).trim().replace(/\s+/g, ' ');
  if (!value || value.length > 80 || /[\u0000-\u001f]/.test(value) || BLOCKED_PRODUCT_TERMS.test(value)) return null;
  return value;
}

export const UNITS: ProduceUnit[] = ['quintal', 'kg', 'tonne', 'bag'];

export const UNIT_LABEL_KEY: Record<ProduceUnit, string> = {
  kg: 'produce.unitKg',
  quintal: 'produce.unitQuintal',
  tonne: 'produce.unitTonne',
  bag: 'produce.unitBag',
};

export const GRADES: ProduceGrade[] = ['a', 'b', 'c', 'faq', 'mixed', 'ungraded'];

export const GRADE_LABEL_KEY: Record<ProduceGrade, string> = {
  a: 'produce.gradeA',
  b: 'produce.gradeB',
  c: 'produce.gradeC',
  faq: 'produce.gradeFaq',
  mixed: 'produce.gradeMixed',
  ungraded: 'produce.gradeUngraded',
};

export const STATUS_LABEL_KEY: Record<ProduceStatus, string> = {
  draft: 'produce.statusDraft',
  submitted: 'produce.statusSubmitted',
  planned: 'produce.statusPlanned',
  harvested: 'produce.statusHarvested',
  fulfilled: 'produce.statusFulfilled',
  withdrawn: 'produce.statusWithdrawn',
  expired: 'produce.statusExpired',
};

export const STATUS_TONE: Record<
  ProduceStatus,
  'primary' | 'success' | 'warning' | 'danger' | 'info' | 'neutral'
> = {
  draft: 'neutral',
  submitted: 'primary',
  planned: 'info',
  harvested: 'success',
  fulfilled: 'success',
  withdrawn: 'danger',
  expired: 'warning',
};

export const HARVEST_WINDOW_LABEL_KEY: Record<HarvestWindow, string> = {
  overdue: 'produce.windowOverdue',
  this_week: 'produce.windowThisWeek',
  this_month: 'produce.windowThisMonth',
  later: 'produce.windowLater',
};

export const HARVEST_WINDOW_TONE: Record<
  HarvestWindow,
  'success' | 'warning' | 'danger' | 'neutral'
> = {
  overdue: 'danger',
  this_week: 'warning',
  this_month: 'success',
  later: 'neutral',
};

/** Statuses a farmer can set directly from the UI (mirrors the backend). */
export const FARMER_SETTABLE_STATUSES: ProduceStatus[] = [
  'draft',
  'submitted',
  'harvested',
  'withdrawn',
];
