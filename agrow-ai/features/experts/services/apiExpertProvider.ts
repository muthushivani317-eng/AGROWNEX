import { internalTestFlags } from '@/config/internalTestFlags';
import { api } from '@/services/apiClient';
import { endpoints } from '@/services/endpoints';
import { ApiError, type Paginated as ApiPaginated } from '@/types';

import { DEFAULT_PAGE_SIZE } from '../constants';
import type {
  ApiConsultationDetail,
  ApiConsultationSummary,
  ApiExpertDetail,
  ApiExpertSummary,
  AttachmentInput,
  Consultation,
  ConsultationDetail,
  ConsultationInput,
  ConsultationListParams,
  ConsultationStatus,
  Expert,
  ExpertDetail,
  ExpertListParams,
  Paginated,
  ReplyInput,
} from '../types';
import {
  apiToConsultation,
  apiToConsultationDetail,
  apiToConsultationList,
  apiToExpert,
  apiToExpertDetail,
  apiToExpertList,
  consultationInputToApi,
  attachmentToApi,
  replyInputToApi,
} from './expertMapper';
import type { ExpertProvider } from './expertProvider';
import {
  consultationListKey,
  expertListKey,
  expertStorage,
} from './expertStorage';

/**
 * Backend Expert Connect provider (docs/API_CONTRACT.md → experts/consultations).
 * Successful lists are mirrored to MMKV so experts/consultations stay readable
 * offline; on a network error the last cached copy is served. Reply/status/
 * attachment mutations surface the network error so the hook queues them for retry.
 *
 * Gated the same way as features/equipment and features/community: the
 * production expert roster isn't populated/verified yet, so this is not
 * ready for real farmers (2026-08 pre-release audit). Hidden from Home
 * (features/home/components/QuickActions.tsx) and fail-closed here too, so a
 * direct deep link can't reach live expert/consultation data outside a
 * controlled test build.
 */
function controlled(): void {
  if (!internalTestFlags.internalFeatureTesting) {
    throw new Error('CONTROLLED_TEST_BUILD_REQUIRED');
  }
}

function cachedExperts(key: string, err: unknown): Paginated<Expert> {
  const cached = expertStorage.getCachedExpertList(key);
  if (cached && err instanceof ApiError && err.isNetwork) {
    return { items: cached, page: 1, pageSize: cached.length, total: cached.length, totalPages: 1 };
  }
  throw err;
}

function cachedConsultations(key: string, err: unknown): Paginated<Consultation> {
  const cached = expertStorage.getCachedConsultationList(key);
  if (cached && err instanceof ApiError && err.isNetwork) {
    return { items: cached, page: 1, pageSize: cached.length, total: cached.length, totalPages: 1 };
  }
  throw err;
}

export const apiExpertProvider: ExpertProvider = {
  async listExperts(params: ExpertListParams): Promise<Paginated<Expert>> {
    controlled();
    const key = expertListKey(params as Record<string, unknown>);
    try {
      const dto = await api.get<ApiPaginated<ApiExpertSummary>>(endpoints.experts.root, {
        params: {
          category: params.category ?? undefined,
          crop: params.crop ?? undefined,
          district: params.district ?? undefined,
          language: params.language ?? undefined,
          expert_type: params.expertType ?? undefined,
          search: params.search ?? undefined,
          page: params.page ?? 1,
          page_size: params.pageSize ?? DEFAULT_PAGE_SIZE,
        },
      });
      const result = apiToExpertList(dto);
      if (result.page === 1) expertStorage.cacheExpertList(key, result.items);
      return result;
    } catch (err) {
      return cachedExperts(key, err);
    }
  },

  async getExpert(id: string): Promise<ExpertDetail> {
    controlled();
    return apiToExpertDetail(await api.get<ApiExpertDetail>(endpoints.experts.byId(id)));
  },

  async listConsultations(
    params: ConsultationListParams,
  ): Promise<Paginated<Consultation>> {
    controlled();
    const key = consultationListKey('all', params as Record<string, unknown>);
    try {
      const dto = await api.get<ApiPaginated<ApiConsultationSummary>>(
        endpoints.consultations.root,
        {
          params: {
            status: params.status ?? undefined,
            category: params.category ?? undefined,
            page: params.page ?? 1,
            page_size: params.pageSize ?? DEFAULT_PAGE_SIZE,
          },
        },
      );
      const result = apiToConsultationList(dto);
      if (result.page === 1) expertStorage.cacheConsultationList(key, result.items);
      return result;
    } catch (err) {
      return cachedConsultations(key, err);
    }
  },

  async pending(page = 1, pageSize = DEFAULT_PAGE_SIZE): Promise<Paginated<Consultation>> {
    controlled();
    const key = consultationListKey('pending', { page });
    try {
      const dto = await api.get<ApiPaginated<ApiConsultationSummary>>(
        endpoints.consultations.pending,
        { params: { page, page_size: pageSize } },
      );
      const result = apiToConsultationList(dto);
      if (result.page === 1) expertStorage.cacheConsultationList(key, result.items);
      return result;
    } catch (err) {
      return cachedConsultations(key, err);
    }
  },

  async history(page = 1, pageSize = DEFAULT_PAGE_SIZE): Promise<Paginated<Consultation>> {
    controlled();
    const key = consultationListKey('history', { page });
    try {
      const dto = await api.get<ApiPaginated<ApiConsultationSummary>>(
        endpoints.consultations.history,
        { params: { page, page_size: pageSize } },
      );
      const result = apiToConsultationList(dto);
      if (result.page === 1) expertStorage.cacheConsultationList(key, result.items);
      return result;
    } catch (err) {
      return cachedConsultations(key, err);
    }
  },

  async getConsultation(id: string): Promise<ConsultationDetail> {
    controlled();
    return apiToConsultationDetail(
      await api.get<ApiConsultationDetail>(endpoints.consultations.byId(id)),
    );
  },

  async createConsultation(input: ConsultationInput): Promise<ConsultationDetail> {
    controlled();
    return apiToConsultationDetail(
      await api.post<ApiConsultationDetail>(
        endpoints.consultations.root,
        consultationInputToApi(input),
      ),
    );
  },

  async reply(id: string, input: ReplyInput): Promise<ConsultationDetail> {
    controlled();
    return apiToConsultationDetail(
      await api.post<ApiConsultationDetail>(
        endpoints.consultations.reply(id),
        replyInputToApi(input),
      ),
    );
  },

  async addAttachment(id: string, attachment: AttachmentInput): Promise<ConsultationDetail> {
    controlled();
    return apiToConsultationDetail(
      await api.post<ApiConsultationDetail>(
        endpoints.consultations.attachments(id),
        attachmentToApi(attachment),
      ),
    );
  },

  async updateStatus(
    id: string,
    status: ConsultationStatus,
    note?: string,
  ): Promise<ConsultationDetail> {
    controlled();
    return apiToConsultationDetail(
      await api.put<ApiConsultationDetail>(endpoints.consultations.statusOf(id), {
        status,
        note: note ?? null,
      }),
    );
  },
};

// A single-item mapper re-export kept for hook optimistic paths.
export { apiToConsultation };
