import type { LatLng } from '../types';

/**
 * Web Mercator projection for the boundary editor. The map backdrop is a Mapbox
 * static image centred on `center` at `zoom`; these helpers convert between
 * geographic coordinates and on-screen pixels so taps/pans map to real lng/lat.
 *
 * Pure functions — unit-tested for projection round-trips.
 */

const TILE_SIZE = 512; // Mapbox static tiles are 512px.

export interface Size {
  width: number;
  height: number;
}

export interface Point {
  x: number;
  y: number;
}

function worldSize(zoom: number): number {
  return TILE_SIZE * 2 ** zoom;
}

/** Absolute world pixel coordinate at a given zoom (top-left origin). */
export function lngLatToWorld(point: LatLng, zoom: number): Point {
  const size = worldSize(zoom);
  const x = ((point.longitude + 180) / 360) * size;
  const sinLat = Math.sin((point.latitude * Math.PI) / 180);
  const clamped = Math.max(-0.9999, Math.min(0.9999, sinLat));
  const y =
    (0.5 - Math.log((1 + clamped) / (1 - clamped)) / (4 * Math.PI)) * size;
  return { x, y };
}

export function worldToLngLat(point: Point, zoom: number): LatLng {
  const size = worldSize(zoom);
  const lng = (point.x / size) * 360 - 180;
  const n = Math.PI - (2 * Math.PI * point.y) / size;
  const lat = (180 / Math.PI) * Math.atan(0.5 * (Math.exp(n) - Math.exp(-n)));
  return { latitude: lat, longitude: lng };
}

/** Geographic point → screen pixel within a canvas of `size` centred on `center`. */
export function project(
  point: LatLng,
  center: LatLng,
  zoom: number,
  size: Size,
): Point {
  const world = lngLatToWorld(point, zoom);
  const centerWorld = lngLatToWorld(center, zoom);
  return {
    x: world.x - centerWorld.x + size.width / 2,
    y: world.y - centerWorld.y + size.height / 2,
  };
}

/** Screen pixel → geographic point (inverse of `project`). */
export function unproject(
  screen: Point,
  center: LatLng,
  zoom: number,
  size: Size,
): LatLng {
  const centerWorld = lngLatToWorld(center, zoom);
  return worldToLngLat(
    {
      x: screen.x - size.width / 2 + centerWorld.x,
      y: screen.y - size.height / 2 + centerWorld.y,
    },
    zoom,
  );
}

/** Shift `center` by a screen-pixel delta (used when panning the map). */
export function panCenter(
  center: LatLng,
  dx: number,
  dy: number,
  zoom: number,
): LatLng {
  const world = lngLatToWorld(center, zoom);
  return worldToLngLat({ x: world.x - dx, y: world.y - dy }, zoom);
}
