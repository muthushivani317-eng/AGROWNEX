import { uuid } from '@/utils/id';

import type {
  BoundaryInput,
  Farm,
  FarmBoundary,
  FarmImage,
  FarmImageInput,
  FarmInput,
  FarmListParams,
  FarmListResult,
} from '../types';
import { assembleFarm, computeBoundary, farmToSummary } from './farmMapper';
import { FarmError, type FarmProvider } from './farmProvider';
import { farmStorage } from './farmStorage';

/**
 * Offline-first provider backed by MMKV. Active until a real backend is
 * configured; every operation is local and synchronous, so farm creation and
 * editing work with no connectivity (docs: OFFLINE → offline farm creation).
 */
const nowIso = () => new Date().toISOString();

function assertUniqueName(name: string, excludeId?: string): void {
  const target = name.trim().toLowerCase();
  const clash = farmStorage
    .all()
    .some((f) => f.id !== excludeId && f.name.trim().toLowerCase() === target);
  if (clash) throw new FarmError('duplicate_farm', 'farm.errorDuplicate');
}

function requireFarm(id: string): Farm {
  const farm = farmStorage.get(id);
  if (!farm) throw new FarmError('farm_not_found', 'farm.errorNotFound');
  return farm;
}

export const localFarmProvider: FarmProvider = {
  async list(params: FarmListParams): Promise<FarmListResult> {
    let items = farmStorage.all();
    if (params.status) items = items.filter((f) => f.status === params.status);
    if (params.crop) items = items.filter((f) => f.crop === params.crop);
    if (params.district) {
      const d = params.district.toLowerCase();
      items = items.filter((f) => (f.location?.district ?? '').toLowerCase() === d);
    }
    if (params.search) {
      const q = params.search.toLowerCase();
      items = items.filter((f) => f.name.toLowerCase().includes(q));
    }
    items.sort((a, b) => (b.updatedAt ?? '').localeCompare(a.updatedAt ?? ''));

    const total = items.length;
    const page = params.page ?? 1;
    const pageSize = params.pageSize ?? 20;
    const start = (page - 1) * pageSize;
    return {
      items: items.slice(start, start + pageSize).map(farmToSummary),
      total,
    };
  },

  async get(id: string): Promise<Farm> {
    return requireFarm(id);
  },

  async create(input: FarmInput): Promise<Farm> {
    assertUniqueName(input.name);
    return farmStorage.upsert(assembleFarm(input, { id: uuid() }));
  },

  async update(id: string, input: FarmInput): Promise<Farm> {
    const existing = requireFarm(id);
    assertUniqueName(input.name, id);
    return farmStorage.upsert(assembleFarm(input, { id, existing }));
  },

  async remove(id: string): Promise<void> {
    requireFarm(id);
    farmStorage.remove(id);
  },

  async getBoundary(id: string): Promise<FarmBoundary | null> {
    return requireFarm(id).boundary;
  },

  async updateBoundary(id: string, input: BoundaryInput): Promise<FarmBoundary> {
    const existing = requireFarm(id);
    const boundary = computeBoundary(input);
    farmStorage.upsert({
      ...existing,
      boundary,
      areaHectares:
        existing.areaSource === 'auto' ? boundary.areaHectares : existing.areaHectares,
      updatedAt: nowIso(),
    });
    return boundary;
  },

  async listImages(id: string): Promise<FarmImage[]> {
    return requireFarm(id).images;
  },

  async addImage(id: string, media: FarmImageInput): Promise<FarmImage> {
    const existing = requireFarm(id);
    const image: FarmImage = {
      id: uuid(),
      fileUrl: media.fileUrl,
      fileName: media.fileName ?? null,
      mimeType: media.mimeType ?? null,
      fileSize: media.fileSize ?? null,
      caption: media.caption ?? null,
      createdAt: nowIso(),
    };
    const images = [...existing.images, image];
    farmStorage.upsert({
      ...existing,
      images,
      imageCount: images.length,
      updatedAt: nowIso(),
    });
    return image;
  },
};
