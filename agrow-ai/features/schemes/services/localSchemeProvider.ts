import {
  DEFAULT_PAGE_SIZE,
  RECOMMENDED_MIN_COUNT,
  RECOMMENDED_SCORE_THRESHOLD,
  DOCUMENT_TYPES,
  classifySchemeDocument,
} from '../constants';
import type {
  Eligibility,
  EligibleSchemes,
  RecommendedSchemes,
  SchemeContext,
  SchemeDetail,
  SchemeListFilters,
  SchemePage,
  SchemeQuery,
  SchemeSummary,
  DocumentType,
  FarmerDocument,
} from '../types';
import {
  contextFromQuery,
  evaluate,
  type FarmerContext,
  isEligible,
  rank,
} from './eligibility';
import { SAMPLE_SCHEMES, type LocalScheme } from './sampleSchemes';
import { SchemeError, type SchemeProvider } from './schemeProvider';
import { schemeStorage } from './schemeStorage';

/**
 * Local, offline scheme provider. Runs the same deterministic eligibility engine
 * as the backend over verified sample schemes so the engine is fully usable in
 * dev / without a backend, and persists bookmarks in MMKV. Never fabricates
 * schemes for production — it is only selected when no verified backend is
 * configured (docs/PRODUCT_RULES.md rule 4).
 */

function toSummary(
  scheme: LocalScheme,
  eligibility: Eligibility | null,
): SchemeSummary {
  return {
    id: scheme.id,
    slug: scheme.slug,
    title: scheme.title,
    category: scheme.category,
    description: scheme.description,
    departments: scheme.departments,
    state: scheme.state,
    officialUrl: scheme.officialUrl,
    lastDate: scheme.lastDate,
    status: scheme.status,
    bookmarked: schemeStorage.isBookmarked(scheme.id),
    eligibility,
  };
}

function toDetail(
  scheme: LocalScheme,
  eligibility: Eligibility | null,
): SchemeDetail {
  return {
    ...toSummary(scheme, eligibility),
    benefits: scheme.benefits,
    eligibilitySummary: scheme.eligibilitySummary,
    applicationSteps: scheme.applicationSteps,
    documents: scheme.documents.map((doc) => {
      const documentType = classifySchemeDocument(doc.name);
      return { ...doc, documentType, hasDocument: Boolean(schemeStorage.documentStates()[documentType]) };
    }),
    documentReadiness: (() => {
      const types = scheme.documents.map((doc) => classifySchemeDocument(doc.name));
      const states = schemeStorage.documentStates();
      return { readyCount: types.filter((type) => states[type]).length, totalCount: types.length };
    })(),
    source: scheme.source,
    verifiedAt: scheme.verifiedAt,
  };
}

function contextMeta(context: FarmerContext): SchemeContext {
  return {
    district: context.district,
    crop: context.crop,
    landHectares: context.landHectares,
    farmerCategory: context.farmerCategory,
  };
}

function matchesSearch(scheme: LocalScheme, search?: string | null): boolean {
  if (!search) return true;
  const needle = search.trim().toLowerCase();
  return (
    scheme.title.toLowerCase().includes(needle) ||
    scheme.description.toLowerCase().includes(needle)
  );
}

/** Evaluate every active sample scheme against a farmer context. */
function evaluateAll(
  context: FarmerContext,
): { scheme: LocalScheme; eligibility: Eligibility }[] {
  const today = new Date();
  return SAMPLE_SCHEMES.filter((s) => s.status === 'active').map((scheme) => ({
    scheme,
    eligibility: evaluate({ ...scheme.rules, lastDate: scheme.lastDate }, context, today),
  }));
}

