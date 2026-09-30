import * as Location from 'expo-location';

import { TAMIL_NADU_DISTRICTS } from '@/constants/locations';

export interface LocationAutofillResult {
  status: 'success' | 'permissionDenied' | 'unavailable' | 'noDistrictMatch';
  district: string | null;
  block: string | null;
  village: string | null;
  rawLocationHint: string | null;
  latitude: number | null;
  longitude: number | null;
}

const EMPTY_RESULT: LocationAutofillResult = {
  status: 'unavailable',
  district: null,
  block: null,
  village: null,
  rawLocationHint: null,
  latitude: null,
  longitude: null,
};

export async function autofillAddressFromCoordinates(
  latitude: number,
  longitude: number,
): Promise<LocationAutofillResult> {
  try {
    const results = await Location.reverseGeocodeAsync({ latitude, longitude });
    const place = results[0];
    if (!place) return EMPTY_RESULT;

    const locationFields = [place.district, place.subregion, place.city, place.region]
      .filter((field): field is string => Boolean(field?.trim()));
    const matched = locationFields
      .map((field) => TAMIL_NADU_DISTRICTS.find((candidate) =>
        field.toLowerCase().includes(candidate.en.toLowerCase()),
      ))
      .find(Boolean);

    return {
      status: matched ? 'success' : 'noDistrictMatch',
      district: matched?.id ?? null,
      block: place.city ?? place.subregion ?? null,
      // `name` is normally the locality/settlement returned by Android;
      // use the road name only as a last resort for the village field.
      village: place.name ?? place.street ?? null,
      rawLocationHint: place.city ?? place.subregion ?? place.district ?? place.region ?? null,
      latitude,
      longitude,
    };
  } catch {
    return EMPTY_RESULT;
  }
}

export async function autofillAddressFromGPS(): Promise<LocationAutofillResult> {
  try {
    const permission = await Location.requestForegroundPermissionsAsync();
    if (!permission.granted) {
      return { ...EMPTY_RESULT, status: 'permissionDenied' };
    }

    const position = await Location.getCurrentPositionAsync({
      accuracy: Location.Accuracy.Balanced,
    });
    return autofillAddressFromCoordinates(
      position.coords.latitude,
      position.coords.longitude,
    );
  } catch {
    return EMPTY_RESULT;
  }
}
