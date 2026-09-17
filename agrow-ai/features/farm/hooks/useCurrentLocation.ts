import * as Location from 'expo-location';
import { useState } from 'react';

import { logger } from '@/lib/logger';

import type { LatLng } from '../types';

export interface CurrentLocation extends LatLng {
  accuracy: number | null;
}

export type LocationErrorKind = 'permission' | 'unavailable';

/**
 * One-shot GPS reader (docs: MAPS → Current GPS). Requests foreground permission
 * then returns the current position, or null with an error kind set.
 */
export function useCurrentLocation() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<LocationErrorKind | null>(null);

  const getCurrentLocation = async (): Promise<CurrentLocation | null> => {
    setLoading(true);
    setError(null);
    try {
      const permission = await Location.requestForegroundPermissionsAsync();
      if (!permission.granted) {
        setError('permission');
        return null;
      }
      let timeout: ReturnType<typeof setTimeout> | undefined;
      const position = await Promise.race([
        Location.getCurrentPositionAsync({
          accuracy: Location.Accuracy.High,
        }),
        new Promise<never>((_, reject) => {
          timeout = setTimeout(
            () => reject(new Error('LOCATION_TIMEOUT')),
            12_000,
          );
        }),
      ]).finally(() => {
        if (timeout) clearTimeout(timeout);
      });
      return {
        latitude: position.coords.latitude,
        longitude: position.coords.longitude,
        accuracy: position.coords.accuracy ?? null,
      };
    } catch (e) {
      logger.warn('useCurrentLocation', e);
      setError('unavailable');
      return null;
    } finally {
      setLoading(false);
    }
  };

  return { getCurrentLocation, loading, error };
}
