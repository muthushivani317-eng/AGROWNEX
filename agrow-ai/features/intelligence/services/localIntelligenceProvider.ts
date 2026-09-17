import { logger } from '@/lib/logger';
import { uuid } from '@/utils/id';

import { nutrientStorage } from '@/features/nutrient/services/nutrientStorage';
import { satelliteStorage } from '@/features/satellite/services/satelliteStorage';

import { DEFAULT_PAGE_SIZE } from '../constants';
import type {
  IntelligenceDashboard,
  IntelligenceHistoryEntry,
  IntelligenceInputs,
  IntelligenceReport,
  NutrientSignal,
  Paginated,
  SatelliteSignal,
} from '../types';
import {
  assessRisk,
  computeHealth,
  detectIssues,
  generateRecommendations,
} from './intelligenceEngine';
import { IntelligenceError, type IntelligenceProvider } from './intelligenceProvider';
import { intelligenceStorage } from './intelligenceStorage';

/**
 * Local, offline Crop Intelligence provider. On refresh it aggregates whatever the
 * sibling module stores (Nutrient, Satellite) hold in MMKV — each read is **guarded**,
 * exactly like the backend sources, so one missing module simply lowers confidence and
 * is never fabricated. The client engine mirror then produces the same health score,
 * risk and generic recommendations as the backend. Reports are flagged ``isSample`` so
 * a locally-derived assessment is never mistaken for a verified one.
 */
function guard<T>(name: string, fn: () => T): T | null {
  try {
    return fn();
  } catch (err) {
    logger.warn('intelligence', `local source '${name}' failed; skipping`, err);
    return null;
  }
}

function readNutrient(farmId: string): NutrientSignal | null {
  const report = nutrientStorage.localReports(farmId)[0];
  const a = report?.analysis;
  if (!a) return null;
  return {
    primary: a.primaryDeficiency,
    status: a.status,
    confidence: a.confidence,
    severity: a.severity,
    needsTest: a.needsTest,
  };
}

function readSatellite(farmId: string): SatelliteSignal | null {
  const session = satelliteStorage
    .localSessions(farmId)
    .find((s) => s.status === 'available');
  if (!session) return null;
  return {
    ndvi: session.ndvi,
    vegetationHealth: session.vegetationHealth,
    stressLevel: session.stressLevel,
    moistureStatus: session.moistureStatus,
    trend: session.trend,
    confidence: session.confidence,
    alertCodes: session.alerts.map((al) => al.code),
  };
}

function gather(farmId: string): IntelligenceInputs {
  return {
    nutrient: guard('nutrient', () => readNutrient(farmId)),
    satellite: guard('satellite', () => readSatellite(farmId)),
    calendar: { today: 0, upcoming: 0, missed: 0 },
    expert: { openConsultation: false },
  };
}

function buildReport(farmId: string): IntelligenceReport {
  const inputs = gather(farmId);
  const health = computeHealth(inputs);
  const issues = detectIssues(inputs, health);
  const risk = assessRisk(inputs, health, issues);
  const recs = generateRecommendations(inputs, health, issues, risk);
  const now = new Date().toISOString();

  return {
    id: uuid(),
    farmId,
    crop: null,
    generatedAt: now,
    overallHealthScore: health.overallHealthScore,
    confidence: health.confidence,
    overallRisk: risk,
    riskScore: health.overallHealthScore !== null ? 100 - health.overallHealthScore : null,
    sourcesUsed: health.sourcesUsed,
    health: {
      overallHealthScore: health.overallHealthScore,
      confidence: health.confidence,
      diseaseScore: health.diseaseScore,
      nutrientScore: health.nutrientScore,
      soilScore: health.soilScore,
      satelliteScore: health.satelliteScore,
      weatherScore: health.weatherScore,
      growthScore: health.growthScore,
    },
    priorityIssues: issues,
    recommendations: recs,
    createdAt: now,
    isSample: true,
  };
}

export const localIntelligenceProvider: IntelligenceProvider = {
  async refresh(farmId: string): Promise<IntelligenceReport> {
    const report = buildReport(farmId);
    intelligenceStorage.addLocalReport(farmId, report);
    return report;
  },

  async dashboard(farmId: string): Promise<IntelligenceDashboard> {
    const report = intelligenceStorage.localReports(farmId)[0] ?? null;
    return {
      farmId,
      hasData: report !== null,
      messageCode: report ? null : 'intelligence.status.no_report',
      report,
    };
  },

  async latest(farmId: string): Promise<IntelligenceReport> {
    const report = intelligenceStorage.localReports(farmId)[0];
    if (!report) throw new IntelligenceError('unavailable', 'No intelligence report yet');
    return report;
  },

  async history(
    farmId: string,
    page = 1,
    pageSize = DEFAULT_PAGE_SIZE,
  ): Promise<Paginated<IntelligenceHistoryEntry>> {
    const rows: IntelligenceHistoryEntry[] = intelligenceStorage
      .localReports(farmId)
      .map((r) => ({
        id: r.id,
        farmId: r.farmId,
        reportId: r.id,
        overallHealthScore: r.overallHealthScore,
        overallRisk: r.overallRisk,
        confidence: r.confidence,
        recordedAt: r.createdAt,
      }));
    const start = (page - 1) * pageSize;
    return {
      items: rows.slice(start, start + pageSize),
      page,
      pageSize,
      total: rows.length,
      totalPages: Math.max(1, Math.ceil(rows.length / pageSize)),
    };
  },

  async getReport(id: string): Promise<IntelligenceReport> {
    const report = intelligenceStorage.getLocalReport(id);
    if (!report) throw new IntelligenceError('not_found', 'Report not found');
    return report;
  },
};
