/**
 * Farm Registration domain types (docs/API_CONTRACT.md → FARM MODULE).
 * Client-side camelCase mirror of the backend farm schemas.
 */

export type FarmStatus = 'draft' | 'active' | 'harvested' | 'archived';
export type AreaSource = 'auto' | 'manual';
export type LocationSource = 'gps' | 'manual';
export type BoundarySource = 'drawn' | 'gps' | 'imported';
export type SyncStatus = 'synced' | 'pending' | 'conflict';

export interface LatLng {
  latitude: number;
  longitude: number;
}

/** GeoJSON Polygon: coordinates = [ring][position][lng, lat]. */
export interface GeoJSONPolygon {
  type: 'Polygon';
  coordinates: number[][][];
}

export interface FarmLocation {
  latitude: number | null;
  longitude: number | null;
  accuracy: number | null;
  elevation: number | null;
  address: string | null;
  district: string | null;
  block: string | null;
  village: string | null;
  source: LocationSource;
}

export interface FarmBoundary {
  geojson: GeoJSONPolygon | null;
  areaHectares: number | null;
  perimeterM: number | null;
  centroidLat: number | null;
  centroidLng: number | null;
  vertexCount: number | null;
  source: BoundarySource;
}

export interface FarmImage {
  id: string;
  fileUrl: string;
  fileName: string | null;
  mimeType: string | null;
  fileSize: number | null;
  caption: string | null;
  createdAt: string | null;
}

export interface Farm {
  id: string;
  name: string;
  crop: string | null;
  cropVariety: string | null;
  sowingDate: string | null;
  soilType: string | null;
  irrigationType: string | null;
  waterSource: string | null;
  areaHectares: number | null;
  areaSource: AreaSource;
  notes: string | null;
  status: FarmStatus;
  location: FarmLocation | null;
  boundary: FarmBoundary | null;
  images: FarmImage[];
  imageCount: number;
  createdAt: string | null;
  updatedAt: string | null;
  /** Offline bookkeeping (local mirror / outbox). */
  syncStatus: SyncStatus;
}

export interface FarmSummary {
  id: string;
  name: string;
  crop: string | null;
  status: FarmStatus;
  areaHectares: number | null;
  district: string | null;
  hasBoundary: boolean;
  centroidLat: number | null;
  centroidLng: number | null;
  latitude: number | null;
  longitude: number | null;
  imageCount: number;
  updatedAt: string | null;
  syncStatus: SyncStatus;
}

/** Boundary payload produced by the editor. */
export interface BoundaryInput {
  geojson: GeoJSONPolygon;
  source: BoundarySource;
}

/** What the Add/Edit form produces. */
export interface FarmInput {
  name: string;
  crop: string | null;
  cropVariety: string | null;
  sowingDate: string | null;
  soilType: string | null;
  irrigationType: string | null;
  waterSource: string | null;
  notes: string | null;
  status: FarmStatus;
  areaHectares: number | null;
  areaSource: AreaSource;
  location: FarmLocation | null;
  boundary: BoundaryInput | null;
}

export interface FarmListParams {
  status?: FarmStatus;
  district?: string;
  crop?: string;
  search?: string;
  page?: number;
  pageSize?: number;
}

export interface FarmListResult {
  items: FarmSummary[];
  total: number;
}

export interface FarmImageInput {
  fileUrl: string;
  fileName?: string | null;
  mimeType?: string | null;
  fileSize?: number | null;
  caption?: string | null;
}

// --------------------------------------------------------------------------- //
// Backend envelope shapes (snake_case) — used only by the API provider/mapper.
// --------------------------------------------------------------------------- //
export interface ApiFarmLocation {
  latitude: number | null;
  longitude: number | null;
  accuracy: number | null;
  elevation: number | null;
  address: string | null;
  district: string | null;
  block: string | null;
  village: string | null;
  source: LocationSource;
}

export interface ApiFarmBoundary {
  geojson: GeoJSONPolygon | null;
  area_hectares: number | null;
  perimeter_m: number | null;
  centroid_lat: number | null;
  centroid_lng: number | null;
  vertex_count: number | null;
  source: BoundarySource;
}

export interface ApiFarmImage {
  id: string;
  file_url: string;
  file_name: string | null;
  mime_type: string | null;
  file_size: number | null;
  caption: string | null;
  created_at: string | null;
}

export interface ApiFarm {
  id: string;
  user_id: string;
  name: string;
  crop: string | null;
  crop_variety: string | null;
  sowing_date: string | null;
  soil_type: string | null;
  irrigation_type: string | null;
  water_source: string | null;
  area_hectares: number | null;
  area_source: AreaSource;
  notes: string | null;
  status: FarmStatus;
  created_at: string | null;
  updated_at: string | null;
  location: ApiFarmLocation | null;
  boundary: ApiFarmBoundary | null;
  images: ApiFarmImage[];
  image_count: number;
}

export interface ApiFarmSummary {
  id: string;
  name: string;
  crop: string | null;
  status: FarmStatus;
  area_hectares: number | null;
  district: string | null;
  has_boundary: boolean;
  centroid_lat: number | null;
  centroid_lng: number | null;
  latitude: number | null;
  longitude: number | null;
  image_count: number;
  updated_at: string | null;
}
