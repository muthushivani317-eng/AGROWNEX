import { useQuery } from '@tanstack/react-query';

import { farmKeys } from '../constants';
import { localFarmProvider } from '../services/localFarmProvider';
import { getFarmProvider } from '../services/farmProvider';
import { farmStorage } from '../services/farmStorage';
import { isOfflineError } from '../services/farmSync';
import type { FarmListParams, LatLng } from '../types';
import { polygonToRing } from '../utils/geo';

/**
 * Farm list. When the backend is unreachable, falls back to the local mirror so
 * the list (including offline-created farms) stays available.
 */
export function useFarms(
  params: FarmListParams = {},
  options?: { refetchOnMount?: boolean | 'always' },
) {
  return useQuery({
    queryKey: farmKeys.list(params),
    queryFn: async () => {
      try {
        return await getFarmProvider().list(params);
      } catch (error) {
        if (isOfflineError(error)) return localFarmProvider.list(params);
        throw error;
      }
    },
    ...options,
  });
}

/** Single farm detail, mirrored locally for offline viewing. */
export function useFarm(id: string | undefined) {
  return useQuery({
    queryKey: farmKeys.detail(id ?? 'none'),
    enabled: Boolean(id),
    queryFn: async () => {
      const farmId = id as string;
      try {
        const farm = await getFarmProvider().get(farmId);
        farmStorage.upsert(farm);
        return farm;
      } catch (error) {
        const cached = farmStorage.get(farmId);
        if (isOfflineError(error) && cached) return cached;
        throw error;
      }
    },
  });
}

/** Derive editor state (vertices + initial centre) from a farm's boundary. */
export function useBoundaryVertices(id: string) {
  const { data: farm, isLoading } = useFarm(id);
  const vertices = farm?.boundary?.geojson ? polygonToRing(farm.boundary.geojson) : [];
  const center: LatLng | null =
    farm?.boundary?.centroidLat != null && farm?.boundary?.centroidLng != null
      ? { latitude: farm.boundary.centroidLat, longitude: farm.boundary.centroidLng }
      : farm?.location?.latitude != null && farm?.location?.longitude != null
        ? { latitude: farm.location.latitude, longitude: farm.location.longitude }
        : null;
  return { vertices, center, isLoading };
}
