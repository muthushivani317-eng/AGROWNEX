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

/** Google "plus codes" (e.g. R545+Q76) come back as `name` where no named
 * place exists; they are not a village name. */
const PLUS_CODE = /^[23456789CFGHJMPQRVWX]{2,8}\+[23456789CFGHJMPQRVWX]{0,3}\b/i;

function usablePlaceName(value: string | null | undefined, exclude: (string | null)[]): string | null {
  const text = value?.trim();
  if (!text || PLUS_CODE.test(text) || /^\d+$/.test(text)) return null;
  const lower = text.toLowerCase();
  return exclude.some((other) => other?.trim().toLowerCase() === lower) ? null : text;
}

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

    const block = usablePlaceName(place.city, []) ?? usablePlaceName(place.subregion, []);
    // `name` is normally the locality/settlement returned by Android; skip
    // plus codes and names that just repeat the block/district, then fall
    // back to the road name.
    const village = [place.name, place.street]
      .map((candidate) => usablePlaceName(candidate, [block, matched?.en ?? null]))
      .find(Boolean) ?? null;

    return {
      status: matched ? 'success' : 'noDistrictMatch',
      district: matched?.id ?? null,
      block,
      village,
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
