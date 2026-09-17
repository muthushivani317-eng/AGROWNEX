import {
  apiToDashboard,
  apiToHistoryEntry,
  apiToReport,
} from '../services/intelligenceMapper';
import type {
  ApiIntelligenceDashboard,
  ApiIntelligenceHistoryEntry,
  ApiIntelligenceReport,
} from '../types';

const apiReport: ApiIntelligenceReport = {
  id: 'r1',
  farm_id: 'f1',
  crop: 'paddy',
  generated_at: '2026-07-12T06:00:00Z',
  overall_health_score: 72,
  confidence: 64,
  overall_risk: 'high',
  risk_score: 28,
  sources_used: ['disease', 'weather'],
  health: {
    overall_health_score: 72,
    confidence: 64,
    disease_score: 40,
    nutrient_score: null,
    soil_score: null,
    satellite_score: null,
    weather_score: 92,
    growth_score: null,
  },
  priority_issues: [
    { code: 'intelligence.issue.disease_active', severity: 'critical', modules: ['disease'] },
  ],
  recommendations: [
    { code: 'intelligence.rec.treat_disease', priority: 'high', category: 'treatment', modules: ['disease'] },
  ],
  created_at: '2026-07-12T06:00:01Z',
};

describe('intelligenceMapper', () => {
  it('fails closed for legacy reports aggregated from one source', () => {
    const legacy = apiToReport({ ...apiReport, sources_used: ['disease'] });
    expect(legacy.overallHealthScore).toBeNull();
    expect(legacy.riskScore).toBeNull();
    expect(legacy.health?.overallHealthScore).toBeNull();
    expect(legacy.health?.diseaseScore).not.toBeNull();
  });
  it('maps a report envelope to the domain shape (snake → camel)', () => {
    const r = apiToReport(apiReport);
    expect(r.farmId).toBe('f1');
    expect(r.overallHealthScore).toBe(72);
    expect(r.overallRisk).toBe('high');
    expect(r.riskScore).toBe(28);
    expect(r.sourcesUsed).toEqual(['disease', 'weather']);
    expect(r.health?.diseaseScore).toBe(40);
    // Absent modules stay null — never fabricated.
    expect(r.health?.soilScore).toBeNull();
    expect(r.priorityIssues[0].code).toBe('intelligence.issue.disease_active');
    expect(r.recommendations[0].priority).toBe('high');
    expect(r.isSample).toBe(false);
  });

  it('maps a null health block', () => {
    const r = apiToReport({ ...apiReport, health: null });
    expect(r.health).toBeNull();
  });

  it('maps a dashboard with and without a report', () => {
    const withData: ApiIntelligenceDashboard = {
      farm_id: 'f1',
      has_data: true,
      message_code: null,
      report: apiReport,
    };
    const mapped = apiToDashboard(withData);
    expect(mapped.hasData).toBe(true);
    expect(mapped.report?.id).toBe('r1');

    const empty: ApiIntelligenceDashboard = {
      farm_id: 'f1',
      has_data: false,
      message_code: 'intelligence.status.no_report',
      report: null,
    };
    const mappedEmpty = apiToDashboard(empty);
    expect(mappedEmpty.hasData).toBe(false);
    expect(mappedEmpty.report).toBeNull();
    expect(mappedEmpty.messageCode).toBe('intelligence.status.no_report');
  });

  it('maps a history entry', () => {
    const dto: ApiIntelligenceHistoryEntry = {
      id: 'h1',
      farm_id: 'f1',
      report_id: 'r1',
      overall_health_score: 72,
      overall_risk: 'high',
      confidence: 64,
      recorded_at: '2026-07-12T06:00:00Z',
    };
    const h = apiToHistoryEntry(dto);
    expect(h.reportId).toBe('r1');
    expect(h.overallHealthScore).toBe(72);
    expect(h.overallRisk).toBe('high');
    expect(h.recordedAt).toBe('2026-07-12T06:00:00Z');
  });
});
