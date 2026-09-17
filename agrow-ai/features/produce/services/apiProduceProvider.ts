import { api } from '@/services/apiClient';
import { endpoints } from '@/services/endpoints';
import { ApiError, type Paginated } from '@/types';

import { DEFAULT_PAGE_SIZE } from '../constants';
import type {
  ApiProduceDetail,
  ApiProduceSummary,
  ProduceImageInput,
  ProduceInput,
  ProduceListParams,
  ProduceListResult,
  ProduceOfferDetail,
  FrozenBuyerOffer,
  ApiFrozenBuyerOffer,
} from '../types';
import {
  apiToDetail,
  apiToListResult,
  imageInputToApi,
  inputToApi,
  updateInputToApi,
} from './produceMapper';
import type { ProduceProvider } from './produceProvider';
import { listCacheKey, produceStorage } from './produceStorage';

/**
 * Backend produce provider (docs/API_CONTRACT.md → PRODUCE). Every successful
 * list is mirrored to MMKV so offers stay readable offline; on a network error
 * the last cached list is served instead of erroring.
 */
function cachedFallback(key: string, err: unknown): ProduceListResult {
  const cached = produceStorage.getCachedList(key);
  if (cached && err instanceof ApiError && err.isNetwork) {
    return {
      items: cached,
      page: 1,
      pageSize: cached.length,
      total: cached.length,
      totalPages: 1,
      cached: true,
    };
  }
  throw err;
}

export const apiProduceProvider: ProduceProvider = {
  async list(params: ProduceListParams): Promise<ProduceListResult> {
    const key = listCacheKey(params, 'all');
    try {
      const dto = await api.get<Paginated<ApiProduceSummary>>(endpoints.produce.root, {
        params: {
          status: params.status ?? undefined,
          crop: params.crop ?? undefined,
          availability_type: params.availabilityType ?? undefined,
          category: params.category ?? undefined,
          farm_id: params.farmId ?? undefined,
          search: params.search ?? undefined,
          page: params.page ?? 1,
          page_size: params.pageSize ?? DEFAULT_PAGE_SIZE,
        },
      });
      const result = apiToListResult(dto);
      if (result.page === 1) produceStorage.cacheList(key, result.items);
      return result;
    } catch (err) {
      return cachedFallback(key, err);
    }
  },

  async upcoming(page = 1, pageSize = DEFAULT_PAGE_SIZE): Promise<ProduceListResult> {
    const key = listCacheKey({ page }, 'upcoming');
    try {
      const dto = await api.get<Paginated<ApiProduceSummary>>(endpoints.produce.upcoming, {
        params: { page, page_size: pageSize },
      });
      const result = apiToListResult(dto);
      if (result.page === 1) produceStorage.cacheList(key, result.items);
      return result;
    } catch (err) {
      return cachedFallback(key, err);
    }
  },

  async history(page = 1, pageSize = DEFAULT_PAGE_SIZE): Promise<ProduceListResult> {
    const key = listCacheKey({ page }, 'history');
    try {
      const dto = await api.get<Paginated<ApiProduceSummary>>(endpoints.produce.history, {
        params: { page, page_size: pageSize },
      });
      const result = apiToListResult(dto);
      if (result.page === 1) produceStorage.cacheList(key, result.items);
      return result;
    } catch (err) {
      return cachedFallback(key, err);
    }
  },

  async get(id: string): Promise<ProduceOfferDetail> {
    return apiToDetail(await api.get<ApiProduceDetail>(endpoints.produce.byId(id)));
  },

  async create(input: ProduceInput): Promise<ProduceOfferDetail> {
    return apiToDetail(
      await api.post<ApiProduceDetail>(endpoints.produce.root, inputToApi(input)),
    );
  },

  async update(id: string, input: ProduceInput): Promise<ProduceOfferDetail> {
    return apiToDetail(
      await api.put<ApiProduceDetail>(endpoints.produce.byId(id), updateInputToApi(input)),
    );
  },

  async remove(id: string): Promise<void> {
    await api.delete<null>(endpoints.produce.byId(id));
  },

  async addImage(id: string, image: ProduceImageInput): Promise<ProduceOfferDetail> {
    return apiToDetail(
      await api.post<ApiProduceDetail>(
        endpoints.produce.images(id),
        imageInputToApi(image),
      ),
    );
  },

  async buyerOffer(id: string): Promise<FrozenBuyerOffer> {
    const dto = await api.get<ApiFrozenBuyerOffer>(endpoints.produce.buyerOffer(id));
    return {
      offerId: dto.offer_id, caseId: dto.case_id, status: dto.status,
      termsHash: dto.terms_hash, frozenAt: dto.frozen_at, terms: dto.terms,
      decision: dto.decision, decidedAt: dto.decided_at,
    };
  },

  async decideBuyerOffer(id, decision, idempotencyKey, reason): Promise<FrozenBuyerOffer> {
    const dto = await api.post<ApiFrozenBuyerOffer>(endpoints.produce.buyerOfferDecision(id), {
      decision, idempotency_key: idempotencyKey, reason: reason ?? null,
    });
    return {
      offerId: dto.offer_id, caseId: dto.case_id, status: dto.status,
      termsHash: dto.terms_hash, frozenAt: dto.frozen_at, terms: dto.terms,
      decision: dto.decision, decidedAt: dto.decided_at,
    };
  },
};
