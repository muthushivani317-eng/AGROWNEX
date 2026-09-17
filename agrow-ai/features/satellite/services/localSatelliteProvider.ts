import { uuid } from '@/utils/id';

import { DEFAULT_PAGE_SIZE, TIMELINE_MONTHLY } from '../constants';
import type {
  Paginated,
  SatelliteAlert,
  SatelliteDashboard,
  SatelliteHistoryEntry,
  SatelliteIndex,
  SatelliteSession,
  SatelliteTimeline,
} from '../types';
import {
  assess,
  buildAlerts,
  computeConfidence,
  computeIndices,
  type Bands,
} from './satelliteEngine';
import { type SatelliteProvider } from './satelliteProvider';
import { satelliteStorage } from './satelliteStorage';

/**
 * Local, offline Satellite provider. Produces **deterministic sample** sessions
 * (clearly flagged ``isSample``, with **no** fabricated imagery) using the same
 * engine + alert logic as the backend, so the dashboard works in dev / without a
 * backend. Honours the polygon rule and the honest "Not Available" states.
 */
function seedOf(text: string): number {
  let h = 0;
  for (let i = 0; i < text.length; i += 1) h = (h * 31 + text.charCodeAt(i)) >>> 0;
  return h;
}

function sampleBands(seed: number): Bands {
  const ndvi = 0.35 + (seed % 40) / 100;
  const ndmi = 0.1 + (seed % 30) / 100;
  const nir = 0.45;
  const red = Math.round((nir * (1 - ndvi)) / (1 + ndvi) * 10000) / 10000;
  const swir = Math.round((nir * (1 - ndmi)) / (1 + ndmi) * 10000) / 10000;
  const redEdge = Math.round((red + 0.6 * (nir - red)) * 10000) / 10000;
  return { red, nir, redEdge, swir, blue: 0.06 };
}

function toIndexRows(indices: {
  ndvi: number | null;
  ndre: number | null;
  evi: number | null;
  ndmi: number | null;
}): SatelliteIndex[] {
  const rows: SatelliteIndex[] = [];
  ([['ndvi', indices.ndvi], ['ndre', indices.ndre], ['evi', indices.evi], ['ndmi', indices.ndmi]] as const).forEach(
    ([name, value]) => {
      if (value !== null) {
        rows.push({ indexName: name, mean: value, minimum: value - 0.05, maximum: value + 0.05, std: 0.05 });
      }
    },
  );
  return rows;
}

function toHistory(session: SatelliteSession): SatelliteHistoryEntry {
  return {
    id: session.id,
    farmId: session.farmId,
    sessionId: session.id,
    captureDate: session.captureDate,
    ndvi: session.ndvi,
    ndre: session.ndre,
    evi: session.evi,
    ndmi: session.ndmi,
    vegetationHealth: session.vegetationHealth,
    stressLevel: session.stressLevel,
    moistureStatus: session.moistureStatus,
    source: session.provider,
    confidence: session.confidence,
    recordedAt: session.createdAt,
  };
}

function unavailableSession(farmId: string, reason: SatelliteSession['unavailableReason']): SatelliteSession {
  return {
    id: uuid(),
    farmId,
    provider: 'sentinel',
    status: 'unavailable',
    unavailableReason: reason,
    isSample: false,
    captureDate: null,
    cloudCover: null,
    resolutionM: null,
    ndvi: null,
    ndre: null,
    evi: null,
    ndmi: null,
    vegetationHealth: null,
    stressLevel: null,
    moistureStatus: null,
    trend: null,
    ndviDelta: null,
    confidence: 0,
    metadata: null,
    createdAt: new Date().toISOString(),
    images: [],
    indices: [],
    alerts:
      reason === 'no_polygon'
        ? []
        : buildAlerts({ status: 'unavailable', unavailableReason: reason }),
  };
}

