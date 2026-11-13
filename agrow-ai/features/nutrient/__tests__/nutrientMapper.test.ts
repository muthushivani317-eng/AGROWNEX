import {
  apiToAnalysis,
  apiToHistoryEntry,
  apiToRecommendation,
  apiToReport,
} from '../services/nutrientMapper';
import type {
  ApiNutrientAnalysis,
  ApiNutrientHistoryEntry,
  ApiNutrientReport,
} from '../types';

const apiAnalysis: ApiNutrientAnalysis = {
  primary_deficiency: 'nitrogen',
  secondary_deficiency: null,
  status: 'possible',
  confidence: 68,
  severity: 'moderate',
  affected_area: 'widespread',
  disease_conflict: false,
  needs_test: true,
  needs_expert: false,
  soil_reference: { has_data: true },
  satellite_reference: null,
  weather_reference: null,
  explanation_tamil: 'ta',
  explanation_english: 'en',
};

const apiReport: ApiNutrientReport = {
  id: 'r1',
  farm_id: 'f1',
  crop: 'paddy',
  image_url: 'https://r2/leaf.jpg',
  thumbnail_url: null,
  capture_date: '2026-07-12',
  provider: 'gemini',
  model_used: 'gemini-x',
  status: 'analyzed',
  language: 'ta',
  latitude: 10.7,
  longitude: 79.1,
  weather_snapshot: null,
  analysis: apiAnalysis,
  symptoms: ['yellowing', 'older_leaf_first'],
  recommendations: [
    {
      category: 'nutrient',
      code: 'nutrient.rec.nitrogen.deficiency',
      nutrient: 'nitrogen',
      severity: 'warning',
      priority: 'medium',
    },
  ],
  created_at: '2026-07-12T06:00:00Z',
};

describe('nutrientMapper', () => {
  it('maps a report envelope to the camelCase domain shape', () => {
    const r = apiToReport(apiReport);
    expect(r.farmId).toBe('f1');
    expect(r.imageUrl).toBe('https://r2/leaf.jpg');
    expect(r.language).toBe('ta');
    expect(r.symptoms).toEqual(['yellowing', 'older_leaf_first']);
    expect(r.recommendations[0].code).toBe('nutrient.rec.nitrogen.deficiency');
    expect(r.analysis?.primaryDeficiency).toBe('nitrogen');
    expect(r.analysis?.needsTest).toBe(true);
  });

  it('preserves honest nulls (never fabricated)', () => {
    const r = apiToReport({
      ...apiReport,
      analysis: { ...apiAnalysis, primary_deficiency: null, status: 'not_confirmed' },
      symptoms: [],
      recommendations: [],
    });
    expect(r.analysis?.primaryDeficiency).toBeNull();
    expect(r.analysis?.status).toBe('not_confirmed');
    expect(r.symptoms).toEqual([]);
    expect(r.recommendations).toEqual([]);
  });

  it('applies the Groundnut-specific safety gate to specific findings', () => {
    const r = apiToReport({
      ...apiReport,
      crop: 'Groundnut',
      analysis: {
        ...apiAnalysis,
        status: 'confirmed',
        confidence: 94,
        needs_test: false,
        needs_expert: false,
        result_code: 'supported_finding',
        expert_verified: true,
      },
      recommendations: [
        ...apiReport.recommendations,
        { category: 'test', code: 'nutrient.rec.test.soil_test', nutrient: null, severity: 'warning', priority: 'medium' },
        { category: 'expert', code: 'nutrient.rec.expert.consult', nutrient: null, severity: 'warning', priority: 'medium' },
      ],
    });

    expect(r.analysis).toMatchObject({
      status: 'possible',
      confidence: null,
      confidenceBand: null,
      needsTest: true,
      needsExpert: true,
      expertVerified: false,
    });
    expect(r.recommendations.map((item) => item.category)).toEqual(['test', 'expert']);
  });

  it('does not change the same specific result for another crop', () => {
    const r = apiToReport({
      ...apiReport,
      crop: 'paddy',
      analysis: { ...apiAnalysis, confidence: 94 },
    });
    expect(r.analysis?.confidence).toBe(94);
    expect(r.analysis?.confidenceBand).toBe('low');
    expect(r.recommendations[0].category).toBe('nutrient');
  });

  it('maps analysis and recommendation directly', () => {
    expect(apiToAnalysis(apiAnalysis).affectedArea).toBe('widespread');
    expect(
      apiToRecommendation({
        category: 'test',
        code: 'nutrient.rec.test.soil_test',
        nutrient: null,
        severity: 'warning',
        priority: 'medium',
      }).code,
    ).toBe('nutrient.rec.test.soil_test');
  });

  it('maps a history entry', () => {
    const h: ApiNutrientHistoryEntry = {
      id: 'h1',
      farm_id: 'f1',
      report_id: 'r1',
      crop: 'paddy',
      primary_deficiency: 'nitrogen',
      status: 'possible',
      confidence: 68,
      severity: 'moderate',
      recorded_at: '2026-07-12T06:00:00Z',
    };
    const entry = apiToHistoryEntry(h);
    expect(entry.reportId).toBe('r1');
    expect(entry.primaryDeficiency).toBe('nitrogen');
    expect(entry.recordedAt).toBe('2026-07-12T06:00:00Z');
  });
});
