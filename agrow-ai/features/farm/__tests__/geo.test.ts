import type { LatLng } from '../types';
import {
  centroid,
  geodesicAreaSqm,
  hectaresToAcres,
  isClosedRing,
  perimeterM,
  polygonToRing,
  ringToPolygon,
  sqmToHectares,
  validateRing,
} from '../utils/geo';

const EARTH_R = 6_378_137;
const sideMeters = (deg: number) => (deg * Math.PI * EARTH_R) / 180;

function square(side: number, lat0 = 0, lng0 = 0): LatLng[] {
  return [
    { latitude: lat0, longitude: lng0 },
    { latitude: lat0, longitude: lng0 + side },
    { latitude: lat0 + side, longitude: lng0 + side },
    { latitude: lat0 + side, longitude: lng0 },
  ];
}

describe('farm geo', () => {
  it('computes polygon area within 1% near the equator', () => {
    const ring = square(0.01);
    const expected = sideMeters(0.01) ** 2;
    expect(Math.abs(geodesicAreaSqm(ring) - expected) / expected).toBeLessThan(0.01);
  });

  it('computes perimeter as four sides', () => {
    const ring = square(0.01);
    expect(perimeterM(ring)).toBeCloseTo(4 * sideMeters(0.01), -1);
  });

  it('computes the centroid at the square centre', () => {
    const c = centroid(square(0.02, 10, 78));
    expect(c?.latitude).toBeCloseTo(10.01, 6);
    expect(c?.longitude).toBeCloseTo(78.01, 6);
  });

  it('validates rings', () => {
    expect(validateRing(square(0.01)).ok).toBe(true);
    expect(isClosedRing(square(0.01))).toBe(true);
    const twoPoints = validateRing([
      { latitude: 0, longitude: 0 },
      { latitude: 0, longitude: 1 },
    ]);
    expect(twoPoints.ok).toBe(false);
    expect(twoPoints.errorKey).toBe('farm.errorBoundaryPoints');
  });

  it('rejects out-of-range coordinates', () => {
    const bad = validateRing([
      { latitude: 0, longitude: 0 },
      { latitude: 0, longitude: 200 },
      { latitude: 1, longitude: 1 },
    ]);
    expect(bad.ok).toBe(false);
    expect(bad.errorKey).toBe('farm.errorBoundaryRange');
  });

  it('round-trips ring ↔ GeoJSON polygon', () => {
    const ring = square(0.01, 9.9, 78.1);
    const polygon = ringToPolygon(ring);
    expect(polygon.type).toBe('Polygon');
    // Closed ring: first and last coordinates match, [lng, lat] order.
    const coords = polygon.coordinates[0];
    expect(coords[0]).toEqual(coords[coords.length - 1]);
    expect(coords[0]).toEqual([78.1, 9.9]);

    const back = polygonToRing(polygon);
    expect(back).toHaveLength(4);
    expect(back[0]).toEqual({ latitude: 9.9, longitude: 78.1 });
  });

  it('converts units', () => {
    expect(sqmToHectares(10_000)).toBe(1);
    expect(hectaresToAcres(1)).toBeCloseTo(2.4710538, 4);
  });
});