export const localSchemeProvider: SchemeProvider = {
  async list(filters: SchemeListFilters): Promise<SchemePage> {
    const rows = SAMPLE_SCHEMES.filter(
      (s) =>
        (!filters.category || s.category === filters.category) &&
        matchesSearch(s, filters.search),
    ).sort((a, b) => a.title.localeCompare(b.title));

    const pageSize = filters.pageSize ?? DEFAULT_PAGE_SIZE;
    const page = filters.page ?? 1;
    const items = rows
      .slice((page - 1) * pageSize, page * pageSize)
      .map((s) => toSummary(s, null));
    return {
      items,
      page,
      pageSize,
      total: rows.length,
      totalPages: Math.max(1, Math.ceil(rows.length / pageSize)),
    };
  },

  async eligible(
    query: SchemeQuery,
    page = 1,
    pageSize = DEFAULT_PAGE_SIZE,
  ): Promise<EligibleSchemes> {
    const context = contextFromQuery(query);
    const eligibleOnly = evaluateAll(context).filter((e) =>
      isEligible(e.eligibility),
    );
    const ranked = rank(
      eligibleOnly.map((e) => ({
        lastDate: e.scheme.lastDate,
        eligibility: e.eligibility,
        scheme: e.scheme,
      })),
    );
    const total = ranked.length;
    const start = (page - 1) * pageSize;
    const items = ranked
      .slice(start, start + pageSize)
      .map((r) => toSummary(r.scheme, r.eligibility));
    return {
      results: {
        items,
        page,
        pageSize,
        total,
        totalPages: total ? Math.ceil(total / pageSize) : 0,
      },
      context: contextMeta(context),
    };
  },

  async recommended(query: SchemeQuery): Promise<RecommendedSchemes> {
    const context = contextFromQuery(query);
    const eligibleOnly = evaluateAll(context).filter((e) =>
      isEligible(e.eligibility),
    );
    const ranked = rank(
      eligibleOnly.map((e) => ({
        lastDate: e.scheme.lastDate,
        eligibility: e.eligibility,
        scheme: e.scheme,
      })),
    );
    const strong = ranked.filter(
      (r) => r.eligibility.score >= RECOMMENDED_SCORE_THRESHOLD,
    );
    const chosen =
      strong.length >= RECOMMENDED_MIN_COUNT
        ? strong
        : ranked.slice(0, RECOMMENDED_MIN_COUNT);
    return {
      items: chosen.map((r) => toSummary(r.scheme, r.eligibility)),
      context: contextMeta(context),
    };
  },

  async detail(id: string, query: SchemeQuery): Promise<SchemeDetail> {
    const scheme = SAMPLE_SCHEMES.find((s) => s.id === id || s.slug === id);
    if (!scheme) throw new SchemeError('scheme_not_found', 'Scheme not found.');
    const eligibility = evaluate(
      { ...scheme.rules, lastDate: scheme.lastDate },
      contextFromQuery(query),
      new Date(),
    );
    return toDetail(scheme, eligibility);
  },

  async bookmarks(query: SchemeQuery): Promise<SchemeSummary[]> {
    const ids = schemeStorage.bookmarkIds();
    const context = contextFromQuery(query);
    const today = new Date();
    return ids
      .map((id) => SAMPLE_SCHEMES.find((s) => s.id === id))
      .filter((s): s is LocalScheme => Boolean(s))
      .map((s) =>
        toSummary(s, evaluate({ ...s.rules, lastDate: s.lastDate }, context, today)),
      );
  },

  async addBookmark(schemeId: string): Promise<void> {
    if (schemeStorage.isBookmarked(schemeId)) {
      throw new SchemeError('scheme_bookmark_exists', 'Already bookmarked.');
    }
    schemeStorage.addBookmark(schemeId);
  },

  async removeBookmark(schemeId: string): Promise<void> {
    schemeStorage.removeBookmark(schemeId);
  },
  async myDocuments(): Promise<FarmerDocument[]> {
    const states = schemeStorage.documentStates();
    return DOCUMENT_TYPES.map((documentType) => ({
      documentType,
      hasDocument: Boolean(states[documentType]),
    }));
  },
  async setMyDocument(documentType: DocumentType, hasDocument: boolean): Promise<FarmerDocument> {
    schemeStorage.setDocument(documentType, hasDocument);
    return { documentType, hasDocument };
  },
};
