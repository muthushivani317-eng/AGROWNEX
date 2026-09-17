import { api } from '@/services/apiClient';
import { endpoints } from '@/services/endpoints';
import { ApiError } from '@/types';

import { DEFAULT_PAGE_SIZE } from '../constants';
import type {
  ApiEligibleSchemes,
  ApiRecommendedSchemes,
  ApiSchemeDetail,
  ApiSchemePage,
  ApiSchemeSummary,
  ApiFarmerDocument,
  DocumentType,
  FarmerDocument,
  EligibleSchemes,
  RecommendedSchemes,
  SchemeDetail,
  SchemeListFilters,
  SchemePage,
  SchemeQuery,
  SchemeSummary,
} from '../types';
import {
  apiToDetail,
  apiToEligible,
  apiToPage,
  apiToRecommended,
  apiToSummary,
} from './schemeMapper';
import type { SchemeProvider } from './schemeProvider';
import { listCacheKey, queryCacheKey, schemeStorage } from './schemeStorage';

/** Translate a SchemeQuery into backend query params (snake_case). */
function queryParams(query: SchemeQuery): Record<string, unknown> {
  return {
    farm_id: query.farmId ?? undefined,
    state: query.state ?? undefined,
    district: query.district ?? undefined,
    crop: query.crop ?? undefined,
    land_hectares: query.landHectares ?? undefined,
    annual_income: query.annualIncome ?? undefined,
    farmer_category: query.farmerCategory ?? undefined,
  };
}

/**
 * Backend scheme provider (docs/API_CONTRACT.md → GOVERNMENT SCHEMES). Every
 * successful list is mirrored to MMKV so schemes stay readable offline; on a
 * network error the last cached list is served instead of erroring.
 */
export const apiSchemeProvider: SchemeProvider = {
  async list(filters: SchemeListFilters): Promise<SchemePage> {
    const params = {
      category: filters.category ?? undefined,
      search: filters.search ?? undefined,
      page: filters.page ?? 1,
      page_size: filters.pageSize ?? DEFAULT_PAGE_SIZE,
    };
    const key = `all|${listCacheKey(filters)}`;
    try {
      const dto = await api.get<ApiSchemePage>(endpoints.schemes.root, { params });
      const page = apiToPage(dto);
      if ((page.page ?? 1) === 1) schemeStorage.cacheList(key, page.items);
      return page;
    } catch (err) {
      const cached = schemeStorage.getCachedList(key);
      if (cached && err instanceof ApiError && err.isNetwork) {
        return {
          cached: true,
          items: cached,
          page: 1,
          pageSize: cached.length,
          total: cached.length,
          totalPages: 1,
        };
      }
      throw err;
    }
  },

  async eligible(
    query: SchemeQuery,
    page = 1,
    pageSize = DEFAULT_PAGE_SIZE,
  ): Promise<EligibleSchemes> {
    const params = { ...queryParams(query), page, page_size: pageSize };
    const key = `eligible|${queryCacheKey(query)}`;
    try {
      const dto = await api.get<ApiEligibleSchemes>(endpoints.schemes.eligible, {
        params,
      });
      const result = apiToEligible(dto);
      if ((result.results.page ?? 1) === 1) {
        schemeStorage.cacheList(key, result.results.items);
      }
      return result;
    } catch (err) {
      const cached = schemeStorage.getCachedList(key);
      if (cached && err instanceof ApiError && err.isNetwork && page === 1) {
        return {
          cached: true,
          results: {
            items: cached,
            page: 1,
            pageSize: cached.length,
            total: cached.length,
            totalPages: 1,
          },
          context: {
            district: null,
            crop: null,
            landHectares: null,
            farmerCategory: null,
          },
        };
      }
      throw err;
    }
  },

  async recommended(query: SchemeQuery): Promise<RecommendedSchemes> {
    const key = `recommended|${queryCacheKey(query)}`;
    try {
      const dto = await api.get<ApiRecommendedSchemes>(
        endpoints.schemes.recommended,
        { params: queryParams(query) },
      );
      const result = apiToRecommended(dto);
      schemeStorage.cacheList(key, result.items);
      return result;
    } catch (err) {
      const cached = schemeStorage.getCachedList(key);
      if (cached && err instanceof ApiError && err.isNetwork) {
        return {
          cached: true,
          items: cached,
          context: {
            district: null,
            crop: null,
            landHectares: null,
            farmerCategory: null,
          },
        };
      }
      throw err;
    }
  },

  async detail(id: string, query: SchemeQuery): Promise<SchemeDetail> {
    const dto = await api.get<ApiSchemeDetail>(endpoints.schemes.byId(id), {
      params: { farm_id: query.farmId ?? undefined },
    });
    return apiToDetail(dto);
  },

  async bookmarks(): Promise<SchemeSummary[]> {
    const dto = await api.get<ApiSchemeSummary[]>(endpoints.schemes.bookmarks);
    const items = dto.map(apiToSummary);
    schemeStorage.cacheList('bookmarked', items);
    return items;
  },

  async addBookmark(schemeId: string): Promise<void> {
    await api.post<null>(endpoints.schemes.bookmarks, { scheme_id: schemeId });
  },

  async removeBookmark(schemeId: string): Promise<void> {
    await api.delete<null>(endpoints.schemes.bookmark(schemeId));
  },
  async myDocuments(): Promise<FarmerDocument[]> {
    const rows = await api.get<ApiFarmerDocument[]>(endpoints.schemes.myDocuments);
    return rows.map((row) => ({ documentType: row.document_type, hasDocument: row.has_document }));
  },
  async setMyDocument(documentType: DocumentType, hasDocument: boolean): Promise<FarmerDocument> {
    const row = await api.put<ApiFarmerDocument>(endpoints.schemes.myDocument(documentType), {
      has_document: hasDocument,
    });
    return { documentType: row.document_type, hasDocument: row.has_document };
  },
};
