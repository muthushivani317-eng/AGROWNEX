import type { AreaSource, FarmStatus, LatLng } from './types';

/** Option lists — `labelKey` resolves under the `farm` i18n namespace. */
export interface FarmOption<T extends string = string> {
  value: T;
  labelKey: string;
}

export const SOIL_TYPES: FarmOption[] = [
  { value: 'alluvial', labelKey: 'farm.soilAlluvial' },
  { value: 'black', labelKey: 'farm.soilBlack' },
  { value: 'red', labelKey: 'farm.soilRed' },
  { value: 'laterite', labelKey: 'farm.soilLaterite' },
  { value: 'sandy', labelKey: 'farm.soilSandy' },
  { value: 'clay', labelKey: 'farm.soilClay' },
  { value: 'loamy', labelKey: 'farm.soilLoamy' },
  { value: 'silt', labelKey: 'farm.soilSilt' },
];

export const IRRIGATION_TYPES: FarmOption[] = [
  { value: 'rainfed', labelKey: 'farm.irrigationRainfed' },
  { value: 'canal', labelKey: 'farm.irrigationCanal' },
  { value: 'borewell', labelKey: 'farm.irrigationBorewell' },
  { value: 'open_well', labelKey: 'farm.irrigationOpenWell' },
  { value: 'drip', labelKey: 'farm.irrigationDrip' },
  { value: 'sprinkler', labelKey: 'farm.irrigationSprinkler' },
  { value: 'tank', labelKey: 'farm.irrigationTank' },
];

export const WATER_SOURCES: FarmOption[] = [
  { value: 'rain', labelKey: 'farm.waterRain' },
  { value: 'river', labelKey: 'farm.waterRiver' },
  { value: 'canal', labelKey: 'farm.waterCanal' },
  { value: 'borewell', labelKey: 'farm.waterBorewell' },
  { value: 'open_well', labelKey: 'farm.waterOpenWell' },
  { value: 'pond', labelKey: 'farm.waterPond' },
  { value: 'tank', labelKey: 'farm.waterTank' },
];

export const FARM_STATUSES: FarmOption<FarmStatus>[] = [
  { value: 'draft', labelKey: 'farm.statusDraft' },
  { value: 'active', labelKey: 'farm.statusActive' },
  { value: 'harvested', labelKey: 'farm.statusHarvested' },
  { value: 'archived', labelKey: 'farm.statusArchived' },
];

export const AREA_SOURCES: FarmOption<AreaSource>[] = [
  { value: 'auto', labelKey: 'farm.areaAuto' },
  { value: 'manual', labelKey: 'farm.areaManual' },
];

/** Map defaults: centred on Tamil Nadu (primary region). */
export const DEFAULT_MAP_CENTER: LatLng = { latitude: 10.79, longitude: 78.7 };
export const DEFAULT_MAP_ZOOM = 15;
export const MIN_MAP_ZOOM = 3;
export const MAX_MAP_ZOOM = 20;
export const HECTARES_PER_ACRE = 0.4046856;

/** MMKV keys for the local farm mirror + offline outbox. */
export const FARM_STORE_KEY = 'agrowai.farm.items';
export const FARM_OUTBOX_KEY = 'agrowai.farm.outbox';

/** React Query keys. */
export const farmKeys = {
  all: ['farms'] as const,
  list: (params?: unknown) => ['farms', 'list', params ?? {}] as const,
  detail: (id: string) => ['farms', 'detail', id] as const,
  boundary: (id: string) => ['farms', 'boundary', id] as const,
  images: (id: string) => ['farms', 'images', id] as const,
  team: (id: string) => ['farms', 'team-controlled', id] as const,
};
