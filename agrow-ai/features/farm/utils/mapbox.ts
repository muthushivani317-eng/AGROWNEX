import { env } from '@/config/env';

import type { LatLng } from '../types';

/**
 * Mapbox Static Images API (docs: MAPS → Use Mapbox). We render the map as a
 * raster backdrop image — no native SDK required — and overlay the SVG polygon
 * editor on top. Falls back to `null` (a plain grid canvas) when no token is set.
 */

export type MapStyle = 'satellite-streets-v12' | 'outdoors-v12' | 'streets-v12';

export interface StaticMapOptions {
  center: LatLng;
  zoom: number;
  width: number;
  height: number;
  style?: MapStyle;
  retina?: boolean;
}

export const isMapboxConfigured = Boolean(env.mapboxToken);

export function staticMapUrl(opts: StaticMapOptions): string | null {
  if (!env.mapboxToken) return null;
  const { center, zoom, width, height, style = 'satellite-streets-v12' } = opts;
  // Mapbox caps static image dimensions at 1280px.
  const w = Math.max(1, Math.min(1280, Math.round(width)));
  const h = Math.max(1, Math.min(1280, Math.round(height)));
  const lng = center.longitude.toFixed(6);
  const lat = center.latitude.toFixed(6);
  const z = Math.max(0, Math.min(20, zoom)).toFixed(2);
  const scale = opts.retina ? '@2x' : '';
  return (
    `https://api.mapbox.com/styles/v1/mapbox/${style}/static/` +
    `${lng},${lat},${z},0/${w}x${h}${scale}` +
    `?access_token=${env.mapboxToken}&attribution=false&logo=false`
  );
}
