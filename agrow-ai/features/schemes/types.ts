/**
 * Government Scheme domain types (docs/API_CONTRACT.md → GOVERNMENT SCHEMES).
 * Client-side camelCase mirror of the backend scheme schemas. This is an
 * eligibility engine, not a listing app — every scheme carries the engine's
 * transparent verdict. Schemes come only from verified sources
 * (docs/PRODUCT_RULES.md rule 4) — nothing here is fabricated.
 */

export type SchemeCategory =
  | 'insurance'
  | 'subsidy'
  | 'loan'
  | 'equipment'
  | 'seeds'
  | 'irrigation'
  | 'organic_farming'
  | 'income_support'
  | 'other';

export type SchemeStatus = 'active' | 'closed';

export type EligibilityStatus = 'eligible' | 'likely_eligible' | 'not_eligible';

export type FarmerCategory =
  | 'marginal'
  | 'small'
  | 'semi_medium'
  | 'medium'
  | 'large';

export type SchemeTab = 'eligible' | 'recommended' | 'all' | 'bookmarked';
export type DocumentType =
  | 'aadhaar' | 'land_tenure_proof' | 'bank_passbook' | 'photograph'
  | 'income_certificate' | 'sowing_certificate' | 'service_connection'
  | 'water_source_proof' | 'other';

export interface FarmerDocument { documentType: DocumentType; hasDocument: boolean }
export interface DocumentReadiness { readyCount: number; totalCount: number }

/** The engine's transparent verdict for a scheme + farmer. */
export interface Eligibility {
  status: EligibilityStatus;
  score: number;
  matched: string[];
  unmet: string[];
  unknown: string[];
}

export interface SchemeDocument {
  name: string;
  required: boolean;
  documentType: DocumentType;
  hasDocument: boolean;
}

export interface SchemeSummary {
  id: string;
  slug: string;
  title: string;
  category: SchemeCategory;
  description: string;
  departments: string[];
  state: string;
  officialUrl: string | null;
  lastDate: string | null; // YYYY-MM-DD
  status: SchemeStatus;
  bookmarked: boolean;
  eligibility: Eligibility | null;
}

export interface SchemeDetail extends SchemeSummary {
  benefits: string | null;
  eligibilitySummary: string | null;
  applicationSteps: string[];
  documents: SchemeDocument[];
  documentReadiness: DocumentReadiness;
  source: string | null;
  verifiedAt: string | null;
}

/** Context echoed back so the client can show what the ranking was based on. */
export interface SchemeContext {
  district: string | null;
  crop: string | null;
  landHectares: number | null;
  farmerCategory: string | null;
}

export interface SchemePage {
  cached?: boolean;
  items: SchemeSummary[];
  page: number;
  pageSize: number;
  total: number;
  totalPages: number;
}

export interface EligibleSchemes {
  cached?: boolean;
  results: SchemePage;
  context: SchemeContext;
}

export interface RecommendedSchemes {
  cached?: boolean;
  items: SchemeSummary[];
  context: SchemeContext;
}

/**
 * Optional overrides for the eligibility check. Defaults are derived server-side
 * from the farmer's profile + farm; the client passes the selected farm's id and
 * any known overrides so both the API and offline providers evaluate identically.
 */
export interface SchemeQuery {
  farmId?: string | null;
  state?: string | null;
  district?: string | null;
  crop?: string | null;
  landHectares?: number | null;
  annualIncome?: number | null;
  farmerCategory?: FarmerCategory | null;
}

export interface SchemeListFilters {
  category?: SchemeCategory | null;
  search?: string | null;
  page?: number;
  pageSize?: number;
}

// --------------------------------------------------------------------------- //
// Backend envelope shapes (snake_case).
// --------------------------------------------------------------------------- //
export interface ApiEligibility {
  status: EligibilityStatus;
  score: number;
  matched: string[];
  unmet: string[];
  unknown: string[];
}

export interface ApiSchemeDocument {
  name: string;
  required: boolean;
  document_type: DocumentType;
  has_document: boolean;
}
export interface ApiFarmerDocument { document_type: DocumentType; has_document: boolean }

export interface ApiSchemeSummary {
  id: string;
  slug: string;
  title: string;
  category: SchemeCategory;
  description: string;
  departments: string[];
  state: string;
  official_url: string | null;
  last_date: string | null;
  status: SchemeStatus;
  bookmarked: boolean;
  eligibility: ApiEligibility | null;
}

export interface ApiSchemeDetail extends ApiSchemeSummary {
  benefits: string | null;
  eligibility_summary: string | null;
  application_steps: string[];
  documents: ApiSchemeDocument[];
  document_readiness: { ready_count: number; total_count: number };
  source: string | null;
  verified_at: string | null;
}

export interface ApiSchemeContext {
  district: string | null;
  crop: string | null;
  land_hectares: number | null;
  farmer_category: string | null;
}

export interface ApiSchemePage {
  items: ApiSchemeSummary[];
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
}

export interface ApiEligibleSchemes {
  results: ApiSchemePage;
  context: ApiSchemeContext;
}

export interface ApiRecommendedSchemes {
  items: ApiSchemeSummary[];
  context: ApiSchemeContext;
}
