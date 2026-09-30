import * as Location from 'expo-location';

import { autofillAddressFromCoordinates } from '../hooks/useLocationAutofill';

jest.mock('expo-location', () => ({
  reverseGeocodeAsync: jest.fn(),
  requestForegroundPermissionsAsync: jest.fn(),
  getCurrentPositionAsync: jest.fn(),
  Accuracy: { Balanced: 3 },
}));

const reverseGeocode = Location.reverseGeocodeAsync as jest.MockedFunction<
  typeof Location.reverseGeocodeAsync
>;

describe('autofillAddressFromCoordinates', () => {
  beforeEach(() => jest.clearAllMocks());

  it('maps a reverse-geocoded Tamil Nadu address to all farm fields', async () => {
    reverseGeocode.mockResolvedValue([
      {
        city: 'Pollachi North',
        district: 'Coimbatore District',
        isoCountryCode: 'IN',
        name: 'Achipatti',
        postalCode: '642002',
        region: 'Tamil Nadu',
        street: 'Achipatti',
        streetNumber: null,
        subregion: 'Pollachi',
        timezone: null,
        country: 'India',
        formattedAddress: null,
      },
    ]);

    await expect(autofillAddressFromCoordinates(10.66, 76.99)).resolves.toMatchObject({
      status: 'success',
      district: 'coimbatore',
      block: 'Pollachi North',
      village: 'Achipatti',
    });
    expect(reverseGeocode).toHaveBeenCalledWith({ latitude: 10.66, longitude: 76.99 });
  });

  it('returns unavailable fields when the device geocoder has no result', async () => {
    reverseGeocode.mockResolvedValue([]);

    await expect(autofillAddressFromCoordinates(0, 0)).resolves.toEqual({
      status: 'unavailable',
      district: null,
      block: null,
      village: null,
      rawLocationHint: null,
      latitude: null,
      longitude: null,
    });
  });
});
