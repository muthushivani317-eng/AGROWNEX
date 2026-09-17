import type { GeoJSONPolygon, LatLng } from '../types';
import { HECTARES_PER_ACRE } from '../constants';

/**
 * Client-side geometry helpers — the exact geodesic formulas the backend uses
 * (app/modules/farms/geo.py), so the live area shown while drawing matches what
 * the server stores. A ring is an ordered list of {latitude, longitude}.
 */

const EARTH_RADIUS_M = 6_378_137;
const SQM_PER_HECTARE = 10_000;

const toRad = (deg: number) => (deg * Math.PI) / 180;

/** Drop the closing duplicate and any consecutive duplicate vertices. */
function coreVertices(ring: LatLng[]): LatLng[] {
  const pts =
    ring.length > 1 && samePoint(ring[0], ring[ring.length - 1])
      ? ring.slice(0, -1)
      : ring.slice();
  const out: LatLng[] = [];
  for (const p of pts) {
    if (!out.length || !samePoint(out[out.length - 1], p)) out.push(p);
  }
  return out;
}

function samePoint(a: LatLng, b: LatLng): boolean {
  return a.latitude === b.latitude && a.longitude === b.longitude;
}

export function isClosedRing(ring: LatLng[]): boolean {
  return coreVertices(ring).length >= 3;
}

/** Geodesic polygon area in square metres (spherical excess formula). */
export function geodesicAreaSqm(ring: LatLng[]): number {
  const core = coreVertices(ring);
  if (core.length < 3) return 0;
  let total = 0;
  for (let i = 0; i < core.length; i++) {
    const a = core[i];
    const b = core[(i + 1) % core.length];
    total +=
      toRad(b.longitude - a.longitude) *
      (2 + Math.sin(toRad(a.latitude)) + Math.sin(toRad(b.latitude)));
  }
  return Math.abs((total * EARTH_RADIUS_M * EARTH_RADIUS_M) / 2);
}

export function perimeterM(ring: LatLng[]): number {
  const core = coreVertices(ring);
  if (core.length < 2) return 0;
  const closed = [...core, core[0]];
  let total = 0;
  for (let i = 0; i < closed.length - 1; i++) {
    total += haversineM(closed[i], closed[i + 1]);
  }
  return total;
}

export function centroid(ring: LatLng[]): LatLng | null {
  const core = coreVertices(ring);
  if (!core.length) return null;
  const lat = core.reduce((s, p) => s + p.latitude, 0) / core.length;
  const lng = core.reduce((s, p) => s + p.longitude, 0) / core.length;
  return { latitude: lat, longitude: lng };
}

function haversineM(a: LatLng, b: LatLng): number {
  const dLat = toRad(b.latitude - a.latitude);
  const dLng = toRad(b.longitude - a.longitude);
  const s =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(toRad(a.latitude)) *
      Math.cos(toRad(b.latitude)) *
      Math.sin(dLng / 2) ** 2;
  return 2 * EARTH_RADIUS_M * Math.asin(Math.min(1, Math.sqrt(s)));
}

export const sqmToHectares = (sqm: number) => sqm / SQM_PER_HECTARE;
export const hectaresToAcres = (ha: number) => ha / HECTARES_PER_ACRE;

/** Convert a ring of {lat,lng} into a closed GeoJSON Polygon ([lng,lat] order). */
export function ringToPolygon(ring: LatLng[]): GeoJSONPolygon {
  const core = coreVertices(ring);
  const coords = core.map((p) => [p.longitude, p.latitude]);
  if (coords.length) coords.push([core[0].longitude, core[0].latitude]);
  return { type: 'Polygon', coordinates: [coords] };
}

/** Convert a GeoJSON Polygon's outer ring back into {lat,lng} vertices. */
export function polygonToRing(polygon: GeoJSONPolygon | null): LatLng[] {
  const outer = polygon?.coordinates?.[0];
  if (!outer) return [];
  const ring = outer.map((pos) => ({ latitude: pos[1], longitude: pos[0] }));
  return coreVertices(ring);
}

export interface BoundaryValidation {
  ok: boolean;
  errorKey?: string;
}

/** Validate a drawn ring before saving (docs: boundary validation). */
export function validateRing(ring: LatLng[]): BoundaryValidation {
  const core = coreVertices(ring);
  if (core.length < 3) return { ok: false, errorKey: 'farm.errorBoundaryPoints' };
  for (const p of core) {
    if (
      p.latitude < -90 ||
      p.latitude > 90 ||
      p.longitude < -180 ||
      p.longitude > 180
    ) {
      return { ok: false, errorKey: 'farm.errorBoundaryRange' };
    }
  }
  return { ok: true };
}
