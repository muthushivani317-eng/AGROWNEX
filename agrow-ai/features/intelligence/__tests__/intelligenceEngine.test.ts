import {
  assessRisk,
  computeHealth,
  detectIssues,
  generateRecommendations,
} from '../services/intelligenceEngine';
import type { IntelligenceInputs } from '../types';

function assess(inputs: IntelligenceInputs) {
  const health = computeHealth(inputs);
  const issues = detectIssues(inputs, health);
  const risk = assessRisk(inputs, health, issues);
  const recs = generateRecommendations(inputs, health, issues, risk);
  return { health, issues, risk, recs };
}

const codes = (arr: { code: string }[]) => arr.map((x) => x.code);

describe('intelligenceEngine — health scoring', () => {
  it('returns no data for empty inputs (never fabricated)', () => {
    const h = computeHealth({});
    expect(h.overallHealthScore).toBeNull();
    expect(h.confidence).toBe(0);
    expect(h.sourcesUsed).toEqual([]);
  });

  it('keeps a single module visible without claiming whole-farm health', () => {
    const h = computeHealth({ weather: { insightCodes: [] } });
    expect(h.weatherScore).toBe(92);
    expect(h.overallHealthScore).toBeNull();
    expect(h.sourcesUsed).toEqual(['weather']);
  });

  it('forms overall health from at least two independent modules', () => {
    const h = computeHealth({
      weather: { insightCodes: [] },
      growth: { healthScore: 80, healthDelta: 0, riskLevel: 'low' },
    });
    expect(h.overallHealthScore).not.toBeNull();
  });

  it('raises confidence as more modules are present', () => {
    const one = computeHealth({ weather: { insightCodes: [] } });
    const many = computeHealth({
      weather: { insightCodes: [] },
      disease: { disease: null, confidence: 80, severity: 'none' },
      growth: { healthScore: 80, healthDelta: 0, riskLevel: 'low' },
      soil: { hasData: true, nitrogen: 'high', phosphorus: 'high', potassium: 'high' },
    });
    expect(many.confidence).toBeGreaterThan(one.confidence);
    expect(many.sourcesUsed).toHaveLength(4);
  });

  it('leaves absent modules null, not invented', () => {
    const h = computeHealth({ weather: { insightCodes: [] } });
    expect(h.soilScore).toBeNull();
    expect(h.diseaseScore).toBeNull();
    expect(h.nutrientScore).toBeNull();
  });

  it('penalizes a severe disease and floors weather at 40', () => {
    expect(
      computeHealth({ disease: { disease: 'x', confidence: 90, severity: 'high' } }).diseaseScore,
    ).toBeLessThan(40);
    expect(
      computeHealth({
        weather: { insightCodes: ['heavy_rain.severe', 'heat_stress.extreme', 'wind.strong'] },
      }).weatherScore,
    ).toBeGreaterThanOrEqual(40);
  });
});

describe('intelligenceEngine — decision', () => {
  it('finds no issues and low risk with no data', () => {
    const { issues, risk } = assess({});
    expect(issues).toEqual([]);
    expect(risk).toBe('low');
  });

  it('forces critical for a confident, severe disease', () => {
    const { risk, issues } = assess({
      disease: { disease: 'blast', confidence: 90, severity: 'high' },
    });
    expect(risk).toBe('critical');
    expect(codes(issues)).toContain('intelligence.issue.disease_active');
  });

  it('flags soil salinity and low nitrogen', () => {
    const { issues } = assess({
      soil: { hasData: true, nitrogen: 'low', phosphorus: 'low', potassium: 'medium', salinity: 'high' },
    });
    expect(codes(issues)).toEqual(
      expect.arrayContaining([
        'intelligence.issue.soil_salinity',
        'intelligence.issue.soil_low_nitrogen',
      ]),
    );
  });

  it('sorts issues most-severe first', () => {
    const { issues } = assess({
      disease: { disease: 'blast', confidence: 90, severity: 'high' },
      calendar: { today: 0, upcoming: 0, missed: 1 },
    });
    expect(issues.length).toBeGreaterThan(1);
    expect(issues[0].severity).toBe('critical');
  });
});

