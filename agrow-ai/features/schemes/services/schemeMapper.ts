import type {
  ApiEligibility,
  ApiEligibleSchemes,
  ApiRecommendedSchemes,
  ApiSchemeContext,
  ApiSchemeDetail,
  ApiSchemePage,
  ApiSchemeSummary,
  Eligibility,
  EligibleSchemes,
  RecommendedSchemes,
  SchemeContext,
  SchemeDetail,
  SchemePage,
  SchemeSummary,
} from '../types';

/** Pure API-envelope → domain conversions (snake_case → camelCase). */

export function apiToEligibility(dto: ApiEligibility | null): Eligibility | null {
  if (!dto) return null;
  return {
    status: dto.status,
    score: dto.score,
    matched: dto.matched ?? [],
    unmet: dto.unmet ?? [],
    unknown: dto.unknown ?? [],
  };
}

export function apiToSummary(dto: ApiSchemeSummary): SchemeSummary {
  return {
    id: dto.id,
    slug: dto.slug,
    title: dto.title,
    category: dto.category,
    description: dto.description,
    departments: dto.departments ?? [],
    state: dto.state,
    officialUrl: dto.official_url,
    lastDate: dto.last_date,
    status: dto.status,
    bookmarked: dto.bookmarked,
    eligibility: apiToEligibility(dto.eligibility),
  };
}

export function apiToDetail(dto: ApiSchemeDetail): SchemeDetail {
  return {
    ...apiToSummary(dto),
    benefits: dto.benefits,
    eligibilitySummary: dto.eligibility_summary,
    applicationSteps: dto.application_steps ?? [],
    documents: (dto.documents ?? []).map((d) => ({
      name: d.name,
      required: d.required,
      documentType: d.document_type,
      hasDocument: d.has_document,
    })),
    documentReadiness: {
      readyCount: dto.document_readiness.ready_count,
      totalCount: dto.document_readiness.total_count,
    },
    source: dto.source,
    verifiedAt: dto.verified_at,
  };
}

export function apiToContext(dto: ApiSchemeContext): SchemeContext {
  return {
    district: dto.district,
    crop: dto.crop,
    landHectares: dto.land_hectares,
    farmerCategory: dto.farmer_category,
  };
}

export function apiToPage(dto: ApiSchemePage): SchemePage {
  return {
    items: dto.items.map(apiToSummary),
    page: dto.page,
    pageSize: dto.page_size,
    total: dto.total,
    totalPages: dto.total_pages,
  };
}

export function apiToEligible(dto: ApiEligibleSchemes): EligibleSchemes {
  return {
    results: apiToPage(dto.results),
    context: apiToContext(dto.context),
  };
}

export function apiToRecommended(dto: ApiRecommendedSchemes): RecommendedSchemes {
  return {
    items: dto.items.map(apiToSummary),
    context: apiToContext(dto.context),
  };
}
