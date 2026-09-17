import type { LatLng } from '../types';
import {
  lngLatToWorld,
  panCenter,
  project,
  unproject,
  worldToLngLat,
} from '../utils/mercator';

const size = { width: 300, height: 300 };
const center: LatLng = { latitude: 10.79, longitude: 78.7 };
const zoom = 16;

describe('mercator projection', () => {
  it('round-trips lngLat ↔ world pixels', () => {
    const world = lngLatToWorld(center, zoom);
    const back = worldToLngLat(world, zoom);
    expect(back.latitude).toBeCloseTo(center.latitude, 6);
    expect(back.longitude).toBeCloseTo(center.longitude, 6);
  });

  it('projects the centre to the canvas centre', () => {
    const p = project(center, center, zoom, size);
    expect(p.x).toBeCloseTo(150, 6);
    expect(p.y).toBeCloseTo(150, 6);
  });

  it('round-trips project ↔ unproject for a nearby point', () => {
    const point: LatLng = { latitude: 10.7905, longitude: 78.7008 };
    const screen = project(point, center, zoom, size);
    const back = unproject(screen, center, zoom, size);
    expect(back.latitude).toBeCloseTo(point.latitude, 5);
    expect(back.longitude).toBeCloseTo(point.longitude, 5);
  });

  it('pans the centre west when dragging right', () => {
    // Dragging the map right (dx > 0) reveals area to the west → longitude drops.
    const moved = panCenter(center, 120, 0, zoom);
    expect(moved.longitude).toBeLessThan(center.longitude);
    // And a zero delta leaves the centre unchanged.
    const same = panCenter(center, 0, 0, zoom);
    expect(same.latitude).toBeCloseTo(center.latitude, 9);
    expect(same.longitude).toBeCloseTo(center.longitude, 9);
  });
});
