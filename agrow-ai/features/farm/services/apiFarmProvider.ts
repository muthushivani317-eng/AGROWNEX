import { api } from '@/services/apiClient';
import { endpoints } from '@/services/endpoints';
import type { Paginated } from '@/types';

import type {
  ApiFarm,
  ApiFarmBoundary,
  ApiFarmImage,
  ApiFarmSummary,
  BoundaryInput,
  Farm,
  FarmBoundary,
  FarmImage,
  FarmImageInput,
  FarmInput,
  FarmListParams,
  FarmListResult,
} from '../types';
import {
  apiToBoundary,
  apiToFarm,
  apiToImage,
  apiToSummary,
  farmInputToApi,
} from './farmMapper';
import type { FarmProvider } from './farmProvider';

/**
 * Backend provider (docs/API_CONTRACT.md → FARM MODULE) via the shared `api`
 * client, which attaches the JWT/request-id/language and unwraps the envelope.
 */
export const apiFarmProvider: FarmProvider = {
  async list(params: FarmListParams): Promise<FarmListResult> {
    const data = await api.get<Paginated<ApiFarmSummary>>(endpoints.farms.root, {
      params: {
        page: params.page ?? 1,
        page_size: params.pageSize ?? 20,
        status: params.status,
        district: params.district,
        crop: params.crop,
        q: params.search,
      },
    });
    return { items: data.items.map(apiToSummary), total: data.total };
  },

  async get(id: string): Promise<Farm> {
    return apiToFarm(await api.get<ApiFarm>(endpoints.farms.byId(id)));
  },

  async create(input: FarmInput): Promise<Farm> {
    return apiToFarm(await api.post<ApiFarm>(endpoints.farms.root, farmInputToApi(input)));
  },

  async update(id: string, input: FarmInput): Promise<Farm> {
    return apiToFarm(
      await api.put<ApiFarm>(endpoints.farms.byId(id), farmInputToApi(input)),
    );
  },

  async remove(id: string): Promise<void> {
    await api.delete<null>(endpoints.farms.byId(id));
  },

  async getBoundary(id: string): Promise<FarmBoundary | null> {
    const dto = await api.get<ApiFarmBoundary | null>(endpoints.farms.boundary(id));
    return apiToBoundary(dto);
  },

  async updateBoundary(id: string, input: BoundaryInput): Promise<FarmBoundary> {
    const dto = await api.put<ApiFarmBoundary>(endpoints.farms.boundary(id), {
      geojson: input.geojson,
      source: input.source,
    });
    return apiToBoundary(dto) as FarmBoundary;
  },

  async listImages(id: string): Promise<FarmImage[]> {
    const rows = await api.get<ApiFarmImage[]>(endpoints.farms.images(id));
    return rows.map(apiToImage);
  },

  async addImage(id: string, media: FarmImageInput): Promise<FarmImage> {
    const dto = await api.post<ApiFarmImage>(endpoints.farms.images(id), {
      file_url: media.fileUrl,
      file_name: media.fileName,
      mime_type: media.mimeType,
      file_size: media.fileSize,
      caption: media.caption,
    });
    return apiToImage(dto);
  },
};