describe('intelligenceEngine — recommendations', () => {
  it('only ever emits generic codes (no brands)', () => {
    const { recs } = assess({ disease: { disease: 'blast', confidence: 90, severity: 'high' } });
    expect(recs.length).toBeGreaterThan(0);
    expect(recs.every((r) => r.code.startsWith('intelligence.rec.'))).toBe(true);
  });

  it('treats a confident disease first', () => {
    const { recs } = assess({ disease: { disease: 'blast', confidence: 85, severity: 'high' } });
    expect(recs[0].code).toBe('intelligence.rec.treat_disease');
    expect(recs[0].priority).toBe('high');
  });

  it('prioritizes nitrogen when soil + leaf agree', () => {
    const { recs } = assess({
      soil: { hasData: true, nitrogen: 'low', phosphorus: 'medium', potassium: 'high' },
      nutrient: { primary: 'nitrogen', status: 'confirmed', confidence: 75, severity: 'moderate' },
    });
    expect(codes(recs)).toContain('intelligence.rec.address_nitrogen');
  });

  it('checks irrigation on vigour decline with healthy leaves', () => {
    const { recs } = assess({
      satellite: {
        ndvi: 0.3, vegetationHealth: 'low', stressLevel: 'moderate',
        moistureStatus: 'normal', trend: 'declining',
      },
    });
    expect(codes(recs)).toContain('intelligence.rec.check_irrigation');
  });

  it('asks for more data when confidence is low', () => {
    const { recs } = assess({
      soil: { hasData: true, nitrogen: 'high', phosphorus: 'high', potassium: 'high' },
    });
    expect(codes(recs)).toContain('intelligence.rec.gather_more_data');
  });

  it('consults an expert on high risk, or awaits an open one', () => {
    const closed = assess({
      disease: { disease: 'blast', confidence: 90, severity: 'high' },
      expert: { openConsultation: false },
    });
    expect(codes(closed.recs)).toContain('intelligence.rec.consult_expert');
    const open = assess({
      disease: { disease: 'blast', confidence: 90, severity: 'high' },
      expert: { openConsultation: true },
    });
    expect(codes(open.recs)).toContain('intelligence.rec.await_expert');
  });

  it('maintains the routine when healthy and quiet', () => {
    const { recs } = assess({
      weather: { insightCodes: [] },
      growth: { healthScore: 92, healthDelta: 1, riskLevel: 'low' },
      soil: { hasData: true, nitrogen: 'high', phosphorus: 'high', potassium: 'high' },
      satellite: {
        ndvi: 0.8, vegetationHealth: 'very_good', stressLevel: null,
        moistureStatus: 'normal', trend: 'stable',
      },
    });
    expect(codes(recs)).toContain('intelligence.rec.maintain');
  });

  it('caps at five recommendations, priority-ordered', () => {
    const { recs } = assess({
      disease: { disease: 'blast', confidence: 90, severity: 'high' },
      nutrient: { primary: 'nitrogen', status: 'confirmed', confidence: 80, severity: 'severe' },
      soil: { hasData: true, nitrogen: 'low', phosphorus: 'low', potassium: 'low', salinity: 'high' },
      satellite: {
        ndvi: 0.2, vegetationHealth: 'low', stressLevel: 'severe',
        moistureStatus: 'very_dry', trend: 'declining',
      },
      weather: { insightCodes: ['heavy_rain.severe'] },
      calendar: { today: 0, upcoming: 0, missed: 5 },
      expert: { openConsultation: false },
    });
    expect(recs.length).toBeLessThanOrEqual(5);
    const order = { high: 0, medium: 1, low: 2 } as const;
    const priorities = recs.map((r) => order[r.priority]);
    expect(priorities).toEqual([...priorities].sort((a, b) => a - b));
  });
});
