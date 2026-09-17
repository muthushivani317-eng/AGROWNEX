import {
  apiToAlert,
  apiToDashboard,
  apiToHistoryEntry,
  apiToSession,
  apiToTimeline,
} from '../services/satelliteMapper';
import type {
  ApiSatelliteDashboard,
  ApiSatelliteHistoryEntry,
  ApiSatelliteSession,
  ApiSatelliteTimeline,
} from '../types';

const apiSession: ApiSatelliteSession = {
  id: 's1',
  farm_id: 'f1',
  provider: 'sentinel',
  status: 'available',
  unavailable_reason: 'none',
  is_sample: false,
  capture_date: '2026-07-10',
  cloud_cover: 12,
  resolution_m: 10,
  ndvi: 0.72,
  ndre: 0.31,
  evi: 0.44,
  ndmi: 0.18,
  vegetation_health: 'good',
  stress_level: 'none',
  moisture_status: 'adequate',
  trend: 'improving',
  ndvi_delta: 0.04,
  confidence: 82,
  metadata: { note: 'x' },
  created_at: '2026-07-11T06:00:00Z',
  images: [
    { id: 'img1', band: 'true_color', image_url: 'https://r2/tc.png', thumbnail_url: null, resolution_m: 10 },
  ],
  indices: [{ index_name: 'ndvi', mean: 0.72, minimum: 0.6, maximum: 0.85, std: 0.06 }],
  alerts: [
    { code: 'satellite.alert.low_vigor', category: 'vegetation', severity: 'warning', priority: 'medium', value: 0.2, params: {} },
  ],
};

describe('satelliteMapper', () => {
  it('maps a session envelope (snake_case) to the camelCase domain shape', () => {
    const s = apiToSession(apiSession);
    expect(s.farmId).toBe('f1');
    expect(s.isSample).toBe(false);
    expect(s.captureDate).toBe('2026-07-10');
    expect(s.vegetationHealth).toBe('good');
    expect(s.moistureStatus).toBe('adequate');
    expect(s.ndviDelta).toBe(0.04);
    expect(s.images[0].imageUrl).toBe('https://r2/tc.png');
    expect(s.images[0].thumbnailUrl).toBeNull();
    expect(s.indices[0].indexName).toBe('ndvi');
    expect(s.alerts[0].code).toBe('satellite.alert.low_vigor');
  });

  it('preserves honest nulls rather than fabricating values', () => {
    const s = apiToSession({
      ...apiSession,
      ndvi: null,
      ndmi: null,
      vegetation_health: null,
      capture_date: null,
      images: [],
      indices: [],
      alerts: [],
    });
    expect(s.ndvi).toBeNull();
    expect(s.ndmi).toBeNull();
    expect(s.vegetationHealth).toBeNull();
    expect(s.captureDate).toBeNull();
    expect(s.images).toEqual([]);
    expect(s.indices).toEqual([]);
    expect(s.alerts).toEqual([]);
  });

  it('defaults a null alert params object to an empty object', () => {
    const a = apiToAlert({
      code: 'satellite.alert.moisture_stress',
      category: 'moisture',
      severity: 'warning',
      priority: 'medium',
      value: null,
      params: null as unknown as Record<string, unknown>,
    });
    expect(a.params).toEqual({});
  });

  it('maps a dashboard incl. its session and alerts', () => {
    const dto: ApiSatelliteDashboard = {
      farm_id: 'f1',
      has_polygon: true,
      has_data: true,
      status: 'available',
      unavailable_reason: 'none',
      message_code: null,
      session: apiSession,
      alerts: apiSession.alerts,
    };
    const dash = apiToDashboard(dto);
    expect(dash.farmId).toBe('f1');
    expect(dash.hasPolygon).toBe(true);
    expect(dash.hasData).toBe(true);
    expect(dash.session?.id).toBe('s1');
    expect(dash.alerts[0].code).toBe('satellite.alert.low_vigor');
  });

  it('maps a dashboard with no session (honest "Not Available")', () => {
    const dto: ApiSatelliteDashboard = {
      farm_id: 'f1',
      has_polygon: false,
      has_data: false,
      status: 'unavailable',
      unavailable_reason: 'no_polygon',
      message_code: 'satellite.status.no_polygon',
      session: null,
      alerts: [],
    };
    const dash = apiToDashboard(dto);
    expect(dash.session).toBeNull();
    expect(dash.hasData).toBe(false);
    expect(dash.messageCode).toBe('satellite.status.no_polygon');
  });

  it('maps a history entry and a timeline', () => {
    const h: ApiSatelliteHistoryEntry = {
      id: 'h1',
      farm_id: 'f1',
      session_id: 's1',
      capture_date: '2026-07-10',
      ndvi: 0.72,
      ndre: 0.31,
      evi: 0.44,
      ndmi: 0.18,
      vegetation_health: 'good',
      stress_level: 'none',
      moisture_status: 'adequate',
      source: 'sentinel',
      confidence: 82,
      recorded_at: '2026-07-11T06:00:00Z',
    };
    const entry = apiToHistoryEntry(h);
    expect(entry.sessionId).toBe('s1');
    expect(entry.recordedAt).toBe('2026-07-11T06:00:00Z');

    const tl: ApiSatelliteTimeline = {
      farm_id: 'f1',
      range: 'weekly',
      points: [{ period: '2026-W28', ndvi: 0.7, ndre: 0.3, ndmi: 0.15, count: 2 }],
    };
    const timeline = apiToTimeline(tl);
    expect(timeline.range).toBe('weekly');
    expect(timeline.points[0].period).toBe('2026-W28');
    expect(timeline.points[0].count).toBe(2);
  });
});
