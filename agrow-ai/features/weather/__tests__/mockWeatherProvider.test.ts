import { mockWeatherProvider } from '../services/mockWeatherProvider';

describe('mockWeatherProvider', () => {
  it('returns a complete, well-shaped bundle', async () => {
    const bundle = await mockWeatherProvider.getWeather({
      farmId: 'f1',
      latitude: 9.9,
      longitude: 78.1,
      name: 'North Field',
    });
    expect(bundle.location.name).toBe('North Field');
    expect(bundle.location.latitude).toBe(9.9);
    expect(bundle.hourly).toHaveLength(24);
    expect(bundle.daily).toHaveLength(7);
    expect(bundle.insights.length).toBeGreaterThan(0);
    expect(bundle.source).toBe('mock');
    // Every hourly point carries a condition and a numeric temperature.
    for (const point of bundle.hourly) {
      expect(typeof point.temperatureC).toBe('number');
      expect(point.condition).toBeDefined();
    }
  });

  it('falls back to a default location when coordinates are absent', async () => {
    const bundle = await mockWeatherProvider.getWeather({});
    expect(bundle.location.latitude).toBeCloseTo(10.79, 2);
    expect(bundle.location.name).toBeNull();
  });
});
