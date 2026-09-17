import { uuid } from '@/utils/id';

import type {
  ApiFarm,
  ApiFarmBoundary,
  ApiFarmImage,
  ApiFarmLocation,
  ApiFarmSummary,
  AreaSource,
  BoundaryInput,
  Farm,
  FarmBoundary,
  FarmImage,
  FarmInput,
  FarmLocation,
  FarmSummary,
  SyncStatus,
} from '../types';
import { centroid, geodesicAreaSqm, perimeterM, polygonToRing, sqmToHectares } from '../utils/geo';

/** Pure conversions between API envelopes, the domain model, and form input. */

// --- API → domain --- //
function apiToLocation(dto: ApiFarmLocation | null): FarmLocation | null {
  if (!dto) return null;
  return {
    latitude: dto.latitude,
    longitude: dto.longitude,
    accuracy: dto.accuracy,
    elevation: dto.elevation,
    address: dto.address,
    district: dto.district,
    block: dto.block,
    village: dto.village,
    source: dto.source,
  };
}

export function apiToBoundary(dto: ApiFarmBoundary | null): FarmBoundary | null {
  if (!dto) return null;
  return {
    geojson: dto.geojson,
    areaHectares: dto.area_hectares,
    perimeterM: dto.perimeter_m,
    centroidLat: dto.centroid_lat,
    centroidLng: dto.centroid_lng,
    vertexCount: dto.vertex_count,
    source: dto.source,
  };
}

export function apiToImage(dto: ApiFarmImage): FarmImage {
  return {
    id: dto.id,
    fileUrl: dto.file_url,
    fileName: dto.file_name,
    mimeType: dto.mime_type,
    fileSize: dto.file_size,
    caption: dto.caption,
    createdAt: dto.created_at,
  };
}

export function apiToFarm(dto: ApiFarm): Farm {
  return {
    id: dto.id,
    name: dto.name,
    crop: dto.crop,
    cropVariety: dto.crop_variety,
    sowingDate: dto.sowing_date,
    soilType: dto.soil_type,
    irrigationType: dto.irrigation_type,
    waterSource: dto.water_source,
    areaHectares: dto.area_hectares,
    areaSource: dto.area_source,
    notes: dto.notes,
    status: dto.status,
    location: apiToLocation(dto.location),
    boundary: apiToBoundary(dto.boundary),
    images: dto.images.map(apiToImage),
    imageCount: dto.image_count,
    createdAt: dto.created_at,
    updatedAt: dto.updated_at,
    syncStatus: 'synced',
  };
}

export function apiToSummary(dto: ApiFarmSummary): FarmSummary {
  return {
    id: dto.id,
    name: dto.name,
    crop: dto.crop,
    status: dto.status,
    areaHectares: dto.area_hectares,
    district: dto.district,
    hasBoundary: dto.has_boundary,
    centroidLat: dto.centroid_lat,
    centroidLng: dto.centroid_lng,
    latitude: dto.latitude,
    longitude: dto.longitude,
    imageCount: dto.image_count,
    updatedAt: dto.updated_at,
    syncStatus: 'synced',
  };
}

export function farmToSummary(farm: Farm): FarmSummary {
  return {
    id: farm.id,
    name: farm.name,
    crop: farm.crop,
    status: farm.status,
    areaHectares: farm.areaHectares,
    district: farm.location?.district ?? null,
    hasBoundary: Boolean(farm.boundary?.geojson),
    centroidLat: farm.boundary?.centroidLat ?? null,
    centroidLng: farm.boundary?.centroidLng ?? null,
    latitude: farm.location?.latitude ?? null,
    longitude: farm.location?.longitude ?? null,
    imageCount: farm.images.length,
    updatedAt: farm.updatedAt,
    syncStatus: farm.syncStatus,
  };
}

// --- form input → API payload --- //
export function farmInputToApi(input: FarmInput): Record<string, unknown> {
  const payload: Record<string, unknown> = {
    name: input.name,
    crop: input.crop,
    crop_variety: input.cropVariety,
    sowing_date: input.sowingDate,
    soil_type: input.soilType,
    irrigation_type: input.irrigationType,
    water_source: input.waterSource,
    notes: input.notes,
    status: input.status,
    area_source: input.areaSource,
  };
  if (input.areaHectares != null) payload.area_hectares = input.areaHectares;
  if (input.location) {
    payload.location = {
      latitude: input.location.latitude,
      longitude: input.location.longitude,
      accuracy: input.location.accuracy,
      elevation: input.location.elevation,
      address: input.location.address,
      district: input.location.district,
      block: input.location.block,
      village: input.location.village,
      source: input.location.source,
    };
  }
  if (input.boundary) {
    payload.boundary = {
      geojson: input.boundary.geojson,
      source: input.boundary.source,
    };
  }
  return payload;
}

// --- domain construction (shared by the local provider) --- //
export function computeBoundary(input: BoundaryInput): FarmBoundary {
  const ring = polygonToRing(input.geojson);
  const c = centroid(ring);
  return {
    geojson: input.geojson,
    areaHectares: sqmToHectares(geodesicAreaSqm(ring)),
    perimeterM: perimeterM(ring),
    centroidLat: c?.latitude ?? null,
    centroidLng: c?.longitude ?? null,
    vertexCount: ring.length,
    source: input.source,
  };
}

/** Effective area: manual override wins, else the computed boundary area. */
export function resolveArea(
  areaSource: AreaSource,
  manualArea: number | null,
  boundary: FarmBoundary | null,
): number | null {
  if (areaSource === 'manual') {
    if (manualArea != null) return manualArea;
    return boundary?.areaHectares ?? null;
  }
  return boundary?.areaHectares ?? manualArea;
}

/**
 * Build a full Farm from form input (shared by the local provider and by the
 * offline optimistic path). When `existing` is given, its id/images/creation
 * time and any un-edited boundary/location are preserved.
 */
export function assembleFarm(
  input: FarmInput,
  opts: { id?: string; existing?: Farm; syncStatus?: SyncStatus } = {},
): Farm {
  const existing = opts.existing;
  const boundary = input.boundary
    ? computeBoundary(input.boundary)
    : (existing?.boundary ?? null);
  const location = input.location ?? existing?.location ?? null;
  const nowIso = new Date().toISOString();
  return {
    id: opts.id ?? existing?.id ?? uuid(),
    name: input.name.trim(),
    crop: input.crop,
    cropVariety: input.cropVariety,
    sowingDate: input.sowingDate,
    soilType: input.soilType,
    irrigationType: input.irrigationType,
    waterSource: input.waterSource,
    areaHectares: resolveArea(input.areaSource, input.areaHectares, boundary),
    areaSource: input.areaSource,
    notes: input.notes,
    status: input.status,
    location,
    boundary,
    images: existing?.images ?? [],
    imageCount: existing?.images.length ?? 0,
    createdAt: existing?.createdAt ?? nowIso,
    updatedAt: nowIso,
    syncStatus: opts.syncStatus ?? 'synced',
  };
}
