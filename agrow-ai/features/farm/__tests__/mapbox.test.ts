import { isMapboxConfigured, staticMapUrl } from '../utils/mapbox';

// No EXPO_PUBLIC_MAPBOX_TOKEN in the test env → the editor uses the grid fallback.
describe('mapbox static map', () => {
  it('is not configured without a token', () => {
    expect(isMapboxConfigured).toBe(false);
  });

  it('returns null (grid fallback) when no token is set', () => {
    const url = staticMapUrl({
      center: { latitude: 10.79, longitude: 78.7 },
      zoom: 15,
      width: 300,
      height: 300,
    });
    expect(url).toBeNull();
  });
});
