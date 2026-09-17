import type {
  EligibilityStatus,
  SchemeCategory,
  SchemeTab,
  DocumentType,
} from './types';

export const SCHEMES_CACHE_KEY = 'agrowai.schemes.cache';
export const SCHEME_BOOKMARKS_KEY = 'agrowai.schemes.bookmarks';
export const SCHEME_DOCUMENTS_KEY = 'agrowai.schemes.documents';

export const DEFAULT_PAGE_SIZE = 20;
export const SEARCH_DEBOUNCE_MS = 300;

/** A scheme is "recommended" at or above this score (mirrors the backend). */
export const RECOMMENDED_SCORE_THRESHOLD = 70;
export const RECOMMENDED_MIN_COUNT = 3;

/** The app is Tamil-Nadu-first; unknown state defaults here (mirrors backend). */
export const DEFAULT_STATE = 'Tamil Nadu';

export const schemeKeys = {
  all: ['schemes'] as const,
  list: (filterKey: string) => ['schemes', 'list', filterKey] as const,
  eligible: (queryKey: string) => ['schemes', 'eligible', queryKey] as const,
  recommended: (queryKey: string) =>
    ['schemes', 'recommended', queryKey] as const,
  bookmarks: ['schemes', 'bookmarks'] as const,
  documents: ['schemes', 'my-documents'] as const,
  detail: (id: string, queryKey: string) =>
    ['schemes', 'detail', id, queryKey] as const,
};

export const DOCUMENT_TYPES: DocumentType[] = [
  'aadhaar', 'land_tenure_proof', 'bank_passbook', 'photograph',
  'income_certificate', 'sowing_certificate', 'service_connection',
  'water_source_proof', 'other',
];
export const DOCUMENT_LABEL_KEY: Record<DocumentType, string> = {
  aadhaar: 'schemes.documentTypeAadhaar',
  land_tenure_proof: 'schemes.documentTypeLandTenure',
  bank_passbook: 'schemes.documentTypeBankPassbook',
  photograph: 'schemes.documentTypePhotograph',
  income_certificate: 'schemes.documentTypeIncomeCertificate',
  sowing_certificate: 'schemes.documentTypeSowingCertificate',
  service_connection: 'schemes.documentTypeServiceConnection',
  water_source_proof: 'schemes.documentTypeWaterSource',
  other: 'schemes.documentTypeOther',
};
const DOCUMENT_ALIASES: Record<string, DocumentType> = {
  'Aadhaar card': 'aadhaar', 'Identity proof (Aadhaar/Voter ID)': 'aadhaar',
  'Land ownership records': 'land_tenure_proof', 'Land ownership documents': 'land_tenure_proof',
  'Land records': 'land_tenure_proof', 'Land records / tenancy proof': 'land_tenure_proof',
  'Bank account passbook': 'bank_passbook', 'Bank passbook': 'bank_passbook',
  'Passport-size photograph': 'photograph', 'Income certificate': 'income_certificate',
  'Sowing certificate': 'sowing_certificate',
  'Agricultural service connection number': 'service_connection',
  'Water source proof': 'water_source_proof',
};
export const classifySchemeDocument = (name: string): DocumentType =>
  DOCUMENT_ALIASES[name] ?? 'other';

export const SCHEME_TABS: SchemeTab[] = [
  'eligible',
  'recommended',
  'all',
  'bookmarked',
];

export const TAB_LABEL_KEY: Record<SchemeTab, string> = {
  eligible: 'schemes.tabEligible',
  recommended: 'schemes.tabRecommended',
  all: 'schemes.tabAll',
  bookmarked: 'schemes.tabBookmarked',
};

/** Scheme category → localized label key (under the `schemes` namespace). */
export const CATEGORY_LABEL_KEY: Record<SchemeCategory, string> = {
  insurance: 'schemes.categoryInsurance',
  subsidy: 'schemes.categorySubsidy',
  loan: 'schemes.categoryLoan',
  equipment: 'schemes.categoryEquipment',
  seeds: 'schemes.categorySeeds',
  irrigation: 'schemes.categoryIrrigation',
  organic_farming: 'schemes.categoryOrganic',
  income_support: 'schemes.categoryIncomeSupport',
  other: 'schemes.categoryOther',
};

/** Filterable categories, in display order. */
export const FILTER_CATEGORIES: SchemeCategory[] = [
  'income_support',
  'insurance',
  'subsidy',
  'loan',
  'irrigation',
  'seeds',
  'equipment',
  'organic_farming',
  'other',
];

/** Eligibility status → localized label key + badge tone. */
export const STATUS_LABEL_KEY: Record<EligibilityStatus, string> = {
  eligible: 'schemes.statusEligible',
  likely_eligible: 'schemes.statusLikely',
  not_eligible: 'schemes.statusNotEligible',
};

export const STATUS_TONE: Record<
  EligibilityStatus,
  'success' | 'warning' | 'danger'
> = {
  eligible: 'success',
  likely_eligible: 'warning',
  not_eligible: 'danger',
};

/** Eligibility criteria code → localized label key (matched/unmet/unknown). */
export const CRITERION_LABEL_KEY: Record<string, string> = {
  state: 'schemes.criterionState',
  district: 'schemes.criterionDistrict',
  crop: 'schemes.criterionCrop',
  category: 'schemes.criterionCategory',
  land: 'schemes.criterionLand',
  income: 'schemes.criterionIncome',
};