export const localSatelliteProvider: SatelliteProvider = {
  async refresh(farmId: string, hasPolygon = true): Promise<SatelliteSession> {
    if (!hasPolygon) {
      const s = unavailableSession(farmId, 'no_polygon');
      satelliteStorage.addLocalSession(farmId, s);
      return s;
    }
    const existing = satelliteStorage.localSessions(farmId);
    const seed = seedOf(`${farmId}:${existing.length}`);
    const bands = sampleBands(seed);
    const indices = computeIndices(bands);
    const previous = existing.find((s) => s.status === 'available' && s.ndvi !== null)?.ndvi ?? null;
    const a = assess(indices, previous);
    const cloudCover = seed % 20;
    const alerts: SatelliteAlert[] = buildAlerts({
      status: 'available',
      cloudCover,
      ndvi: a.ndvi,
      ndmi: a.ndmi,
      ndviDelta: a.ndviDelta,
      trend: a.trend,
      ndviStd: 0.05,
    });
    const now = new Date();
    const session: SatelliteSession = {
      id: uuid(),
      farmId,
      provider: 'mock',
      status: 'available',
      unavailableReason: 'none',
      isSample: true,
      captureDate: new Date(now.getTime() - 86400000).toISOString().slice(0, 10),
      cloudCover,
      resolutionM: 10,
      ndvi: a.ndvi,
      ndre: a.ndre,
      evi: a.evi,
      ndmi: a.ndmi,
      vegetationHealth: a.vegetationHealth,
      stressLevel: a.stressLevel,
      moistureStatus: a.moistureStatus,
      trend: a.trend,
      ndviDelta: a.ndviDelta,
      confidence: computeConfidence(cloudCover, true),
      metadata: { note: 'sample data (development only)' },
      createdAt: now.toISOString(),
      images: [],
      indices: toIndexRows(indices),
      alerts,
    };
    satelliteStorage.addLocalSession(farmId, session);
    return session;
  },

  async dashboard(farmId: string, hasPolygon = true): Promise<SatelliteDashboard> {
    const sessions = satelliteStorage.localSessions(farmId);
    if (sessions.length === 0) {
      return {
        farmId,
        hasPolygon,
        hasData: false,
        status: 'pending',
        unavailableReason: hasPolygon ? 'none' : 'no_polygon',
        messageCode: hasPolygon ? 'satellite.status.never_refreshed' : 'satellite.status.no_polygon',
        session: null,
        alerts: [],
      };
    }
    const latest = sessions[0];
    const available = latest.status === 'available';
    return {
      farmId,
      hasPolygon,
      hasData: available,
      status: latest.status,
      unavailableReason: latest.unavailableReason,
      messageCode: !hasPolygon
        ? 'satellite.status.no_polygon'
        : available
          ? null
          : `satellite.status.${latest.unavailableReason}`,
      session: latest,
      alerts: latest.alerts,
    };
  },

  async history(
    farmId: string,
    page = 1,
    pageSize = DEFAULT_PAGE_SIZE,
  ): Promise<Paginated<SatelliteHistoryEntry>> {
    const rows = satelliteStorage
      .localSessions(farmId)
      .filter((s) => s.status === 'available')
      .map(toHistory);
    const start = (page - 1) * pageSize;
    return {
      items: rows.slice(start, start + pageSize),
      page,
      pageSize,
      total: rows.length,
      totalPages: Math.max(1, Math.ceil(rows.length / pageSize)),
    };
  },

  async timeline(farmId: string, range: string): Promise<SatelliteTimeline> {
    const rows = satelliteStorage.localSessions(farmId).filter((s) => s.status === 'available');
    const buckets = new Map<string, SatelliteSession[]>();
    for (const s of rows) {
      const d = new Date(s.captureDate ?? s.createdAt);
      const key =
        range === TIMELINE_MONTHLY
          ? `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
          : `${d.getFullYear()}-W${String(isoWeek(d)).padStart(2, '0')}`;
      buckets.set(key, [...(buckets.get(key) ?? []), s]);
    }
    const points = [...buckets.keys()].sort().map((key) => {
      const group = buckets.get(key)!;
      return {
        period: key,
        ndvi: mean(group.map((s) => s.ndvi)),
        ndre: mean(group.map((s) => s.ndre)),
        ndmi: mean(group.map((s) => s.ndmi)),
        count: group.length,
      };
    });
    return { farmId, range, points };
  },

  async alerts(farmId: string): Promise<SatelliteAlert[]> {
    const sessions = satelliteStorage.localSessions(farmId);
    return sessions.length ? sessions[0].alerts : [];
  },
};

function mean(values: (number | null)[]): number | null {
  const present = values.filter((v): v is number => v !== null);
  return present.length ? Math.round((present.reduce((a, b) => a + b, 0) / present.length) * 10000) / 10000 : null;
}

function isoWeek(date: Date): number {
  const d = new Date(Date.UTC(date.getFullYear(), date.getMonth(), date.getDate()));
  const day = d.getUTCDay() || 7;
  d.setUTCDate(d.getUTCDate() + 4 - day);
  const yearStart = new Date(Date.UTC(d.getUTCFullYear(), 0, 1));
  return Math.ceil(((d.getTime() - yearStart.getTime()) / 86400000 + 1) / 7);
}
